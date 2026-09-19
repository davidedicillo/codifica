import hmac
import ipaddress
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from .common import reject, hash_secret, digest, encode, uid, emit
from .schemas import Login, Join

router = APIRouter()


@dataclass
class Credential:
    user_id: str | None = None
    participant_id: str | None = None
    csrf: str | None = None


def authenticate(request, db, mutation=False, human=False):
    authorization = request.headers.get("authorization")
    if authorization:
        if not authorization.startswith("Bearer "):
            reject(401, "UNAUTHORIZED", "Use a bearer credential")
        row = db.execute(
            "SELECT * FROM participants WHERE token_hash=? AND active=1 AND kind='agent'",
            (hash_secret(authorization[7:]),),
        ).fetchone()
        if not row:
            reject(401, "UNAUTHORIZED", "Credential is invalid or revoked")
        if human:
            reject(403, "FORBIDDEN", "A human account is required")
        return Credential(participant_id=row["id"])
    token = request.cookies.get("codifica_session", "")
    row = db.execute(
        "SELECT * FROM sessions WHERE hash=? AND expires>?",
        (hash_secret(token), time.time()),
    ).fetchone()
    if not row:
        reject(401, "UNAUTHORIZED", "Sign in to continue")
    if mutation:
        if request.headers.get("origin") != request.app.state.settings.origin:
            reject(403, "FORBIDDEN", "A same-origin request is required")
        if not hmac.compare_digest(
            request.headers.get("x-csrf-token", ""), row["csrf"]
        ):
            reject(403, "FORBIDDEN", "Invalid CSRF token")
    return Credential(user_id=row["user_id"], csrf=row["csrf"])


def member(
    request, db, channel, mutation=False, human=False, owner=False, writable=False
):
    auth = authenticate(request, db, mutation, human or owner)
    if auth.user_id:
        row = db.execute(
            "SELECT * FROM participants WHERE channel_id=? AND user_id=? AND active=1",
            (channel, auth.user_id),
        ).fetchone()
    else:
        row = db.execute(
            "SELECT * FROM participants WHERE channel_id=? AND id=? AND active=1",
            (channel, auth.participant_id),
        ).fetchone()
    if not row:
        reject(403, "FORBIDDEN", "Channel membership is required")
    ch = db.execute("SELECT * FROM channels WHERE id=?", (channel,)).fetchone()
    if owner and ch["owner_id"] != row["user_id"]:
        reject(403, "FORBIDDEN", "Only the channel owner can do that")
    if writable and ch["archived"]:
        reject(403, "FORBIDDEN", "This channel is archived and read-only")
    db.execute(
        "UPDATE participants SET last_active=? WHERE id=?", (time.time(), row["id"])
    )
    return row


def public_participant(row, app):
    presence = (
        "waiting"
        if row["id"] in app.state.polls
        else ("recent" if time.time() - row["last_active"] < 90 else "offline")
    )
    return dict(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        provider=row["provider"],
        invitedBy=row["invited_by"],
        userId=row["user_id"],
        presence=presence,
    )


def add_participant(
    db, channel, name, kind, user=None, provider=None, invited_by=None, token=None
):
    if (
        db.execute(
            "SELECT COUNT(*) FROM participants WHERE channel_id=? AND active=1",
            (channel,),
        ).fetchone()[0]
        >= 20
    ):
        reject(409, "CONFLICT", "This channel has reached its 20 participant limit")
    pid = uid()
    db.execute(
        "INSERT INTO participants VALUES (?,?,?,?,?,?,?,?,1,?)",
        (
            pid,
            channel,
            user,
            name,
            kind,
            provider,
            invited_by,
            hash_secret(token) if token else None,
            time.time(),
        ),
    )
    db.execute("INSERT INTO activity_state(participant_id) VALUES (?)", (pid,))
    emit(db, channel, "participants", {"participantId": pid})
    return db.execute("SELECT * FROM participants WHERE id=?", (pid,)).fetchone()


def normalized_email(email):
    email = email.strip().lower()
    if (
        "@" not in email
        or email.startswith("@")
        or email.endswith("@")
        or any(c.isspace() for c in email)
    ):
        reject(400, "INVALID_ARGUMENT", "A valid email address is required")
    return email


def sign_in(request, response, issuer, subject, email, name):
    settings = request.app.state.settings
    email = normalized_email(email)
    with request.app.state.db.transaction() as db:
        user = db.execute(
            "SELECT * FROM users WHERE issuer=? AND subject=?", (issuer, subject)
        ).fetchone()
        if not user:
            invitation = db.execute(
                "SELECT 1 FROM invites i JOIN participants p ON p.id=i.invited_by JOIN channels c ON c.id=i.channel_id WHERE i.email=? AND i.kind='human' AND i.used=0 AND i.revoked=0 AND i.expires>? AND p.active=1 AND c.archived=0",
                (email, time.time()),
            ).fetchone()
            if email not in settings.pilot_emails and not invitation:
                reject(403, "FORBIDDEN", "This pilot is invitation-only")
            user_id = uid()
            db.execute(
                "INSERT INTO users VALUES (?,?,?,?,?)",
                (user_id, issuer, subject, email, name[:100]),
            )
        else:
            user_id = user["id"]
            db.execute(
                "UPDATE users SET email=?,name=? WHERE id=?",
                (email, name[:100], user_id),
            )
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO sessions VALUES (?,?,?,?)",
            (hash_secret(token), user_id, csrf, time.time() + settings.session_seconds),
        )
    response.set_cookie(
        "codifica_session",
        token,
        max_age=settings.session_seconds,
        httponly=True,
        secure=not settings.dev_auth,
        samesite="lax",
        path="/",
    )
    return dict(user=dict(id=user_id, name=name[:100], email=email), csrfToken=csrf)


@router.get("/auth/config")
def auth_config(request: Request):
    return dict(
        devAuth=request.app.state.settings.dev_auth, loginUrl="/api/v1/auth/login"
    )


@router.post("/auth/dev-login")
def dev_login(payload: Login, request: Request, response: Response):
    settings = request.app.state.settings
    try:
        loopback = ipaddress.ip_address(request.client.host).is_loopback
    except (ValueError, AttributeError):
        loopback = False
    if not settings.dev_auth or not loopback:
        reject(403, "FORBIDDEN", "Development sign-in is available only on loopback")
    if request.headers.get("origin") not in (None, settings.origin):
        reject(403, "FORBIDDEN", "A same-origin request is required")
    email = normalized_email(payload.email)
    return sign_in(
        request, response, "development", email, email, payload.name.strip() or email
    )


@router.get("/auth/login")
async def oidc_login(request: Request, invite: str | None = None):
    if not request.app.state.oauth:
        reject(503, "UNAVAILABLE", "OIDC is not configured")
    request.session.pop("return_invite", None)
    if invite:
        with request.app.state.db.connect() as db:
            invitation = get_invite(db, invite)
            if invitation["kind"] != "human":
                reject(
                    400,
                    "INVALID_ARGUMENT",
                    "Agent invitations use the HTTP registration endpoint",
                )
        request.session["return_invite"] = invite
    return await request.app.state.oauth.provider.authorize_redirect(
        request, request.app.state.settings.origin + "/api/v1/auth/callback"
    )


@router.get("/auth/callback")
async def oidc_callback(request: Request):
    if not request.app.state.oauth:
        reject(503, "UNAVAILABLE", "OIDC is not configured")
    try:
        token = await request.app.state.oauth.provider.authorize_access_token(request)
        info = token.get("userinfo")
        if (
            not info
            or info.get("email_verified") is not True
            or not info.get("sub")
            or not info.get("iss")
        ):
            reject(403, "FORBIDDEN", "The identity provider must verify your email")
    except Exception as error:
        from .common import APIError

        if isinstance(error, APIError):
            raise
        reject(401, "UNAUTHORIZED", "Sign-in could not be verified; please start again")
    destination = "/"
    invitation_secret = request.session.pop("return_invite", None)
    if invitation_secret:
        with request.app.state.db.connect() as db:
            invitation = get_invite(db, invitation_secret)
            if invitation["kind"] != "human" or invitation["email"] != normalized_email(
                info.get("email", "")
            ):
                reject(
                    403,
                    "FORBIDDEN",
                    "Sign in with the email address on this invitation",
                )
        destination = "/i/" + invitation_secret
    response = RedirectResponse(destination, status_code=303)
    sign_in(
        request,
        response,
        info["iss"],
        info["sub"],
        info.get("email", ""),
        info.get("name") or info.get("email", ""),
    )
    return response


@router.get("/me")
def me(request: Request):
    with request.app.state.db.connect() as db:
        auth = authenticate(request, db, human=True)
        user = db.execute("SELECT * FROM users WHERE id=?", (auth.user_id,)).fetchone()
        return dict(
            user=dict(id=user["id"], name=user["name"], email=user["email"]),
            csrfToken=auth.csrf,
        )


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    with request.app.state.db.transaction() as db:
        authenticate(request, db, mutation=True, human=True)
        db.execute(
            "DELETE FROM sessions WHERE hash=?",
            (hash_secret(request.cookies.get("codifica_session", "")),),
        )
    response.delete_cookie("codifica_session", path="/")


def get_invite(db, secret, allow_used=False, allow_expired=False):
    row = db.execute(
        "SELECT i.*,c.name AS channel_name,c.archived,p.active AS inviter_active FROM invites i JOIN channels c ON c.id=i.channel_id JOIN participants p ON p.id=i.invited_by WHERE secret_hash=?",
        (hash_secret(secret),),
    ).fetchone()
    if not row:
        reject(404, "NOT_FOUND", "Invitation not found")
    if row["revoked"] or not row["inviter_active"]:
        reject(403, "FORBIDDEN", "Invitation has been revoked")
    if row["expires"] <= time.time() and not allow_expired:
        reject(410, "EXPIRED", "Invitation has expired")
    if row["used"] and not allow_used:
        reject(409, "CONFLICT", "Invitation has already been used")
    return row


@router.get("/invites/{secret}")
def invite_info(secret: str, request: Request):
    with request.app.state.db.connect() as db:
        row = get_invite(db, secret, allow_used=True)
        return dict(
            channelName=row["channel_name"],
            kind=row["kind"],
            email=row["email"],
            expiresAt=datetime.fromtimestamp(row["expires"], timezone.utc).isoformat(),
        )


@router.post("/invites/{secret}/join")
def join(secret: str, payload: Join, request: Request):
    body = payload.model_dump(mode="json")
    with request.app.state.db.transaction() as db:
        invitation = get_invite(db, secret, allow_used=True, allow_expired=True)
        auth = (
            authenticate(request, db, mutation=True, human=True)
            if invitation["kind"] == "human"
            else None
        )
        if auth:
            user = db.execute(
                "SELECT * FROM users WHERE id=?", (auth.user_id,)
            ).fetchone()
            if user["email"] != invitation["email"]:
                reject(
                    403,
                    "FORBIDDEN",
                    "Sign in with the email address on this invitation",
                )
        prior = db.execute(
            "SELECT * FROM registrations WHERE invite_id=?", (invitation["id"],)
        ).fetchone()
        token = hmac.new(
            request.app.state.settings.secret_key.encode(),
            ("agent:" + invitation["id"] + ":" + body["requestId"]).encode(),
            "sha256",
        ).hexdigest()
        if prior:
            if prior["request_id"] != body["requestId"] or prior["digest"] != digest(
                body
            ):
                reject(
                    409,
                    "CONFLICT",
                    "Invitation has already been used with a different registration",
                )
            person = db.execute(
                "SELECT * FROM participants WHERE id=? AND active=1",
                (prior["participant_id"],),
            ).fetchone()
            if not person:
                reject(403, "FORBIDDEN", "Membership has been revoked")
            if auth and person["user_id"] != auth.user_id:
                reject(403, "FORBIDDEN", "Registration belongs to another account")
            result = json.loads(prior["response"])
            if invitation["kind"] == "agent":
                result["token"] = token
            return result
        if invitation["expires"] <= time.time():
            reject(410, "EXPIRED", "Invitation has expired")
        if invitation["archived"]:
            reject(403, "FORBIDDEN", "This channel is archived")
        if auth:
            person = db.execute(
                "SELECT * FROM participants WHERE channel_id=? AND user_id=? AND active=1",
                (invitation["channel_id"], auth.user_id),
            ).fetchone()
            if not person:
                person = add_participant(
                    db,
                    invitation["channel_id"],
                    user["name"],
                    "human",
                    user=auth.user_id,
                    invited_by=invitation["invited_by"],
                )
        else:
            if not payload.name or not payload.name.strip():
                reject(400, "INVALID_ARGUMENT", "Agent name is required")
            person = add_participant(
                db,
                invitation["channel_id"],
                payload.name.strip(),
                "agent",
                provider=payload.provider,
                invited_by=invitation["invited_by"],
                token=token,
            )
        result = dict(
            channelId=invitation["channel_id"],
            participant=public_participant(person, request.app),
        )
        if not auth:
            from .messages import message_json

            recent = db.execute(
                "SELECT * FROM messages WHERE channel_id=? AND root_id IS NULL ORDER BY sequence DESC LIMIT 20",
                (invitation["channel_id"],),
            ).fetchall()
            result["recentMessages"] = [message_json(db, m) for m in reversed(recent)]
        db.execute("UPDATE invites SET used=1 WHERE id=?", (invitation["id"],))
        db.execute(
            "INSERT INTO registrations VALUES (?,?,?,?,?)",
            (
                invitation["id"],
                body["requestId"],
                digest(body),
                person["id"],
                encode(result),
            ),
        )
        if not auth:
            result["token"] = token
    return result
