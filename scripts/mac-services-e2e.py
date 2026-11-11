#!/usr/bin/env python3
"""Drive the real lifecycle runner with failing and signalled child processes."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/macos/service-runner.py'
REPORT = ROOT / '.openbot-build/mac-services-e2e/report.json'


def main():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        def command(source):
            return [sys.executable, str(RUNNER), '--name', 'app', '--log-directory', temporary,
                    '--', sys.executable, '-u', '-c', source]
        secret = 'SYNTHETIC-SECRET-MUST-NOT-APPEAR'
        source = "print('Authorization: Bearer " + secret + "'); print('[api] stopped with code 7. Stopping the other services.'); raise SystemExit(7)"
        first = subprocess.run(command(source), timeout=10)
        assert first.returncode == 7
        # A second run must append, rather than erase the first shutdown record.
        second = subprocess.Popen(command('import signal; signal.pause()'))
        try:
            deadline = time.monotonic() + 10
            while True:
                events = [json.loads(line) for line in (directory / 'app.jsonl').read_text().splitlines()]
                if sum(item['event'] == 'started' for item in events) == 2:
                    break
                if time.monotonic() > deadline:
                    raise AssertionError('Runner did not start.')
                time.sleep(0.02)
            second.send_signal(signal.SIGTERM)
            assert second.wait(timeout=10) == 143
        finally:
            if second.poll() is None:
                second.kill()
                second.wait()
        text = (directory / 'app.jsonl').read_text()
        events = [json.loads(line) for line in text.splitlines()]
        assert secret not in text and 'Authorization' not in text
        assert any(item['event'] == 'component-exited' and item['result'] == 'code 7' for item in events)
        assert [item['code'] for item in events if item['event'] == 'exited'] == [7, -15]
        assert any(item['event'] == 'stop-requested' and item['signal'] == 15 for item in events)
        assert (directory / 'app.jsonl').stat().st_mode & 0o077 == 0
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps({'passed': True, 'checks': ['failure code', 'component exit', 'append across restart',
            'signal forwarding', 'shutdown record', 'secret exclusion', 'private file permissions'], 'events': events}, indent=2))
        print('Passed. Report: ' + str(REPORT))


if __name__ == '__main__':
    main()
