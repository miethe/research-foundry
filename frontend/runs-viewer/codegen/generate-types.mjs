/**
 * generate-types.mjs — P2-TS-CODEGEN
 *
 * Reads all 20 schemas/*.schema.yaml files from the repo root, converts YAML
 * to JSON-Schema, and uses json-schema-to-typescript to emit TypeScript
 * interfaces into src/types/rf/.
 *
 * Usage:
 *   node codegen/generate-types.mjs
 *   # or:
 *   pnpm run codegen
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

const SCHEMA_FILES = [
  "arc_review_request.schema.yaml",
  "ccdash_event.schema.yaml",
  "claim_ledger.schema.yaml",
  "evidence_bundle.schema.yaml",
  "extraction_card.schema.yaml",
  "foundry.schema.yaml",
  "ibom.schema.yaml",
  "intenttree_node.schema.yaml",
  "intenttree_update.schema.yaml",
  "meatywiki_writeback.schema.yaml",
  "notebooklm_update.schema.yaml",
  "raw_idea.schema.yaml",
  "report_frontmatter.schema.yaml",
  "research_brief.schema.yaml",
  "research_intent.schema.yaml",
  "review_packet.schema.yaml",
  "routing_decision.schema.yaml",
  "skillbom_candidate.schema.yaml",
  "source_card.schema.yaml",
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
const barrel = ["/* AUTO-GENERATED barrel — do not edit by hand. Run `pnpm codegen` to regenerate. */\n"];

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
    writeFileSync(outPath, ts, "utf-8");
    console.log(`  ✓ ${schemaFile} → ${outFile}`);
    barrel.push(`export * from "./${baseName}.generated.js";`);
    generatedCount++;
  } catch (err) {
    console.error(`  ✗ ${schemaFile}: ${err.message}`);
  }
}

// Write barrel (re-exports all generated files)
// Note: .js extension needed in ESM barrel for bundler resolution
writeFileSync(join(OUT_DIR, "generated.ts"), barrel.join("\n") + "\n", "utf-8");

console.log(`\nCodegen complete: ${generatedCount}/${SCHEMA_FILES.length} schemas → src/types/rf/`);
