# OpenBot app and web setup

Source reviewed: `seshakiran/openbot`, commit `28b1b1123`.
Review date: 2026-11-09. Local startup and initial UI checks completed.

## Intended result

Run persistent AI agents with a choice of MiniMax, OpenAI or Claude. Access the same
host from desktop, mobile and a browser. Save shared agent and provider settings on
that host. Keep credentials out of browser storage, logs and source control.

## Existing implementation

| Requirement | Source evidence | Next action |
| --- | --- | --- |
| Desktop app | Electron entry points in `src/main`, shared SolidJS UI in `src/renderer` and `packages/ui` | Start the existing app in its isolated development profile. |
| Mobile app | Expo app in `apps/mobile` | Reuse the existing app. Check each required settings action on a real connection. |
| Web GUI | `src/renderer/src/features/web-client`, served by `apps/auth-api` at `/app` | Reuse the browser client and existing host connection. |
| OpenAI backend | Existing Codex provider and Codex API-key capability | Choose account sign-in or API-key use, then test a turn. |
| Claude backend | Existing Claude provider and Claude API-key capability | Choose account sign-in or API-key use, then test a turn. |
| MiniMax backend | Custom OpenAI-compatible endpoint support, `src/main/custom-provider-store.ts` | Add MiniMax through the custom endpoint form and test the selected model. No dedicated MiniMax preset was found. |
| Web provider settings | `web-provider-admin.ts` supports provider keys and custom endpoint create/update/delete | Verify owner/admin permissions, save, reload and deletion. |
| Mobile provider settings | `apps/mobile/src/features/servers/screens/server-custom-provider-screen.tsx` | Complete the mobile edit and API-key entry gaps before claiming full parity. |
| Remote access | Auth API, Signal, TURN and Team API; `docs/self-hosted-server.md` | Select the host and account service before deployment. |

## Host layout

Desktop, mobile and web connect to one OpenBot host. The host runs the agent
runtimes and stores the workspace and SQLite database. Model requests leave the
host through the chosen provider. Account and connection services handle sign-in
and remote connection setup. Reuse the existing Team API and capability checks.
Do not add a second database or a new HTTP proxy for configuration.

A Mac host must remain awake and online for access. An always-on Linux host is
supported through the existing server or Docker setup. A fully private account
service also needs its own Signal, TURN, signing keys, email delivery and browser
origin. The upstream browser at `openbot.run/app` cannot use a different account
service. See `docs/self-hosting.md`.

## MiniMax configuration

The official OpenAI-compatible base URL is `https://api.minimax.io/v1`:
<https://platform.minimax.io/docs/api-reference/text-openai-api>.

Use the existing custom endpoint form. Enter a model ID available to the user's
account. Keep the model ID and context limits editable. Do not assume every account
has the same models or key entitlement. Let the existing OpenCode or Pi harness run
the endpoint; do not redirect the Claude adapter to a different model vendor.

Before release, test streamed text, tool calls across several turns, reasoning
history, cancellation, usage reporting and restart recovery. An API-compatible
endpoint alone does not prove the agent harness works with every model.

## Remaining implementation

1. Use this Mac as the first host. The requested reference is grok.com and Grok Bot.
   Start with Claude. Detailed feature parity remains to be defined.
2. Install the repository-pinned Bun version, then run `bun install --frozen-lockfile`.
   Completed: Bun 1.4.2 is installed under ignored `.openbot/toolchain`.
   The locked dependency installation completed successfully.
3. Start the existing isolated development stack. Do not deploy the full upstream
   service configuration: it contains upstream domains and production assumptions.
4. Configure one provider and verify a complete task before adding the other two.
5. Add mobile custom endpoint editing with the existing `custom-provider-edit-v1`
   capability, including retention, replacement and removal of saved credentials.
6. Add mobile Codex and Claude API-key controls if API-key configuration on the phone
   is required. Reuse the released key capabilities and host permission checks.
7. Verify that changes made on one client appear on the other clients after refresh
   and reconnect. Include non-admin refusal, deletion and sign-out.
8. Configure the chosen remote host and check app/web reconnection from an external
   network. Keep the current audience until an explicit access change is requested.

## Verification limits

The isolated development stack is running on this Mac. The local API is at
`http://localhost:3100`, the browser client is at `http://localhost:3100/app`,
and Signal listens on port 3101. Electron started successfully and its
accessibility tree was inspected. The development profile contains sample agents
and sample chats from the upstream seed.

Claude was downloaded through the existing provider installer. A later UI read
showed Claude usage in the page rail; a successful Claude reply has not been
verified. The browser client loaded its account sign-in screen; browser sign-in
remains unverified. The iPhone completed account pairing over Tailscale. After
fixing the missing Electron Signal-origin setting, the Mac host reported online.
On 2026-11-09, the user confirmed that the iPhone could see the agents. A complete
phone chat remains unverified. No production service was deployed.

The local toolchain is not on the system PATH. To run this checkout in a terminal:

```sh
export PATH="$PWD/.openbot/toolchain/node_modules/@oven/bun-darwin-aarch64/bin:$PATH"
bun run dev
```

Use `bun run dev:stop` for this checkout when the development stack is no longer
needed. A development stack is not yet an always-on production installation.

The fork retains PolyForm Noncommercial 1.0.0. A commercial launch needs a separate
license decision; preserve the repository license during implementation.


## Native phone access over Tailscale

See [Mac and iPhone over Tailscale](mac-iphone-tailscale.md) for the repeatable setup,
security boundaries, checks and restart commands. All device names, local settings
and pairing credentials are excluded from the tracked examples.
