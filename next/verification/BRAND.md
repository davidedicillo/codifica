# Chat application brand update

Applies the selected Codifica style guide to the current React chat application in `next/web`, rather than the legacy protocol website at the repository root.

## Implementation

- Six-bubble cobalt/coral logo, warm-white sidebar and sign-in area, white reading surfaces, and cobalt actions/selection/focus.
- Locally hosted Source Sans 3 regular, semibold, and bold. Font license is included in `web/public/brand/fonts`.
- Shared semantic tokens in `web/src/brand-tokens.css`; consistent treatments for chat, threads, recipients, documents, participants, notices, invitations, and dialogs.
- Larger message/metadata text, visible keyboard focus, responsive side panels, and mobile composer controls.
- No changes to authentication, message delivery, agent credentials, channel permissions, database schema, or document revision logic.
- The logo is the generated raster proof from the selected identity. Compact navigation crops the same image to its bubble mark with CSS; a finalized vector master remains future brand production work.

## Verification

- Production TypeScript/Vite build passes.
- All nine existing end-to-end browser tests pass: named agents and explicit requests, message/reload/archive, thread draft isolation, document retries and conflicts, mobile/keyboard use, invited member permissions, and email sign-in recovery/reset.
- Two tests now wait for the newly created channel's own heading before typing. They previously raced the old channel's composer while the new channel loaded; product logic was unchanged.
- Manual browser review of sign-in, channel conversation, participants, and docs; no page overflow at 320 and 390 pixels. Production asset delivery is checked separately at deployment.
- The VPS online database backup completed successfully before deployment.

The earlier standalone website preview does not represent the new application and is superseded by this release.
