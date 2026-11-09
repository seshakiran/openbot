#!/bin/sh
# Development-only phone access. No credentials belong in this file.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
if [ -x "$repo_root/.openbot/toolchain/node_modules/@oven/bun-darwin-aarch64/bin/bun" ]; then
  PATH="$repo_root/.openbot/toolchain/node_modules/@oven/bun-darwin-aarch64/bin:$PATH"
  export PATH
fi
export OPENBOT_API_PORT="${OPENBOT_API_PORT:-3100}"
export REMOTE_SIGNAL_PORT="${REMOTE_SIGNAL_PORT:-3101}"
export OPENBOT_PHONE_GATEWAY_PORT="${OPENBOT_PHONE_GATEWAY_PORT:-3110}"
export OPENBOT_TAILNET_API_PORT="${OPENBOT_TAILNET_API_PORT:-8443}"
export OPENBOT_TAILNET_SIGNAL_PORT="${OPENBOT_TAILNET_SIGNAL_PORT:-8444}"
for port in "$OPENBOT_API_PORT" "$REMOTE_SIGNAL_PORT" "$OPENBOT_PHONE_GATEWAY_PORT" "$OPENBOT_TAILNET_API_PORT" "$OPENBOT_TAILNET_SIGNAL_PORT"; do
  case "$port" in ''|*[!0-9]*) echo 'Ports must be integers from 1 to 65535.' >&2; exit 2;; esac
  if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then echo 'Port is out of range.' >&2; exit 2; fi
done
case "${1:-}" in
  gateway) exec bun tools/tailnet/phone-gateway.mjs ;;
  app)
    : "${OPENBOT_TAILNET_HOST:?Set OPENBOT_TAILNET_HOST to the full Tailscale DNS name of this Mac}"
    case "$OPENBOT_TAILNET_HOST" in *[!a-zA-Z0-9.-]*|.*|*..*) echo 'Invalid Tailscale hostname.' >&2; exit 2;; esac
    case "$OPENBOT_TAILNET_HOST" in *.ts.net) ;; *) echo 'Use the full Tailscale .ts.net hostname.' >&2; exit 2;; esac
    export OPENBOT_MOBILE_AUTH_API_URL="https://$OPENBOT_TAILNET_HOST:$OPENBOT_TAILNET_API_PORT"
    export REMOTE_SIGNAL_URL="wss://$OPENBOT_TAILNET_HOST:$OPENBOT_TAILNET_SIGNAL_PORT/v1/signal"
    export OPENBOT_REMOTE_SIGNAL_URL="$REMOTE_SIGNAL_URL"
    exec bun run dev
    ;;
  *) echo 'Usage: sh scripts/start-tailnet.sh gateway|app' >&2; exit 2 ;;
esac
