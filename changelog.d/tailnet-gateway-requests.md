### Fixed

- Buffer phone API request bodies and remove transport headers before forwarding through the Tailscale gateway. Apply a 15-second upstream deadline so a stalled API returns a gateway timeout.
