#!/usr/bin/env python3
"""Prepare and manage private OpenBot LaunchAgents for this checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / '.openbot' / 'mac-services'
NAMES = ('app', 'gateway', 'woof')
PREFIX = 'run.openbot.' + hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
DOMAIN = 'gui/' + str(os.getuid())


def label(name):
    return PREFIX + '.' + name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'install', 'status', 'stop', 'start', 'uninstall'])
    parser.add_argument('--host', help='Full Tailscale .ts.net hostname; used by prepare only.')
    parser.add_argument('--with-woof', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == 'prepare':
        if not args.host or not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.ts\.net', args.host):
            parser.error('Set --host to the full Tailscale .ts.net hostname.')
        bun = ROOT / '.openbot/toolchain/node_modules/@oven/bun-darwin-aarch64/bin/bun'
        if not bun.is_file():
            found = shutil.which('bun')
            if not found:
                parser.error('Install Bun first.')
            bun = Path(found).absolute()
        node = shutil.which('node')
        if not node:
            parser.error('Install Node first.')
        python = Path(sys.executable).absolute()
        names = NAMES if args.with_woof else NAMES[:2]
        if args.with_woof:
            for relative in ('.openbot/woof-venv/bin/python', '.openbot/woof-model/underdog_woof/__init__.py', '.openbot/woof-api-key'):
                if not (ROOT / relative).exists():
                    parser.error('Complete the Woof setup first: ' + relative)
        STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in names:
            command = ['/bin/sh', str(ROOT / 'scripts/start-tailnet.sh'), name]
            if name == 'woof':
                command = [str(ROOT / '.openbot/woof-venv/bin/python'), str(ROOT / 'tools/woof/server.py'),
                           '--model-directory', str(ROOT / '.openbot/woof-model'),
                           '--key-file', str(ROOT / '.openbot/woof-api-key')]
            environment = {'PATH': ':'.join(dict.fromkeys([str(bun.parent), str(Path(node).parent), '/usr/bin', '/bin', '/usr/sbin', '/sbin'])),
                           'OPENBOT_TAILNET_HOST': args.host, 'PYTHONUNBUFFERED': '1'}
            job = {'Label': label(name), 'ProgramArguments': [str(python), str(ROOT / 'tools/macos/service-runner.py'),
                   '--name', name, '--log-directory', str(STATE / 'logs'), '--', *command],
                   'WorkingDirectory': str(ROOT), 'EnvironmentVariables': environment,
                   'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 30,
                   'ExitTimeOut': 60, 'LimitLoadToSessionType': 'Aqua', 'Umask': 0o077,
                   'StandardOutPath': '/dev/null', 'StandardErrorPath': '/dev/null'}
            (STATE / (label(name) + '.plist')).write_bytes(plistlib.dumps(job))
        (STATE / 'manifest.json').write_text(json.dumps({'names': list(names), 'root': str(ROOT)}))
        print('Prepared ' + ', '.join(names) + '. Review files in ' + str(STATE))
        return
    manifest = json.loads((STATE / 'manifest.json').read_text())
    if manifest['root'] != str(ROOT) or any(name not in NAMES for name in manifest['names']):
        parser.error('Prepare service files again for this checkout.')
    destination = Path.home() / 'Library/LaunchAgents'
    if args.action == 'install':
        for name in manifest['names']:
            path = destination / (label(name) + '.plist')
            if path.exists():
                parser.error('A service file already exists. Use start, or uninstall before install.')
            if not (STATE / path.name).is_file():
                parser.error('Prepare all service files first.')
    for name in manifest['names']:
        target = DOMAIN + '/' + label(name)
        path = destination / (label(name) + '.plist')
        if args.action == 'install':
            destination.mkdir(parents=True, exist_ok=True)
            if path.exists():
                parser.error('A service file already exists. Use start, or uninstall before install.')
            shutil.copyfile(STATE / path.name, path)
            os.chmod(path, 0o600)
            subprocess.run(['/bin/launchctl', 'enable', target], check=True)
            subprocess.run(['/bin/launchctl', 'bootstrap', DOMAIN, str(path)], check=True)
        elif args.action in ('stop', 'uninstall'):
            loaded = subprocess.run(['/bin/launchctl', 'print', target], capture_output=True).returncode == 0
            if loaded:
                subprocess.run(['/bin/launchctl', 'bootout', target], check=True)
                deadline = time.monotonic() + 65
                while subprocess.run(['/bin/launchctl', 'print', target], capture_output=True).returncode == 0:
                    if time.monotonic() >= deadline:
                        parser.error('Service did not finish shutdown: ' + name)
                    time.sleep(0.2)
            if args.action == 'uninstall' and path.exists():
                path.unlink()
        elif args.action == 'start':
            subprocess.run(['/bin/launchctl', 'bootstrap', DOMAIN, str(path)], check=True)
        else:
            result = subprocess.run(['/bin/launchctl', 'print', target], capture_output=True, text=True)
            fields = re.findall(r'^\s*(state = [\w-]+|pid = \d+|last exit code = \d+|last terminating signal = \w+)', result.stdout, re.M)
            print(name + ': ' + (', '.join(fields) if result.returncode == 0 else 'not loaded'))
    if args.action != 'status':
        print('Service action complete: ' + args.action)


if __name__ == '__main__':
    main()
