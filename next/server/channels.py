import secrets
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from .common import uid, emit, reject, hash_secret
from .identity import (
    authenticate,
    member,
    public_participant,
    add_participant,
    normalized_email,
)
from .schemas import ChannelCreate, ChannelPatch, InviteCreate

router = APIRouter()


def channel_json(row, user):
    return dict(
        id=row["id"],
        name=row["name"],
        ownerId=row["owner_id"],
        role="owner" if row["owner_id"] == user else "member",
        archived=bool(row["archived"]),
    )


@router.get("/channels")
def channels(request: Request):
    with request.app.state.db.connect() as db:
        auth = authenticate(request, db, human=True)
        rows = db.execute(
            "SELECT c.* FROM channels c JOIN participants p ON p.channel_id=c.id WHERE p.user_id=? AND p.active=1 ORDER BY c.rowid",
            (auth.user_id,),
        ).fetchall()
        return dict(channels=[channel_json(row, auth.user_id) for row in rows])


@router.post("/channels")
def create_channel(payload: ChannelCreate, request: Request):
    with request.app.state.db.transaction() as db:
        auth = authenticate(request, db, mutation=True, human=True)
        if not payload.name.strip():
            reject(400, "INVALID_ARGUMENT", "Channel name is required")
        channel = uid()
        db.execute(
            "INSERT INTO channels VALUES (?,?,?,0)",
            (channel, payload.name.strip(), auth.user_id),
        )
        user = db.execute("SELECT * FROM users WHERE id=?", (auth.user_id,)).fetchone()
        add_participant(db, channel, user["name"], "human", user=auth.user_id)
        return channel_json(
            db.execute("SELECT * FROM channels WHERE id=?", (channel,)).fetchone(),
            auth.user_id,
        )


@router.patch("/channels/{channel}")
def update_channel(channel: str, payload: ChannelPatch, request: Request):
    with request.app.state.db.transaction() as db:
        person = member(request, db, channel, mutation=True, owner=True)
        values = payload.model_dump(exclude_unset=True)
        if not values or any(v is None for v in values.values()):
            reject(400, "INVALID_ARGUMENT", "Provide channel changes")
        if payload.ownerId is not None:
            if not db.execute(
                "SELECT 1 FROM participants WHERE channel_id=? AND user_id=? AND kind='human' AND active=1",
                (channel, payload.ownerId),
            ).fetchone():
                reject(400, "INVALID_ARGUMENT", "New owner must be a human member")
            db.execute(
                "UPDATE channels SET owner_id=? WHERE id=?", (payload.ownerId, channel)
            )
        if payload.name is not None:
            if not payload.name.strip():
                reject(400, "INVALID_ARGUMENT", "Channel name is required")
            db.execute(
                "UPDATE channels SET name=? WHERE id=?", (payload.name.strip(), channel)
            )
        if payload.archived is not None:
            db.execute(
                "UPDATE channels SET archived=? WHERE id=?", (payload.archived, channel)
            )
        result = channel_json(
            db.execute("SELECT * FROM channels WHERE id=?", (channel,)).fetchone(),
            person["user_id"],
        )
        emit(db, channel, "channel", result)
        return result


@router.get("/channels/{channel}/participants")
def participants(channel: str, request: Request):
    with request.app.state.db.connect() as db:
        member(request, db, channel)
        return dict(
            participants=[
                public_participant(p, request.app)
                for p in db.execute(
                    "SELECT * FROM participants WHERE channel_id=? AND active=1 ORDER BY rowid",
                    (channel,),
                )
            ]
        )


@router.post("/channels/{channel}/invites")
def invite(channel: str, payload: InviteCreate, request: Request):
    with request.app.state.db.transaction() as db:
        person = member(
            request,
            db,
            channel,
            mutation=True,
            human=True,
            owner=payload.kind == "human",
            writable=True,
        )
        if payload.kind == "human" and not payload.email:
            reject(400, "INVALID_ARGUMENT", "Human invitations require an email")
        email = normalized_email(payload.email) if payload.kind == "human" else None
        secret = secrets.token_urlsafe(32)
        identity = uid()
        expires = time.time() + 7 * 86400
        db.execute(
            "INSERT INTO invites VALUES (?,?,?,?,?,?,?,0,0)",
            (
                identity,
                channel,
                hash_secret(secret),
                payload.kind,
                email,
                person["id"],
                expires,
            ),
        )
    origin = request.app.state.settings.origin
    return dict(
        id=identity,
        url=origin + "/i/" + secret,
        instructionsUrl=origin + "/api/v1/invites/" + secret + "/instructions",
        expiresAt=datetime.fromtimestamp(expires, timezone.utc).isoformat(),
    )


@router.get("/channels/{channel}/invites")
def invites(channel: str, request: Request):
    with request.app.state.db.connect() as db:
        member(request, db, channel, owner=True)
        rows = db.execute(
            "SELECT * FROM invites WHERE channel_id=? ORDER BY rowid DESC", (channel,)
        ).fetchall()
        return dict(
            invites=[
                dict(
                    id=r["id"],
                    kind=r["kind"],
                    email=r["email"],
                    expiresAt=datetime.fromtimestamp(
                        r["expires"], timezone.utc
                    ).isoformat(),
                    used=bool(r["used"]),
                    revoked=bool(r["revoked"]),
                )
                for r in rows
            ]
        )


@router.delete("/channels/{channel}/invites/{invite_id}", status_code=204)
def revoke_invite(channel: str, invite_id: str, request: Request):
    with request.app.state.db.transaction() as db:
        member(request, db, channel, mutation=True, owner=True)
        if not db.execute(
            "UPDATE invites SET revoked=1 WHERE id=? AND channel_id=?",
            (invite_id, channel),
        ).rowcount:
            reject(404, "NOT_FOUND", "Invitation not found")


@router.delete("/channels/{channel}/participants/{pid}", status_code=204)
def remove_participant(channel: str, pid: str, request: Request):
    with request.app.state.db.transaction() as db:
        caller = member(request, db, channel, mutation=True, human=True, writable=True)
        target = db.execute(
            "SELECT * FROM participants WHERE id=? AND channel_id=? AND active=1",
            (pid, channel),
        ).fetchone()
        if not target:
            reject(404, "NOT_FOUND", "Participant not found")
        owner = db.execute(
            "SELECT owner_id FROM channels WHERE id=?", (channel,)
        ).fetchone()[0]
        if target["user_id"] == owner:
            reject(409, "CONFLICT", "Transfer ownership before leaving")
        if (
            caller["user_id"] != owner
            and caller["id"] != pid
            and not (target["kind"] == "agent" and target["invited_by"] == caller["id"])
        ):
            reject(
                403,
                "FORBIDDEN",
                "Only the owner or inviting member can remove this participant",
            )
        db.execute("UPDATE participants SET active=0 WHERE id=?", (pid,))
        if target["kind"] == "human":
            db.execute(
                "UPDATE participants SET active=0 WHERE invited_by=? AND kind='agent'",
                (pid,),
            )
        db.execute("UPDATE invites SET revoked=1 WHERE invited_by=? AND used=0", (pid,))
        emit(db, channel, "participants", dict(participantId=pid, removed=True))
