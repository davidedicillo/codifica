from fastapi.testclient import TestClient
from conftest import ORIGIN, agent, invite, login, rid, send


def test_generic_messages_remain_history_without_waking_agents(api, channel):
    a, headers = agent(api, channel)
    path = f"/api/v1/channels/{channel}"
    general = send(api, channel, body="Who's here?").json()
    assert api.get(path + "/activity?wait=0", headers=headers).json()["batchId"] is None
    assert api.get(path + "/messages", headers=headers).json()["messages"][0]["id"] == general["id"]
    addressed = send(api, channel, mentions=[a["participant"]["id"]]).json()
    assert [m["id"] for m in api.get(path + "/activity?wait=0", headers=headers).json()["activities"]] == [addressed["id"]]


def test_all_agent_mentions_human_followups_and_no_implicit_agent_loops(api, channel):
    a, ha = agent(api, channel, "Backend")
    b, hb = agent(api, channel, "Reviewer")
    path = f"/api/v1/channels/{channel}"
    activity = path + "/activity?wait=0"
    root = send(api, channel, mentions=[a["participant"]["id"], b["participant"]["id"]]).json()
    for headers in (ha, hb):
        batch = api.get(activity, headers=headers).json()
        assert [m["id"] for m in batch["activities"]] == [root["id"]]
        api.get(activity + "&ackBatch=" + batch["batchId"], headers=headers)
    send(api, channel, ha, rootMessageId=root["id"], body="My answer")
    assert api.get(activity, headers=hb).json()["batchId"] is None
    followup = send(api, channel, rootMessageId=root["id"], body="Tell me more").json()
    for headers in (ha, hb):
        batch = api.get(activity, headers=headers).json()
        assert [m["id"] for m in batch["activities"]] == [followup["id"]]
        api.get(activity + "&ackBatch=" + batch["batchId"], headers=headers)
    direct = send(api, channel, ha, rootMessageId=root["id"], mentions=[b["participant"]["id"]]).json()
    assert api.get(activity, headers=hb).json()["activities"][0]["id"] == direct["id"]


def test_agent_rename_preserves_identity_mentions_history_and_token(api, channel):
    a, headers = agent(api, channel, "Codex")
    pid = a["participant"]["id"]
    path = f"/api/v1/channels/{channel}"
    sent = send(api, channel, headers, body="Already here").json()
    changed = api.patch(path + f"/participants/{pid}", json={"name": "  Backend reviewer  "})
    assert changed.status_code == 200
    assert changed.json()["id"] == pid and changed.json()["name"] == "Backend reviewer"
    history = api.get(path + "/messages", headers=headers).json()["messages"]
    assert history[0]["id"] == sent["id"] and history[0]["senderName"] == "Backend reviewer"
    addressed = send(api, channel, mentions=[pid]).json()
    assert api.get(path + "/activity?wait=0", headers=headers).json()["activities"][0]["id"] == addressed["id"]
    assert any(e["kind"] == "participants" and e["data"].get("participantId") == pid
               for e in api.get(path + "/events?wait=0").json()["events"])


def test_only_owner_or_inviter_can_rename_active_agents(api, app, channel):
    owned, agent_headers = agent(api, channel)
    path = f"/api/v1/channels/{channel}/participants/"
    owned_path = path + owned["participant"]["id"]
    secret = invite(api, channel, "human", "guest@example.com")
    with TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 3456)) as guest:
        login(guest, "guest@example.com")
        human = guest.post(f"/api/v1/invites/{secret}/join", json={"requestId": rid()}).json()
        linked, _ = agent(guest, channel)
        linked_path = path + linked["participant"]["id"]
        assert guest.patch(owned_path, json={"name": "Hijacked"}).status_code == 403
        assert guest.patch(linked_path, json={"name": "My Claude"}).status_code == 200
        assert api.patch(linked_path, json={"name": "Reviewer"}).status_code == 200
        assert api.patch(path + human["participant"]["id"], json={"name": "Human"}).status_code == 400
    assert api.patch(owned_path, headers=agent_headers, json={"name": "Self"}).status_code == 403
    assert api.patch(owned_path, headers={"X-CSRF-Token": "bad"}, json={"name": "X"}).status_code == 403
    for name in ("", "   ", "x" * 101):
        assert api.patch(owned_path, json={"name": name}).status_code == 400
    other = api.post("/api/v1/channels", json={"name": "Elsewhere"}).json()["id"]
    assert api.patch(f"/api/v1/channels/{other}/participants/{owned['participant']['id']}", json={"name": "X"}).status_code == 404
    api.patch(f"/api/v1/channels/{channel}", json={"archived": True})
    assert api.patch(owned_path, json={"name": "Archived"}).status_code == 403
    api.patch(f"/api/v1/channels/{channel}", json={"archived": False})
    api.delete(owned_path)
    assert api.patch(owned_path, json={"name": "Removed"}).status_code == 404
