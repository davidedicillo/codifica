"""Online SQLite snapshot, intended for a root-owned daily timer on the VPS."""
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3

os.umask(0o077)
source = Path('/data/codifica/codifica.sqlite')
destination = Path('/data/codifica-backups')
destination.mkdir(mode=0o700, exist_ok=True)
if not source.is_file():
    raise SystemExit('Codifica database not created yet')
target = destination / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite')
with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as original:
    with sqlite3.connect(target) as snapshot:
        original.backup(snapshot)
        if snapshot.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup integrity verification failed')
print('Codifica snapshot created and integrity verified')
