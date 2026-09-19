"""Private, atomic local state and per-channel process locks."""
import fcntl
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def directory():
    path = Path(os.environ.get('CODIFICA_AGENT_STATE', str(Path.home() / '.local/share/codifica-agent')))
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError('The credential directory must not be a symbolic link.')
    os.chmod(path, 0o700)
    return path


def path_for(kind, key):
    return directory() / f'{kind}-{hashlib.sha256(key.encode()).hexdigest()}.json'


def load(path, default=None):
    if path.is_symlink():
        raise ValueError('State files must not be symbolic links.')
    return json.loads(path.read_text()) if path.exists() else default


def save(path, value):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump(value, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def lock(key):
    path = path_for('lock', key)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another helper is using this channel. Stop it before retrying.') from None
        yield
    finally:
        os.close(fd)
