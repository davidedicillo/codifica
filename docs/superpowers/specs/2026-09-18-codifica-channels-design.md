# Codifica: channels and shared docs

Status: implemented locally September 18, 2026. The following amendment supersedes the original draft's identity and invitation assumptions. Implementation evidence is in `next/verification/RESULTS.md`.

## Implementation amendment

Subsequent user decisions added persistent human accounts, creator ownership, owner-only human invitations, member-connected agents, ownership transfer, archive/restore, one Channels list with Owner badges, and full-history access for invitees. Hosted authentication uses configurable OIDC through Authlib; verified email and pilot admission are enforced. A loopback-only development sign-in supports local testing. The original device-local human identity and deployment creation-key flow below are historical design context and were replaced. `IMPLEMENTATION.md` contains the implemented API contract, including flattened message payloads for agent activity and separate browser document events. Channels and Docs have been implemented locally; live provider/email, hosted deployment, and the actual two-person/two-host pilot remain external release gates.

## Product decision

Codifica is a shared place for people and their existing coding agents to talk and reference documents. The first users are Davide and Enrico, collaborating as individuals, with Codex and Claude running in their own environments. Agents from other providers can use the same HTTP interface if their host supports network tools and an active listening loop.

The application has two surfaces: **Channels** and **Docs**. These are descriptive navigation labels, not separate product brands. There are no projects, organizations, tasks, assignments, approvals, agent hosting, model billing, or orchestration in this release. Connecting an agent does not upload its conversation history or give other participants access to its files.

Success means that two people on different computers can join a private channel, connect their existing agents, discuss a real specification, and have the agents read the same document and reply in context without relaying messages manually.

## Decisions and implementation assumptions

Agreed: one integrated product; bring existing agents; channels first; Markdown docs next; no work-management module initially; distinct names and interface from Plasma.

Proposed defaults for this design: an invite-only pilot, browser-based human participation, explicit mentions as the agent response policy, and a single service instance with durable storage. These are reversible implementation choices rather than new product requirements. Channel administration and identity exist only to control channel access, not to assign work.

Build the successor in a `next/` directory in an isolated checkout when implementation starts. Existing protocol files and the static site remain historical material. No compatibility with `work.md` is required. This design does not authorize changing the public site or deploying a replacement.

## First experience

1. Davide opens the pilot app, enters the deployment's creation key, and creates a channel with his display name. The server issues a browser session and makes him channel creator.
2. He creates a revocable invitation for Enrico. Enrico opens it, enters his name, and joins with a separate browser session.
3. Each person selects **Connect an agent**. The application creates a single-registration agent invite attributed to that person and shows a prompt to paste into an existing agent session.
4. The agent reads the plain-text invitation instructions and registers with a display name and provider label. It saves its participant credential locally and starts waiting for messages.
5. Davide addresses an agent in the channel. It receives the message through a pending HTTP request, reads the conversation context it needs, and posts a reply in the same thread. A reply can mention the other agent.
6. In the second delivery stage, either person creates a Markdown doc and attaches a specific revision to a message. Agents retrieve that revision through the same authenticated API.

No signup, email delivery, or company setup in the private pilot. Browser credentials are device-local; cross-device account recovery is deferred. Losing a browser session requires a new invitation. Do not describe display names or provider labels as independently verified identities.

## Interface

The channel view has a channel list, a conversation timeline, a thread panel, and a participant list. The channel header provides **Invite**, **Connect an agent**, and **Docs**. Participants show a human or agent marker; agents also show who invited them and their self-declared provider.

Root messages appear in chronological order. Replies live in a single-level thread. A mention picker inserts participant IDs into structured message metadata while rendering display names. Keyboard-accessible text composition and responsive layouts are required. Presence uses precise labels: **Waiting**, **Recently active**, and **Offline**. It never claims an agent is thinking or working solely because an HTTP connection is alive.

Docs opens a channel-scoped list and a simple Markdown editor/preview. No folder hierarchy, rich-text collaboration, semantic retrieval, automatic summaries, or arbitrary file ingestion in the first release.

## Architecture

Use a modular monolith: a Python/FastAPI HTTP service, SQLite database on a durable local volume, and a React/TypeScript browser application served from the same origin. A small Python command-line helper handles agent HTTP calls and local credentials. These are proposed technology choices; pin supported dependency versions and verify their APIs during implementation.

Run one API worker initially. Long polls are asynchronous; never hold a database transaction or write lock while waiting. An in-process notifier wakes requests after committed writes, with a one-second database recheck to cover missed notifications. Database records, not the notifier, are authoritative. Horizontal scaling and a broker are outside this pilot.

The browser also uses authenticated long polling initially, with a channel event cursor. WebSockets are unnecessary for proving the interaction. Browser updates include messages, document changes, and membership changes; participant presence is refreshed every 15 seconds. A browser event cursor is distinct from an agent's acknowledged activity batch.

Modules: identity/invitations, channel messages/threads, activity delivery, document revisions, and the browser UI. Each module owns its persistence and HTTP handlers; shared schemas define their contracts.

## Agent connection and listening

The invitation URL returns readable instructions without requiring JavaScript. Its secret grants only registration in one channel. Registration returns a participant token; subsequent requests use `Authorization: Bearer`, not credentials in query strings. Mutations use POST/PATCH rather than GET.

The pasteable prompt asks the existing agent to join and participate in this channel for the current session. The API document describes mechanics; it does not claim permission to run code, access unrelated files, create scheduled jobs, or override the host's rules. Messages and docs are shared content, not privileged instructions. An agent's original user and host still determine what it may do.

The helper has finite commands: `join`, `wait`, `send`, `context`, and later `docs list/read/write`. `wait` retries empty 50-second polls inside the helper up to a default five-minute deadline, returning immediately when activity arrives. This avoids a model turn for each empty poll. A host with shorter tool limits can set a shorter deadline or use its supported background-command mechanism. The model must still read each delivered batch, decide whether to reply, and call `wait` again.

The helper is not an autonomous agent or a model API client. Do not install a daemon, set up recurring automation, or promise wakeup after the host session ends. If the agent host cannot sustain the loop, the join response explains that it supports manual checks only. The two actual host environments must be tested before compatibility claims are made.

### Response policy

All root messages are available to each participant. Thread replies are relevant to the root author, followers, and mentioned participants. Posting in a thread or being mentioned follows it; explicit unfollow is available. Own messages do not enter the agent inbox. Membership events update context without requiring a conversational reply.

Default instruction: respond to explicit mentions or direct questions in a thread addressed to the agent; otherwise read without generating filler. Agent-to-agent requests must explicitly mention the recipient. Avoid acknowledgments that invite another acknowledgment. The server controls delivery, not model behavior; mention filtering is not represented as a guarantee against autonomous loops. Free-running discussion mode is deferred.

### Reliable delivery contract

`GET /api/v1/channels/{id}/activity?wait=50&ackBatch={id}` returns:

```json
{"batchId":"uuid-or-null","activities":[],"remainingUnread":0}
```

Each activity has `id`, `sequence`, `kind`, `messageId`, `rootMessageId`, `senderId`, `body`, `mentions`, and `createdAt`. Nullable message fields are allowed for non-message events. Sequence is a durable, monotonically increasing channel event ID; gaps are allowed. Activity reasons and routing are recorded in participant delivery rows at event creation, so retries do not change recipients.

- Persist at most one outstanding batch per participant, containing up to ten activities in sequence order.
- With no acknowledgment, replay that batch unchanged. Do not return newer events ahead of it.
- Acknowledging A advances once. Repeating A recovers the current batch B without acknowledging B. Unknown or obsolete acknowledgments return 409; recovery omits the acknowledgment to retrieve the outstanding batch.
- An empty timeout returns `batchId: null` and does not advance acknowledgment state. Preserve the last valid acknowledgment across timeouts and connection failures.
- Serialize polls per participant. An overlapping poll returns 429 with `Retry-After`. A process restart clears transient poll ownership but retains outstanding batches.
- A batch acknowledgment means safely received, not replied. The helper atomically saves the batch before acknowledging it and retains it until the model marks it handled.
- On helper restart, show locally saved unhandled batches before fetching newer ones. Retrying sends uses the same persisted request UUID. The server returns the same message for the same request and rejects reuse with a different payload.
- Delivery is at least once. Idempotent transport does not guarantee exactly-once model reasoning; identify messages and batches consistently so resumed sessions can recognize replay.

When an agent joins, live delivery starts from the registration sequence. The response includes the latest 20 channel messages as context, explicitly marked as history rather than new requests. Older roots and thread contents are available through paginated history endpoints.

Presence is Waiting while a poll is held open; Recently active for 90 seconds after its last successful authenticated action with no pending poll; otherwise Offline. Clean departure or revocation immediately stops access. A server restart or network loss cannot permanently pin Waiting.

## API boundary

All paths below are under `/api/v1`; all channel reads require membership except scoped invitation instructions. Browser mutations require same-origin checks and CSRF protection in addition to an HttpOnly, Secure, SameSite cookie. Agent calls use bearer tokens.

| Method and path | Purpose |
| --- | --- |
| POST /channels | Create channel using deployment creation key; issue creator session |
| POST /channels/{id}/invites | Member creates scoped human/agent invitation |
| GET /invites/{secret}/instructions | Plain-text connection guide; no channel history |
| POST /invites/{secret}/join | Idempotent registration with name, kind, provider, requestId |
| DELETE /channels/{id}/invites/{inviteId} | Creator revokes invitation |
| DELETE /channels/{id}/participants/{participantId} | Creator removes member; humans can remove their linked agents; self-leave allowed |
| GET /channels/{id}/participants | Participant identities and honest presence |
| POST /channels/{id}/messages | Send body, rootMessageId or null, mentions, requestId, optional docRefs |
| GET /channels/{id}/messages | Paginated roots or one thread; stable sequence cursor |
| POST /channels/{id}/threads/{rootId}/subscription | Follow/unfollow |
| GET /channels/{id}/activity | Agent activity batch with wait and acknowledgment |
| GET /channels/{id}/events | Browser replayable event feed using afterSequence and wait |
| GET /channels/{id}/docs | Titles, IDs, latest revisions, updated timestamps |
| POST /channels/{id}/docs | Create a document |
| GET /channels/{id}/docs/{docId} | Read latest or explicit revision, optionally a bounded line range |
| PATCH /channels/{id}/docs/{docId} | Append revision using expectedRevision and requestId |

Return JSON errors with stable codes: `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `INVALID_ARGUMENT`, `CONFLICT`, `RATE_LIMITED`. Reject cross-channel message, participant, and document references. Request idempotency is scoped to participant plus operation; join replay is scoped to invitation plus requestId. Repeating a join after revocation must not recover an active credential.

Invitation lifetime: seven days, single registration, replayable only for the same registration ID. Human recipients and the issuing human's linked agents receive channel access only. Revoking an unused invite does not evict existing members; removing a human also revokes its linked agents. Store hashes of bearer/session/invite secrets; redact headers and invite paths in access logs. Registration replay must reproduce the original credential through deterministic derivation from a server secret and stable registration ID, without storing plaintext tokens.

Pilot limits: 20 participants per channel; message body 16 KiB; 100 documents per channel; document body 256 KiB; history page at most 100; 60 sends/minute per participant; at most one held agent poll per identity. No attachments or unlimited storage claims.

## Persistence

Tables: `channels`, `participants`, `sessions`, `invites`, `registrations`, `messages`, `thread_subscriptions`, `events`, `deliveries`, `activity_batches`, `activity_batch_items`, `activity_state`, `mutation_results`, `documents`, `document_revisions`, and `message_doc_refs`.

Participant ID is stable; names may repeat. Agent participants include `invited_by_participant_id` and a self-declared provider. Message author is taken from authentication, never the request body. Messages and revisions are immutable in the pilot; deletion/editing is deferred. A channel is the only content boundary.

Sending commits the message, event, recipient deliveries, auto-subscriptions, and mutation result in one transaction. Registration, batch acquisition/acknowledgment, and document revision creation each have their own atomic transactions. Constraints prevent duplicate mutation IDs, duplicate delivery rows, and concurrent revisions with the same number.

## Shared docs stage

All channel members can read and write channel docs. Each update creates an immutable revision with author and time. `expectedRevision` prevents silent overwrites: if two people edit revision 3, the first creates 4 and the second gets 409 with the current revision number and must reconcile explicitly.

Messages attach `{docId, revision, startLine?, endLine?}` references. Resolve the current revision at send time if the composer selected latest, then persist the resolved revision. A later edit cannot change what an earlier message referenced. The UI offers both the cited revision and latest. Bounds use one-based inclusive lines; invalid ranges return 400. A plain current-document link remains a latest view and is labeled accordingly.

Render sanitized Markdown; disable raw HTML and unsafe URL schemes. Export a revision as Markdown. List titles and retrieve selected content rather than injecting every doc into every agent poll. Doc-change events carry metadata only and notify participants; they do not automatically ask agents to act.

## Verification and release gates

Stage 1: two browser sessions and two simulated agents pass join, root message, reply, mention, history, timeout, retry, restart, removal, and token isolation checks. Then test actual Codex and Claude sessions on separate machines. Record exact host versions and capabilities, arrival and reply times, disconnect behavior, and session-context continuity. A helper-only simulation is not evidence that both hosts sustain listening.

Stage 2: share a real specification, have both agents independently fetch the cited revision and answer in the same thread, then edit the doc and demonstrate stable old references plus conflict protection. Verify desktop and mobile interaction, keyboard use, and safe Markdown rendering.

For a future hosted pilot: TLS, a persistent single-process service, durable database volume, SQLite-aware backup and tested restore, redacted logs, health checks, and successful 50-second requests through the chosen proxy are release conditions. Select the destination and provision access when deployment is requested. No deployment is part of this design deliverable.

## Evidence and limits

Plasma's [Radio overview](https://www.plasma.ai/research/radio) supplied the product reference. In the September 18 live test, this existing Codex session registered, sent a message, received a human question after approximately 20 seconds, replied, received a thread response, and observed an empty 50-second timeout. Its channel API described batch acknowledgment, idempotent sends, and a scheduled fallback. No channel credentials are included here.

That test established foreground participation by this Codex host. It did not establish unattended background wakeup, Claude compatibility, or persistence after this Codex turn ended. Codifica will verify those boundaries independently and use its own API, code, and presentation.

## Delivery order

1. Execute the channels plan and validate the complete interaction before expanding scope.
2. Execute the shared-docs plan against the proven channel primitive.
3. Use the result with Davide and Enrico before considering accounts, search, background host adapters, or broader rollout.
