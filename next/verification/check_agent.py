"""Opt-in local integration of the real HTTP API with helper subprocesses.

Run against the documented development server. Creates a clearly named test
channel; does not impersonate live models or send any external invitations.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API = 'http://127.0.0.1:8791/api/v1'


def main():
    with httpx.Client(base_url=API, headers={'Origin': 'http://127.0.0.1:5173'}) as human, tempfile.TemporaryDirectory() as state:
        login = human.post('/auth/dev-login', json={'email': 'davide@example.com', 'name': 'Davide'})
        login.raise_for_status()
        human.headers['X-CSRF-Token'] = human.get('/me').json()['csrfToken']
        channel = human.post('/channels', json={'name': f'Transport verification {int(time.time())}'}).json()
        cid = channel['id']
        invite = human.post(f'/channels/{cid}/invites', json={'kind': 'agent'}).json()
        env = {**os.environ, 'CODIFICA_AGENT_STATE': state}

        def command(*args):
            return [sys.executable, '-m', 'agent.cli', *args]

        def cli(*args):
            result = subprocess.run(command(*args), cwd=ROOT, env=env, capture_output=True, text=True, timeout=65)
            assert result.returncode == 0, result.stderr
            return json.loads(result.stdout)

        joined = cli('join', invite['instructionsUrl'], '--name', 'Transport test agent', '--provider', 'other')
        key = joined['channelKey']
        agent_id = joined['participant']['id']
        start = time.monotonic()
        listener = subprocess.Popen(command('wait', key, '--deadline', '10'), cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(.5)
        message = human.post(f'/channels/{cid}/messages', json={'body': 'Please verify this channel.', 'rootMessageId': None, 'mentions': [agent_id], 'requestId': str(uuid.uuid4())}).json()
        stdout, stderr = listener.communicate(timeout=15)
        assert listener.returncode == 0, stderr
        batch = json.loads(stdout)
        assert batch['activities'][0]['id'] == message['id']
        assert cli('wait', key, '--deadline', '1') == batch
        reply = cli('send', key, '--reply-to', message['id'], '--message', 'The HTTP helper round trip is working.')
        assert cli('send', key, '--reply-to', message['id'], '--message', 'The HTTP helper round trip is working.')['id'] == reply['id']
        cli('handled', key, batch['batchId'])
        doc = human.post(f'/channels/{cid}/docs', json={'title': 'Transport specification', 'body': '# Pilot\nUse existing agent sessions.', 'requestId': str(uuid.uuid4())}).json()
        fetched = cli('docs', 'read', key, doc['id'], '--revision', '1')
        assert fetched['body'] == doc['body']
        reference = cli('send', key, '--general', '--message', 'I read the pinned specification.', '--doc', f"{doc['id']}:1")
        assert reference['docRefs'][0]['revision'] == 1
        other_invite = human.post(f'/channels/{cid}/invites', json={'kind': 'agent'}).json()
        other = cli('join', other_invite['instructionsUrl'], '--name', 'Second transport test agent', '--provider', 'other')
        assert other['channelKey'] != key
        assert cli('join', invite['instructionsUrl'], '--name', 'Transport test agent')['participant']['id'] == agent_id
        history = human.get(f'/channels/{cid}/messages', params={'rootMessageId': message['id']}).json()['messages']
        assert len(history) == 1 and history[0]['id'] == reply['id']
        print(json.dumps({'passed': True, 'channelId': cid, 'elapsedSeconds': round(time.monotonic()-start, 3), 'checks': ['held HTTP poll', 'saved batch replay', 'threaded reply', 'send retry deduplication', 'pinned document read and citation', 'two local identities', 'identity reuse'], 'liveModels': False}))


if __name__ == '__main__':
    main()
