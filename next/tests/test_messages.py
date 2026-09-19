from conftest import agent, send, rid


def test_idempotency_routing_and_history(api, channel):
    a, ha = agent(api, channel, "A")
    b, hb = agent(api, channel, "B")
    c, hc = agent(api, channel, "C")
    key = rid()
    recipients = [b["participant"]["id"], c["participant"]["id"]]
    root = send(api, channel, ha, requestId=key, mentions=recipients).json()
    assert send(api, channel, ha, requestId=key, mentions=recipients).json() == root
    assert send(api, channel, ha, requestId=key, mentions=recipients, body="different").status_code == 409
    activity = f"/api/v1/channels/{channel}/activity?wait=0"
    assert api.get(activity, headers=ha).json()["activities"] == []
    batch = api.get(activity, headers=hb).json()
    api.get(activity + "&ackBatch=" + batch["batchId"], headers=hb)
    batch = api.get(activity, headers=hc).json()
    api.get(activity + "&ackBatch=" + batch["batchId"], headers=hc)
    reply = send(api, channel, hb, rootMessageId=root["id"], mentions=[a["participant"]["id"]]).json()
    assert [m["id"] for m in api.get(activity, headers=ha).json()["activities"]] == [
        reply["id"]
    ]
    assert api.get(activity, headers=hc).json()["activities"] == []
    mention = send(
        api, channel, ha, rootMessageId=root["id"], mentions=[c["participant"]["id"]]
    ).json()
    assert api.get(activity, headers=hc).json()["activities"][0]["id"] == mention["id"]
    roots = api.get(f"/api/v1/channels/{channel}/messages").json()["messages"]
    assert [m["id"] for m in roots] == [root["id"]]
    assert (
        len(
            api.get(
                f'/api/v1/channels/{channel}/messages?rootMessageId={root["id"]}'
            ).json()["messages"]
        )
        == 2
    )


def test_limits_foreign_references_archive(api, channel):
    assert send(api, channel, rootMessageId="").status_code == 400
    assert (
        api.get(f"/api/v1/channels/{channel}/messages?rootMessageId=").status_code
        == 400
    )
    other = api.post("/api/v1/channels", json={"name": "Elsewhere"}).json()["id"]
    root = send(api, other).json()
    assert send(api, channel, rootMessageId=root["id"]).status_code == 400
    assert send(api, channel, mentions=["missing"]).status_code == 400
    assert send(api, channel, body="é" * 8193).status_code == 400
    assert (
        api.patch(f"/api/v1/channels/{channel}", json={"archived": True}).status_code
        == 200
    )
    assert send(api, channel).status_code == 403
    assert api.get(f"/api/v1/channels/{channel}/messages").status_code == 200
