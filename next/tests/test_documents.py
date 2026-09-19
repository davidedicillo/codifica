from conftest import send, rid


def test_revisions_replay_conflict_and_pinned_reference(api, channel):
    path = f"/api/v1/channels/{channel}/docs"
    body = {"title": "Spec", "body": "first\nsecond\nthird", "requestId": rid()}
    doc = api.post(path, json=body).json()
    assert doc["revision"] == 1
    assert api.post(path, json=body).json() == doc
    message = send(
        api, channel, docRefs=[{"docId": doc["id"], "startLine": 2, "endLine": 3}]
    ).json()
    update = {
        "title": "New",
        "body": "updated",
        "expectedRevision": 1,
        "requestId": rid(),
    }
    assert api.patch(path + "/" + doc["id"], json=update).json()["revision"] == 2
    assert api.patch(path + "/" + doc["id"], json=update).json()["revision"] == 2
    conflict = api.patch(path + "/" + doc["id"], json={**update, "requestId": rid()})
    assert conflict.status_code == 409 and conflict.json()["currentRevision"] == 2
    assert message["docRefs"][0]["revision"] == 1
    read = api.get(path + "/" + doc["id"] + "?revision=1&startLine=2&endLine=3").json()
    assert read["body"] == "second\nthird"
    assert api.get(path + "/" + doc["id"] + "?startLine=9").status_code == 400
    assert (
        send(api, channel, docRefs=[{"docId": doc["id"], "revision": 99}]).status_code
        == 400
    )


def test_concurrent_revision_writers_use_separate_connections(api, channel):
    from concurrent.futures import ThreadPoolExecutor

    path = f"/api/v1/channels/{channel}/docs"
    doc = api.post(
        path, json={"title": "Spec", "body": "original", "requestId": rid()}
    ).json()
    bodies = [
        {"title": "Spec", "body": text, "expectedRevision": 1, "requestId": rid()}
        for text in ("alpha", "beta")
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda body: api.patch(path + "/" + doc["id"], json=body), bodies)
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert api.get(path + "/" + doc["id"]).json()["revision"] == 2
    assert api.get(path + "/" + doc["id"] + "?revision=1").json()["body"] == "original"


def test_document_isolation_and_reference_validation(api, channel):
    from conftest import agent

    other = api.post("/api/v1/channels", json={"name": "Private"}).json()["id"]
    doc = api.post(
        f"/api/v1/channels/{other}/docs",
        json={"title": "Private", "body": "secret", "requestId": rid()},
    ).json()
    _, headers = agent(api, channel)
    assert (
        api.get(
            f'/api/v1/channels/{other}/docs/{doc["id"]}', headers=headers
        ).status_code
        == 403
    )
    assert send(api, channel, docRefs=[{"docId": doc["id"]}]).status_code == 400
    assert api.get(f'/api/v1/channels/{channel}/docs/{doc["id"]}').status_code == 404
    assert api.get(f"/api/v1/channels/{channel}/messages").json()["messages"] == []
