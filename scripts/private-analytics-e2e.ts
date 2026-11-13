// Exercise the real report transport against a local HTTP capture server.
import { mkdir, writeFile } from "node:fs/promises";
import { OPTIONAL_ANALYTICS_ENABLED, openPanelTransport, type Report } from "@openbot/telemetry";
import { Effect } from "effect";

let requests = 0;
const server = Bun.serve({
  hostname: "127.0.0.1",
  port: 0,
  fetch() {
    requests += 1;
    return new Response(null, { status: 202 });
  },
});
try {
  const report: Report = {
    id: "privacy-check",
    timestamp: new Date().toISOString(),
    profileId: "synthetic-account",
    name: "client_operation_failed",
    surface: "desktop",
    app_version: "0.0.0",
    platform: "darwin",
    event_schema_version: 1,
    properties: { operation: "auth", source: "auth", cause_code: "authentication", severity: "error" },
  };
  const transport = openPanelTransport({ clientId: "synthetic", endpoint: `http://127.0.0.1:${server.port}/track` });
  await Effect.runPromise(transport(report, new AbortController().signal));
  await Effect.runPromise(transport({ ...report, profileId: null }, new AbortController().signal));
  if (OPTIONAL_ANALYTICS_ENABLED || requests !== 0) throw new Error("Optional analytics must send no requests.");
  await mkdir(".openbot-build/private-analytics-e2e", { recursive: true });
  await writeFile(
    ".openbot-build/private-analytics-e2e/report.json",
    JSON.stringify({
      passed: true,
      identifiedRequests: 0,
      anonymousRequests: 0,
      policyEnabled: OPTIONAL_ANALYTICS_ENABLED,
    }),
  );
  process.stdout.write("Passed: identified and anonymous reports made zero HTTP requests.\n");
} finally {
  await server.stop(true);
}
