# Managed Mac services

This setup keeps the current development profile and private Tailscale addresses.
It does not move the database, change pairing, or reset agents. It uses three
user LaunchAgents: the OpenBot development stack, the phone API gateway, and
optional Woof speech. There is no new network listener or public endpoint.

## Requirements

- macOS, a logged-in desktop session, Node, Python 3 and the installed Bun toolchain.
- Complete [Mac and iPhone setup](../../docs/mac-iphone-tailscale.md) first.
- Tailscale must stay connected on the Mac and iPhone. The Mac must stay awake.
- For Woof, complete [speech setup](../woof/README.md) first.

These are user services. They start at login, not before login. After a reboot,
unlock FileVault and log in. Closing the OpenBot window does not disable the
service. Quitting its process causes a restart. Logout stops user services.
This setup restarts exited processes; it does not detect every frozen process
or repair a VPN outage. Updates to source or dependencies can still require work.

## Prepare and review

From the repository root, replace the example hostname:

```sh
python3 tools/macos/manage-services.py prepare --host example.tail123456.ts.net --with-woof
```

Omit `--with-woof` if speech is not installed. Generated property lists and local
settings stay in ignored `.openbot/mac-services/`. Review the property lists
before installation. They contain local paths and a hostname, but no API keys.
The Woof key stays in its existing private file. The service labels contain a
hash of this checkout path, so another checkout has different labels.

The jobs use `RunAtLoad`, `KeepAlive`, and a 30-second restart throttle. They use
the same `scripts/start-tailnet.sh` commands as the manual setup. No cloud
credentials are copied from the terminal environment. Local development keeps
using the existing generated identity and saved state.

## Install

Installation writes three files to `~/Library/LaunchAgents/`. Ask the computer
owner before this step. Do not run manual and managed copies at the same time.

1. Stop this checkout's manual stack with `bun run dev:stop`. Stop its manual
   gateway and Woof terminal jobs with Ctrl-C. Do not stop other applications.
2. Install and start the prepared jobs:

```sh
python3 tools/macos/manage-services.py install
python3 tools/macos/manage-services.py status
```

If installation stops partway, use `uninstall` to remove this setup's loaded jobs
and property lists, then install again. Logs and application data remain.

If macOS blocks access to this checkout in Downloads, review the macOS privacy
prompt for the selected Python executable. Do not disable system protection.
A failed start can be checked with `launchctl print gui/$(id -u)/<label>` using
the label from the prepared file. A wrapper that cannot start has no lifecycle
log; `launchctl` still reports its exit status.

## Check and restart

```sh
python3 tools/macos/manage-services.py status
```

Check the private `/v1/mobile/features` address from the iPhone, then open
OpenBot and select the host. The existing guide has the exact URL pattern.
A successful Mac check does not prove that the phone's VPN is connected.

For a controlled restart, stop all jobs first, then start them:

```sh
python3 tools/macos/manage-services.py stop
python3 tools/macos/manage-services.py start
```

`stop` unloads the jobs for this login session. The files remain, so the jobs
start at the next login. To stop automatic startup, use `uninstall`.
Never use `launchctl kickstart -k` as the normal stop command; it can skip the
application's normal shutdown. These commands can interrupt a current chat.

## Saved logs

`.openbot/mac-services/logs/{app,gateway,woof}.jsonl` contains UTC timestamps,
start events, child PIDs, requested shutdown signals, and exit codes. The app
log also records the supervisor's fixed component-exit messages. The runner
appends across restarts and rotates each log at 1 MiB, keeping seven old files.
Logs and local setup files are private and ignored by Git.

Arbitrary child output is discarded. It can contain credentials or user text.
The lifecycle logs deliberately do not save commands, environment values,
requests, chat text, or exception messages. A SIGKILL or power loss cannot write
a final shutdown event. A later `starting` event without an earlier `exited`
event shows an incomplete shutdown; it does not prove its cause. Log rotation
limits history, so copy relevant lifecycle files before long investigations.

Run the focused process test:

```sh
python3 scripts/mac-services-e2e.py
```

It writes `.openbot-build/mac-services-e2e/report.json`. A live restart check must
also confirm that launchd starts a new PID and that the private phone API returns
HTTP 200. Do this while the host has no active work.

## Remove

```sh
python3 tools/macos/manage-services.py uninstall
```

This unloads only this checkout's jobs and removes only their LaunchAgent files.
It preserves agents, chats, pairing, local keys, model files, and saved logs.
Restart the manual commands in the Mac guide if required. Existing Tailscale
Serve routes, the other service on port 443, and Ollama are not changed.

## Verification on 2026-11-10

Installed all three jobs on the setup Mac. Each child process restarted after
a test SIGTERM. Controlled stop/start passed after adding a wait for launchd
unload to finish. The private API and voice HTTPS endpoints returned HTTP 200,
and the existing host reported online. Saved lifecycle logs contained shutdown
events with private file permissions. Phone reconnection and startup after a
real logout or reboot remain unverified. No reboot was done.
