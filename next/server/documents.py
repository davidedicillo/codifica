from fastapi import APIRouter, Request, Query
from .identity import member
from .common import uid, stamp, reject, replay, remember, emit
from .schemas import DocCreate, DocPatch

router = APIRouter()


def image_metadata(db, doc_id):
    row = db.execute(
        "SELECT filename,media_type,size FROM document_images WHERE doc_id=?", (doc_id,)
    ).fetchone()
    return dict(kind="image", filename=row["filename"], mediaType=row["media_type"], size=row["size"]) if row else {}


def get_revision(db, channel, doc_id, revision=None, reference=False):
    doc = db.execute(
        "SELECT * FROM documents WHERE id=? AND channel_id=?", (doc_id, channel)
    ).fetchone()
    if not doc:
        reject(
            400 if reference else 404,
            "INVALID_ARGUMENT" if reference else "NOT_FOUND",
            "Document not found in this channel",
        )
    row = db.execute(
        "SELECT * FROM document_revisions WHERE doc_id=? AND revision=?",
        (doc_id, revision or doc["revision"]),
    ).fetchone()
    if not row:
        reject(
            400 if reference else 404,
            "INVALID_ARGUMENT" if reference else "NOT_FOUND",
            "Document revision not found",
        )
    return dict(
        id=doc_id,
        channelId=channel,
        title=row["title"],
        body=row["body"],
        revision=row["revision"],
        authorId=row["author_id"],
        updatedAt=row["updated_at"],
        **image_metadata(db, doc_id),
    )


def line_range(doc, start, end):
    if start is None and end is None:
        return doc
    if doc.get("kind") == "image":
        reject(400, "INVALID_ARGUMENT", "Images do not have line ranges")
    lines = doc["body"].split("\n")
    start = 1 if start is None else start
    end = len(lines) if end is None else end
    if start < 1 or end < start or end > len(lines):
        reject(400, "INVALID_ARGUMENT", "Line range is outside this revision")
    return {
        **doc,
        "body": "\n".join(lines[start - 1 : end]),
        "startLine": start,
        "endLine": end,
    }


def resolve_refs(db, channel, refs):
    result = []
    for ref in refs:
        doc = get_revision(
            db, channel, ref["docId"], ref.get("revision"), reference=True
        )
        selected = line_range(doc, ref.get("startLine"), ref.get("endLine"))
        resolved = dict(docId=doc["id"], revision=doc["revision"], title=doc["title"])
        resolved.update(image_metadata(db, doc["id"]))
        if "startLine" in selected:
            resolved.update(
                startLine=selected["startLine"], endLine=selected["endLine"]
            )
        result.append(resolved)
    return result


@router.get("/channels/{channel}/docs")
def list_docs(channel: str, request: Request):
    with request.app.state.db.connect() as db:
        member(request, db, channel)
        rows = db.execute(
            "SELECT d.id,r.title,d.revision,r.updated_at FROM documents d JOIN document_revisions r ON r.doc_id=d.id AND r.revision=d.revision WHERE channel_id=? ORDER BY r.updated_at DESC",
            (channel,),
        ).fetchall()
        return dict(
            documents=[
                dict(
                    id=r["id"],
                    title=r["title"],
                    revision=r["revision"],
                    updatedAt=r["updated_at"],
                    **image_metadata(db, r["id"]),
                )
                for r in rows
            ]
        )


@router.get("/channels/{channel}/docs/{doc_id}")
def read_doc(
    channel: str,
    doc_id: str,
    request: Request,
    revision: int | None = Query(default=None, ge=1),
    startLine: int | None = Query(default=None, ge=1),
    endLine: int | None = Query(default=None, ge=1),
):
    with request.app.state.db.connect() as db:
        member(request, db, channel)
        return line_range(
            get_revision(db, channel, doc_id, revision), startLine, endLine
        )


def write_doc(request, channel, payload, doc_id=None):
    body = payload.model_dump(mode="json")
    with request.app.state.db.transaction() as db:
        person = member(request, db, channel, mutation=True, writable=True)
        operation = "doc:" + doc_id if doc_id else "doc:create"
        prior = replay(db, person["id"], operation, body)
        if prior is not None:
            return prior
        if len(payload.body.encode()) > 262144:
            reject(400, "INVALID_ARGUMENT", "Document exceeds 256 KiB")
        if not payload.title.strip():
            reject(400, "INVALID_ARGUMENT", "Document title is required")
        if doc_id:
            current = get_revision(db, channel, doc_id)
            if current.get("kind") == "image":
                reject(400, "INVALID_ARGUMENT", "Images cannot be edited as Markdown")
            if current["revision"] != payload.expectedRevision:
                reject(
                    409,
                    "CONFLICT",
                    "This document has changed",
                    currentRevision=current["revision"],
                )
            revision = current["revision"] + 1
            db.execute("UPDATE documents SET revision=? WHERE id=?", (revision, doc_id))
        else:
            if (
                db.execute(
                    "SELECT COUNT(*) FROM documents WHERE channel_id=?", (channel,)
                ).fetchone()[0]
                >= 100
            ):
                reject(
                    409, "CONFLICT", "This channel has reached its 100 document limit"
                )
            doc_id, revision = uid(), 1
            db.execute(
                "INSERT INTO documents VALUES (?,?,?)", (doc_id, channel, revision)
            )
        updated = stamp()
        db.execute(
            "INSERT INTO document_revisions VALUES (?,?,?,?,?,?)",
            (
                doc_id,
                revision,
                payload.title.strip(),
                payload.body,
                person["id"],
                updated,
            ),
        )
        result = get_revision(db, channel, doc_id)
        emit(
            db,
            channel,
            "document",
            dict(
                id=doc_id, title=result["title"], revision=revision, updatedAt=updated
            ),
        )
        remember(db, person["id"], operation, body, result)
        return result


@router.post("/channels/{channel}/docs")
def create_doc(channel: str, payload: DocCreate, request: Request):
    return write_doc(request, channel, payload)


@router.patch("/channels/{channel}/docs/{doc_id}")
def update_doc(channel: str, doc_id: str, payload: DocPatch, request: Request):
    return write_doc(request, channel, payload, doc_id)
