# Codifica Channels Implementation Plan

Execution status: local implementation and automated validation completed. Human accounts and ownership follow the subsequent decisions in `IMPLEMENTATION.md`, superseding the original device-local registration steps below. See `next/README.md` and `next/verification/RESULTS.md` for the delivered state. Live identity-provider and external Codex/Claude participation remain unverified; no deployment or push occurred.

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task in the current session. Do not delegate without explicit user authorization. Steps use checkbox syntax for tracking.

**Goal:** Davide and Enrico can exchange messages with their existing agents through one private channel.

**Architecture:** A single HTTP service owns identity, messages, and durable inbox batches. A browser client and a finite-command agent helper share its API. Model execution stays in the existing agent hosts.

**Tech Stack:** Proposed Python/FastAPI/SQLite service, Python helper, React/TypeScript browser, pytest and Playwright verification. Resolve and lock supported versions when scaffolding; this plan does not assert specific current package versions.

**Spec:** [Channels and shared docs design](../specs/2026-09-18-codifica-channels-design.md), sections through Persistence and stage-one verification. Docs are a separate plan.

## Global constraints

- Channel is the only content boundary; no projects, tasks, assignments, or agent execution service.
- Use Channels and Docs as navigation labels; no Plasma product names in the UI.
- One API worker and durable SQLite storage; no database lock held during a long poll.
- Agent long-poll wait maximum 50 seconds; activity batch maximum ten items; overlapping polls return 429.
- Browser sessions use HttpOnly, Secure, SameSite cookies and CSRF/origin checks; agents use bearer headers.
- Invitation lifetime seven days; one registration per invite with idempotent replay.
- Limits: 20 participants/channel, 16 KiB/message, 100/history page, 60 sends/minute/participant.
- No unattended wakeup or cross-provider compatibility claim without actual host verification.
- No public deployment or replacement of the existing website in this plan.

## File map

All implementation paths are relative to the existing repository in an isolated checkout.

```text
next/
  README.md                     local run and agent connection instructions
  pyproject.toml                API/helper dependencies and console entry point
  uv.lock                       pinned Python dependency resolution
  .gitignore                    local credentials, SQLite files, build output
  server/
    __init__.py
    app.py                      application factory and same-origin static serving
    settings.py                 secret key, database path, origin, creation key
    db.py                       connections, transactions, migration execution
    migrations/001_channels.sql durable identity, message, event, and inbox tables
    schemas.py                  public request/response models
    identity.py                 credentials, invites, registration, removal
    channels.py                 channel creation and membership-scoped reads
    messages.py                 atomic sends, history, threading, subscriptions
    activity.py                 inbox acquisition, acknowledgment, wait and presence
    events.py                   browser event replay and in-process notification
    routes.py                   HTTP adapters, errors, limits, authentication
    instructions.py             agent-readable invitation and command guide
  agent/
    __init__.py
    cli.py                      join/wait/send/context/handled commands
    client.py                   authenticated requests and bounded retries
    state.py                    credential and batch persistence
  web/
    package.json
    package-lock.json
    index.html
    src/main.tsx
    src/api.ts
    src/ChannelPage.tsx
    src/ChannelList.tsx
    src/ThreadPanel.tsx
    src/Composer.tsx
    src/Participants.tsx
    src/JoinPage.tsx
    src/InviteDialog.tsx
    src/styles.css
  tests/
    conftest.py                 temporary DB, app, browser and agent fixtures
    test_identity.py
    test_messages.py
    test_activity.py
    test_agent_cli.py
    test_restart.py
    test_limits.py
  web/e2e/channels.spec.ts
  verification/agent-pilot.md   actual host observations and limitations
```

Use a fresh worktree at implementation time. Do not move or delete the existing protocol or change historical human review records. This new product design supersedes the legacy protocol's product constraints for the successor; it is not a claim to execute an old `work.md` task.

## Task 1: Private channel and idempotent identities

**Files:** `next/pyproject.toml`, `next/server/{app,settings,db,schemas,identity,channels,routes}.py`, `next/server/migrations/001_channels.sql`, `next/tests/{conftest,test_identity}.py`, `next/.gitignore`.

**Interfaces:** `create_app(settings) -> FastAPI`; authenticated `Principal(participant_id, channel_id, kind)`; `require_member(channel_id, credential) -> Principal`. API paths and bodies follow the design. Join accepts `{name, kind, provider?, requestId}` and returns `{participant, token?, recentMessages}`; human credentials go only into cookies.

- [ ] Create the `next/` Python project and temporary-database fixture. Write identity contract tests before implementing routes:

```python
def test_join_retry_preserves_identity(api, agent_invite):
    body = {"name": "Davide's Codex", "kind": "agent",
            "provider": "openai", "requestId": "join-1"}
    first = api.post(f"/api/v1/invites/{agent_invite}/join", json=body)
    second = api.post(f"/api/v1/invites/{agent_invite}/join", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["participant"]["id"] == second.json()["participant"]["id"]
    assert first.json()["token"] == second.json()["token"]
```

The fixture creates a channel with the configured creation key, then an agent invite through its authenticated creator session. Use valid UUIDs for request IDs in the implementation tests; the short IDs here illustrate logical request identity.

- [ ] Run `cd next && uv run pytest tests/test_identity.py -q`; establish failure for the missing behavior.
- [ ] Implement migration-backed channel creation, human session issuance, invite exchange, registration replay, access checks, expiry, and removals. Use random participant IDs, cryptographic invite secrets, and HMAC-derived registration credentials. Store only credential hashes; preserve original registration IDs and canonical payload digests for idempotency.

```python
# Registration must commit invite consumption and identity together.
with db.transaction(immediate=True) as tx:
    prior = lookup_registration(tx, invite_id, request_id)
    if prior:
        require_same_payload(prior.payload_digest, payload_digest)
        require_active(prior.participant_id)
        return recover_credential(prior)
    require_unexpired_unused_invite(tx, invite_id)
    return consume_invite_and_create_participant(tx, payload)
```

Implement the named internal functions within `identity.py`; they are not public APIs. Join kind must match invitation kind. An agent may not create invites or become a human by choosing a different kind.

- [ ] Add tests for expired/revoked invites, new request ID against consumed invite, revoked participant replay, duplicate names, spoofed kind, missing credentials, cross-channel access, origin/CSRF rejection, and removal cascading to linked agents. Run the identity suite and commit only this task's files.

## Task 2: Messages, mentions, and threads

**Files:** `next/server/{messages,events,schemas,routes}.py`, migration additions before first pilot release, `next/tests/{test_messages,test_limits}.py`.

**Interfaces:** `POST /channels/{id}/messages` accepts `{body, rootMessageId: string|null, mentions: string[], requestId: string}`; it returns the immutable message. `GET .../messages?rootMessageId=...&afterSequence=...&limit=...` returns ordered items and a cursor. Root messages omit the history root filter. Subscription POST accepts `{following: boolean}`.

- [ ] Write tests using three registered agent credentials: A sends a root, B follows and replies, C is mentioned. Assert all receive the root except A; only the thread's followers/author and C receive the reply, excluding its sender. Add stable ordered pagination coverage.

```python
def test_send_retry_does_not_duplicate(api, channel, agent_headers, send_body):
    path = f"/api/v1/channels/{channel}/messages"
    a = api.post(path, headers=agent_headers, json=send_body)
    b = api.post(path, headers=agent_headers, json=send_body)
    assert a.json()["id"] == b.json()["id"]
    changed = {**send_body, "body": "Different content"}
    assert api.post(path, headers=agent_headers, json=changed).status_code == 409
```

- [ ] Run `uv run pytest tests/test_messages.py -q` from `next/` and establish failures.
- [ ] Implement one transaction for author-validated message insert, monotonic event insert, follower updates, recipient delivery rows, and cached mutation result. After commit, notify waiters. Accept only a root message from this channel as `rootMessageId`; reject invalid mention IDs. Rate limit before writing, but successful idempotent replay must not count as another send.
- [ ] Verify oversized UTF-8 body rejection, participant caps, invalid thread/channel references, nonmember access, replay after a lost response, and the complete routing matrix. Run both suites and commit this task.

## Task 3: Reliable long polling and browser events

**Files:** `next/server/{activity,events,routes}.py`, `next/tests/{test_activity,test_restart}.py`.

**Interfaces:** Activity response is exactly `{batchId: string|null, activities: Activity[], remainingUnread: number}`. `Activity` follows the design. Browser events return `{events: Event[], nextSequence: number}`; event IDs are stable across reconnects. Read/catch-up APIs use membership authentication each time.

- [ ] Write tests for replay without acknowledgment, acknowledgment advancement, acknowledgment retry, null timeout, and two simultaneous polls. A concrete replay test:

```python
async def test_retry_ack_a_does_not_ack_b(client, activity_url, send_to_agent):
    await send_to_agent("first")
    a = (await client.get(activity_url, params={"wait": 0})).json()
    await send_to_agent("second")
    params = {"wait": 0, "ackBatch": a["batchId"]}
    b = (await client.get(activity_url, params=params)).json()
    retry = (await client.get(activity_url, params=params)).json()
    assert b == retry
    assert b["batchId"] != a["batchId"]
```

- [ ] Run `uv run pytest tests/test_activity.py tests/test_restart.py -q`; confirm missing behavior fails.
- [ ] Implement participant serialization, persisted batch/state transitions, and bounded asynchronous waiting. Register the event listener before the final database recheck to avoid a send-between-check-and-wait race. Release all database transactions before sleeping. Use the one-second fallback database recheck and a monotonic deadline. Disconnect and cancellation must release the participant poll slot in `finally`.
- [ ] Implement authenticated browser event replay using `afterSequence`; render presence from pending-poll state plus last activity, not a permanently stored online boolean. Member removal wakes pending polls and returns an authorization error instead of queued private content.
- [ ] Test 11-message batching, simultaneous sends and polls, failed connections, repeated last ACK after an empty timeout, obsolete ACK recovery, process restart with an outstanding batch, and revocation during a held request. Use shortened configurable waits for most tests and one actual 50-second idle acceptance test at integration time. Commit passing delivery behavior.

## Task 4: Agent instructions and finite-command helper

**Files:** `next/server/instructions.py`, `next/agent/{cli,client,state}.py`, `next/tests/test_agent_cli.py`, `next/README.md`, console entry point in `next/pyproject.toml`.

**Interfaces:** After installing the local package, `codifica-agent join URL --name NAME --provider PROVIDER`; `wait CHANNEL --deadline 300`; `send CHANNEL --reply-to ROOT_ID --message TEXT --mention PARTICIPANT_ID`; `context CHANNEL --thread ROOT_ID`; `handled CHANNEL BATCH_ID`. `send --general` and `--reply-to` are mutually exclusive. JSON output is the agent-facing contract.

Store credentials and pending mutations under a user-private application state directory outside the repository; restrict directory/file permissions to 0700/0600. Maintain a per-channel helper lock so two local waits cannot race. Never print tokens in normal output or subprocess failure diagnostics.

- [ ] Add a subprocess test that joins twice using the saved registration ID and asserts one identity. Add a crash test: deliver batch A, kill the helper before model handling, restart, and assert A is returned before new server work.
- [ ] Run `uv run pytest tests/test_agent_cli.py -q` and confirm the missing behavior fails.
- [ ] Implement `client.py` with bounded timeouts and jittered retry for connection failures/429/5xx. Do not retry validation/auth failures indefinitely. Persist mutation UUID and exact payload before send; on uncertain response reuse both. Refuse conflicting pending sends until the previous result is recovered.
- [ ] Implement batch handoff in `state.py`: atomic local write before printing a received batch; do not acknowledge or move past that batch until `handled` is recorded. On empty timeout the helper repeats the same ACK until its deadline, without calling a model. Flush structured stdout on delivery.
- [ ] Serve invitation instructions describing the API, local helper setup, raw HTTP alternative, registration reuse, thread targeting, response policy, and host limitations. Keep joining accessible through ordinary HTTP calls: helper installation is optional. Include a `--deadline 45` example for hosts with short tool-call limits.
- [ ] Test forced process termination, local lock contention, network loss after successful send, secret redaction, and clean stop. Document that backgrounding a process does not automatically return its messages to the model. Commit the helper and guide.

## Task 5: Browser channel experience

**Files:** `next/web/` files from the map, `next/web/e2e/channels.spec.ts`; static serving in `next/server/app.py`.

**Interfaces:** Browser requests send session cookies and a CSRF token on mutations; `api.ts` centralizes JSON errors, long-poll abort/reconnect, and cursor state. The UI uses stable participant/message IDs rather than display-name keys.

- [ ] Scaffold React/TypeScript with a locked dependency tree. Configure same-origin API access in development and production; application source modules stay independent of the legacy static site. Define `npm run build`, `npm run typecheck`, and `npm run test:e2e`.
- [ ] Write a two-browser-context test: creator creates a channel and invite; second human joins; both send roots and replies; only one copy of each message appears after reconnect. Use an API fixture to add an agent and verify mention rendering.

```typescript
await first.getByRole('textbox', { name: 'Message' }).fill('Review the spec');
await first.getByRole('button', { name: 'Send', exact: true }).click();
await expect(second.getByText('Review the spec', { exact: true })).toBeVisible();
await second.reload();
await expect(second.getByText('Review the spec', { exact: true })).toHaveCount(1);
```

- [ ] Implement channel list, channel creation, invite landing, one-level threads, composer, mentions, participant states, connection prompt copying, and creator removal/revocation controls. Optimistic messages retain the request UUID and reconcile with returned/event messages. A failed send remains visibly retryable.
- [ ] Show a closed-session explanation beside Offline agents. Empty channels explain how to invite a person and connect an agent. Do not include task-board UI or unusable Docs controls before the second stage.
- [ ] Run build/typecheck/E2E; inspect desktop and narrow/mobile layouts with keyboard-only navigation. Verify pending poll cleanup on channel switch, auth loss handling, plaintext/safe Markdown message rendering, and no secrets in copied ordinary channel URLs. Commit the channel UI.

## Task 6: Cross-host pilot and operational handoff

**Files:** `next/README.md`, `next/verification/agent-pilot.md`, `next/tests/test_restart.py`; local run configuration as needed.

- [ ] Run the complete API/helper suites and browser checks once. Run one full-duration idle poll; verify it returns null near 50 seconds and a new message wakes a subsequent poll before its deadline.
- [ ] Start the local application with its persistent database and one API worker. Restart it during an outstanding batch; verify the existing credentials and message history still work. Back up SQLite using its backup API, restore to a separate temporary database, and check identities, message IDs, and batch continuity.
- [ ] Use two existing agent sessions, initially two local sessions if needed, to exercise the exact invitation text. Record whether commands run synchronously, return resumable process handles, or are killed by the host; adjust examples based on observed behavior.
- [ ] Complete the actual Davide/Codex and Enrico/Claude test when both environments are available on a shared test endpoint. The endpoint setup requires a selected hosting/access arrangement; do not expose the service automatically. Record unavailable external participation as unverified rather than substituting two simulated agents.
- [ ] Record time to first message, a human-to-agent mention, an agent-to-agent mention, a threaded reply, an interrupted listener, successful identity reuse, and honest Offline status after stopping. Include host versions and exact commands, excluding secrets.
- [ ] Review the result against the stage-one design gate. Commit the run instructions and evidence. Keep public launch separate from local implementation completion.

## Review checklist

- Every identity and message API is channel-scoped, authenticated, and exercised by the channel UI or helper.
- Long-poll acknowledgments survive retries and restarts without silently discarding unhandled batches.
- The helper transports messages; only the existing agent host runs the model.
- The connection guide never claims authority beyond the initiating user's channel participation request.
- Pilot readiness lists actual Codex/Claude verification separately from automated simulations and deployment status.
