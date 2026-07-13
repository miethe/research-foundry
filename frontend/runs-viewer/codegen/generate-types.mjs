/**
 * generate-types.mjs — P2-TS-CODEGEN
 *
 * Reads the 27 viewer-consumed schemas/*.schema.yaml files from the repo root, converts YAML
 * to JSON-Schema, and uses json-schema-to-typescript to emit TypeScript
 * interfaces into src/types/rf/.
 *
 * Usage:
 *   node codegen/generate-types.mjs
 *   # or:
 *   pnpm run codegen
 *   pnpm run codegen:check
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";
import { compile } from "json-schema-to-typescript";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");
const SCHEMAS_DIR = join(REPO_ROOT, "schemas");
const OUT_DIR = join(__dirname, "../src/types/rf");
const CHECK_ONLY = process.argv.includes("--check");

const SCHEMA_FILES = [
  "arc_review_request.schema.yaml",
  "assertion_evaluation.schema.yaml",
  "assertion_lifecycle_event.schema.yaml",
  "canonical_claim.schema.yaml",
  "ccdash_event.schema.yaml",
  "claim_ledger.schema.yaml",
  "evidence_bundle.schema.yaml",
  "extraction_card.schema.yaml",
  "foundry.schema.yaml",
  "ibom.schema.yaml",
  "inference_record.schema.yaml",
  "intenttree_node.schema.yaml",
  "intenttree_update.schema.yaml",
  "meatywiki_writeback.schema.yaml",
  "notebooklm_update.schema.yaml",
  "passage.schema.yaml",
  "raw_idea.schema.yaml",
  "report_frontmatter.schema.yaml",
  "research_brief.schema.yaml",
  "research_intent.schema.yaml",
  "review_packet.schema.yaml",
  "routing_decision.schema.yaml",
  "skillbom_candidate.schema.yaml",
  "source_card.schema.yaml",
  "source_assertion.schema.yaml",
  "source_edition.schema.yaml",
  "swarm_plan.schema.yaml",
];

// Compile options — optional fields MUST be emitted as TS optional (?)
const COMPILE_OPTIONS = {
  bannerComment: "/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */",
  additionalProperties: false,
  style: { singleQuote: false },
  unknownAny: false,
};

mkdirSync(OUT_DIR, { recursive: true });

let generatedCount = 0;
const staleFiles = [];
const barrel = ["/* AUTO-GENERATED barrel — do not edit by hand. Run `pnpm codegen` to regenerate. */\n"];

function writeGenerated(outPath, contents) {
  if (!CHECK_ONLY) {
    writeFileSync(outPath, contents, "utf-8");
    return;
  }
  let existing = "";
  try {
    existing = readFileSync(outPath, "utf-8");
  } catch {
    staleFiles.push(outPath);
    return;
  }
  if (existing !== contents) staleFiles.push(outPath);
}

for (const schemaFile of SCHEMA_FILES) {
  const schemaPath = join(SCHEMAS_DIR, schemaFile);
  const yamlSource = readFileSync(schemaPath, "utf-8");

  // Parse YAML → plain JS object (JSON-Schema)
  const jsonSchema = yaml.load(yamlSource);

  // Derive a clean output filename: strip .schema.yaml → _generated.ts
  // e.g. source_card.schema.yaml → source_card.generated.ts
  const baseName = schemaFile.replace(".schema.yaml", "");
  const outFile = `${baseName}.generated.ts`;
  const outPath = join(OUT_DIR, outFile);

  try {
    const ts = await compile(jsonSchema, jsonSchema.title ?? baseName, COMPILE_OPTIONS);
    writeGenerated(outPath, ts);
    console.log(`  ✓ ${schemaFile} → ${outFile}`);
    barrel.push(`export * from "./${baseName}.generated.js";`);
    generatedCount++;
  } catch (err) {
    console.error(`  ✗ ${schemaFile}: ${err.message}`);
  }
}

// Write barrel (re-exports all generated files)
// Note: .js extension needed in ESM barrel for bundler resolution
writeGenerated(join(OUT_DIR, "generated.ts"), barrel.join("\n") + "\n");

if (CHECK_ONLY && staleFiles.length) {
  console.error(`\nCodegen drift: ${staleFiles.length} generated file(s) differ. Run \`pnpm codegen\`.`);
  for (const staleFile of staleFiles) console.error(`  ✗ ${staleFile}`);
  process.exitCode = 1;
} else {
  console.log(`\nCodegen ${CHECK_ONLY ? "check passed" : "complete"}: ${generatedCount}/${SCHEMA_FILES.length} schemas → src/types/rf/`);
}
