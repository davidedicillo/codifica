import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from conftest import agent, send, ORIGIN
from server.app import create_app


def test_durable_batches_ack_retry_and_restart(api, channel, settings):
    a, headers = agent(api, channel)
    for n in range(11):
        assert send(api, channel, body=str(n), mentions=[a["participant"]["id"]]).status_code == 200
    path = f"/api/v1/channels/{channel}/activity?wait=0"
    first = api.get(path, headers=headers).json()
    assert len(first["activities"]) == 10 and first["remainingUnread"] == 1
    assert api.get(path, headers=headers).json() == first
    with TestClient(create_app(settings), base_url=ORIGIN) as restarted:
        assert restarted.get(path, headers=headers).json() == first
        second = restarted.get(
            path + "&ackBatch=" + first["batchId"], headers=headers
        ).json()
        assert len(second["activities"]) == 1
        assert (
            restarted.get(
                path + "&ackBatch=" + first["batchId"], headers=headers
            ).json()
            == second
        )
        assert (
            restarted.get(
                path + "&ackBatch=" + second["batchId"], headers=headers
            ).json()["batchId"]
            is None
        )
        assert (
            restarted.get(
                path + "&ackBatch=" + second["batchId"], headers=headers
            ).json()["batchId"]
            is None
        )
        assert (
            restarted.get(
                path + "&ackBatch=" + first["batchId"], headers=headers
            ).status_code
            == 409
        )


@pytest.mark.asyncio
async def test_wait_wakeup_concurrent_poll_and_revocation(api, app, channel):
    a, headers = agent(api, channel)
    path = f"/api/v1/channels/{channel}/activity?wait=2"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ORIGIN, headers=headers
    ) as client:
        held = asyncio.create_task(client.get(path))
        await asyncio.sleep(0.05)
        assert (await client.get(path)).status_code == 429
        await asyncio.to_thread(send, api, channel, body="Wake", mentions=[a["participant"]["id"]])
        result = await held
        assert (
            result.status_code == 200
            and result.json()["activities"][0]["body"] == "Wake"
        )
        batch = result.json()["batchId"]
        held = asyncio.create_task(client.get(path + "&ackBatch=" + batch))
        await asyncio.sleep(0.05)
        await asyncio.to_thread(
            api.delete,
            f'/api/v1/channels/{channel}/participants/{a["participant"]["id"]}',
        )
        assert (await held).status_code in (401, 403)


@pytest.mark.asyncio
async def test_cancel_releases_poll_and_empty_ack_survives_new_message(
    api, app, channel
):
    a, headers = agent(api, channel)
    path = f"/api/v1/channels/{channel}/activity"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=ORIGIN, headers=headers
    ) as client:
        held = asyncio.create_task(client.get(path, params={"wait": 2}))
        await asyncio.sleep(0.05)
        held.cancel()
        with pytest.raises(asyncio.CancelledError):
            await held
        assert a["participant"]["id"] not in app.state.polls
        timeout = await client.get(path, params={"wait": 0.02})
        assert timeout.json() == {
            "batchId": None,
            "activities": [],
            "remainingUnread": 0,
        }
        await asyncio.to_thread(send, api, channel, body="One", mentions=[a["participant"]["id"]])
        first = (await client.get(path, params={"wait": 0})).json()
        assert (
            await client.get(path, params={"wait": 0, "ackBatch": first["batchId"]})
        ).json()["batchId"] is None
        await asyncio.to_thread(send, api, channel, body="Two", mentions=[a["participant"]["id"]])
        second = (
            await client.get(path, params={"wait": 0, "ackBatch": first["batchId"]})
        ).json()
        assert second["activities"][0]["body"] == "Two"
        assert (
            await client.get(path, params={"wait": 0, "ackBatch": first["batchId"]})
        ).json() == second


def test_doc_events_do_not_enter_agent_inbox(api, channel):
    from conftest import rid

    _, headers = agent(api, channel)
    doc = api.post(
        f"/api/v1/channels/{channel}/docs",
        json={"title": "Context", "body": "Shared", "requestId": rid()},
    ).json()
    assert (
        api.get(f"/api/v1/channels/{channel}/activity?wait=0", headers=headers).json()[
            "batchId"
        ]
        is None
    )
    events = api.get(f"/api/v1/channels/{channel}/events?wait=0").json()
    event = next(e for e in events["events"] if e["kind"] == "document")
    assert event["data"]["id"] == doc["id"] and "body" not in event["data"]
    assert (
        api.get(
            f'/api/v1/channels/{channel}/events?wait=0&afterSequence={events["nextSequence"]}'
        ).json()["events"]
        == []
    )
