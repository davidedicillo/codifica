from fastapi.testclient import TestClient
from conftest import ORIGIN, login, invite, agent, rid


def test_registration_replay_and_revocation(api, channel):
    secret = invite(api, channel)
    path = f"/api/v1/invites/{secret}/join"
    body = {"name": "Codex", "provider": "openai", "requestId": rid()}
    first = api.post(path, json=body)
    assert first.status_code == 200
    assert api.post(path, json=body).json() == first.json()
    assert api.post(path, json={**body, "name": "Changed"}).status_code == 409
    assert api.post(path, json={**body, "requestId": rid()}).status_code == 409
    pid = first.json()["participant"]["id"]
    assert (
        api.delete(f"/api/v1/channels/{channel}/participants/{pid}").status_code == 204
    )
    assert api.post(path, json=body).status_code == 403


def test_browser_csrf_and_cross_channel_agent(api, channel):
    data, headers = agent(api, channel)
    other = api.post("/api/v1/channels", json={"name": "Other"}).json()["id"]
    assert (
        api.get(f"/api/v1/channels/{other}/messages", headers=headers).status_code
        == 403
    )
    assert (
        api.post(
            f"/api/v1/channels/{channel}/invites",
            headers=headers,
            json={"kind": "agent"},
        ).status_code
        == 403
    )
    assert (
        api.post(
            "/api/v1/channels", headers={"X-CSRF-Token": "bad"}, json={"name": "Bad"}
        ).status_code
        == 403
    )
    assert (
        api.post(
            "/api/v1/channels",
            headers={"Origin": "https://evil.example"},
            json={"name": "Bad"},
        ).status_code
        == 403
    )


def test_human_email_invite_owner_transfer_and_cascade(api, app, channel):
    secret = invite(api, channel, "human", "guest@example.com")
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 3456)) as guest:
        user = login(guest, "guest@example.com")
        joined = guest.post(f"/api/v1/invites/{secret}/join", json={"requestId": rid()})
        assert joined.status_code == 200, joined.text
        assert (
            guest.post(
                f"/api/v1/channels/{channel}/invites",
                json={"kind": "human", "email": "x@example.com"},
            ).status_code
            == 403
        )
        linked, headers = agent(guest, channel)
        assert (
            api.patch(
                f"/api/v1/channels/{channel}", json={"ownerId": user["id"]}
            ).status_code
            == 200
        )
        assert (
            api.patch(
                f"/api/v1/channels/{channel}", json={"archived": True}
            ).status_code
            == 403
        )
        assert (
            guest.delete(
                f'/api/v1/channels/{channel}/participants/{joined.json()["participant"]["id"]}'
            ).status_code
            == 409
        )
        owner_id = api.get("/api/v1/me").json()["user"]["id"]
        guest.patch(f"/api/v1/channels/{channel}", json={"ownerId": owner_id})
        assert (
            guest.delete(
                f'/api/v1/channels/{channel}/participants/{joined.json()["participant"]["id"]}'
            ).status_code
            == 204
        )
        assert (
            api.get(f"/api/v1/channels/{channel}/messages", headers=headers).status_code
            == 401
        )


def test_dev_login_loopback_and_allowlist(app):
    with TestClient(app, base_url=ORIGIN, client=("192.0.2.5", 123)) as remote:
        assert (
            remote.post(
                "/api/v1/auth/dev-login",
                json={"email": "owner@example.com", "name": "O"},
            ).status_code
            == 403
        )
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 123)) as local:
        assert (
            local.post(
                "/api/v1/auth/dev-login",
                json={"email": "unknown@example.com", "name": "O"},
            ).status_code
            == 403
        )


def test_invite_expiry_revoke_spoof_and_wrong_human(api, app, channel):
    import time
    from server.common import hash_secret

    secret = invite(api, channel)
    path = f"/api/v1/invites/{secret}/join"
    assert (
        api.post(
            path, json={"name": "X", "kind": "human", "requestId": rid()}
        ).status_code
        == 400
    )
    with app.state.db.transaction() as db:
        db.execute(
            "UPDATE invites SET expires=? WHERE secret_hash=?",
            (time.time() - 1, hash_secret(secret)),
        )
    assert api.post(path, json={"name": "X", "requestId": rid()}).status_code == 410
    human = invite(api, channel, "human", "guest@example.com")
    assert (
        api.post(f"/api/v1/invites/{human}/join", json={"requestId": rid()}).status_code
        == 403
    )
    data = api.post(
        f"/api/v1/channels/{channel}/invites", json={"kind": "agent"}
    ).json()
    assert (
        api.delete(f'/api/v1/channels/{channel}/invites/{data["id"]}').status_code
        == 204
    )
    assert (
        api.get("/api/v1/invites/" + data["url"].rsplit("/", 1)[-1]).status_code == 403
    )


def test_logout_invalidates_session_and_no_bearer_query(api, channel):
    _, headers = agent(api, channel)
    token = headers["Authorization"][7:]
    assert api.post("/api/v1/auth/logout").status_code == 204
    assert api.get("/api/v1/me").status_code == 401
    assert (
        api.get(f"/api/v1/channels/{channel}/messages?token={token}").status_code == 401
    )
    assert (
        api.get(f"/api/v1/channels/{channel}/messages", headers=headers).status_code
        == 200
    )


def test_production_settings_fail_closed(settings):
    from dataclasses import replace
    import pytest
    from server.app import create_app

    for invalid in (
        replace(settings, secret_key="short"),
        replace(settings, dev_auth=False),
        replace(settings, origin="http://example.com"),
    ):
        with pytest.raises(ValueError):
            create_app(invalid)


def test_registration_recovery_survives_invitation_expiry(api, app, channel):
    from server.common import hash_secret

    secret = invite(api, channel)
    payload = {"name": "Recoverable", "requestId": rid()}
    path = f"/api/v1/invites/{secret}/join"
    original = api.post(path, json=payload)
    with app.state.db.transaction() as db:
        db.execute(
            "UPDATE invites SET expires=0 WHERE secret_hash=?", (hash_secret(secret),)
        )
    assert api.post(path, json=payload).json() == original.json()
