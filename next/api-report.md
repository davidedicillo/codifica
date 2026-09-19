# API implementation report

Implemented in `next/server/` as a single-worker FastAPI/SQLite service. The authoritative external API is `IMPLEMENTATION.md`; browser invitation URLs are `/i/{secret}` to match the integrated client.

## Delivered behavior

- Persistent OIDC issuer/subject accounts, verified email admission via allowlist or active human invitation, private cookie sessions, CSRF tokens and exact-origin browser mutation checks. Agent bearer credentials cannot use human administration endpoints. OIDC uses Authlib discovery, state/nonce validation, ID-token parsing and PKCE; no custom OTP or password implementation.
- Explicit loopback-only development login. Production configuration requires a 32-character-or-longer secret, HTTPS origin, and complete HTTPS OIDC configuration; absent configuration fails during application startup. `create_app(settings)` initializes isolated test databases without affecting the module-level app.
- Owner/member channels, owner-only human invitations, member-owned agent invitations, owner transfer, archive/restore, scoped invite revocation and human removal cascading to linked agents. Joining grants full message history and document revisions. Self-declared agent provider labels are not verified identities.
- Transactional idempotent registration, messages, document creation and revision writes. Credential/session/invitation secrets are hashed at rest. Registration replay derives its credential with keyed HMAC; plaintext tokens are not cached in the database. A completed registration can recover after the invitation expires, while new registrations cannot.
- Immutable ordered messages, channel-validated mentions and root references, explicit thread following/unfollowing, sender exclusion and recorded delivery routing. Root history and thread history have independent bounded pagination.
- Durable activity batches of ten, stable retries, exact ACK state transitions, repeated-last-ACK recovery, obsolete-ACK rejection, and persisted outstanding batches across process/database restore. One held poll per participant, cancellation cleanup, one-second fallback recheck, monotonic deadline and no open database transaction while waiting. A held poll revalidates credentials/membership before releasing private content.
- Browser event replay for messages, channel changes, membership and document metadata. Document events do not generate agent inbox work. Presence reflects a currently held poll or authenticated activity within 90 seconds.
- Immutable document revisions, expected-revision conflict detection, transactionally pinned message references and one-based inclusive line ranges. Atomic competing writes through separate SQLite connections produce one success and one conflict.
- Limits: 20 active participants, 60 new sends/minute/participant, 16 KiB UTF-8 messages, 100 documents/channel, 256 KiB UTF-8 document bodies, 100 history messages/page and 50-second activity waits.
- Plain-text invitation instructions support raw HTTP without helper installation, finite listening, persistent request IDs and batches, thread replies, explicit response policy and document retrieval/citation. They do not claim background wakeup or cross-host compatibility.
- Same-origin built frontend serving, health endpoint, no-store/no-referrer/security headers and sensitive invitation/auth URL redaction for Uvicorn access records. Run with `--no-access-log`; any future proxy must independently redact invitation paths and auth callback queries.

## Configuration and local use

Use Python 3.13 on the current host: the installed Python 3.14 `venv` failed during `ensurepip`; `.venv-api` was created successfully with Python 3.13. `requirements-lock.txt` pins the complete API/test resolution. No `uv` requirement.

```sh
cd next
python3.13 -m venv .venv-api
.venv-api/bin/python -m pip install -r requirements-lock.txt
.venv-api/bin/python -m pip install -e . --no-deps
```

Environment:

| Variable | Meaning |
| --- | --- |
| `CODIFICA_DATABASE_PATH` | Durable SQLite file; default `codifica.sqlite` |
| `CODIFICA_SECRET_KEY` | Required persistent secret, at least 32 characters; generate privately |
| `CODIFICA_ORIGIN` | Exact browser origin; local Vite integration uses `http://127.0.0.1:5173` |
| `CODIFICA_DEV_AUTH` | Set exactly `1` only for explicit loopback HTTP development |
| `CODIFICA_PILOT_EMAILS` | Comma-separated first-login allowlist; local test examples `davide@example.com,enrico@example.com` |
| `CODIFICA_OIDC_METADATA_URL` | Production HTTPS discovery URL |
| `CODIFICA_OIDC_CLIENT_ID` | Production provider application ID |
| `CODIFICA_OIDC_CLIENT_SECRET` | Production provider application secret |

With environment set, the integration API command is:

```sh
.venv-api/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8791 --no-access-log
```

Port 8787 already belongs to an unrelated local service. Vite runs at 5173 and proxies `/api` to the API at 8791. For serving the built web bundle directly, set `CODIFICA_ORIGIN` to the API's actual browser origin instead. Use exactly one API worker; multiple workers are not supported by the in-process poll reservation model.

Configure a provider callback at `${CODIFICA_ORIGIN}/api/v1/auth/callback`. Authlib handles the OIDC protocol. The application accepts only explicitly verified email claims and persistent issuer/subject identity. Invitation login stores only a validated invitation return destination and checks its target email before issuing the new account session. No arbitrary redirect URL is accepted.

## Verification

API test-first baseline initially failed because the `server` package did not yet exist. The OIDC invitation-return tests specifically failed with redirect `/` and absent invitation-email checking before the fix, then passed. Registration replay after expiry also had an observed failing regression test before its fix.

```sh
.venv-api/bin/python -m pytest tests/test_identity.py tests/test_messages.py tests/test_documents.py tests/test_activity.py tests/test_limits.py tests/test_oidc.py tests/test_restart.py -q
```

Result: **26 passed**. Covers account and credential isolation, owner transfer, invite expiry/revoke/replay, wrong human email, origin/CSRF, cross-channel references, root/thread delivery matrix, idempotent replay, archival, immutable revisions and line ranges, competing document edits, byte/count/rate limits, exact ACK transitions, outstanding batch restart, held poll wakeup/concurrency/revocation/cancellation, doc-event inbox exclusion, SQLite-aware backup/restore, joining full history without treating bootstrap context as inbox work, production cookie flags, and stable subject identity across email changes. Independent review caught an empty-string thread-root validation bypass; the regression reproduced a foreign-key exception and the fixed schema returns 400.

The opt-in real HTTP acceptance test also passed against an isolated single-worker Uvicorn process:

```sh
CODIFICA_HTTP_ACCEPTANCE=1 .venv-api/bin/python -m pytest tests/test_http_acceptance.py -q -s
```

Measured empty poll: **50.013 seconds**. Message-triggered wake: **0.009 seconds**. Actual process termination/restart retained both the outstanding delivery batch and the existing browser cookie session. Total test duration 51.25 seconds. This test is skipped in ordinary fast test runs and cleans up its own local process.

Three upstream deprecation warnings remain: Starlette's HTTPX test transport, AnyIO's BlockingPortal alias, and Authlib's HTTPX integration are transitioning to successor APIs. They do not indicate test failures. The lock file preserves the successfully exercised versions.

Authlib's official documentation confirms `authorize_access_token` automatically parses and validates the ID token and exposes `userinfo`: https://docs.authlib.org/en/stable/oauth2/client/web/index.html . Static review also inspected the installed Authlib state lookup/clear, nonce, issuer, audience and signed-ID-token validation paths and PKCE option handling. OIDC adapter tests substitute the remote provider boundary; they verify our email/admission/return-destination logic, not a real provider deployment. Actual provider credentials, TLS/proxy behavior, email delivery, public deployment, Enrico participation and cross-host Codex/Claude compatibility remain unverified prerequisites. The primary integration agent records actual browser/helper acceptance separately.

## Storage/operational boundaries

SQLite WAL and transactionally committed delivery state are authoritative. Back up with the SQLite backup API; copying only the main database while a process is writing may omit WAL state. The automated restore test validates persisted credentials, outstanding batches, message IDs and cited document revisions. Keep the database and its volume private and durable. Persist the server secret across restarts; rotating it changes deterministic registration replay credentials and should be treated as an operational credential rotation, not routine startup.

No deployment, proxy exposure, external email invitation or persistent daemon was created by this API implementation.
