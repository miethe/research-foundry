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
import process from "node:process";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";
import { compile } from "json-schema-to-typescript";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");
const SCHEMAS_DIR = join(REPO_ROOT, "schemas");
const OUT_DIR = join(__dirname, "../src/types/rf");
const OPENAPI_PATH = join(REPO_ROOT, "src/research_foundry/api/openapi.json");
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

const ASSERTION_COMPONENTS = [
  "RightsDecision",
  "AssertionSummary",
  "AssertionFacets",
  "AssertionSearchResponse",
  "EvidencePacket",
  "AssertionLineage",
];

const ASSERTION_PATHS = [
  "/api/assertions/search",
  "/api/assertions/{assertion_id}",
  "/api/assertions/{assertion_id}/lineage",
];

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

function asObject(value, description) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`OpenAPI ${description} must be an object`);
  }
  return value;
}

function refName(ref) {
  const prefix = "#/components/schemas/";
  if (typeof ref !== "string" || !ref.startsWith(prefix)) {
    throw new Error(`Unsupported OpenAPI schema reference: ${ref}`);
  }
  return ref.slice(prefix.length);
}

function schemaType(schema) {
  const value = asObject(schema, "schema");
  if (value.$ref) return refName(value.$ref);
  if (Array.isArray(value.anyOf)) {
    return [...new Set(value.anyOf.map(schemaType))].join(" | ");
  }
  if (value.type === "array") return `Array<${schemaType(value.items ?? {})}>`;
  if (value.type === "object" || value.additionalProperties) {
    if (value.additionalProperties && value.additionalProperties !== true) {
      return `Record<string, ${schemaType(value.additionalProperties)}>`;
    }
    return "Record<string, unknown>";
  }
  if (value.type === "integer" || value.type === "number") return "number";
  if (value.type === "boolean") return "boolean";
  if (value.type === "string") return "string";
  if (value.type === "null") return "null";
  return "unknown";
}

function propertyName(name) {
  return /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(name) ? name : JSON.stringify(name);
}

function renderInterface(name, schema, typeOverrides = {}) {
  const properties = asObject(schema.properties, `${name}.properties`);
  const required = new Set(schema.required ?? []);
  const lines = Object.entries(properties).map(([property, definition]) => {
    const optional = required.has(property) ? "" : "?";
    return `  ${propertyName(property)}${optional}: ${typeOverrides[property] ?? schemaType(definition)};`;
  });
  return `export interface ${name} {\n${lines.join("\n")}\n}`;
}

function renderAssertionApiTypes() {
  const openapi = JSON.parse(readFileSync(OPENAPI_PATH, "utf8"));
  const paths = asObject(openapi.paths, "paths");
  const schemas = asObject(openapi.components?.schemas, "components.schemas");

  for (const path of ASSERTION_PATHS) {
    if (!paths[path]) throw new Error(`OpenAPI assertion path is missing: ${path}`);
  }
  for (const name of ASSERTION_COMPONENTS) {
    if (!schemas[name]) throw new Error(`OpenAPI assertion component is missing: ${name}`);
  }

  const searchOperation = asObject(paths["/api/assertions/search"].get, "search operation");
  const parameters = Array.isArray(searchOperation.parameters)
    ? searchOperation.parameters
    : [];
  const searchParameters = Object.fromEntries(
    parameters.map((parameter) => {
      const item = asObject(parameter, "search parameter");
      if (item.in !== "query" || typeof item.name !== "string") {
        throw new Error("OpenAPI assertion search parameters must be named query parameters");
      }
      return [item.name, item];
    }),
  );
  const cursor = searchParameters.cursor;
  if (!cursor?.schema) throw new Error("OpenAPI assertion search cursor is missing");

  const requestLines = Object.entries(searchParameters).map(([name, parameter]) => {
    const optional = parameter.required ? "" : "?";
    const type = name === "cursor" ? "AssertionSearchCursor" : schemaType(parameter.schema);
    return `  ${propertyName(name)}${optional}: ${type};`;
  });
  const responseProperties = asObject(
    schemas.AssertionSearchResponse.properties,
    "AssertionSearchResponse.properties",
  );
  if (!responseProperties.next_cursor || !responseProperties.denial_reason) {
    throw new Error("OpenAPI assertion search response is missing cursor or denial fields");
  }

  return `/** Generated from src/research_foundry/api/openapi.json. Do not edit manually. */
export type AssertionSearchCursor = ${schemaType(cursor.schema)};

export interface AssertionSearchRequest {
${requestLines.join("\n")}
}

${ASSERTION_COMPONENTS.map((name) => renderInterface(
  name,
  schemas[name],
  name === "AssertionSearchResponse" ? { next_cursor: "AssertionSearchCursor" } : {},
)).join("\n\n")}

/** A rights-denied search result uses the normal response envelope with no results. */
export interface AssertionSearchDenialResponse {
  items: Array<never>;
  next_cursor: null;
  facets: AssertionFacets;
  denial_reason: string;
}
`;
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

writeGenerated(
  join(OUT_DIR, "assertions_api.generated.ts"),
  renderAssertionApiTypes(),
);
barrel.push('export * from "./assertions_api.generated.js";');

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
