#!/usr/bin/env python3
"""Run one launchd-owned process and save private lifecycle events."""
import argparse
import datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import signal
import subprocess
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', choices=['app', 'gateway', 'woof'], required=True)
    parser.add_argument('--log-directory', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A command is required.')
    os.umask(0o077)
    args.log_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    logger = logging.getLogger('lifecycle')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(args.log_directory / (args.name + '.jsonl'),
                                  maxBytes=1024 * 1024, backupCount=7)
    logger.addHandler(handler)

    def record(event, **values):
        logger.info(json.dumps({'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                'service': args.name, 'event': event, **values}))

    child = None
    requested_signal = None

    def stop(signum, _frame):
        nonlocal requested_signal
        if requested_signal is not None:
            return
        requested_signal = signum
        record('stop-requested', signal=signum)
        if child is not None and child.poll() is None:
            try:
                child.send_signal(signum)
            except ProcessLookupError:
                pass

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, stop)
    record('starting')
    try:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as error:
        record('start-failed', errno=error.errno)
        return 1
    record('started', pid=child.pid)
    if requested_signal is not None:
        child.send_signal(requested_signal)

    def read_events():
        # Strict allowlist: never save arbitrary output, paths, URLs, text or exceptions.
        pattern = re.compile(rb'\[(api|remote|app)\] stopped with (code [0-9]+|signal SIG[A-Z0-9]+)\. Stopping the other services\.')
        pending = b''
        while True:
            chunk = os.read(child.stdout.fileno(), 4096)
            if not chunk:
                break
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                match = pattern.search(line)
                if match:
                    record('component-exited', component=match[1].decode(), result=match[2].decode())
            pending = pending[-4096:]

    reader = threading.Thread(target=read_events, daemon=True)
    reader.start()
    code = child.wait()
    reader.join(timeout=2)
    record('exited', code=code, requestedSignal=requested_signal)
    handler.close()
    return code if code >= 0 else 128 - code


if __name__ == '__main__':
    raise SystemExit(main())
