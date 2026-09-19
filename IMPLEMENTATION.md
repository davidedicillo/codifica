# Codifica implementation ledger

Implementation of docs/superpowers/plans/2026-09-18-codifica-channels.md and 2026-09-18-codifica-docs.md.

## Updated decisions from the conversation

- Persistent human accounts replace browser-local identities. Channel creator is owner, owner alone invites people, all human members connect their own agents, ownership can transfer, owner can archive. One Channels list with Owner badge.
- Joining grants full history and doc revisions. Registration bootstrap is recent context, not requests to execute.
- Use established OIDC integration through Authlib. Hosted provider can offer email code/magic-link login; credentials/provider provisioning are deployment prerequisites. Explicit development mode supports local-only sign-in for verification, never enabled in production.
- Execute both implementation stages locally; no deployment or live invitations to Enrico are authorized by implementation alone.
- Skill-directed bounded delegation: one API implementer, primary owns UI/helper/integration; review after integration. File ownership prevents concurrent edits.

## Contracts (authoritative for this implementation)

All API under `/api/v1`. CamelCase JSON. Errors `{code,message,currentRevision?}`.
Cookie sessions for browsers, `Authorization: Bearer` for agents. Browser gets csrfToken from GET /me and sends X-CSRF-Token on mutations (dev-login and invite join registration exempt only where explicitly credential-based).

- GET /auth/config -> `{devAuth:boolean,loginUrl:string}`.
- POST /auth/dev-login `{email,name}` -> `{user,csrfToken}`; only explicit local development mode and loopback HTTP clients. First email must be in configured pilot allowlist or hold a human invite; accepting invitation adds membership after authenticated login. Development option permits arbitrary loopback test accounts for isolated tests only.
- GET /auth/login, GET /auth/callback -> OIDC login; configured verified-email allowlist OR active invite matching verified email (authenticated login then join). Provider-managed sign-in; no custom OTP.
- POST /auth/logout -> 204.
- GET /me -> `{user:{id,name,email},csrfToken}` or 401.
- GET /channels -> `{channels:Channel[]}`.
- POST /channels `{name}` -> Channel.
- Channel: `{id,name,ownerId,role:'owner'|'member',archived:boolean}`. ownerId is user ID.
- PATCH /channels/{id} `{name?,archived?,ownerId?}` -> Channel, owner only.
- GET /channels/{id}/participants -> `{participants:Participant[]}`.
- Participant: `{id,name,kind:'human'|'agent',provider:null|string,invitedBy:null|string,userId:null|string,presence:'waiting'|'recent'|'offline'}`. invitedBy is human participant ID.
- POST /channels/{id}/invites `{kind:'human'|'agent',email?:string}` -> `{id,url,instructionsUrl,expiresAt}`. Human requires target email and owner; agent available to any human member.
- GET /channels/{id}/invites -> `{invites:[{id,kind,email,expiresAt,used,revoked}]}` owner only.
- DELETE /channels/{id}/invites/{inviteId} -> 204 owner only.
- GET /invites/{secret} -> `{channelName,kind,email?,expiresAt}` no history.
- GET /invites/{secret}/instructions -> text/plain, HTTP API joining instructions.
- POST /invites/{secret}/join `{name?,provider?,requestId}` -> human `{channelId,participant}` via signed-in target email, agent `{channelId,participant,token,recentMessages}` via invite secret. No CSRF for bearer-capability agent join; human join requires cookie+CSRF.
- DELETE /channels/{id}/participants/{pid} -> 204, owner or own agent or human self-leave; owner must transfer before leave. Removing human revokes linked agents.
- GET /channels/{id}/messages?rootMessageId=&afterSequence=0&limit=100 -> `{messages:Message[],nextSequence:number}`; omit root for roots; root filter for replies. Full history allowed. Agent join returns last 20 roots context only.
- POST /channels/{id}/messages `{body,rootMessageId:null|string,mentions:string[],requestId:UUID,docRefs?:DocRef[]}` -> Message.
- Message: `{id,rootMessageId:null|string,sequence:number,senderId,senderName,body,mentions:string[],createdAt,docRefs:DocRef[]}`.
- DocRef: `{docId,revision:number,title?,startLine?,endLine?}` input revision optional resolved transactionally.
- POST /channels/{id}/threads/{rootId}/subscription `{following:boolean}` -> `{following}`.
- GET /channels/{id}/activity?wait=50&ackBatch= -> `{batchId:null|string,activities:Message[],remainingUnread:number}`. Messages are activity payload in first release, doc events browser only; stable retry batch, up to 10, own excluded, root all, replies followers/mentions. Concurrent poll 429. GET /events?afterSequence=0&wait=25 -> `{events:[{sequence,kind,data}],nextSequence}`.
- GET /channels/{id}/docs -> `{documents:[{id,title,revision,updatedAt}]}`.
- POST /channels/{id}/docs `{title,body,requestId}` -> Document.
- GET /channels/{id}/docs/{docId}?revision=&startLine=&endLine= -> Document.
- PATCH /channels/{id}/docs/{docId} `{title,body,expectedRevision,requestId}` -> Document or 409 with currentRevision.
- Document: `{id,channelId,title,body,revision,authorId,updatedAt,startLine?,endLine?}`.

## Scope and progress

- [x] Backend identities/accounts, invitations, owner controls. Commit feec9d7.
- [x] Backend messages/activity/events and concurrency/restart behavior. Commit feec9d7.
- [x] Backend docs/references. Commit feec9d7.
- [x] Browser UI and genuine API integration.
- [x] Finite agent CLI with private credentials, retries, acknowledgment persistence.
- [x] Automated tests, actual local browser and HTTP listener test. 26 API + 5 helper + 6 browser tests; separate real HTTP 50-second/restart test passed.
- [x] Independent review and fixes. Backend empty-root validation and seven client/helper findings resolved; scoped reviewers confirmed fixes. Reports in next/api-review.md and next/client-review.md.
- [x] Runbook and exact evidence/remaining deployment prerequisites. next/README.md and next/verification/RESULTS.md.

External release gates still open: provision OIDC/email provider, choose and verify HTTPS deployment with supervision/backups, actual Davide/Codex and Enrico/Claude sessions on separate machines. Local transport simulations are not model compatibility evidence.

## Review rulings

- The original plans' no-delegation line is superseded by the applicable execution skill's explicit delegation workflow; no additional Codex tasks are created.
- OIDC provider is configurable instead of presuming credentials or creating a paid account. Cost if changed: auth adapter/configuration work; persistent user/channel identity remains stable.
- Plans listed single-use invitations and owner transfer without defining account recovery. Persistent OIDC subject IDs and verified email invitations supply that boundary.
- Archive makes the channel read-only while retaining history; restore is owner-only. Agent polls can read pending/history but cannot post while archived.
