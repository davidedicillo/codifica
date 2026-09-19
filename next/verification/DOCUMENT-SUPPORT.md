# Document support verification

Implemented on `codex/document-support` in `/Users/davidedicillo/Projects/Codifica/.worktrees/documents`. The branch includes the current `codex/channels` inline mention work. Local implementation only: not pushed or deployed.

## Result

The old **+ Document** control was a select containing only existing documents. In an empty channel it had no usable action. It now opens a document picker with upload, create, browse, preview and attach actions. The picker works in the main conversation and replies without losing the message draft.

Upload or drop UTF-8 `.md` files up to 256 KiB, or still PNG/JPEG/WebP images up to 5 MiB and 16 million pixels. Markdown is editable with revision history. Images have inline previews and downloads. Attachment-only messages work. The existing 100-document channel limit includes images.

Files remain channel-private, including image requests, and agents can retrieve them with bearer authentication using the documented HTTP API. Upload retries reuse the same request ID. Unsupported files, damaged images, extension/format mismatches and oversized files are rejected. Images are immutable and included in SQLite backups.

## Verification

- `.venv-api/bin/python -m pytest tests -q -rs --tb=short`: **51 passed, 1 skipped**. The existing opt-in 50-second idle HTTP acceptance test was skipped. Three existing dependency deprecation warnings remain.
- `npm run build`: TypeScript and production build passed.
- `npx playwright test --config playwright.documents.config.ts`: **13 passed** after integrating the inline mention editor. Covers existing channel behavior plus empty-channel uploads, opening after reload, image preview/download on mobile, thread drag-and-drop, and retry after a lost upload response without duplication.
- Desktop and mobile screenshots were inspected. No horizontal overflow in the mobile upload test.
- `git diff --check`: passed.

## Screenshots

- [Desktop picker](document-upload-desktop.png)
- [Mobile image preview](document-upload-mobile.png)

## Remaining release step

Merge the feature into the release branch and deploy the application with its updated pinned Python dependency and additive SQLite migration. No production files, records or services were modified during this task.
