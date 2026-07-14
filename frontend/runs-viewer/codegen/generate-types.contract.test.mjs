import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const RUNS_VIEWER = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(RUNS_VIEWER, "../..");
const OPENAPI_PATH = join(REPO_ROOT, "src/research_foundry/api/openapi.json");
const GENERATED_PATH = join(RUNS_VIEWER, "src/types/rf/assertions_api.generated.ts");
const BARREL_PATH = join(RUNS_VIEWER, "src/types/rf/generated.ts");

const openapi = JSON.parse(readFileSync(OPENAPI_PATH, "utf8"));
for (const path of [
  "/api/assertions/search",
  "/api/assertions/{assertion_id}",
  "/api/assertions/{assertion_id}/lineage",
]) {
  assert.ok(openapi.paths[path], `committed OpenAPI must include ${path}`);
}

execFileSync(process.execPath, ["codegen/generate-types.mjs", "--check"], {
  cwd: RUNS_VIEWER,
  stdio: "pipe",
});

const generated = readFileSync(GENERATED_PATH, "utf8");
for (const typeName of [
  "AssertionSearchCursor",
  "AssertionSearchRequest",
  "AssertionSearchDenialResponse",
  "RightsDecision",
  "AssertionSearchResponse",
  "EvidencePacket",
  "AssertionLineage",
]) {
  assert.match(generated, new RegExp(`(?:interface|type) ${typeName}\\b`));
}
assert.match(generated, /cursor\?: AssertionSearchCursor;/);
assert.match(generated, /next_cursor: AssertionSearchCursor;/);
assert.match(
  readFileSync(BARREL_PATH, "utf8"),
  /export \* from "\.\/assertions_api\.generated\.js";/,
);

console.log("Assertion OpenAPI TypeScript contract is current.");
