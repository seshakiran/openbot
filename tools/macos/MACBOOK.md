# Connect a MacBook to the private host

The current desktop source reads `OPENBOT_AUTH_API_URL` at startup. Opening an
invitation does not change this setting. A normal installed app uses the public
account service, which is why it asks for email sign-in before the server list.

The existing phone gateway blocks desktop email login routes. Keep that rule.
Do not expose the development API directly through Tailscale Serve: development
login can return a sign-in code without email delivery.

## Private connection

`connect-desktop.py` starts an SSH tunnel bound to `127.0.0.1` on the MacBook.
SSH connects to the host through Tailscale and forwards the host's loopback
account API on port 3100. The launcher then starts the installed OpenBot app
with that private API and the existing Tailscale Signal address on port 8444.
It uses a separate `OpenBot Sentinels` profile, so the normal app profile stays
available. Agents and chats still run on the host.

This is an owner connection. Use the same account email as the host. The account
directory lists that account's existing hosts, so an invitation is not required.
This method does not add support for invitations from a different private
account service. It does not change released link validation or trust rules.

## Host requirements

- Keep the managed OpenBot services running and the Mac awake and logged in.
- Keep Tailscale connected on both Macs under the same tailnet.
- macOS Remote Login must already allow your Mac user. Review its access list
  before enabling it on another host. The setup Mac already had SSH available;
  this change does not enable it or change its settings.
- Confirm the host's SSH fingerprint with its owner before accepting a new key.
  On the host, use `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`.

## Download on the MacBook

Open Terminal on the MacBook and run:

```sh
mkdir -p "$HOME/Downloads/Sentinels-Connect"
cd "$HOME/Downloads/Sentinels-Connect"
curl --fail --location --output connect-desktop.py https://raw.githubusercontent.com/seshakiran/openbot/main/tools/macos/connect-desktop.py
curl --fail --location --output Connect-Sentinels.command https://raw.githubusercontent.com/seshakiran/openbot/main/tools/macos/Connect-Sentinels.command
curl --fail --location --output MACBOOK.md https://raw.githubusercontent.com/seshakiran/openbot/main/tools/macos/MACBOOK.md
curl --fail --location --output block-analytics.py https://raw.githubusercontent.com/seshakiran/openbot/main/tools/macos/block-analytics.py
# Read block-analytics.py before running it with sudo.
sudo python3 block-analytics.py install
python3 block-analytics.py status
sh Connect-Sentinels.command
```

The analytics block adds a marked entry to `/etc/hosts` for
`analytics.openbot.run`, on IPv4 and IPv6. It applies to all applications on this
Mac, and keeps the other hosts entries. Close OpenBot before installing it.
It does not block the private account service, Signal or LLM providers.
The launcher refuses to start if DNS does not confirm the block. For removal,
run `sudo python3 block-analytics.py remove`; this restores analytics network
access for old binaries and the private launcher will then refuse to start.

The launcher asks for the host's Tailscale hostname and Mac login short name.
It does not include a real hostname, user name, password or API key. Read the
requirements above before starting. If `python3` is missing, install Python 3
before running the launcher. If OpenBot is installed outside `/Applications`,
use the explicit `--app` command described below.

## MacBook steps

1. Copy `connect-desktop.py`, `block-analytics.py` and `Connect-Sentinels.command` from this directory
   to one folder on the MacBook. Python 3 and the OpenBot app are required.
2. Install and verify the analytics block as shown above. Close the normal OpenBot app to avoid confusion between its two profiles.
3. Open Terminal in that folder and run:

```sh
python3 connect-desktop.py --host example.tail123456.ts.net --user example
```

Replace the hostname with the Sentinels Mac's Tailscale DNS name, and the user
with that Mac's login short name. Do not use an email address as the SSH user.
You can also open `Connect-Sentinels.command`; it asks for those two values.

4. Check the SSH host fingerprint. Enter the Mac login password if SSH asks.
   The launcher does not read or save that password. SSH can also use an existing
   authorized key. Do not turn off SSH host-key checking.
5. In the app, use the same email as the Sentinels owner. Select **Send sign-in
   code**. The development code appears in the app. Enter that code; no email
   is sent. Select **Sentinels** in the server list, then open **Hanu**.
6. Keep the launcher terminal open while using this client. Quit this app or
   press Ctrl-C in that terminal to close the client and tunnel. The host keeps
   running. Run the launcher again for the next session.

If OpenBot is in another folder, add `--app '/path/to/OpenBot.app'`. The default
local tunnel port is 43100; if it is busy, use `--port 43101`. Never change a
previously used profile's port casually: its account service address changes.
The default profile is `~/Library/Application Support/OpenBot Sentinels` on the
MacBook. Do not use the host's database or copy a live database into it.

## Checks and limits

- On 2026-11-12, the setup Mac accepted TCP connections on SSH port 22, and
  Tailscale reported the MacBook peer online. This does not prove SSH login.
- The process E2E test passed for loopback binding, SSH host-key checking options,
  API readiness, app environment, separate profile, occupied-port refusal and
  tunnel cleanup. It uses transport and app process fixtures.
- The installed MacBook app, real SSH authentication, development-code display,
  host discovery and a remote Hanu reply still require a check on the MacBook.
  No new desktop build or installer is included.
- If the app does not show a development code, stop there and report the screen.
  An older app can require an update. Do not expose login routes to work around it.
- If SSH drops, the launcher closes only its client and tunnel. It does not
  reconnect automatically or stop the host's agents. Tailscale must stay on.
- The launcher does not save app output, login codes, passwords or tokens.
  macOS can show a Keychain prompt for the separate profile.

Run the focused process test from the repository root:

```sh
python3 scripts/mac-desktop-connect-e2e.py
```

The report is saved under `.openbot-build/mac-desktop-connect-e2e/` and is ignored
by Git. Generated packages with a real hostname or user must also stay ignored.

## Privacy policy of this fork

This source disables optional product analytics, anonymous usage events, failure
reports, account and sales analytics, public-site analytics and Signal capacity
reports. The shared report transport also refuses sends. A saved preference
cannot enable these collectors. Existing reports and database records are kept;
they are not sent or deleted by this change.

The installed MacBook app is an older binary. The local destination block is
required until it is replaced by a build of this source. The block covers the
analytics hostname found in this source audit; it is not a general firewall or
a promise about every future upstream binary. The installed iPhone app also
needs a new build to receive the source policy. This change does not deploy a
public account service or install a new phone build.

Tailscale and SSH still handle the connection. LLM providers receive requests
you send to them. Updates, catalogs, visited pages and plugins can also use the
network. Local diagnostics stay on the computer unless you share them. These
required or user-requested connections are not optional analytics.

## Connection progress reported on 2026-11-12

The MacBook resolved the host after accepting Tailscale DNS. The user confirmed
SSH host-key acceptance and password authentication. The launcher reported that
the private account API was ready and the app was starting. This confirms the
tunnel and API path, but does not yet confirm sign-in or a Hanu reply.

## Privacy checks on 2026-11-12

| Surface | Result |
| --- | --- |
| Shared failure transport | Identified and anonymous reports made zero HTTP requests to a local capture server. |
| Account and sales collectors | Six focused E2E checks passed; no event or email identity was sent, and an existing pending row stayed unchanged. |
| Desktop launcher | Private connection fixture passed; an unblocked analytics destination was refused. |
| Hosts-file helper | Existing entries survived two installs; removal restored the fixture; malformed markers were refused. |
| Type and lint checks | Focused Node and account API checks passed; changed TypeScript files passed Biome. |
| Installed MacBook and iPhone | Network block and updated phone build still need device checks. |

The hosts-file test uses a private fixture. It does not change the test computer's
`/etc/hosts`. No public service was deployed as part of these checks.
