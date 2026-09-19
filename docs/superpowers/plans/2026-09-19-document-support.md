# Document Support Implementation Plan

**Goal:** Make + Document useful in empty channels and support private Markdown/image uploads.
**Architecture:** Extend document references with optional image metadata and an additive SQLite image table. Reuse DocsPanel for browsing, uploading and choosing a document from each composer.
**Tech Stack:** FastAPI, SQLite, Pillow, React, TypeScript, pytest, Playwright.
**Spec:** ../specs/2026-09-19-document-support.md

## Constraints

256 KiB UTF-8 Markdown; 5 MiB PNG/JPEG/WebP; 16 million pixels; 100 documents/channel. Preserve active edits in the channels worktree by working on codex/document-support. No public image URLs, raw HTML or new agent wakeup behavior.

## Tasks

- [ ] Add failing API tests in next/tests/test_uploads.py for upload/replay, image content retrieval, revisions, authorization, validation and persistence. Run `.venv-api/bin/python -m pytest tests/test_uploads.py -q`.
- [ ] Add next/server/uploads.py and migrations/004_images.sql; extend documents.py, schemas.py, app.py, pyproject.toml and requirements-lock.txt. POST `/channels/{channel}/docs/upload` takes `{filename, data, requestId}`. GET `/channels/{channel}/docs/{doc_id}/content?revision=1` serves authenticated image bytes. Run upload and existing API tests.
- [ ] Add failing next/web/e2e/documents.spec.ts exercising the empty composer control and Markdown/image upload round trips. Use an isolated local API and built frontend on port 8794.
- [ ] Extend api.ts metadata, DocsPanel.tsx uploads/preview/attach, Composer.tsx real document button/dialog, ChannelPage.tsx refresh and inline images, styles.css responsive controls. Keep changes local to document behavior. Run TypeScript/build and browser tests.
- [ ] Update agent HTTP instructions and next/README.md with upload and download contracts. Run the complete backend suite, focused desktop/mobile browser tests, inspect screenshots and review the final diff.
