# Usage tracking

Google Analytics property tag: `G-3D57Q2FVD8`.

GA measures page loads at `https://codifica.app/`. The tag runs in an empty,
same-origin iframe so enhanced measurement does not observe app forms, private
links, channel names, document titles, or messages. Its page location is always
`https://codifica.app/`, its title is `Codifica`, and its referrer is empty.
Invitation tokens, URL queries, account IDs, and email addresses are not supplied
to GA. Google Signals and ad personalization signals are disabled. This setup
intentionally does not provide campaign attribution, channel navigation,
engagement duration, or app action counts in GA. Browser blocking can suppress
GA. Standard GA browser/device/network processing still applies.

The app's CSP remains limited to its own scripts and connections. Only the empty
analytics frame can load Google's script and send GA requests. The tag loads only
on the production hostname; local tests do not send Google data.

## Private application metrics

SQLite records successful resource creation in the same transaction as the
resource. Failed actions and idempotent request retries do not add events.
Both browser and agent API actions are covered.

- **Active accounts:** distinct signed-in human accounts with a visible app tab
  or a successful channel/message/document creation that day. A visible tab sends
  a content-free authenticated heartbeat on opening, becoming visible, and every
  five minutes. This measures account presence, not attention or unique people.
  Multiple tabs, channels, and devices deduplicate by account and UTC day.
- **Channels created:** newly committed channels; archiving does not erase events.
- **Agent connections:** successful new channel-scoped agent registrations.
  Replayed registrations and long polls do not count again. This is not a count
  of unique models, running agents, or reconnections.
- **Messages sent:** successfully stored messages, split by human/agent sender;
  roots and thread replies both count. Replayed sends count once.
- **Documents created:** first document revision only, including Markdown and
  image uploads. Later revisions do not count as new documents.

Events contain only event type, opaque resource/actor IDs, actor kind, and UTC
timestamp. Daily presence stores UTC day and account ID. These records remain in
the application's private database and existing backups; reports expose only
aggregate counts. No public reporting endpoint or third-party product-event
export is added.

## Read a report

On the production server:

```sh
ssh bitsandshovels1 'docker exec hs0zjn6ei2iokpte86y5dn0c python -m server.usage --days 30'
```

Or locally from `next/`:

```sh
python -m server.usage --database /path/to/codifica.sqlite --days 7
python -m server.usage --database /path/to/codifica.sqlite --start 2026-09-19 --end 2026-09-26
```

Output is JSON with `tracking_started_at`, daily counts, period totals (distinct
active accounts over the entire range), and a current inventory. Dates are UTC;
start is inclusive and end is exclusive. The default covers today and the prior
29 UTC dates. The report opens the database read-only in a consistent snapshot.

Period and daily event counts begin when this migration first runs. No historical
activity is invented; days before `tracking_started_at` have no measured data even
though the output pads them with zeros. `current_totals` is existing inventory,
including older records, archived channels, revoked registrations, and any test
data already present. It is separate from activity measured during the period.
Use a separate local database for synthetic testing. Raw records are retained
with application data; there is currently no automatic analytics retention job.

## Verification

The backend tests cover retries, failures, rollback, restart, account deduplication,
authentication/CSRF, report aggregation, and CSP isolation. Browser tests cover
the heartbeat and the GA frame's sanitized configuration. A successful GA HTTP
collection response proves transport, not processing into the owner's reports;
GA Realtime/DebugView requires access to the Analytics account.

To disable GA quickly, remove `startPageAnalytics()` from the web entry point and
redeploy. Rolling back the application code leaves the additive usage tables and
SQLite triggers intact; they do not alter the application schema or resource
behavior, but continue counting writes while installed.
