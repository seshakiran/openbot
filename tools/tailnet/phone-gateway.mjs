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
const timeoutMs = Number(process.env.OPENBOT_PHONE_UPSTREAM_TIMEOUT_MS ?? 15000);
if (!Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 30000) throw new Error("Invalid upstream deadline");
const diagnostics = process.env.OPENBOT_PHONE_GATEWAY_DIAGNOSTICS === "1";
const gatewayPort = port("OPENBOT_PHONE_GATEWAY_PORT", 3110);
Bun.serve({
  hostname: "127.0.0.1",
  port: gatewayPort,
  maxRequestBodySize: 10 * 1024 * 1024,
  async fetch(request) {
    const url = new URL(request.url);
    const started = performance.now();
    const record = (status) => {
      if (!diagnostics) return;
      const route = url.pathname.startsWith("/v2/remote/sessions") ? "remote-session" : "phone-api";
      process.stdout.write(
        `${JSON.stringify({ route, status, durationMs: Math.round(performance.now() - started) })}\n`,
      );
    };
    if (!developmentNetworkRequestAllowed("tailnet", url.pathname)) {
      return new Response("This endpoint is not available through the phone gateway.", { status: 403 });
    }
    const target = new URL(upstream);
    target.pathname = url.pathname;
    target.search = url.search;
    const headers = new Headers(request.headers);
    headers.delete("host");
    for (const field of (headers.get("connection") ?? "").split(",")) {
      if (field.trim()) headers.delete(field.trim());
    }
    for (const field of [
      "connection",
      "content-length",
      "transfer-encoding",
      "keep-alive",
      "te",
      "trailer",
      "upgrade",
      "proxy-authorization",
      "proxy-authenticate",
    ])
      headers.delete(field);
    headers.delete("forwarded");
    headers.delete("x-forwarded-for");
    headers.delete("x-forwarded-host");
    headers.delete("x-forwarded-proto");
    const deadline = AbortSignal.timeout(timeoutMs);
    const signal = AbortSignal.any([request.signal, deadline]);
    try {
      const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
      const response = await fetch(
        new Request(target, {
          method: request.method,
          headers,
          body,
          redirect: "manual",
          signal,
        }),
      );
      record(response.status);
      return response;
    } catch {
      const status = deadline.aborted ? 504 : 502;
      record(status);
      return new Response("OpenBot is unavailable.", { status });
    }
  },
});
process.stdout.write(`OpenBot phone gateway ready on 127.0.0.1:${gatewayPort}\n`);
