#!/usr/bin/env python3
"""Block the known OpenBot analytics destination for installed applications."""
import argparse
import ipaddress
import os
from pathlib import Path
import socket
import subprocess
import tempfile

DOMAIN = 'analytics.openbot.run'
BEGIN = '# BEGIN OPENBOT PRIVATE ANALYTICS BLOCK'
END = '# END OPENBOT PRIVATE ANALYTICS BLOCK'
BLOCK = BEGIN + '\n127.0.0.1 ' + DOMAIN + '\n::1 ' + DOMAIN + '\n' + END + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'install', 'remove'])
    args = parser.parse_args()
    if args.action == 'status':
        try:
            addresses = {entry[4][0] for entry in socket.getaddrinfo(DOMAIN, 443)}
            blocked = bool(addresses) and all(ipaddress.ip_address(value).is_loopback for value in addresses)
        except socket.gaierror:
            blocked = False
        print('Analytics destination blocked.' if blocked else 'Analytics destination block not confirmed.')
        return 0 if blocked else 1
    if os.geteuid() != 0:
        parser.error('This changes /etc/hosts. Run with sudo only after reviewing this file.')
    hosts = Path('/etc/hosts').resolve()
    original = hosts.read_text()
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        parser.error('The existing managed block is not valid. Review /etc/hosts manually.')
    if BEGIN in original and (original.index(END) < original.index(BEGIN) or BEGIN not in original.splitlines() or END not in original.splitlines()):
        parser.error('Review the managed block boundaries in /etc/hosts manually.')
    updated = original
    if BEGIN in original:
        first = original.index(BEGIN)
        last = original.index(END) + len(END)
        if last < len(original) and original[last] == '\n':
            last += 1
        updated = original[:first] + original[last:]
    if args.action == 'install':
        updated = updated.rstrip('\n') + '\n' + BLOCK
    if updated != original:
        info = hosts.stat()
        descriptor, temporary = tempfile.mkstemp(prefix='.openbot-hosts-', dir=hosts.parent)
        try:
            os.fchmod(descriptor, info.st_mode & 0o777)
            os.fchown(descriptor, info.st_uid, info.st_gid)
            with os.fdopen(descriptor, 'w') as output:
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, hosts)
        finally:
            if Path(temporary).exists():
                Path(temporary).unlink()
        subprocess.run(['/usr/bin/dscacheutil', '-flushcache'], check=True)
    print('Analytics block installed.' if args.action == 'install' else 'Managed analytics block removed.')
    print('Close and reopen OpenBot so existing network connections end.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
