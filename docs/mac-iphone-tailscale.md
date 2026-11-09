# Run OpenBot on a Mac and connect an iPhone over Tailscale

This is the development setup used on 2026-11-09. The Mac runs Electron, the
account API and Signal. The iPhone uses the OpenBot phone app on another network.
Both devices must use the same Tailscale tailnet, with access allowed by its rules.
The Mac must stay awake. These processes do not start automatically after reboot.

## What we changed

We cloned this fork, installed Bun 1.4.2 and the locked dependencies, then started
`bun run dev`. We downloaded Claude through Server settings > Providers. Ollama
was already available at `http://127.0.0.1:11434`.

The first phone connection failed because development network detection selected
the Mac's Wi-Fi address. That address was not reachable from the remote phone.
Plain HTTP on a Tailscale `100.x` address also fails the phone's pairing URL rules.
We used private Tailscale HTTPS and secure WebSocket endpoints, then passed their
addresses explicitly to the development launcher.

The user reports that the iPhone connected. The assistant verified HTTPS, phone
API responses and the WebSocket handshake from the Mac. It did not observe a
complete chat on the phone. Browser sign-in and full provider tests remain open.

## Install and start

Use Node 24 and the Bun version in the root `packageManager` field. From the repo:

```sh
bun install --frozen-lockfile
```

If Bun was installed only under `.openbot/toolchain`, the launcher finds the local
Apple silicon package used in this setup. Otherwise install Bun normally and put
it on PATH. No global toolchain changes are required by these scripts.

Inspect existing Tailscale forwarding before adding anything:

```sh
tailscale serve status
```

For the Mac App Store version, the CLI can be at
`/Applications/Tailscale.app/Contents/MacOS/Tailscale`. Use that full path if
`tailscale` is not on PATH. Do not replace an existing Serve or Funnel endpoint.
Choose unused HTTPS ports. Our setup used 8443 and 8444 and preserved the existing
service on port 443.

Start the restricted phone API gateway in terminal 1:

```sh
sh scripts/start-tailnet.sh gateway
```

Add private HTTPS forwarding:

```sh
tailscale serve --bg --https=8443 http://127.0.0.1:3110
tailscale serve --bg --https=8444 http://127.0.0.1:3101
```

Tailscale may require HTTPS to be enabled in its admin console. Use Serve, not
Funnel: the endpoints must stay private to the tailnet. See the official
[Tailscale Serve guide](https://tailscale.com/docs/features/tailscale-serve).

In terminal 2, replace the example hostname with this Mac's full Tailscale DNS name:

```sh
export OPENBOT_TAILNET_HOST='your-mac.your-tailnet.ts.net'
sh scripts/start-tailnet.sh app
```

The launcher sets the phone API to `https://<host>:8443` and Signal to
`wss://<host>:8444/v1/signal`. Shell values are required: automatic Wi-Fi detection
can override network settings saved in `.openbot/dev-state.json`.

The default local ports are API 3100, Signal 3101 and phone gateway 3110. The
launcher supports `OPENBOT_API_PORT`, `REMOTE_SIGNAL_PORT`,
`OPENBOT_PHONE_GATEWAY_PORT`, `OPENBOT_TAILNET_API_PORT` and
`OPENBOT_TAILNET_SIGNAL_PORT`. Keep forwarding targets and both terminals aligned
when changing ports. If the supervisor reports a different allocated API or
Signal port, stop this checkout with `bun run dev:stop`, select unused ports and
restart both commands with matching settings. Never reuse another app's port.

## Pair the iPhone without email

1. Connect Tailscale on both devices to the same tailnet.
2. On the Mac, open OpenBot > Settings > Mobile Connect > Add phone.
3. In the OpenBot iPhone app, scan the new pairing code or open the pairing link
   on that phone. Use the app's pairing flow, not its public email sign-in flow.
4. Check that the link names the HTTPS Tailscale API, not a Wi-Fi address or
   `localhost`. Never post or commit the link: it grants account access.
5. Open an agent and send a short message. Confirm the reply on both devices.

A previously issued code can contain the old Wi-Fi address. Generate a fresh one
after changing the launch settings. A one-time code can expire or be used already.

No email sender is required for phone pairing. The local development account
service deliberately disables SMTP and returns a development code in the local
web login form. It will not send an email. The browser at
`http://localhost:3100/app` is a separate client; this phone gateway does not
publish the browser UI or browser login routes remotely.

## Security and excluded files

The gateway binds only to loopback and reuses the existing remote development
route allowlist in `apps/auth-api/dev-network-access.ts`. It forwards approved
phone routes and preserves their authentication. It blocks development email
login, browser login, host registration and routes outside that allowlist. It
does not print request bodies, headers, tokens or pairing links. Signal still
checks its connection tickets. Tailscale HTTPS terminates on the Mac and forwards
to loopback. Tailnet access rules still apply.

Do not forward port 8443 directly to the Vite API. A loopback proxy would bypass
its remote route guard and expose development login routes. Keep the restricted
gateway between Tailscale Serve and the account API.

Keep `.openbot/`, `.openbot-build/`, `.env.keys`, local env files, databases,
provider credentials, generated signing keys, device identity, logs and pairing
codes out of Git. The repository already ignores these local paths. Do not
commit the Mac's real tailnet hostname or home-directory path. Existing tracked
encrypted upstream env files are not changed by this setup.

## Checks and shutdown

Run the isolated gateway E2E check with Bun:

```sh
bun scripts/tailnet-gateway-e2e.mjs
```

It checks blocked routes, authentication refusal and request forwarding through a
real gateway process. It writes `.openbot-build/tailnet-gateway-e2e/report.json`.
It does not use a real account or phone.

The live setup checks returned HTTP 200 for `/v1/mobile/features`, HTTP 401 for
`/v1/mobile-auth/session` without a token, HTTP 403 for a development login route,
and a successful WSS handshake at `/v1/signal`. These are server checks; test the
actual iPhone connection after every network change.

Stop this checkout with `bun run dev:stop`, then stop the gateway with Ctrl-C in
its terminal. To remove only the forwarding added here:

```sh
tailscale serve --https=8443 off
tailscale serve --https=8444 off
```

Do not run `tailscale serve reset`: it would remove unrelated services.
