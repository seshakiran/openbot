import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { speechTextFromMarkdown } from "../packages/contracts/src/speech-text";

assert.equal(speechTextFromMarkdown("<think>Do not speak this.</think>Ready."), "Ready.");
assert.equal(speechTextFromMarkdown("<think>Still thinking"), "");
assert.equal(speechTextFromMarkdown("<analysis>Hidden.</analysis>117 tokens/sec"), "117 tokens per second.");
assert.equal(speechTextFromMarkdown("**Ready**. [Docs](https://example.com)"), "Ready. Docs.");
assert.equal(speechTextFromMarkdown("<think>First <analysis>Nested.</analysis>Still hidden.</think>Ready."), "Ready.");
assert.equal(speechTextFromMarkdown("```html\n<think>\n```\nReady."), "Ready.");
await mkdir(".openbot-build/speech-text-e2e", { recursive: true });
await writeFile(
  ".openbot-build/speech-text-e2e/report.json",
  JSON.stringify(
    {
      passed: true,
      checks: ["reasoning excluded", "unfinished reasoning withheld", "spoken speed units", "markdown retained"],
    },
    null,
    2,
  ),
);
process.stdout.write("Speech text E2E passed.\n");
