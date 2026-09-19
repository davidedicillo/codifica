# Client and helper review

## Final scoped resolution

The remaining thread finding is resolved by source inspection. `web/src/Composer.tsx` now persists and restores the draft, attachments, mentions, and pending request identity using a user/channel/root-specific session-storage key. Recovered uncertain sends remain locked and retry using the saved UUID. `web/src/ChannelPage.tsx` now merges a returned reply into the open panel only when its `rootMessageId` matches `threadId.current`, preventing a late response from appearing under another thread.

The integration owner reports six passing browser E2E tests and a passing build, including A-to-B-to-A draft restoration and delayed POST completion during a thread switch. This reviewer inspected that fix only and did not rerun tests. All seven original actionable findings are now resolved in the reviewed code. No remaining concrete blocker was found in this scoped follow-up. Browser line-range citation controls remain a previously noted plan-compliance limitation; this is not a claim of deployment readiness or an exhaustive fresh audit. Earlier review sections below are historical and superseded by this resolution.

## Scoped re-review of fixes

The integration owner reports five passing helper tests and five passing API-backed browser tests, including lost document-create response and document draft navigation coverage. This follow-up inspected changed source only and did not rerun those checks. The initial findings below are retained as historical evidence; their current disposition is:

- Agent identity overwrite: resolved for ordinary joins. Additional same-channel identities receive distinct `channelKey` values, and existing identity state is retained (`agent/cli.py:43-50`).
- Definitive message rejection locks editing: resolved. Rejected 4xx mutations clear pending identity while preserving content (`web/src/Composer.tsx:60-67`).
- Fresh document UUID on retry: resolved. The exact pending signature/UUID is retained and persisted with the draft; content is locked during uncertainty (`web/src/DocsPanel.tsx:113-152`).
- Document panel navigation loses draft: resolved for the reported routes. Draft and pending state are persisted in user/channel-scoped session storage and recovered on remount (`web/src/DocsPanel.tsx:45-74`).
- Event cursor skips failed refresh: resolved. Cursor advances after successful root/docs/people and open-thread refresh (`web/src/ChannelPage.tsx:100-108`).
- Helper forgets result before stdout: resolved for default retries. Completed mutation result is saved atomically with clearing pending state, and identical commands replay it; `--new` explicitly requests another mutation (`agent/cli.py:55-76`).
- Thread composer reuse: partially resolved. A key prevents a draft from being retargeted, but the remaining issue below must be addressed.
- Revision selection: implemented. The earlier missing revision-picker note is resolved. Line-range citation controls remain absent from the browser.

### Remaining P2 — Thread switches discard pending replies and late responses contaminate the new thread

Location: `web/src/ChannelPage.tsx:146-151,365-372`; `web/src/Composer.tsx:27-33,49-59`.

Keying Composer by thread ID unmounts thread A's only draft and pending-request storage when switching to thread B. An uncertain send can no longer be retried with its original request ID after returning to A. An unsent draft is also silently discarded. Preserve draft/pending state by user/channel/thread or prevent navigation until the user explicitly resolves/discards it.

There is also an asynchronous destination error: click Send in A, switch to B while the request is in flight, then let A's POST return. The unmounted Composer still calls its captured `sent` callback, which unconditionally merges into the shared `replies` state now displayed under B. Guard the callback using `m.rootMessageId === threadId.current` (and retain any appropriate draft recovery handling). The saved server message still belongs to A; this issue is the incorrect current-thread display and lost local recovery state.

Current verdict: all three original P1 findings and three of the original P2 findings have been addressed by the inspected changes; thread navigation/recovery remains a P2 blocker. No new unrelated scan was performed.

Read-only source review of `next/web/src` and `next/agent`, using `IMPLEMENTATION.md` as the authoritative contract and the Channels/Docs plans as supporting requirements. Server code was inspected only to establish client-facing semantics. Existing build and three helper subprocess tests were reported passing by the integration owner; this review did not rerun them or claim they cover the scenarios below.

## Actionable findings

### P1 — Connecting a second agent overwrites the first agent's identity and recovery state

Location: `next/agent/cli.py:38-43` (also registration reuse at 29-32).

Each successful join writes its token, participant, and empty pending state to a file keyed only by `channelId`. Two existing agent sessions on the same machine use the same default credential directory. Joining the second invitation therefore replaces the first agent's token and clears its pending activity/mutation state. Subsequent commands in the first session silently execute as the second participant; replaying the first invitation also reports the second participant from that shared file. The join holds an invitation lock rather than the channel lock, so it can overwrite the state of an active helper operation too.

Preserve separate identity profiles keyed by channel plus registration/participant, make command selection unambiguous, and coordinate state writes under the same identity lock. At minimum, reject an attempted replacement and provide explicit isolated-profile instructions rather than silently switching identity.

### P1 — Definitive send errors permanently lock the message editor

Location: `next/web/src/Composer.tsx:9-16`.

Every failed POST retains `pending.current`, and any error with a pending request disables the textarea, mentions, and document controls. A message longer than the server's 16,384-character limit gets a definitive 422; a mention removed between composing and sending gets a definitive validation failure. The user cannot correct the content, and Retry repeats the same invalid payload forever. Reloading or unmounting the composer is the only escape, which discards the draft. Clear pending request identity after responses that establish the mutation was rejected, while preserving the draft for editing; reserve immutable retries for genuinely uncertain outcomes.

### P1 — Document retries create a fresh request instead of recovering the committed result

Location: `next/web/src/DocsPanel.tsx:8`.

`save()` creates a new UUID on every click. If a document creation commits but its response is lost, Retry creates another document. If an edit commits but its response is lost, Retry uses a fresh UUID with the old expected revision, producing a misleading conflict instead of replaying the original successful result. Retain the request ID and exact payload across uncertain failures, clearing them after a confirmed result or definitive rejection. Preserve editability according to the same distinction used for message retries.

### P2 — Opening another thread carries the existing reply draft and pending mutation into it

Location: `next/web/src/ChannelPage.tsx:21,28`; `next/web/src/Composer.tsx:4-8`.

When thread A is open and a root for thread B is clicked, React retains the same unkeyed Composer instance and changes its `rootId` prop. A draft intended for A is now sent to B. If A's send failed, its pending signature remains, so retry under B fails the signature check and the disabled editor cannot recover. Key or store composers by thread ID, and explicitly preserve/resolve a dirty or uncertain draft when changing threads rather than moving it to a different destination.

### P2 — Closing document UI through other channel controls silently discards drafts

Location: `next/web/src/ChannelPage.tsx:21-22,26,29`; `next/web/src/DocsPanel.tsx:6,11`.

DocsPanel prompts before its own close button and document selector discard dirty edits, but ChannelPage can unmount it directly when People, a thread, the Docs toggle, or a different document reference is clicked. Selecting another channel also unmounts the entire page. Those routes bypass the dirty check and lose the only in-memory draft. Put draft ownership/guarding above the panel or persist drafts by document and use it for every navigation route.

### P2 — Consumed browser event cursor can hide a failed refresh indefinitely

Location: `next/web/src/ChannelPage.tsx:13,16`.

The event loop advances `cursor` before synchronizing the corresponding messages/documents. `refresh()` catches its own network failures and resolves, so the event loop treats the event as processed. If the events request succeeds but the following messages fetch fails, later empty polls never refresh messages again; the 15-second timer refreshes only participants. The UI can show Connected while missing an already-consumed message until another event arrives or the page is reloaded. Make refresh failure visible to the loop and retry synchronization before acknowledging the event cursor locally, or track a retryable dirty state independent of new events.

### P2 — Local mutation result is forgotten before it is delivered to the agent host

Location: `next/agent/cli.py:64-66,113,136`.

The helper clears and persists `pendingMutation` before printing the returned mutation result. Process termination, a broken stdout pipe, or host output loss at that boundary leaves no local result or request identity to recover. Retrying the same command creates a new UUID, duplicating sends/creates; document edits instead produce conflicts. This is distinct from loss of the HTTP response, which correctly retains the request ID. Persist the completed result with its request identity until an explicit consumption/operation boundary, and provide a way to recover that result without treating an intentional future identical message as a retry.

## Contract and quality verdict

The broad client contract is implemented: persistent cookie sessions and CSRF headers, owner/member controls, invitation prompts, explicit root/reply targets and participant IDs, document references pinned to revisions, immutable historical reads, manual conflict reconciliation, finite helper polling, private atomic credential files, and redirect-blocked bearer HTTP. Markdown disables raw HTML and external image rendering; no concrete script-injection path was identified in these reviewed renderers.

The helper's batch protocol is sound by source inspection: it persists a received batch before printing, replays a pending batch without polling, requires `handled` before advancing, and repeats the saved ACK. Server handling of the last ACK makes repeated ACKs safe. This is an inspection conclusion, not a forced-termination or restart test result.

The docs plan is only partially met in the UI: explicit revision selection and line-range attachment/display controls are absent (the helper supports historical revision/range reads; message API types contain line fields). These are missing planned capabilities rather than additional runtime failure findings.

Quality verdict: changes required before calling client/helper recovery complete. In particular, identity isolation, terminal validation recovery, and stable document mutation requests are functional blockers. The passing smoke checks do not substantiate the untested failure boundaries listed above. No deployment or cross-host pilot readiness claim is made.

Integration observation outside this review's ownership: `main.tsx:17` appends the human invite to the login URL, but the inspected OIDC login route does not preserve it and the callback redirects to `/`. The API owner should retain the invitation return route; otherwise the user must reopen the original invitation after sign-in.
