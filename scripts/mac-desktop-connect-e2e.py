#!/usr/bin/env python3
"""Drive the desktop launcher with a real local transport fixture and app process."""
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / '.openbot-build/mac-desktop-connect-e2e/report.json'


def main():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        ssh = directory / 'ssh-fixture'
        ssh.write_text('#!' + sys.executable + '\n' + '''
import http.server,json,sys
forward=sys.argv[sys.argv.index('-L')+1].split(':')
assert forward[0]=='127.0.0.1' and forward[2:] == ['127.0.0.1','3100']
assert 'StrictHostKeyChecking=ask' in sys.argv
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  assert self.path == '/v1/mobile/features'
  self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
http.server.HTTPServer((forward[0],int(forward[1])),Handler).serve_forever()
''')
        ssh.chmod(0o700)
        # Replace only the transport executable in an isolated copy. No production test hook.
        launcher = directory / 'connect.py'
        launcher.write_text((ROOT / 'tools/macos/connect-desktop.py').read_text().replace("'/usr/bin/ssh'", repr(str(ssh))).replace("'analytics.openbot.run'", "'localhost'"))
        bundle = directory / 'OpenBot.app'
        (bundle / 'Contents/MacOS').mkdir(parents=True)
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': 'OpenBot'}))
        app = bundle / 'Contents/MacOS/OpenBot'
        evidence = directory / 'app.json'
        app.write_text('#!' + sys.executable + '\n' + 'import json,os,sys\nfrom pathlib import Path\n' +
            'Path(' + repr(str(evidence)) + ').write_text(json.dumps({"api":os.environ["OPENBOT_AUTH_API_URL"],"signal":os.environ["OPENBOT_REMOTE_SIGNAL_URL"],"nodeMode":os.environ.get("ELECTRON_RUN_AS_NODE"),"arguments":sys.argv[1:]}))\n')
        app.chmod(0o700)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        profile = directory / 'private-profile'
        command = [sys.executable, str(launcher), '--host', 'example.tail123456.ts.net', '--user', 'example',
                   '--app', str(bundle), '--profile', str(profile), '--port', str(port)]
        environment = os.environ.copy()
        environment['ELECTRON_RUN_AS_NODE'] = '1'
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        observed = json.loads(evidence.read_text())
        assert observed == {'api': f'http://127.0.0.1:{port}', 'signal': 'wss://example.tail123456.ts.net:8444/v1/signal',
                            'nodeMode': None, 'arguments': ['--user-data-dir=' + str(profile.resolve())]}
        with socket.socket() as probe:
            assert probe.connect_ex(('127.0.0.1', port)) != 0, 'Tunnel survived app exit.'
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            busy_command = [*command[:-1], str(occupied.getsockname()[1])]
            result = subprocess.run(busy_command, capture_output=True, text=True, timeout=10)
            assert result.returncode != 0 and 'port is busy' in result.stderr
        denied_launcher = directory / 'denied.py'
        denied_launcher.write_text((ROOT / 'tools/macos/connect-desktop.py').read_text().replace("'analytics.openbot.run'", "'192.0.2.1'"))
        with socket.socket() as free:
            free.bind(('127.0.0.1', 0))
            denied_port = free.getsockname()[1]
        denied = subprocess.run([sys.executable, str(denied_launcher), *command[2:-1], str(denied_port)], capture_output=True, text=True, timeout=10)
        assert denied.returncode != 0 and 'analytics destination block first' in denied.stderr
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps({'passed': True, 'checks': ['loopback binding', 'SSH host-key checking',
            'API readiness', 'private API and Signal environment', 'separate profile', 'Electron Node mode removed',
            'tunnel cleanup on app exit', 'occupied port refusal', 'unblocked analytics refusal'],
            'limits': 'Loopback analytics DNS, transport and installed-app fixtures; no MacBook or real SSH authentication in this test.'}, indent=2))
        print('Passed. Report: ' + str(REPORT))


if __name__ == '__main__':
    main()
