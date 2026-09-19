from types import SimpleNamespace
from starlette.responses import RedirectResponse
from conftest import invite


class Provider:
    def __init__(self, email="guest@example.com", verified=True):
        self.email, self.verified = email, verified

    async def authorize_redirect(self, request, redirect_uri):
        return RedirectResponse("https://identity.example/authorize")

    async def authorize_access_token(self, request):
        # Boundary double only: real Authlib owns signed token/state validation.
        return {
            "userinfo": {
                "iss": "https://identity.example",
                "sub": "subject-1",
                "email": self.email,
                "email_verified": self.verified,
                "name": "Guest",
            }
        }


def test_production_session_cookie_and_subject_identity(settings):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from server.app import create_app

    production = replace(
        settings,
        dev_auth=False,
        origin="https://codifica.example",
        oidc_metadata_url="https://identity.example/.well-known/openid-configuration",
        oidc_client_id="client",
        oidc_client_secret="provider-secret",
    )
    app = create_app(production)
    provider = Provider("owner@example.com")
    app.state.oauth = SimpleNamespace(provider=provider)
    with TestClient(app, base_url="https://codifica.example") as client:
        result = client.get("/api/v1/auth/callback", follow_redirects=False)
        assert result.status_code == 303
        cookie = result.headers["set-cookie"]
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
        original = client.get("/api/v1/me").json()
        provider.email = "new-address@example.com"
        assert (
            client.get("/api/v1/auth/callback", follow_redirects=False).status_code
            == 303
        )
        updated = client.get("/api/v1/me").json()
        assert updated["user"]["id"] == original["user"]["id"]
        assert updated["user"]["email"] == "new-address@example.com"
        assert (
            client.post("/api/v1/channels", json={"name": "No CSRF"}).status_code == 403
        )
        assert (
            client.post(
                "/api/v1/auth/dev-login",
                json={"name": "X", "email": "owner@example.com"},
            ).status_code
            == 403
        )


def test_oidc_invitation_return_and_verified_email(api, app, channel):
    secret = invite(api, channel, "human", "guest@example.com")
    app.state.oauth = SimpleNamespace(provider=Provider())
    assert (
        api.get(
            "/api/v1/auth/login", params={"invite": secret}, follow_redirects=False
        ).status_code
        == 307
    )
    result = api.get("/api/v1/auth/callback", follow_redirects=False)
    assert result.status_code == 303
    assert result.headers["location"] == "/i/" + secret
    assert api.get("/api/v1/me").json()["user"]["email"] == "guest@example.com"


def test_oidc_rejects_unverified_and_unvalidated_redirect(api, app, channel):
    app.state.oauth = SimpleNamespace(provider=Provider("owner@example.com", False))
    assert api.get("/api/v1/auth/callback", follow_redirects=False).status_code == 403
    assert (
        api.get(
            "/api/v1/auth/login?invite=https://evil.example", follow_redirects=False
        ).status_code
        == 404
    )


def test_oidc_wrong_invite_email_cannot_issue_session(api, app, channel):
    secret = invite(api, channel, "human", "guest@example.com")
    app.state.oauth = SimpleNamespace(provider=Provider("other@example.com"))
    api.get("/api/v1/auth/login", params={"invite": secret}, follow_redirects=False)
    assert api.get("/api/v1/auth/callback", follow_redirects=False).status_code == 403
