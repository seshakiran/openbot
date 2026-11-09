// Local phone-only gateway. Reuse the development server's remote route policy.
import { developmentNetworkRequestAllowed } from "../../apps/auth-api/dev-network-access.ts";

function port(name, fallback) {
  const value = process.env[name] ?? String(fallback);
  if (!/^\d+$/.test(value) || Number(value) < 1 || Number(value) > 65535) {
    throw new Error(`Invalid port: ${name}`);
  }
  return Number(value);
}
const upstream = `http://127.0.0.1:${port("OPENBOT_API_PORT", 3100)}`;
const gatewayPort = port("OPENBOT_PHONE_GATEWAY_PORT", 3110);
Bun.serve({
  hostname: "127.0.0.1",
  port: gatewayPort,
  maxRequestBodySize: 10 * 1024 * 1024,
  async fetch(request) {
    const url = new URL(request.url);
    if (!developmentNetworkRequestAllowed("tailnet", url.pathname)) {
      return new Response("This endpoint is not available through the phone gateway.", { status: 403 });
    }
    const target = new URL(upstream);
    target.pathname = url.pathname;
    target.search = url.search;
    const headers = new Headers(request.headers);
    headers.delete("host");
    headers.delete("connection");
    headers.delete("forwarded");
    headers.delete("x-forwarded-for");
    headers.delete("x-forwarded-host");
    headers.delete("x-forwarded-proto");
    try {
      return await fetch(
        new Request(target, {
          method: request.method,
          headers,
          body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
          redirect: "manual",
          signal: request.signal,
        }),
      );
    } catch {
      return new Response("OpenBot is unavailable.", { status: 502 });
    }
  },
});
process.stdout.write(`OpenBot phone gateway ready on 127.0.0.1:${gatewayPort}\n`);
