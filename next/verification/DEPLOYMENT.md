# Codifica production deployment

Status: live at https://codifica.app/. Updated 2026-09-19 UTC.

Target: original VPS `bitsandshovels1`, 104.168.122.13. Existing Coolify project `tk4w8g04cwgk8w400kosso8w`, production environment `kkgws4os444cg8cc0ccocg84`. Application ID 33, UUID `hs0zjn6ei2iokpte86y5dn0c`. Repository branch `codex/channels`, Dockerfile build context `/next`, one API worker, port8000 (no host-port publication). Data bind mount `/data/codifica` → `/data`, UID10001. Runtime secret generated privately in Coolify. Initial admitted account: davide@dicillo.com. Pilot sender: existing SendGrid-verified davide@dicillo.com.

Deployed revision: `7b9882ccab518e355d290e70604f5ac6070ca722`, successful Coolify deployment `tg4fule6ofmtw4ffi5cwk106`. Container healthy with `unless-stopped` restart policy. Consistent-container-name mode is enabled for subsequent deployments to prevent overlapping API instances; this intentionally trades rolling updates for a short restart interval.

The user approved creation and private storage of the dedicated `Codifica production` SendGrid key. It is Mail Send only, runtime-only in Coolify, never a build argument. No key appears in this repository or report.

## Rollback

The previous static site lives on Cloudflare Pages and has not been deleted. Original DNS record: proxied CNAME `codifica.app` → `codifica-website.pages.dev`, TTL Auto, record ID `detail-15d86e7360eb69af22cf2210beea498f` in UI. Current record: proxied A `codifica.app` → `104.168.122.13`. To roll back, replace the A with the original CNAME and verify Pages routing (re-associate its custom domain if Cloudflare requires it). Do not delete the new SQLite data during rollback.

## Verification before release

- Backend:31 passed,1 skipped (optional50-second test),3 upstream deprecation warnings.
- Browser:8 passed, including email error recovery and sign-in/sign-out/reset.
- Frontend production build passes.
- VPS Docker build succeeds: image `codifica-pilot:b75d135`, SHA256 `e662f6bca554f0479ca81a796cff39c36d0f2577bc302c6fd9d544c713817c43`. Isolated container smoke test passes for health, built frontend, unauthenticated API denial, and development login disabled. Dummy email configuration in that disposable smoke test did not send mail.
- Branch `codex/channels` pushed; app code commit `b75d135ef07e50e0acda3ae25b417e2a6ec2ffb0` verified against remote.
- Daily backup timer is enabled and active. Two online backups completed and passed SQLite integrity checks. Snapshots stay on this VPS; an offsite copy is not configured.
- Email-code tests use a mocked SendGrid transport, not proof of real email delivery.
- Public HTTPS: `/health` returns JSON200, `/api/v1/auth/config` reports emailAuth=true/devAuth=false, private `/api/v1/channels` returns401, frontend/assets render the production sign-in screen in the browser. Responses use no-store.
- Origin TLS: Let's Encrypt certificate for codifica.app, expires2026-12-18. First issuance hit the old Pages site during DNS transition; a low-priority certificate-only router at `/data/coolify/proxy/dynamic/codifica-certificate.yaml` obtained the valid certificate without restarting the shared proxy.
- Real SendGrid request accepted from the public email-code endpoint; secure challenge cookie verified. The live browser successfully requested a fresh code for the owner and displayed the code-entry form. Inbox delivery and a completed human sign-in are not yet verified.
- Email challenge data persisted across the second Coolify deployment; SQLite integrity remains ok. No production channels or documents have been created by this deployment check.
- Cloudflare rejects Python's generic default user-agent with error1010. The helper now identifies itself as Codifica-Agent/0.1; all six helper tests pass, and the real helper transport successfully reads public `/health`. No Cloudflare security setting was disabled.

## Operational notes

Email login requires no third-party identity provider. Never enable `CODIFICA_DEV_AUTH` publicly. Preserve server secret across deployments. Invite emails admit new human accounts; connecting an agent uses a separate channel-scoped credential. A shared peer flood cap is intentional until trusted proxy client-IP attribution is configured.

Back up SQLite via its online backup API, not by copying the database alone while WAL is active. Preserve Coolify configuration including the private application secret. The owner should finish the email-code login in the open browser tab, then invite Enrico and connect their real coding agents. Actual cross-host agent use remains a pilot acceptance check.
