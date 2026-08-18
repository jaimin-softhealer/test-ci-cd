# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies Pvt. Ltd.
#!/usr/bin/env python3
"""Secure GitHub push webhook receiver for local CI."""

import hashlib
import hmac
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


WEBHOOK_SECRET = os.environ['WEBHOOK_SECRET'].encode()
REPO_DIR = Path(os.environ.get('CI_REPO_DIR', Path(__file__).resolve().parents[1])).resolve()
RUNNER = Path(os.environ.get('CI_RUNNER', Path(__file__).with_name('run_ci.sh'))).resolve()
BRANCH = os.environ.get('CI_BRANCH', 'main')
LOG_DIR = Path(os.environ.get('CI_LOG_DIR', REPO_DIR / 'logs'))
PORT = int(os.environ.get('WEBHOOK_PORT', '8080'))


class Handler(BaseHTTPRequestHandler):
    """Handle signed GitHub webhook requests."""

    def _reply(self, code, message):
        body = f'{message}\n'.encode()
        self.send_response(code)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == '/health':
            self._reply(200, 'ok')
            return
        self._reply(404, 'not found')

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length)
        signature = self.headers.get('X-Hub-Signature-256', '')
        expected = 'sha256=' + hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            self._reply(403, 'invalid signature')
            return
        if self.headers.get('X-GitHub-Event') != 'push':
            self._reply(202, 'ignored event')
            return

        try:
            payload = json.loads(body)
            ref = payload['ref']
            after = payload['after']
            before = payload.get('before', '0' * 40)
            author = (payload.get('pusher') or {}).get('email', '')
            if not author:
                author = (payload.get('head_commit') or {}).get('author', {}).get('email', '')
            actor = (payload.get('sender') or {}).get('login', '')
        except (KeyError, json.JSONDecodeError):
            self._reply(400, 'invalid payload')
            return

        if ref != f'refs/heads/{BRANCH}':
            self._reply(202, 'ignored branch')
            return

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f'{after}.webhook.log'
        with log_file.open('ab') as output:
            subprocess.Popen(
                [str(RUNNER), before, after, author, actor],
                cwd=REPO_DIR,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self._reply(202, 'CI queued')

    def log_message(self, format, *args):
        return


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
