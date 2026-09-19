import base64
import io

import pytest
from PIL import Image
from conftest import agent, rid, send
from server.db import Database


def image_bytes(format="PNG"):
    out = io.BytesIO()
    Image.new("RGB", (3, 2), "red").save(out, format=format)
    return out.getvalue()


def upload(api, channel, filename="notes.md", data=b"# Notes\nHello", request_id=None, headers=None):
    return api.post(f"/api/v1/channels/{channel}/docs/upload", headers=headers or {}, json={
        "filename": filename, "data": base64.b64encode(data).decode(), "requestId": request_id or rid(),
    })


def test_markdown_import_is_editable_and_replayable(api, channel):
    request_id = rid()
    first = upload(api, channel, request_id=request_id)
    assert first.status_code == 200, first.text
    doc = first.json()
    assert doc["body"] == "# Notes\nHello"
    assert doc["title"] == "notes"
    assert upload(api, channel, request_id=request_id).json() == doc
    assert upload(api, channel, data=b"different", request_id=request_id).status_code == 409
    path = f'/api/v1/channels/{channel}/docs/{doc["id"]}'
    assert api.patch(path, json={"title": "Notes", "body": "Edited", "expectedRevision": 1, "requestId": rid()}).json()["revision"] == 2
    assert api.get(path + "?revision=1").json()["body"] == "# Notes\nHello"


@pytest.mark.parametrize("format,extension,mime", [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg"), ("WEBP", "webp", "image/webp")])
def test_image_upload_reference_download_and_persistence(api, channel, format, extension, mime):
    data = image_bytes(format)
    request_id = rid()
    response = upload(api, channel, "photo." + extension, data, request_id)
    assert response.status_code == 200, response.text
    doc = response.json()
    assert doc["kind"] == "image"
    assert doc["mediaType"] == mime
    assert doc["size"] == len(data)
    assert upload(api, channel, "photo." + extension, data, request_id).json() == doc
    path = f'/api/v1/channels/{channel}/docs/{doc["id"]}'
    assert api.get(f"/api/v1/channels/{channel}/docs").json()["documents"][0]["kind"] == "image"
    message = send(api, channel, body="", docRefs=[{"docId": doc["id"]}]).json()
    assert message["docRefs"][0]["kind"] == "image"
    assert message["docRefs"][0]["revision"] == 1
    _, headers = agent(api, channel)
    api.app.state.db = Database(api.app.state.db.path)
    content = api.get(path + "/content?revision=1", headers=headers)
    assert content.content == data
    assert content.headers["content-type"] == mime
    assert "attachment" in api.get(path + "/content?download=true").headers["content-disposition"]
    assert "no-store" in content.headers["cache-control"]
    assert api.get(path + "/content?revision=2").status_code == 404
    assert api.get(path + "?startLine=1").status_code == 400
    assert api.patch(path, json={"title": "Oops", "body": "replace", "expectedRevision": 1, "requestId": rid()}).status_code == 400


@pytest.mark.parametrize("name,data", [
    ("bad.svg", b"<svg/>"), ("bad.pdf", b"%PDF"), ("bad.md", b"\xff"),
    ("fake.png", b"not an image"), ("wrong.jpg", image_bytes()),
    ("cut.png", image_bytes()[:40]), ("../escape.md", b"hi"),
    ("big.md", b"a" * (262144 + 1)), ("big.png", b"a" * (5 * 1024 * 1024 + 1)),
], ids=["svg", "pdf", "invalid-utf8", "fake", "mismatch", "truncated", "path", "large-markdown", "large-image"])
def test_rejects_invalid_uploads_without_creating_documents(api, channel, name, data):
    assert upload(api, channel, name, data).status_code in (400, 413)
    assert api.get(f"/api/v1/channels/{channel}/docs").json()["documents"] == []


def test_upload_and_content_enforce_membership_archive_and_csrf(api, channel):
    doc_response = upload(api, channel, "photo.png", image_bytes())
    assert doc_response.status_code == 200
    doc = doc_response.json()
    other = api.post("/api/v1/channels", json={"name": "Other"}).json()["id"]
    _, foreign = agent(api, other)
    path = f'/api/v1/channels/{channel}/docs/{doc["id"]}/content'
    assert api.get(path, headers=foreign).status_code == 403
    assert upload(api, channel, headers=foreign).status_code == 403
    assert api.get(f'/api/v1/channels/{other}/docs/{doc["id"]}/content').status_code == 404
    assert upload(api, channel, headers={"X-CSRF-Token": "bad"}).status_code == 403
    api.patch(f"/api/v1/channels/{channel}", json={"archived": True})
    assert upload(api, channel).status_code == 403
    assert api.get(path).status_code == 200


def test_upload_limits_encoding_and_pixel_count(api, channel):
    path = f"/api/v1/channels/{channel}/docs/upload"
    assert api.post(path, json={"filename": "a.md", "data": "%%%", "requestId": rid()}).status_code == 400
    out = io.BytesIO()
    Image.new("RGB", (4001, 4000)).save(out, format="PNG")
    assert upload(api, channel, "large-pixels.png", out.getvalue()).status_code == 400
    for i in range(100):
        assert upload(api, channel, f"{i}.md", b"").status_code == 200
    assert upload(api, channel).status_code == 409


def test_large_upload_transport_returns_readable_error(api, channel):
    response = api.post(f"/api/v1/channels/{channel}/docs/upload", content=b" " * (8 * 1024 * 1024 + 1), headers={"Content-Type": "application/json"})
    assert response.status_code == 413
