// Run with Bun. Exercise the real gateway against an isolated HTTP fixture.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

let upstreamCalls = 0;
const upstream = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  async fetch(request) {
    upstreamCalls += 1;
    if (request.method === "POST") {
      assert.equal(request.headers.get("authorization"), "Bearer test-session");
      assert.equal(await request.text(), '{"fixture":true}');
      return Response.json({ forwarded: true });
    }
    return new Response("Authentication required", { status: 401 });
  },
});
const reservation = Bun.serve({ hostname: "127.0.0.1", port: 0, fetch: () => new Response() });
const gatewayPort = reservation.port;
reservation.stop(true);
const child = Bun.spawn(
  [process.execPath, fileURLToPath(new URL("../tools/tailnet/phone-gateway.mjs", import.meta.url))],
  {
    env: { ...process.env, OPENBOT_API_PORT: String(upstream.port), OPENBOT_PHONE_GATEWAY_PORT: String(gatewayPort) },
    stdout: "pipe",
    stderr: "inherit",
  },
);
try {
  const ready = await Promise.race([
    child.stdout.getReader().read(),
    child.exited.then(() => {
      throw new Error("Gateway exited before readiness");
    }),
  ]);
  assert.match(new TextDecoder().decode(ready.value), /gateway ready/);
  const base = `http://127.0.0.1:${gatewayPort}`;
  for (const path of ["/api/browser/auth/email/start", "/v1/email/start", "/v2/remote/hosts/register", "/app"]) {
    assert.equal((await fetch(base + path)).status, 403);
  }
  assert.equal(upstreamCalls, 0);
  assert.equal((await fetch(`${base}/v1/mobile-auth/session`)).status, 401);
  const forwarded = await fetch(`${base}/v1/mobile-auth/redeem`, {
    method: "POST",
    headers: { authorization: "Bearer test-session", "content-type": "application/json" },
    body: '{"fixture":true}',
  });
  assert.deepEqual(await forwarded.json(), { forwarded: true });
  assert.equal((await fetch(`${base}//v1/skills`)).status, 401);
  assert.equal(upstreamCalls, 3);
  const report = {
    passed: true,
    checks: [
      "remote login and host registration blocked",
      "session requires authentication",
      "phone request body and authorization preserved",
    ],
  };
  await mkdir(".openbot-build/tailnet-gateway-e2e", { recursive: true });
  await writeFile(".openbot-build/tailnet-gateway-e2e/report.json", JSON.stringify(report, null, 2));
  process.stdout.write("Phone gateway E2E passed. Report: .openbot-build/tailnet-gateway-e2e/report.json\n");
} finally {
  child.kill();
  await child.exited;
  upstream.stop(true);
}
