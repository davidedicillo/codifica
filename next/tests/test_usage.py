import json
from datetime import datetime, timezone, timedelta
from conftest import agent, invite, rid, send


def counts(app):
    with app.state.db.connect() as db:
        return dict(db.execute("SELECT event, COUNT(*) FROM usage_events GROUP BY event"))


def test_successes_count_once_and_private_content_is_absent(api, app, channel):
    secret = invite(api, channel)
    registration = {"name": "Secret Agent", "provider": "private", "requestId": rid()}
    first = api.post(f"/api/v1/invites/{secret}/join", json=registration)
    assert first.status_code == 200
    assert api.post(f"/api/v1/invites/{secret}/join", json=registration).status_code == 200
    headers = {"Authorization": "Bearer " + first.json()["token"]}
    request_id = rid()
    assert send(api, channel, requestId=request_id, body="private message").status_code == 200
    assert send(api, channel, requestId=request_id, body="private message").status_code == 200
    assert send(api, channel, headers=headers).status_code == 200
    body = {"title": "private title", "body": "private document", "requestId": rid()}
    path = f"/api/v1/channels/{channel}/docs"
    doc = api.post(path, json=body).json()
    assert api.post(path, json=body).status_code == 200
    assert api.patch(path + "/" + doc["id"], json={**body, "expectedRevision": 1, "requestId": rid()}).status_code == 200
    assert send(api, channel, body="").status_code == 400
    assert counts(app) == {"channel_created": 1, "agent_connected": 1, "message_sent": 2, "document_created": 1}
    with app.state.db.connect() as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM usage_events")]
    serialized = json.dumps(rows)
    for private in ("private", "Secret Agent", "owner@example.com", secret, first.json()["token"]):
        assert private not in serialized
    assert sorted(r["actor_kind"] for r in rows if r["event"] == "message_sent") == ["agent", "human"]


def test_active_accounts_deduplicate_and_require_human_csrf(api, app, channel):
    assert api.post("/api/v1/usage/active").status_code == 204
    assert api.post("/api/v1/usage/active").status_code == 204
    _, headers = agent(api, channel)
    assert api.post("/api/v1/usage/active", headers=headers).status_code == 403
    assert api.post("/api/v1/usage/active", headers={"X-CSRF-Token": "bad"}).status_code == 403
    with app.state.db.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM usage_active_days").fetchone()[0] == 1
    api.cookies.clear()
    assert api.post("/api/v1/usage/active").status_code == 401


def test_rollback_and_restart_do_not_create_extra_events(api, app, channel):
    from server.db import Database
    before = counts(app)
    with app.state.db.connect() as db:
        owner = db.execute("SELECT owner_id FROM channels LIMIT 1").fetchone()[0]
        db.execute("BEGIN")
        db.execute("INSERT INTO channels VALUES ('rollback','Secret',?,0)", (owner,))
        db.rollback()
    Database(app.state.db.path)
    assert counts(app) == before


def test_report_has_daily_and_period_unique_accounts(api, app, channel):
    from server.usage import report
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    api.post("/api/v1/usage/active")
    with app.state.db.connect() as db:
        user = db.execute("SELECT owner_id FROM channels LIMIT 1").fetchone()[0]
        db.execute("INSERT INTO usage_active_days VALUES (?,?)", (str(yesterday), user))
        result = report(db, yesterday, today + timedelta(days=1))
    assert result["period"]["active_accounts"] == 1
    assert result["period"]["channel_created"] == 1
    assert [r["active_accounts"] for r in result["daily"]] == [1, 1]
    assert result["current_totals"]["channels"] == 1
    assert "owner@example.com" not in json.dumps(result)


def test_ga_frame_policy_does_not_relax_app_policy(api):
    app_policy = api.get("/health").headers["content-security-policy"]
    frame = api.get("/analytics.html")
    assert "googletagmanager.com" not in app_policy
    assert "frame-src 'self'" in app_policy
    assert "https://www.googletagmanager.com" in frame.headers["content-security-policy"]
    assert frame.headers["x-frame-options"] == "SAMEORIGIN"
    assert frame.headers["referrer-policy"] == "no-referrer"
