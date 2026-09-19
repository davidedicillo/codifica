# Local verification evidence

September 18, 2026. Branch `codex/channels`, isolated worktree `.worktrees/channels`.

## Completed

- API: 26 passing automated tests, including persistent human identities, invite/owner controls, token isolation, CSRF/origin enforcement, retry handling, root/thread routing, byte/count/rate limits, document revision races, immutable citations, batch acknowledgments, held poll revocation and cancellation, SQLite backup/restore, and OIDC invitation return logic.
- Real HTTP process test: an empty poll returned after 50.013 seconds; a new message woke a held poll in 0.009 seconds. Terminating/restarting the server preserved browser sessions and the outstanding delivery batch.
- Helper subprocess suite: five passing tests. Covers identity reuse/private file permissions, unhandled batch replay after process restart, bearer-header thread sends, completed-send recovery without duplicate posts, and two local agent identities in the same channel without state overwrite.
- Real helper/API round trip: passed against the running local HTTP server in 0.917 seconds. Held poll delivery, saved batch replay, threaded reply, duplicate-send protection, pinned doc retrieval/citation, separate local identities, and rejoin were exercised. These were explicitly transport test agents, not live frontier-model sessions.
- Frontend production build/typecheck passed. Six browser tests against the real API cover channel creation/reload/archive, full-history human invitation acceptance, member/owner control differences, invalid-message recovery, thread isolation and retained drafts, uncertain doc-save recovery, retained document drafts, conflicting edits/revision selection, and a narrow 390px viewport.
- Desktop/mobile visual inspection and screenshots are recorded alongside this document. Browser tests use named test channels and development accounts only.

## Review changes

- Fixed empty thread ID validation after independent API review reproduced a database FK error; POST and GET now reject malformed IDs before persistence.
- Fixed definitive send failures locking the composer, fresh UUIDs on uncertain doc-save retries, event cursor advancement before successful data refresh, and local agent identity collisions.
- Persisted browser drafts and pending send IDs per human/channel/thread; thread callbacks verify the currently displayed root before adding a late reply.
- Saved helper mutation results before stdout delivery; identical repeats recover the cached result unless explicitly marked new.

## Not established by local tests

- Hosted identity provider configuration and real email delivery. OIDC tests cover our boundary logic with a controlled provider response, not a deployed identity provider.
- Actual Codex and Claude joining from separate computers and sustaining listening through each host's execution limits.
- Public deployment, HTTPS proxy timeout behavior, production backup scheduling, or restart supervision.

Foreground API/Vite preview processes are running locally. They are not an installed service. No external invitations were sent, no model API keys were added, and no remote branch was pushed.
