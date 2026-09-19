import asyncio
import json
import time
from fastapi import APIRouter, Request, Query
from .common import uid, encode, reject
from .identity import member
from .messages import message_json

router = APIRouter()


def acquire(request, channel, ack):
    with request.app.state.db.transaction() as db:
        person = member(request, db, channel)
        pid = person["id"]
        state = db.execute(
            "SELECT * FROM activity_state WHERE participant_id=?", (pid,)
        ).fetchone()
        outstanding = state["outstanding"]
        if ack:
            if ack == outstanding:
                db.execute(
                    "UPDATE deliveries SET acknowledged=1 WHERE participant_id=? AND batch_id=?",
                    (pid, ack),
                )
                db.execute(
                    "UPDATE activity_state SET outstanding=NULL,last_ack=? WHERE participant_id=?",
                    (ack, pid),
                )
                outstanding = None
            elif ack != state["last_ack"]:
                reject(
                    409,
                    "CONFLICT",
                    "Unknown or obsolete acknowledgment; retry without ackBatch",
                )
        if outstanding:
            return json.loads(
                db.execute(
                    "SELECT response FROM activity_batches WHERE id=?", (outstanding,)
                ).fetchone()[0]
            )
        rows = db.execute(
            "SELECT m.* FROM deliveries d JOIN messages m ON m.id=d.message_id WHERE d.participant_id=? AND d.acknowledged=0 ORDER BY d.sequence LIMIT 10",
            (pid,),
        ).fetchall()
        if not rows:
            return dict(batchId=None, activities=[], remainingUnread=0)
        batch = uid()
        count = db.execute(
            "SELECT COUNT(*) FROM deliveries WHERE participant_id=? AND acknowledged=0",
            (pid,),
        ).fetchone()[0]
        result = dict(
            batchId=batch,
            activities=[message_json(db, r) for r in rows],
            remainingUnread=count - len(rows),
        )
        db.execute(
            "INSERT INTO activity_batches VALUES (?,?,?)", (batch, pid, encode(result))
        )
        db.execute(
            "UPDATE activity_state SET outstanding=? WHERE participant_id=?",
            (batch, pid),
        )
        for row in rows:
            db.execute(
                "UPDATE deliveries SET batch_id=? WHERE participant_id=? AND message_id=?",
                (batch, pid, row["id"]),
            )
        return result


@router.get("/channels/{channel}/activity")
async def activity(
    channel: str,
    request: Request,
    wait: float = Query(default=50, ge=0, le=50),
    ackBatch: str | None = None,
):
    with request.app.state.db.connect() as db:
        pid = member(request, db, channel)["id"]
    # No await between check and reservation: serialized on the one API event loop.
    if pid in request.app.state.polls:
        reject(429, "RATE_LIMITED", "Only one poll may be held per participant")
    request.app.state.polls.add(pid)
    deadline = time.monotonic() + wait
    try:
        while True:
            # Subscribe before the authoritative recheck; the DB is never held while sleeping.
            changed = asyncio.Event()
            request.app.state.listeners.add(changed)
            try:
                result = acquire(request, channel, ackBatch)
                if result["batchId"] or time.monotonic() >= deadline:
                    return result
                if await request.is_disconnected():
                    return result
                try:
                    await asyncio.wait_for(
                        changed.wait(),
                        timeout=min(1, max(0, deadline - time.monotonic())),
                    )
                except asyncio.TimeoutError:
                    pass
            finally:
                request.app.state.listeners.discard(changed)
    finally:
        request.app.state.polls.discard(pid)


@router.get("/channels/{channel}/events")
async def events(
    channel: str,
    request: Request,
    afterSequence: int = Query(default=0, ge=0),
    wait: float = Query(default=25, ge=0, le=25),
):
    deadline = time.monotonic() + wait
    while True:
        changed = asyncio.Event()
        request.app.state.listeners.add(changed)
        try:
            with request.app.state.db.connect() as db:
                member(request, db, channel)
                rows = db.execute(
                    "SELECT * FROM events WHERE channel_id=? AND sequence>? ORDER BY sequence LIMIT 100",
                    (channel, afterSequence),
                ).fetchall()
                result = dict(
                    events=[
                        dict(
                            sequence=r["sequence"],
                            kind=r["kind"],
                            data=json.loads(r["data"]),
                        )
                        for r in rows
                    ],
                    nextSequence=rows[-1]["sequence"] if rows else afterSequence,
                )
            if rows or time.monotonic() >= deadline or await request.is_disconnected():
                return result
            try:
                await asyncio.wait_for(
                    changed.wait(), timeout=min(1, max(0, deadline - time.monotonic()))
                )
            except asyncio.TimeoutError:
                pass
        finally:
            request.app.state.listeners.discard(changed)
