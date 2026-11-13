#!/usr/bin/env python3
"""Connect the installed Mac app to a private OpenBot host through SSH."""
import argparse
import json
import ipaddress
import os
from pathlib import Path
import plistlib
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', help='Sentinels Mac Tailscale .ts.net hostname.')
    parser.add_argument('--user', help='SSH user on the Sentinels Mac, not an email address.')
    parser.add_argument('--app', type=Path, default=Path('/Applications/OpenBot.app'))
    parser.add_argument('--profile', type=Path, default=Path.home() / 'Library/Application Support/OpenBot Sentinels')
    parser.add_argument('--port', type=int, default=43100)
    args = parser.parse_args()
    host = args.host or input('Sentinels Mac Tailscale hostname: ').strip()
    user = args.user or input('Sentinels Mac login user: ').strip()
    if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.ts\.net', host) or '..' in host:
        parser.error('Use the full Tailscale .ts.net hostname.')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*', user):
        parser.error('Use the Mac login short name, not an email address.')
    if not 1024 <= args.port <= 65535:
        parser.error('Use a local port from 1024 to 65535.')
    try:
        info = plistlib.loads((args.app / 'Contents/Info.plist').read_bytes())
        executable = info['CFBundleExecutable']
        if not isinstance(executable, str) or not executable or Path(executable).name != executable:
            raise ValueError()
        app = args.app / 'Contents/MacOS' / executable
        if not app.is_file() or not os.access(app, os.X_OK):
            raise ValueError()
    except (OSError, ValueError, KeyError, plistlib.InvalidFileException):
        parser.error('Cannot find an executable OpenBot app. Set --app to its .app path.')
    # Refuse an occupied port. Never attach the account client to another local service.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', args.port))
        except OSError:
            parser.error('The local port is busy. Close the earlier launcher or select --port.')
    # Installed upstream binaries still send anonymous analytics when their UI switch is off.
    # Require a system-level destination block before opening that binary.
    try:
        analytics_addresses = {entry[4][0] for entry in socket.getaddrinfo('analytics.openbot.run', 443)}
    except socket.gaierror:
        analytics_addresses = set()
    if not analytics_addresses or not all(ipaddress.ip_address(value).is_loopback for value in analytics_addresses):
        parser.error('Install the analytics destination block first: sudo python3 block-analytics.py install')
    os.umask(0o077)
    tunnel = None
    desktop = None
    stopped = False

    def stop(_signum, _frame):
        nonlocal stopped
        stopped = True

    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop)
    try:
        print('Opening SSH. Check the host fingerprint before accepting a new host key.', flush=True)
        tunnel = subprocess.Popen(['/usr/bin/ssh', '-N', '-T', '-o', 'ExitOnForwardFailure=yes',
            '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3',
            '-o', 'StrictHostKeyChecking=ask', '-L', f'127.0.0.1:{args.port}:127.0.0.1:3100',
            '-l', user, host])
        origin = f'http://127.0.0.1:{args.port}'
        # Ignore proxy environment variables for this loopback-only connection.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 120
        while not stopped:
            if tunnel.poll() is not None:
                print('SSH stopped. Check Tailscale and the Mac login.', file=sys.stderr)
                return 1
            try:
                with opener.open(origin + '/v1/mobile/features', timeout=1) as response:
                    ready = response.status == 200 and isinstance(json.load(response), dict)
                if ready:
                    break
            except (OSError, ValueError, urllib.error.URLError):
                pass
            if time.monotonic() >= deadline:
                print('The private API did not become ready. Check SSH and the host services.', file=sys.stderr)
                return 1
            time.sleep(0.2)
        if stopped:
            return 0
        environment = os.environ.copy()
        environment.pop('ELECTRON_RUN_AS_NODE', None)
        environment['OPENBOT_AUTH_API_URL'] = origin
        environment['OPENBOT_REMOTE_SIGNAL_URL'] = f'wss://{host}:8444/v1/signal'
        desktop = subprocess.Popen([str(app), '--user-data-dir=' + str(args.profile.expanduser().resolve())], env=environment,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('The private account API is ready. OpenBot is starting. Keep this terminal open.', flush=True)
        print('Use the Sentinels owner email. The development code appears in the app; no email is sent.', flush=True)
        while not stopped:
            if tunnel.poll() is not None:
                print('SSH disconnected. Closing this client. Run the launcher again.', file=sys.stderr)
                return 1
            if desktop.poll() is not None:
                return desktop.returncode
            time.sleep(0.2)
        return 0
    finally:
        # Stop only processes started by this launcher. Keep account and workspace files.
        for process in (desktop, tunnel):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
