import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4


class APIError(Exception):
    def __init__(self, status, code, message, **extra):
        self.status, self.payload = status, dict(code=code, message=message, **extra)


def reject(status, code, message, **extra):
    raise APIError(status, code, message, **extra)


def uid():
    return str(uuid4())


def stamp():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def hash_secret(value):
    return hashlib.sha256(value.encode()).hexdigest()


def replay(db, pid, operation, payload):
    row = db.execute(
        "SELECT * FROM mutation_results WHERE participant_id=? AND operation=? AND request_id=?",
        (pid, operation, payload["requestId"]),
    ).fetchone()
    if row:
        if row["digest"] != digest(payload):
            reject(409, "CONFLICT", "Request ID already used with different content")
        return json.loads(row["response"])


def remember(db, pid, operation, payload, result):
    db.execute(
        "INSERT INTO mutation_results VALUES (?,?,?,?,?)",
        (pid, operation, payload["requestId"], digest(payload), encode(result)),
    )


def emit(db, channel, kind, data):
    return db.execute(
        "INSERT INTO events(channel_id,kind,data) VALUES (?,?,?)",
        (channel, kind, encode(data)),
    ).lastrowid
