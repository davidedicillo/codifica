import sqlite3
from dataclasses import replace
from fastapi.testclient import TestClient
from server.app import create_app
from conftest import ORIGIN, agent, send, invite, login, rid


def test_sqlite_backup_restore_preserves_credentials_batch_and_citations(
    api, settings, channel, tmp_path
):
    a, headers = agent(api, channel)
    doc = api.post(
        f"/api/v1/channels/{channel}/docs",
        json={"title": "Spec", "body": "Original", "requestId": rid()},
    ).json()
    message = send(api, channel, docRefs=[{"docId": doc["id"]}], mentions=[a["participant"]["id"]]).json()
    path = f"/api/v1/channels/{channel}/activity?wait=0"
    batch = api.get(path, headers=headers).json()
    backup = tmp_path / "restored.sqlite"
    with sqlite3.connect(settings.database_path) as source, sqlite3.connect(
        backup
    ) as destination:
        source.backup(destination)
    with TestClient(
        create_app(replace(settings, database_path=str(backup))), base_url=ORIGIN
    ) as restored:
        assert restored.get(path, headers=headers).json() == batch
        assert restored.get(
            f"/api/v1/channels/{channel}/messages", headers=headers
        ).json()["messages"] == [message]
        assert (
            restored.get(
                f'/api/v1/channels/{channel}/docs/{doc["id"]}?revision=1',
                headers=headers,
            ).json()
            == doc
        )


def test_new_human_full_history_and_agent_bootstrap_are_not_deliveries(
    api, app, channel
):
    roots = [send(api, channel, body=f"History {n}").json() for n in range(21)]
    doc = api.post(
        f"/api/v1/channels/{channel}/docs",
        json={"title": "Old doc", "body": "History", "requestId": rid()},
    ).json()
    api.patch(
        f'/api/v1/channels/{channel}/docs/{doc["id"]}',
        json={
            "title": "Updated",
            "body": "New",
            "expectedRevision": 1,
            "requestId": rid(),
        },
    )
    secret = invite(api, channel, "human", "guest@example.com")
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 4321)) as guest:
        login(guest, "guest@example.com")
        assert (
            guest.post(
                f"/api/v1/invites/{secret}/join", json={"requestId": rid()}
            ).status_code
            == 200
        )
        assert (
            guest.get(f"/api/v1/channels/{channel}/messages").json()["messages"]
            == roots
        )
        assert (
            guest.get(f'/api/v1/channels/{channel}/docs/{doc["id"]}?revision=1').json()
            == doc
        )
        joined, headers = agent(guest, channel)
        assert joined["recentMessages"] == roots[-20:]
        assert (
            guest.get(
                f"/api/v1/channels/{channel}/activity?wait=0", headers=headers
            ).json()["activities"]
            == []
        )
