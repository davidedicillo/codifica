import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class CLIContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = []
        self.polls = 0
        owner = self

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                owner.calls.append((self.path, body, self.headers.get('Authorization')))
                if self.path.endswith('/join'):
                    suffix = 'b' if body.get('name') == 'Claude' else 'a'
                    result = {'channelId': 'channel-a', 'token': 'private-secret' if suffix == 'a' else 'second-secret', 'participant': {'id': f'agent-{suffix}'}, 'recentMessages': []}
                else:
                    result = {'id': 'message-a', 'body': body.get('body')}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

            def do_GET(self):
                owner.polls += 1
                result = {'batchId': 'batch-a', 'activities': [{'id': 'message-a', 'body': 'Please review this.'}], 'remainingUnread': 0}
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), API)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.server.server_port}/api/v1/invites/secret/instructions'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def cli(self, *args):
        env = {**os.environ, 'CODIFICA_AGENT_STATE': self.temp.name}
        result = subprocess.run([sys.executable, '-m', 'agent.cli', *args], cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('private-secret', result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_join_retry_reuses_identity_request_and_protects_credentials(self):
        self.cli('join', self.url, '--name', 'Codex', '--provider', 'openai')
        self.cli('join', self.url, '--name', 'Codex', '--provider', 'openai')
        joins = [c for c in self.calls if c[0].endswith('/join')]
        self.assertEqual(len(joins), 1)
        state = list(Path(self.temp.name).glob('channel-*.json'))[0]
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)

    def test_wait_replays_saved_unhandled_batch_without_polling_again(self):
        self.cli('join', self.url, '--name', 'Codex')
        first = self.cli('wait', 'channel-a', '--deadline', '1')
        second = self.cli('wait', 'channel-a', '--deadline', '1')
        self.assertEqual(first['batchId'], 'batch-a')
        self.assertEqual(first, second)
        self.assertEqual(self.polls, 1)
        self.cli('handled', 'channel-a', 'batch-a')
        self.cli('wait', 'channel-a', '--deadline', '1')
        self.assertEqual(self.polls, 2)

    def test_send_uses_bearer_and_structured_thread_target(self):
        self.cli('join', self.url, '--name', 'Codex')
        self.cli('send', 'channel-a', '--reply-to', 'root-1', '--message', 'Review complete.', '--mention', 'claude-1')
        _, body, authorization = self.calls[-1]
        self.assertEqual(authorization, 'Bearer private-secret')
        self.assertEqual(body['rootMessageId'], 'root-1')
        self.assertEqual(body['mentions'], ['claude-1'])

    def test_identical_command_recovers_completed_send_instead_of_duplicating(self):
        self.cli('join', self.url, '--name', 'Codex')
        first = self.cli('send', 'channel-a', '--general', '--message', 'Done.')
        retry = self.cli('send', 'channel-a', '--general', '--message', 'Done.')
        self.assertEqual(first, retry)
        self.assertEqual(len([c for c in self.calls if c[0].endswith('/messages')]), 1)

    def test_second_agent_in_same_channel_cannot_overwrite_first_identity_or_batch(self):
        self.cli('join', self.url, '--name', 'Codex')
        original = self.cli('wait', 'channel-a', '--deadline', '1')
        second = self.cli('join', self.url.replace('/secret/', '/secret-two/'), '--name', 'Claude')
        self.assertEqual(second['channelKey'], 'channel-a:agent-b')
        self.assertEqual(self.cli('wait', 'channel-a', '--deadline', '1'), original)
        self.assertEqual(self.polls, 1)
        self.cli('send', 'channel-a', '--general', '--message', 'Original agent')
        self.assertEqual(self.calls[-1][2], 'Bearer private-secret')
        self.cli('send', second['channelKey'], '--general', '--message', 'Second agent')
        self.assertEqual(self.calls[-1][2], 'Bearer second-secret')


if __name__ == '__main__':
    unittest.main()
