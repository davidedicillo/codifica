"""Single-use, browser-bound email codes. No codes or provider responses in logs."""
import hashlib
import hmac
import secrets
import time

import httpx
from fastapi import APIRouter, Request, Response
from pydantic import Field

from .common import hash_secret, reject
from .identity import normalized_email, sign_in
from .schemas import Model

router = APIRouter()


class EmailRequest(Model):
    email: str = Field(min_length=3, max_length=254)


class EmailVerify(Model):
    code: str = Field(pattern=r"^[0-9]{6}$")
    name: str = Field(min_length=1, max_length=100)


def boundary(request):
    config = request.app.state.settings
    if request.headers.get('origin') != config.origin:
        reject(403, 'FORBIDDEN', 'A same-origin request is required')
    if not config.sendgrid_api_key or not config.email_from:
        reject(503, 'UNAVAILABLE', 'Email sign-in is not configured')
    return config


def code_hash(config, challenge, code):
    return hmac.new(config.secret_key.encode(), f'{challenge}:{code}'.encode(), hashlib.sha256).hexdigest()


def admitted(db, config, email):
    return (email in config.pilot_emails
            or db.execute("SELECT 1 FROM users WHERE issuer='email' AND subject=?", (email,)).fetchone()
            or db.execute("SELECT 1 FROM invites i JOIN participants p ON p.id=i.invited_by JOIN channels c ON c.id=i.channel_id WHERE i.email=? AND i.kind='human' AND i.used=0 AND i.revoked=0 AND i.expires>? AND p.active=1 AND c.archived=0", (email, time.time())).fetchone())


@router.post('/auth/email/request')
async def request_code(payload: EmailRequest, request: Request, response: Response):
    config = boundary(request)
    email = normalized_email(payload.email)
    now = time.time()
    # Persistent limits cover restarts. This peer may be a shared reverse proxy;
    # do not present its coarse flood limit as a per-end-user IP limit.
    ip = request.client.host if request.client else 'unknown'
    buckets = [(f'cooldown:{email}', 60, 1), (f'email:{email}', 3600, 5),
               (f'peer:{ip}', 3600, 300)]
    limited = False
    with request.app.state.db.transaction() as db:
        allowed = bool(admitted(db, config, email))
        if allowed:
            buckets.append(('delivery', 3600, 100))
        db.execute('DELETE FROM email_limits WHERE started<?', (now - 3600,))
        db.execute('DELETE FROM email_codes WHERE expires<?', (now - 3600,))
        for key, window, maximum in buckets:
            key = hash_secret(key)
            row = db.execute('SELECT * FROM email_limits WHERE bucket=?', (key,)).fetchone()
            if row and now - row['started'] < window and row['count'] >= maximum:
                limited = True
        if not limited:
            for key, window, _ in buckets:
                key = hash_secret(key)
                row = db.execute('SELECT * FROM email_limits WHERE bucket=?', (key,)).fetchone()
                if not row or now - row['started'] >= window:
                    db.execute('INSERT OR REPLACE INTO email_limits VALUES (?,?,1)', (key, now))
                else:
                    db.execute('UPDATE email_limits SET count=count+1 WHERE bucket=?', (key,))
    if limited:
        reject(429, 'RATE_LIMITED', 'Please wait before requesting another code')
    challenge = secrets.token_urlsafe(32)
    code = f'{secrets.randbelow(1000000):06d}'
    if allowed:
        with request.app.state.db.transaction() as db:
            db.execute('UPDATE email_codes SET used=1 WHERE email=?', (email,))
            db.execute('INSERT INTO email_codes(challenge,email,code_hash,expires) VALUES (?,?,?,?)',
                       (hash_secret(challenge), email, code_hash(config, challenge, code), now + 600))
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                sent = await client.post('https://api.sendgrid.com/v3/mail/send',
                    headers={'Authorization': 'Bearer ' + config.sendgrid_api_key},
                    json={'personalizations': [{'to': [{'email': email}]}],
                          'from': {'email': config.email_from, 'name': 'Codifica'},
                          'subject': 'Your Codifica sign-in code',
                          'content': [{'type': 'text/plain', 'value': f'Your Codifica sign-in code is {code}.\n\nIt expires in 10 minutes and can be used once, in the browser where you requested it. If you did not request this code, ignore this email.'}],
                          'tracking_settings': {'click_tracking': {'enable': False, 'enable_text': False}, 'open_tracking': {'enable': False}}})
            if sent.status_code != 202:
                raise ValueError('Delivery rejected')
        except (httpx.HTTPError, ValueError):
            with request.app.state.db.transaction() as db:
                db.execute('UPDATE email_codes SET used=1 WHERE challenge=?', (hash_secret(challenge),))
            reject(503, 'UNAVAILABLE', 'Email could not be sent. Please try again later.')
    response.set_cookie('codifica_login', challenge, max_age=600, httponly=True,
                        secure=not config.dev_auth, samesite='strict', path='/api/v1/auth/email')
    return {'message': 'If this email has access, a sign-in code is on its way.'}


@router.post('/auth/email/verify')
def verify_code(payload: EmailVerify, request: Request, response: Response):
    config = boundary(request)
    challenge = request.cookies.get('codifica_login', '')
    valid = False
    email = ''
    with request.app.state.db.transaction() as db:
        row = db.execute('SELECT * FROM email_codes WHERE challenge=?', (hash_secret(challenge),)).fetchone()
        if row and not row['used'] and row['expires'] > time.time() and row['attempts'] < 5:
            db.execute('UPDATE email_codes SET attempts=attempts+1 WHERE challenge=?', (hash_secret(challenge),))
            valid = hmac.compare_digest(row['code_hash'], code_hash(config, challenge, payload.code))
            if valid:
                email = row['email']
                db.execute('UPDATE email_codes SET used=1 WHERE challenge=?', (hash_secret(challenge),))
    if not valid:
        reject(401, 'UNAUTHORIZED', 'Invalid or expired code. Request a new code and try again.')
    result = sign_in(request, response, 'email', email, email, payload.name.strip() or email.split('@')[0])
    response.delete_cookie('codifica_login', path='/api/v1/auth/email', secure=not config.dev_auth, httponly=True, samesite='strict')
    return result
