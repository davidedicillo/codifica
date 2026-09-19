"""Join, wait and reply from an existing agent session: python -m agent.cli."""
import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
from . import state
from .client import ApiError, request, validate_url


def output(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def join(args):
    parts = validate_url(args.url)
    path = parts.path.rstrip('/')
    if path.endswith('/instructions'):
        path = path[:-len('/instructions')]
    if '/api/v1/invites/' not in path:
        raise ValueError('Use the agent instructions URL supplied by Connect an agent.')
    invite = urlunsplit((parts.scheme, parts.netloc, path, '', ''))
    with state.lock(invite):
        record_path = state.path_for('registration', invite)
        record = state.load(record_path)
        if record and 'channelId' in record:
            key = record.get('channelKey', record['channelId'])
            saved = state.load(state.path_for('channel', key))
            if saved:
                output({'channelId': record['channelId'], 'channelKey': key, 'participant': saved['participant'], 'reused': True})
                return
        if not record:
            record = {'requestId': str(uuid.uuid4()), 'name': args.name, 'provider': args.provider}
            state.save(record_path, record)
        result = request(invite + '/join', method='POST', body=record)
        channel_id = result['channelId']
        base = urlunsplit((parts.scheme, parts.netloc, '/api/v1', '', ''))
        saved = {'base': base, 'token': result['token'], 'participant': result['participant'], 'channelId': channel_id,
                 'ackBatch': None, 'pendingBatch': None, 'pendingMutation': None}
        with state.lock(channel_id):
            existing = state.load(state.path_for('channel', channel_id))
            key = channel_id if not existing or existing['participant']['id'] == result['participant']['id'] else f"{channel_id}:{result['participant']['id']}"
            prior = state.load(state.path_for('channel', key))
            if prior:
                saved = {**prior, 'token': result['token']}
            state.save(state.path_for('channel', key), saved)
        state.save(record_path, {**record, 'channelId': channel_id, 'channelKey': key})
        output({'channelId': channel_id, 'channelKey': key, 'participant': result['participant'], 'recentMessages': result.get('recentMessages', []),
                'listening': False, 'next': f'Run wait {key} to listen. Historical messages are context, not new requests.'})


def mutate(saved, path, method, payload, file, new=False):
    signature = hashlib.sha256(json.dumps([path, method, payload], sort_keys=True).encode()).hexdigest()
    prior = saved.get('pendingMutation')
    completed = saved.get('completedMutation')
    if not prior and not new and completed and completed['signature'] == signature:
        return completed['result']
    if prior and prior['signature'] != signature:
        raise ValueError('A previous mutation has an uncertain result. Retry that exact command before sending a different one.')
    if not prior:
        prior = {'signature': signature, 'requestId': str(uuid.uuid4())}
        saved['pendingMutation'] = prior
        state.save(file, saved)
    try:
        result = request(path, method=method, body={**payload, 'requestId': prior['requestId']}, token=saved['token'])
    except ApiError as error:
        if error.status in (400, 401, 403, 404, 409, 413, 422):
            saved['pendingMutation'] = None
            state.save(file, saved)
        raise
    saved['pendingMutation'] = None
    saved['completedMutation'] = {**prior, 'result': result}
    state.save(file, saved)
    return result


def channel_command(args):
    with state.lock(args.channel):
        file = state.path_for('channel', args.channel)
        saved = state.load(file)
        if not saved:
            raise ValueError('No saved identity for this channel. Join using its agent invitation first.')
        base = saved['base'] + '/channels/' + saved['channelId']
        if args.command == 'handled':
            batch = saved.get('pendingBatch')
            if not batch or batch['batchId'] != args.batch:
                raise ValueError('This batch is not the saved outstanding batch.')
            saved['ackBatch'], saved['pendingBatch'] = args.batch, None
            state.save(file, saved)
            output({'handled': args.batch})
        elif args.command == 'wait':
            if saved.get('pendingBatch'):
                output(saved['pendingBatch'])
                return
            end = time.monotonic() + args.deadline
            while time.monotonic() < end:
                wait = min(50, max(0, int(end - time.monotonic())))
                query = {'wait': wait}
                if saved.get('ackBatch'):
                    query['ackBatch'] = saved['ackBatch']
                try:
                    batch = request(base + '/activity?' + urlencode(query), token=saved['token'], timeout=wait + 10)
                except ApiError as error:
                    if error.status == 409:
                        saved['ackBatch'] = None
                        state.save(file, saved)
                        continue
                    raise
                if batch['batchId'] is not None:
                    saved['pendingBatch'] = batch
                    state.save(file, saved)
                    output(batch)
                    return
                if wait == 0:
                    break
            output({'batchId': None, 'activities': [], 'remainingUnread': 0, 'listening': False, 'reason': 'deadline'})
        elif args.command == 'send':
            payload = {'body': args.message, 'rootMessageId': args.reply_to, 'mentions': args.mention}
            if args.doc:
                payload['docRefs'] = [{'docId': d.split(':')[0], 'revision': int(d.split(':')[1])} for d in args.doc]
            output(mutate(saved, base + '/messages', 'POST', payload, file, args.new))
        elif args.command == 'context':
            query = {'limit': args.limit, 'afterSequence': args.after}
            if args.thread:
                query['rootMessageId'] = args.thread
            output(request(base + '/messages?' + urlencode(query), token=saved['token']))
        elif args.command == 'docs':
            path = base + '/docs'
            if args.action == 'list':
                output(request(path, token=saved['token']))
            elif args.action == 'read':
                query = {}
                if args.revision:
                    query['revision'] = args.revision
                if args.lines:
                    start, end = args.lines.split(':')
                    query.update(startLine=int(start), endLine=int(end))
                output(request(path + '/' + args.doc_id + '?' + urlencode(query), token=saved['token']))
            else:
                payload = {'title': args.title, 'body': Path(args.file).read_text()}
                if args.action == 'write':
                    path += '/' + args.doc_id
                    payload['expectedRevision'] = args.expected_revision
                output(mutate(saved, path, 'PATCH' if args.action == 'write' else 'POST', payload, file, args.new))


def parser():
    p = argparse.ArgumentParser(description='Connect an existing agent session to Codifica. No model or background daemon is launched.')
    sub = p.add_subparsers(dest='command', required=True)
    j = sub.add_parser('join'); j.add_argument('url'); j.add_argument('--name', required=True); j.add_argument('--provider', default='other')
    w = sub.add_parser('wait'); w.add_argument('channel'); w.add_argument('--deadline', type=int, default=300)
    h = sub.add_parser('handled'); h.add_argument('channel'); h.add_argument('batch')
    s = sub.add_parser('send'); s.add_argument('channel'); s.add_argument('--message', required=True); s.add_argument('--mention', action='append', default=[]); s.add_argument('--doc', action='append', default=[], help='DOC_ID:REVISION')
    s.add_argument('--new', action='store_true', help='Intentionally repeat an identical completed send; otherwise recover its saved result.')
    target = s.add_mutually_exclusive_group(required=True); target.add_argument('--general', action='store_true'); target.add_argument('--reply-to')
    c = sub.add_parser('context'); c.add_argument('channel'); c.add_argument('--thread'); c.add_argument('--after', type=int, default=0); c.add_argument('--limit', type=int, default=100)
    d = sub.add_parser('docs'); ds = d.add_subparsers(dest='action', required=True)
    for action in ('list', 'read', 'create', 'write'):
        command = ds.add_parser(action); command.add_argument('channel')
        if action in ('read', 'write'): command.add_argument('doc_id')
        if action == 'read': command.add_argument('--revision', type=int); command.add_argument('--lines')
        if action in ('create', 'write'): command.add_argument('--title', required=True); command.add_argument('--file', required=True); command.add_argument('--new', action='store_true')
        if action == 'write': command.add_argument('--expected-revision', type=int, required=True)
    return p


def main():
    args = parser().parse_args()
    try:
        if args.command == 'wait' and not 1 <= args.deadline <= 3600:
            raise ValueError('Deadline must be between 1 and 3600 seconds.')
        join(args) if args.command == 'join' else channel_command(args)
    except (ApiError, ValueError, KeyError, OSError) as error:
        # Do not print exception URLs, HTTP headers or credential-bearing state.
        message = str(error) if isinstance(error, (ApiError, ValueError)) else 'Local state or response could not be read. Check your configuration.'
        print(json.dumps({'error': message}), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(json.dumps({'stopped': True}), file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
