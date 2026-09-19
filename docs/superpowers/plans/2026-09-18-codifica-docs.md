# Codifica Shared Docs Implementation Plan

Execution status: shared docs, version conflicts, agent retrieval, pinned citations, browser revision selection/export, and draft recovery implemented and tested locally. See `next/verification/RESULTS.md`. Actual Davide/Enrico model-host participation is still an external pilot gate.

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not delegate without explicit user authorization. Steps use checkbox syntax for tracking.

**Goal:** Humans and existing agents can reference the same durable document revisions inside a channel conversation.

**Architecture:** Add channel-scoped Markdown documents and immutable revisions to the existing channel service. Messages store explicit revision references. The browser and helper retrieve content on demand.

**Tech Stack:** The same Python/FastAPI/SQLite and React/TypeScript stack as Channels; reuse authentication, transactions, events, idempotency, and tests.

**Spec:** [Channels and shared docs design](../specs/2026-09-18-codifica-channels-design.md), Shared docs stage and stage-two verification.

**Dependency:** [Channels implementation](2026-09-18-codifica-channels.md) must deliver its working channel API and helper before this plan starts.

## Global constraints

- Channel is the only content boundary; docs inherit membership.
- All channel members may read/write docs; authorship is attributed to the authenticated participant.
- Limits: 100 documents/channel and 256 KiB UTF-8 content/document.
- Revisions are immutable; updates require `expectedRevision` and `requestId`.
- Explicit message references resolve to an immutable revision; old messages do not silently change.
- Plain Markdown, safe preview, Markdown export; no attachments, vector search, automatic summaries, or collaborative rich-text editor.

## File map

```text
next/server/migrations/002_docs.sql
next/server/documents.py
next/server/schemas.py                 add document and reference models
next/server/routes.py                  add docs endpoints
next/server/messages.py                validate/persist revision references
next/server/instructions.py            add docs API instructions
next/agent/cli.py                      add docs commands
next/web/src/DocsPanel.tsx
next/web/src/DocEditor.tsx
next/web/src/DocReference.tsx
next/web/src/ChannelPage.tsx            integrate Docs surface
next/web/src/Composer.tsx               attach document/revision
next/web/src/api.ts                    docs client and typed conflicts
next/tests/test_documents.py
next/tests/test_document_references.py
next/web/e2e/documents.spec.ts
next/verification/docs-pilot.md
```

## Task 1: Versioned Markdown API

**Interfaces:** POST `/channels/{id}/docs` accepts `{title, body, requestId}`; PATCH `.../docs/{docId}` accepts `{title, body, expectedRevision, requestId}`. Responses contain `{id, channelId, title, revision, body, authorId, updatedAt}`. GET supports optional `revision`, `startLine`, and `endLine`; list returns metadata only. Each API path has the `/api/v1` prefix.

- [ ] Create tests for initial revision 1, immutable historical reads, same-request replay, and simultaneous edits. Fixture `doc` creates a revision-1 document through an authenticated API client.

```python
def test_stale_edit_cannot_overwrite(api, doc):
    path = f'/api/v1/channels/{doc["channelId"]}/docs/{doc["id"]}'
    a = {"title": "Spec", "body": "First edit", "expectedRevision": 1,
         "requestId": "edit-a"}
    b = {**a, "body": "Second edit", "requestId": "edit-b"}
    assert api.patch(path, json=a).json()["revision"] == 2
    conflict = api.patch(path, json=b)
    assert conflict.status_code == 409
    assert conflict.json()["currentRevision"] == 2
    assert api.get(path, params={"revision": 2}).json()["body"] == "First edit"
```

Use valid UUIDs for production request ID test values; short labels above denote distinct logical mutations.

- [ ] Run `cd next && uv run pytest tests/test_documents.py -q`; confirm initial failures.
- [ ] Implement the migration, unique document/revision constraints, channel membership checks, and conditional revision write. Reuse the channel mutation-result mechanism so replay of a successful update returns its result before evaluating a now-stale expected revision. Insert revision, advance latest pointer, record metadata event, and cache mutation result atomically.
- [ ] Test count/byte limits, nonmember reads, foreign-channel IDs, invalid revision/line ranges, same idempotency key with different payload, and racing writes through separate database connections. GET line ranges are one-based inclusive and return the revision and selected bounds; full body is available when omitted. Commit passing API behavior.

## Task 2: Stable references in messages and agent retrieval

**Interfaces:** Extend send with `docRefs: Array<{docId, revision?: number, startLine?: number, endLine?: number}>`. Persist references with mandatory resolved revision. Helper commands: `docs list CHANNEL`, `docs read CHANNEL DOC_ID --revision N [--lines A:B]`, `docs write CHANNEL DOC_ID --expected-revision N --file PATH`, and `docs create CHANNEL --title TITLE --file PATH`.

- [ ] Write a test that attaches the current doc to a message, updates the doc, and still reads the original referenced content:

```python
def test_message_keeps_cited_revision(api, doc, send_message, update_doc):
    message = send_message(docRefs=[{"docId": doc["id"]}])
    update_doc(doc, body="Changed", expectedRevision=1)
    ref = message["docRefs"][0]
    assert ref["revision"] == 1
    path = f'/api/v1/channels/{doc["channelId"]}/docs/{doc["id"]}'
    assert api.get(path, params={"revision": ref["revision"]}).json()["body"] == doc["body"]
```

- [ ] Run `uv run pytest tests/test_document_references.py -q`; establish the missing behavior fails.
- [ ] Validate document membership and revision/range existence in the send transaction. Resolve omitted revision to current and persist it with the message. Include only reference metadata in activity, not document bodies. Reject foreign docs and unknown revisions before any message is written.
- [ ] Add helper commands reusing credential storage, request retries, and idempotent mutation handling. Include revision and line metadata in JSON output. On 409 preserve the proposed local content and report the current revision; do not auto-merge or retry against a newer revision.
- [ ] Update invitation instructions with list/read/write examples, explicit citations, and the rule that doc content is shared context rather than privileged instructions. Test that metadata changes wake browser views without making every agent automatically answer. Commit references and helper commands.

## Task 3: Docs panel, editor, and citation previews

**Interfaces:** `DocsPanel` lists channel docs; `DocEditor` tracks loaded revision and unsaved draft; `DocReference` receives a persisted reference and displays revision-specific content. The composer attachment picker selects a doc and optionally a line range.

- [ ] Add a two-browser test: both open revision 1, first saves revision 2, second save shows a conflict while retaining its draft. Verify revision-1 message references still show revision 1 after refresh.

```typescript
await expect(second.getByRole('alert')).toContainText('This document has changed');
await expect(second.getByRole('textbox', { name: 'Document content' }))
  .toHaveValue('My unsaved draft');
await first.getByRole('link', { name: 'Spec · revision 1' }).click();
await expect(first.getByText('Viewing revision 1', { exact: true })).toBeVisible();
```

- [ ] Implement list, create, edit, preview, revision selection, and Markdown export. Sanitize rendering and reject unsafe protocols; never render raw HTML. On conflict offer to view latest alongside the retained draft, then require an explicit new save with the revision the human has reconciled.
- [ ] Implement message citation cards showing title, revision, and optional lines. The cited revision is the default destination, with a separate latest-version action. Keep ordinary document URLs visibly distinct from pinned references.
- [ ] Run API tests, frontend typecheck/build, and document E2E. Inspect keyboard/mobile behavior and test raw HTML/script links in both preview and messages. Commit the integrated Docs experience.

## Task 4: Real shared-context test

**Files:** `next/verification/docs-pilot.md`, additions to `next/README.md`.

- [ ] Davide creates a short real specification and mentions both connected agents in a message with a pinned doc revision. Each fetches it using its existing session and answers a question that requires reading the content.
- [ ] Enrico edits the doc; confirm old citations still open their original revision and a new citation opens the update. Trigger one concurrent edit and reconcile explicitly.
- [ ] Restart the service and reload both browser clients. Confirm document revisions, message references, and access control persist. Include docs tables in the backup/restore validation from the Channels plan.
- [ ] Record what was tested with actual humans/hosts and what remains simulated. Mark the integrated first-version pilot ready only when both stage-one and stage-two gates pass.

## Review checklist

- No document request bypasses channel authorization.
- Stale updates preserve the losing editor's content instead of overwriting or silently rebasing.
- Every persisted citation has an explicit revision and valid range.
- Agent inboxes carry references rather than entire document libraries.
- Docs add shared context without introducing tasks, orchestration, or new account hierarchy.
