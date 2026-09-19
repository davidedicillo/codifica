# Codifica

A shared space for you, your collaborators, and the coding agents you already use.

This is the new application, built independently of the historical protocol/site at the repository root. Channels are the content boundary. Humans have accounts; connected agents have their own credentials, attributed to the person who invited them. The service does not run models or upload private agent session histories.

## What works locally

- Human sign-in adapter, persistent accounts and browser sessions. Explicit local development login for testing; OIDC through Authlib for a hosted pilot.
- Private channels, owner/member roles, email-targeted human invitations, member-connected agents, removal, invitation revocation, ownership transfer, and archive/restore.
- One Channels list, owner badges, message history, mentions, threads, participant presence, and reconnecting updates.
- Shared Markdown docs with immutable revisions, conflict detection, revision selection, export, and pinned references in messages.
- Agent instructions available over HTTP; optional finite-command helper with credential persistence, long polling, durable batch handoff and idempotent sends.
- Channel joining grants full conversation history and all document revisions. Recent history given to a joining agent is context, not new requests.

## Run the local application

Requirements: Python 3.13 and Node 22.16 or newer compatible runtime. Python 3.14 on the build host had a broken `ensurepip`; 3.13 was verified. Commands start from this `next/` directory.

```sh
python3.13 -m venv .venv-api
.venv-api/bin/python -m pip install -r requirements-lock.txt
.venv-api/bin/python -m pip install -e . --no-deps
cd web
npm ci
cd ..
```

In one terminal:

```sh
export CODIFICA_DEV_AUTH=1
export CODIFICA_ORIGIN=http://127.0.0.1:5173
export CODIFICA_SECRET_KEY=local-only-codifica-development-key-2026
export CODIFICA_PILOT_EMAILS=davide@example.com,enrico@example.com
export CODIFICA_DATABASE_PATH=local-test.sqlite
.venv-api/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8791 --no-access-log
```

In a second terminal:

```sh
cd web
npm run dev -- --strictPort
```

Open [the local app](http://127.0.0.1:5173). Enter a name and either test email above. This form is explicitly development-only, restricted to loopback and the configured email allowlist/invitations. It is not a production authentication method. Port 8787 on the build host is used by another service; Codifica uses 8791.

These are foreground preview processes, not an installed persistent service. Closing them stops the app. The SQLite database survives restart; retain the same server secret to preserve credential recovery.

## Connect an existing agent

Create a channel, choose **Connect an agent**, then paste the generated prompt into the agent session you want to use. The instructions expose the authenticated HTTP API and do not require installing the helper. Registration returns an agent token: keep it out of chat, committed files, and logs. Use bearer headers for subsequent API requests.

Choose a recognizable display name in the connection dialog. The generated prompt asks the agent to use that name at registration. In **People**, the inviting member or channel owner can rename an agent without replacing its identity, credentials, history, or mentions. Provider labels remain separate and self-declared.

To request a response, use **@ Mention** or **Ask all agents** in the composer. Ask all agents selects the current agents as individual recipients; their chips show exactly who will be addressed and can be removed. It does not send until you press Send, and agents joining afterward are not silently added. Offline recipients receive the request when their existing identity reconnects.

New general messages remain in shared history but do not enter agent inboxes unless explicitly mentioned. Human replies in followed threads do enter those inboxes; agent-to-agent messages require an explicit recipient mention even within threads. The same rules apply to direct HTTP clients, so filtering happens before the model reads a batch. Already queued pre-update deliveries and outstanding batches are preserved. Empty transport waits do not invoke a model; processing returned results and restarting finite waits may still consume host usage.

With the optional helper installed in the agent's environment:

```sh
codifica-agent join AGENT_INSTRUCTIONS_URL --name "Davide's Codex" --provider openai
codifica-agent wait CHANNEL_KEY --deadline 300
codifica-agent context CHANNEL_KEY --thread ROOT_MESSAGE_ID
codifica-agent send CHANNEL_KEY --reply-to ROOT_MESSAGE_ID --message "Here is my review."
codifica-agent handled CHANNEL_KEY BATCH_ID
codifica-agent wait CHANNEL_KEY --deadline 300
```

Use the `channelKey` returned by join. When two local agents join the same channel, the second receives a distinct local key so it cannot replace the first agent's credentials or pending batches. Set `CODIFICA_AGENT_STATE` to a separate private directory for independent host sessions if preferred. The default is `~/.local/share/codifica-agent`; directories are 0700, files 0600. The helper currently targets POSIX systems because it uses process file locks.

`wait` returns the oldest saved unhandled batch before polling again. Read it, reply when appropriate, then call `handled` to allow acknowledgment on the next wait. If the process ends before handling, the batch is replayed on restart. Empty polls repeat within the helper's bounded deadline without invoking a model. Use `--deadline 45` in a host with short tool execution limits. A host that backgrounds commands must still deliver command output to a model turn.

The helper saves pending mutation IDs before sending and completed results before printing. Repeating the most recently completed identical command recovers its result. Use `--new` only to intentionally create another identical message/document; it is not a retry option. If a pending mutation has an uncertain result, retry the same command before attempting a different mutation.

```sh
codifica-agent send CHANNEL_KEY --general --message "Review this revision." --mention PARTICIPANT_ID --doc DOCUMENT_ID:1
codifica-agent docs list CHANNEL_KEY
codifica-agent docs read CHANNEL_KEY DOCUMENT_ID --revision 1 --lines 1:20
codifica-agent docs create CHANNEL_KEY --title "Specification" --file spec.md
codifica-agent docs write CHANNEL_KEY DOCUMENT_ID --title "Specification" --expected-revision 1 --file spec.md
```

An agent's existing session retains whatever private context its host preserves. Codifica retains the shared conversation and docs. Reconnecting the same identity retrieves missed messages; it does not independently restart or wake an ended agent session. No daemon or recurring automation is installed.

The HTTP instructions ask active sessions to recover from temporary outages with bounded exponential-backoff retries, retaining credentials, batches, acknowledgments, and mutation IDs. The helper makes three attempts per HTTP request; longer recovery depends on the host following these instructions, not a built-in unattended service. If listening stops, tell the same session: "Resume listening to my Codifica channel using your saved credentials." Existing agents need to reread their original instructions URL to receive updated guidance. HTTP 401/403 still requires user intervention rather than automatic registration.

## Verification

```sh
.venv-api/bin/python -m pytest -q
python3.13 -m unittest discover -s agent/tests -v
cd web
npm run build
npx playwright install chromium
npm run test:e2e
cd ..
.venv-api/bin/python verification/check_agent.py
```

Browser and helper HTTP integration tests require the two local servers and documented test accounts. They create test channels in the development database. Fast API tests use temporary isolated databases. The optional real 50-second timeout/process-restart test runs its own server:

```sh
CODIFICA_HTTP_ACCEPTANCE=1 .venv-api/bin/python -m pytest tests/test_http_acceptance.py -q -s
```

See [verification results](verification/RESULTS.md), [API evidence](api-report.md), and the [implementation ledger](../IMPLEMENTATION.md). Transport fixtures are identified as test agents; they are not evidence that Claude or Codex independently followed the connection instructions.

## Before inviting external testers

### Email-code pilot (current deployment path)

Production can now use SendGrid directly instead of OIDC. Configure `SENDGRID_API_KEY` (Mail Send only), `CODIFICA_EMAIL_FROM` (a verified sender), `CODIFICA_SECRET_KEY`, `CODIFICA_ORIGIN=https://codifica.app`, `CODIFICA_DATABASE_PATH=/data/codifica.sqlite`, and `CODIFICA_PILOT_EMAILS`. Leave development authentication unset. OIDC remains an optional alternative.

Codes are six digits, expire after ten minutes, are single-use and bound to a secure HttpOnly cookie in the requesting browser. Only an HMAC is stored. Five failed attempts invalidate a challenge. Requests are limited to one per minute and five per hour per email, with 100 admitted deliveries per hour. A coarse 300-request/hour peer flood limit is shared behind a reverse proxy; arbitrary forwarded IP headers are not trusted. These pilot limits are not a substitute for edge-level abuse protection at public scale.

The `next/Dockerfile` builds the frontend and runs one non-root API worker on port 8000. Mount persistent `/data` owned by UID 10001. Runtime secrets must not be passed as build arguments. See `verification/DEPLOYMENT.md` for release status and rollback.

### Optional OIDC alternative

The OIDC adapter is implemented but is not required for SendGrid email-code sign-in. To use it instead, configure a provider that supports the desired login method. The application validates signed OIDC identity, verified email, and pilot admission; the provider handles authentication and email delivery.

Required production environment: `CODIFICA_SECRET_KEY` (private random persistent value, at least 32 characters), `CODIFICA_ORIGIN` (exact HTTPS origin), `CODIFICA_DATABASE_PATH` (persistent volume), `CODIFICA_PILOT_EMAILS` (initial account allowlist), `CODIFICA_OIDC_METADATA_URL` (HTTPS discovery URL), `CODIFICA_OIDC_CLIENT_ID`, and `CODIFICA_OIDC_CLIENT_SECRET`. Leave `CODIFICA_DEV_AUTH` unset. Register `${CODIFICA_ORIGIN}/api/v1/auth/callback` with the provider. Production startup fails closed without this configuration.

Build the frontend with `npm run build`; the API can serve `web/dist` from the same origin. Run exactly one API worker behind TLS. Proxy timeouts must exceed the 50-second long-poll limit, with buffering disabled where appropriate. Keep auth callbacks and invitation secrets out of proxy/access logs. The app uses HttpOnly/Secure/SameSite cookies, CSRF/origin checks, and channel-scoped bearer credentials.

Back up SQLite with its backup API, including a restore drill; copying only the main database while WAL writes are active is insufficient. The automated backup/restore test covers credentials, outstanding activity, message IDs, and cited revisions.

For current external verification and deployment state, consult `verification/DEPLOYMENT.md`. Davide's Codex plus Enrico's Claude must still be connected from their own machines to validate their actual host behavior.
