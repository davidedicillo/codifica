from conftest import agent, send, invite, rid


def test_rate_limit_and_successful_replay_does_not_count(api, channel):
    key = rid()
    first = send(api, channel, requestId=key).json()
    for _ in range(59):
        assert send(api, channel).status_code == 200
    limited = send(api, channel)
    assert limited.status_code == 429 and limited.headers["retry-after"] == "1"
    assert send(api, channel, requestId=key).json() == first


def test_participant_cap_cannot_be_bypassed_with_invites(api, channel):
    for _ in range(19):
        agent(api, channel)
    secret = invite(api, channel)
    response = api.post(
        f"/api/v1/invites/{secret}/join",
        json={"name": "Over limit", "requestId": rid()},
    )
    assert response.status_code == 409
    assert (
        len(api.get(f"/api/v1/channels/{channel}/participants").json()["participants"])
        == 20
    )


def test_document_byte_limit_and_count(api, channel):
    path = f"/api/v1/channels/{channel}/docs"
    assert (
        api.post(
            path, json={"title": "large", "body": "é" * 131073, "requestId": rid()}
        ).status_code
        == 400
    )
    for n in range(100):
        assert (
            api.post(
                path, json={"title": str(n), "body": "", "requestId": rid()}
            ).status_code
            == 200
        )
    assert (
        api.post(
            path, json={"title": "overflow", "body": "", "requestId": rid()}
        ).status_code
        == 409
    )
