# Document upload and opening

Approved scope: upload/drop Markdown, PNG, JPEG and WebP; open documents and images; preserve channel privacy and agent access. The existing composer select has no action when the channel has no documents. Replace it with a real button that opens the existing DocsPanel and offers upload, create, browse and attach.

Extend the existing document identity/reference model. Markdown imports become normal editable revision-1 documents. Images are immutable revision-1 documents with typed metadata and original bytes in a separate SQLite table, included in ordinary database backups. Authenticated content retrieval checks membership for every request. Existing Markdown API clients keep working. Agents read metadata then fetch image bytes using bearer authentication; references carry typed metadata without embedding image bytes in messages/activity.

Limits: 256 KiB UTF-8 Markdown, 5 MiB images, 16 million decoded pixels, 100 documents/channel (existing). Validate extension, decoded format and image integrity; reject HTML/SVG/PDF and invalid UTF-8. Uploads use the existing JSON/idempotency/CSRF contract with base64 encoding and a route-specific 8 MiB transport cap. Image revisions cannot be edited as Markdown. Existing references stay immutable.

Upload a single file at a time, with errors always visible. Preserve unsaved document drafts before replacing them. Successful uploads from the composer can be attached using the document panel; closing the panel preserves the message draft. Threads open their own document picker without losing the reply context. Support attachment-only sends, already accepted by the API.

Verify API creation/replay, limits, validation, membership, archive rules, immutable image references, raw download and restart persistence. Browser tests exercise the previously empty + Document control, create/import/open/attach/download, threads, drop, reload and mobile.
