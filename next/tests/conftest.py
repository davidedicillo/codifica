from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server.settings import Settings

ORIGIN = "http://127.0.0.1:8000"


def rid():
    return str(uuid4())


def login(client, email="owner@example.com"):
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "name": email.split("@")[0]},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200, response.text
    client.headers.update(
        {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrfToken"]}
    )
    return response.json()["user"]


@pytest.fixture
def settings(tmp_path):
    return Settings(
        database_path=str(tmp_path / "api.sqlite"),
        secret_key="test-only-secret-" * 4,
        origin=ORIGIN,
        dev_auth=True,
        pilot_emails=("owner@example.com", "other@example.com"),
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def api(app):
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 2345)) as client:
        login(client)
        yield client


@pytest.fixture
def channel(api):
    response = api.post("/api/v1/channels", json={"name": "Engineering"})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def invite(api, channel, kind="agent", email=None):
    r = api.post(
        f"/api/v1/channels/{channel}/invites", json={"kind": kind, "email": email}
    )
    assert r.status_code == 200, r.text
    return r.json()["url"].rsplit("/", 1)[-1]


def agent(api, channel, name="Agent"):
    secret = invite(api, channel)
    r = api.post(
        f"/api/v1/invites/{secret}/join",
        json={"name": name, "provider": "openai", "requestId": rid()},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data, {"Authorization": "Bearer " + data["token"]}


def send(api, channel, headers=None, **kwargs):
    return api.post(
        f"/api/v1/channels/{channel}/messages",
        headers=headers or {},
        json={
            "body": "Hello",
            "rootMessageId": None,
            "mentions": [],
            "requestId": rid(),
            **kwargs,
        },
    )
