# Codifica production deployment

Status: prepared, not yet live. Updated 2026-09-19 UTC.

Target: original VPS `bitsandshovels1`, 104.168.122.13. Existing Coolify project `tk4w8g04cwgk8w400kosso8w`, production environment `kkgws4os444cg8cc0ccocg84`. Created application ID 33, UUID `hs0zjn6ei2iokpte86y5dn0c`. Repository branch `codex/channels`, Dockerfile build context `/next`, one API worker, port8000 (no host-port publication). Data bind mount `/data/codifica` → `/data`, UID10001. Runtime secret generated privately in Coolify. Initial admitted account: davide@dicillo.com. Proposed pilot sender: existing SendGrid-verified davide@dicillo.com.

## Rollback

The previous static site lives on Cloudflare Pages and has not been deleted. Original DNS record: proxied CNAME `codifica.app` → `codifica-website.pages.dev`, TTL Auto, record ID `detail-15d86e7360eb69af22cf2210beea498f` in UI. Restoring that target restores the old site; retain the Pages project/domain association until a replacement rollback path is established. Do not delete the new SQLite data during rollback.

## Verification before release

- Backend:31 passed,1 skipped (optional50-second test),3 upstream deprecation warnings.
- Browser:8 passed, including email error recovery and sign-in/sign-out/reset.
- Frontend production build passes.
- VPS Docker build succeeds: image `codifica-pilot:b75d135`, SHA256 `e662f6bca554f0479ca81a796cff39c36d0f2577bc302c6fd9d544c713817c43`. Isolated container smoke test passes for health, built frontend, unauthenticated API denial, and development login disabled. Dummy email configuration in that disposable smoke test did not send mail.
- Branch `codex/channels` pushed; app code commit `b75d135ef07e50e0acda3ae25b417e2a6ec2ffb0` verified against remote.
- Daily backup service/timer files installed and systemd syntax verified, but timer not enabled before database creation. Snapshots stay on this VPS; an offsite copy is not configured.
- Email-code tests use a mocked SendGrid transport, not proof of real email delivery.
- Mail-only API key creation awaiting user confirmation. Domain not switched yet.

## Operational notes

Email login requires no third-party identity provider. Never enable `CODIFICA_DEV_AUTH` publicly. Preserve server secret across deployments. Invite emails admit new human accounts; connecting an agent uses a separate channel-scoped credential. A shared peer flood cap is intentional until trusted proxy client-IP attribution is configured.

Back up SQLite via its online backup API, not by copying the database alone while WAL is active. Preserve Coolify configuration including the private application secret. Full public login and persistence checks remain release gates.
