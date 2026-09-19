import json
import time
from fastapi import APIRouter, Request, Query
from .common import reject, uid, stamp, encode, emit, replay, remember
from .identity import member
from .schemas import MessageCreate, Subscription
from .documents import resolve_refs

router = APIRouter()


def message_json(db, row):
    name = db.execute(
        "SELECT name FROM participants WHERE id=?", (row["sender_id"],)
    ).fetchone()[0]
    return dict(
        id=row["id"],
        rootMessageId=row["root_id"],
        sequence=row["sequence"],
        senderId=row["sender_id"],
        senderName=name,
        body=row["body"],
        mentions=json.loads(row["mentions"]),
        createdAt=row["created_at"],
        docRefs=json.loads(row["doc_refs"]),
    )


def root_exists(db, channel, root):
    if not db.execute(
        "SELECT 1 FROM messages WHERE id=? AND channel_id=? AND root_id IS NULL",
        (root, channel),
    ).fetchone():
        reject(
            400,
            "INVALID_ARGUMENT",
            "Thread must reference a root message in this channel",
        )


@router.get("/channels/{channel}/messages")
def history(
    channel: str,
    request: Request,
    rootMessageId: str | None = Query(default=None, min_length=1),
    afterSequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    with request.app.state.db.connect() as db:
        member(request, db, channel)
        if rootMessageId:
            root_exists(db, channel, rootMessageId)
        rows = db.execute(
            "SELECT * FROM messages WHERE channel_id=? AND root_id IS ? AND sequence>? ORDER BY sequence LIMIT ?",
            (channel, rootMessageId, afterSequence, limit),
        ).fetchall()
        return dict(
            messages=[message_json(db, row) for row in rows],
            nextSequence=rows[-1]["sequence"] if rows else afterSequence,
        )


@router.post("/channels/{channel}/messages")
def send(channel: str, payload: MessageCreate, request: Request):
    body = payload.model_dump(mode="json")
    with request.app.state.db.transaction() as db:
        person = member(request, db, channel, mutation=True, writable=True)
        prior = replay(db, person["id"], "message", body)
        if prior is not None:
            return prior
        if len(payload.body.encode()) > 16384:
            reject(400, "INVALID_ARGUMENT", "Message exceeds 16 KiB")
        if not payload.body.strip() and not payload.docRefs:
            reject(400, "INVALID_ARGUMENT", "Message is empty")
        count = db.execute(
            "SELECT COUNT(*) FROM messages WHERE sender_id=? AND sent_at>?",
            (person["id"], time.time() - 60),
        ).fetchone()[0]
        if count >= 60:
            reject(429, "RATE_LIMITED", "Send limit is 60 messages per minute")
        if payload.rootMessageId:
            root_exists(db, channel, payload.rootMessageId)
        active = {
            r["id"]
            for r in db.execute(
                "SELECT id FROM participants WHERE channel_id=? AND active=1",
                (channel,),
            )
        }
        if any(pid not in active for pid in payload.mentions):
            reject(
                400,
                "INVALID_ARGUMENT",
                "Mentions must refer to current channel participants",
            )
        refs = resolve_refs(db, channel, body["docRefs"])
        message_id = uid()
        sequence = emit(db, channel, "message", {})
        db.execute(
            "INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                message_id,
                channel,
                payload.rootMessageId,
                person["id"],
                sequence,
                payload.body,
                encode(list(dict.fromkeys(payload.mentions))),
                stamp(),
                time.time(),
                encode(refs),
            ),
        )
        root = payload.rootMessageId or message_id
        for pid in {person["id"], *payload.mentions}:
            db.execute(
                "INSERT OR IGNORE INTO thread_subscriptions VALUES (?,?)", (pid, root)
            )
        if payload.rootMessageId:
            recipients = {
                r[0]
                for r in db.execute(
                    "SELECT participant_id FROM thread_subscriptions WHERE root_id=?",
                    (root,),
                )
            } & active
        else:
            recipients = active
        for pid in recipients - {person["id"]}:
            db.execute(
                "INSERT INTO deliveries(participant_id,message_id,sequence) VALUES (?,?,?)",
                (pid, message_id, sequence),
            )
        result = message_json(
            db,
            db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone(),
        )
        db.execute(
            "UPDATE events SET data=? WHERE sequence=?", (encode(result), sequence)
        )
        remember(db, person["id"], "message", body, result)
        return result


@router.post("/channels/{channel}/threads/{root}/subscription")
def subscription(channel: str, root: str, payload: Subscription, request: Request):
    with request.app.state.db.transaction() as db:
        person = member(request, db, channel, mutation=True, writable=True)
        root_exists(db, channel, root)
        if payload.following:
            db.execute(
                "INSERT OR IGNORE INTO thread_subscriptions VALUES (?,?)",
                (person["id"], root),
            )
        else:
            db.execute(
                "DELETE FROM thread_subscriptions WHERE participant_id=? AND root_id=?",
                (person["id"], root),
            )
    return dict(following=payload.following)
