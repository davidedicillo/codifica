"""Private usage counters. Run `python -m server.usage --days 30` on the server."""

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3

from fastapi import APIRouter, Request, Response
from .identity import authenticate

router = APIRouter()
EVENTS = ('channel_created', 'agent_connected', 'message_sent', 'document_created')


@router.post('/usage/active', status_code=204)
def active(request: Request):
    with request.app.state.db.transaction() as db:
        auth = authenticate(request, db, mutation=True, human=True)
        db.execute(
            "INSERT OR IGNORE INTO usage_active_days VALUES (date('now'),?)",
            (auth.user_id,),
        )
    return Response(status_code=204)


def report(db, start: date, end: date):
    """UTC dates, start inclusive/end exclusive. Never export actor identities."""
    if not start < end or (end - start).days > 366:
        raise ValueError('Choose a report range of 1 to 366 days')
    daily = {}
    day = start
    while day < end:
        daily[str(day)] = dict(day=str(day), active_accounts=0,
                              **{event: 0 for event in EVENTS},
                              human_messages=0, agent_messages=0)
        day += timedelta(days=1)
    for row in db.execute(
        "SELECT substr(occurred_at,1,10),event,actor_kind,COUNT(*) FROM usage_events "
        "WHERE occurred_at>=? AND occurred_at<? GROUP BY 1,2,3", (str(start),str(end))
    ):
        day, event, kind, count = row
        daily[day][event] += count
        if event == 'message_sent':
            daily[day][kind + '_messages'] += count
    for day, count in db.execute(
        'SELECT day,COUNT(*) FROM usage_active_days WHERE day>=? AND day<? GROUP BY day',
        (str(start),str(end)),
    ):
        daily[day]['active_accounts'] = count
    period = {key: sum(row[key] for row in daily.values())
              for key in (*EVENTS, 'human_messages', 'agent_messages')}
    period['active_accounts'] = db.execute(
        'SELECT COUNT(DISTINCT user_id) FROM usage_active_days WHERE day>=? AND day<?',
        (str(start),str(end)),
    ).fetchone()[0]
    totals = {name: db.execute(sql).fetchone()[0] for name, sql in {
        'accounts': 'SELECT COUNT(*) FROM users',
        'channels': 'SELECT COUNT(*) FROM channels',
        'agent_connections': "SELECT COUNT(*) FROM participants WHERE kind='agent'",
        'messages': 'SELECT COUNT(*) FROM messages',
        'documents': 'SELECT COUNT(*) FROM documents',
    }.items()}
    return dict(
        tracking_started_at=db.execute("SELECT value FROM usage_metadata WHERE key='started_at'").fetchone()[0],
        start=str(start), end_exclusive=str(end), timezone='UTC',
        period=period, daily=list(daily.values()), current_totals=totals,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=os.getenv('CODIFICA_DATABASE_PATH', 'codifica.sqlite'))
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat, help='Exclusive UTC end date')
    args = parser.parse_args()
    end = args.end or datetime.now(timezone.utc).date() + timedelta(days=1)
    start = args.start or end - timedelta(days=args.days)
    # Read-only: a typo must never create a new empty database or run migrations.
    try:
        with sqlite3.connect(Path(args.database).resolve().as_uri() + '?mode=ro', uri=True) as db:
            db.execute('BEGIN')
            result = report(db, start, end)
    except (sqlite3.Error, ValueError) as error:
        parser.exit(1, f'Usage report unavailable: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
