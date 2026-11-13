#!/usr/bin/env python3
"""Run the hosts-file installer against a private file fixture, without sudo."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    hosts = directory / 'hosts'
    original = '127.0.0.1 localhost\n::1 localhost\n192.0.2.5 existing-host\n'
    hosts.write_text(original)
    fixture = directory / 'block.py'
    # Isolate only privileged paths and cache reload. The real installer edits the fixture file.
    source = (ROOT / 'tools/macos/block-analytics.py').read_text()
    source = source.replace("Path('/etc/hosts')", 'Path(' + repr(str(hosts)) + ')')
    source = source.replace('if os.geteuid() != 0:', 'if False:')
    source = source.replace("subprocess.run(['/usr/bin/dscacheutil', '-flushcache'], check=True)", 'pass')
    fixture.write_text(source)
    for action in ('install', 'install'):
        subprocess.run([sys.executable, str(fixture), action], check=True, capture_output=True)
    installed = hosts.read_text()
    assert installed.startswith(original)
    assert installed.count('127.0.0.1 analytics.openbot.run') == 1
    assert installed.count('::1 analytics.openbot.run') == 1
    subprocess.run([sys.executable, str(fixture), 'remove'], check=True, capture_output=True)
    assert hosts.read_text() == original
    malformed = original + '# END OPENBOT PRIVATE ANALYTICS BLOCK\n# BEGIN OPENBOT PRIVATE ANALYTICS BLOCK\n'
    hosts.write_text(malformed)
    result = subprocess.run([sys.executable, str(fixture), 'install'], capture_output=True)
    assert result.returncode != 0 and hosts.read_text() == malformed
    report = ROOT / '.openbot-build/mac-analytics-block-e2e/report.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({'passed': True, 'checks': ['existing entries preserved', 'IPv4 and IPv6 block',
        'idempotent install', 'remove restores fixture', 'malformed block refusal'],
        'limits': 'Private hosts fixture; no system DNS or /etc/hosts changed.'}, indent=2))
    print('Passed. Report: ' + str(report))
