"""Channel-private imports, using the same immutable document references as Markdown."""

import base64
import binascii
import io
import warnings
from pathlib import PurePosixPath
from urllib.parse import quote

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

from .common import emit, reject, remember, replay, stamp, uid
from .documents import get_revision
from .identity import member
from .schemas import DocUpload

router = APIRouter()
IMAGE_LIMIT = 5 * 1024 * 1024
FORMATS = {".png": ("PNG", "image/png"), ".jpg": ("JPEG", "image/jpeg"),
           ".jpeg": ("JPEG", "image/jpeg"), ".webp": ("WEBP", "image/webp")}


def decode_upload(payload):
    name = payload.filename
    if name != name.strip() or any(c in name for c in "/\\") or any(ord(c) < 32 or ord(c) == 127 for c in name):
        reject(400, "INVALID_ARGUMENT", "Use a plain filename without paths")
    suffix = PurePosixPath(name).suffix.lower()
    if suffix != ".md" and suffix not in FORMATS:
        reject(400, "INVALID_ARGUMENT", "Choose a .md, PNG, JPEG or WebP file")
    try:
        data = base64.b64decode(payload.data, validate=True)
    except (ValueError, binascii.Error):
        reject(400, "INVALID_ARGUMENT", "Invalid file encoding")
    limit = 262144 if suffix == ".md" else IMAGE_LIMIT
    if len(data) > limit:
        reject(413, "INVALID_ARGUMENT", "File exceeds 256 KiB for Markdown or 5 MiB for images")
    if suffix == ".md":
        try:
            body = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            reject(400, "INVALID_ARGUMENT", "Markdown must be UTF-8 text")
        if "\x00" in body:
            reject(400, "INVALID_ARGUMENT", "Markdown must be text")
        return data, body, None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as im:
                if im.format != FORMATS[suffix][0]:
                    reject(400, "INVALID_ARGUMENT", "Image format does not match its filename")
                if im.width * im.height > 16_000_000:
                    reject(400, "INVALID_ARGUMENT", "Images must be at most 16 million pixels")
                if getattr(im, "n_frames", 1) != 1:
                    reject(400, "INVALID_ARGUMENT", "Choose a still image")
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                im.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        reject(400, "INVALID_ARGUMENT", "The image is damaged or unsupported")
    return data, "", FORMATS[suffix][1]


@router.post("/channels/{channel}/docs/upload")
def upload_doc(channel: str, payload: DocUpload, request: Request):
    body = payload.model_dump(mode="json")
    # Check access before decoding or allocating image pixels.
    with request.app.state.db.connect() as db:
        person = member(request, db, channel, mutation=True, writable=True)
        prior = replay(db, person["id"], "doc:upload", body)
        if prior is not None:
            return prior
    data, markdown, media_type = decode_upload(payload)
    with request.app.state.db.transaction() as db:
        person = member(request, db, channel, mutation=True, writable=True)
        prior = replay(db, person["id"], "doc:upload", body)
        if prior is not None:
            return prior
        if db.execute("SELECT COUNT(*) FROM documents WHERE channel_id=?", (channel,)).fetchone()[0] >= 100:
            reject(409, "CONFLICT", "This channel has reached its 100 document limit")
        doc_id, updated = uid(), stamp()
        title = payload.filename if media_type else PurePosixPath(payload.filename).stem
        db.execute("INSERT INTO documents VALUES (?,?,?)", (doc_id, channel, 1))
        db.execute("INSERT INTO document_revisions VALUES (?,?,?,?,?,?)",
                   (doc_id, 1, title, markdown, person["id"], updated))
        if media_type:
            db.execute("INSERT INTO document_images VALUES (?,?,?,?,?)",
                       (doc_id, payload.filename, media_type, len(data), data))
        result = get_revision(db, channel, doc_id)
        emit(db, channel, "document", dict(id=doc_id, title=title, revision=1, updatedAt=updated))
        remember(db, person["id"], "doc:upload", body, result)
        return result


@router.get("/channels/{channel}/docs/{doc_id}/content")
def image_content(channel: str, doc_id: str, request: Request,
                  revision: int = Query(default=1, ge=1), download: bool = False):
    with request.app.state.db.connect() as db:
        member(request, db, channel)
        doc = get_revision(db, channel, doc_id, revision)
        if doc.get("kind") != "image":
            reject(404, "NOT_FOUND", "This document is not an image")
        row = db.execute("SELECT content FROM document_images WHERE doc_id=?", (doc_id,)).fetchone()
        disposition = "attachment" if download else "inline"
        return Response(bytes(row["content"]), media_type=doc["mediaType"], headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(doc['filename'], safe='')}",
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        })
