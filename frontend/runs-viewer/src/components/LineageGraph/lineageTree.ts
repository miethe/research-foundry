import type { RFClaim, RFResolvedSource, RFRunExport } from "@/types/rf";
import {
  deriveClaimTitle,
  deriveExtractionTitle,
  deriveReportLocationTitle,
  deriveRunTitle,
  deriveSourceTitle,
  deriveWritebackTitle,
} from "@/lib/runs";

export type LineageNodeKind = "run" | "source" | "extraction" | "claim" | "report" | "writeback";

export interface LineageDetail {
  label: string;
  value: string;
  href?: string;
}

export interface LineageNode {
  id: string;
  kind: LineageNodeKind;
  title: string;
  subtitle?: string;
  chips?: string[];
  details?: LineageDetail[];
  claimId?: string;
  children: LineageNode[];
}

export function buildLineageTree(run: RFRunExport): LineageNode[] {
  const sourceMap = new Map<string, { source: RFResolvedSource; claims: RFClaim[] }>();
  const unsourcedClaims: RFClaim[] = [];

  for (const claim of run.claims) {
    if (claim.sources.length === 0) {
      unsourcedClaims.push(claim);
      continue;
    }

    for (const source of claim.sources) {
      const sourceId = source.source_card_id || "unknown-source";
      const existing = sourceMap.get(sourceId);
      if (existing) {
        existing.claims.push(claim);
      } else {
        sourceMap.set(sourceId, { source, claims: [claim] });
      }
    }
  }

  const sourceNodes = Array.from(sourceMap.values()).map(({ source, claims }) => buildSourceNode(source, uniqueClaims(claims), run));
  if (unsourcedClaims.length > 0) {
    sourceNodes.push({
      id: "source:unlinked",
      kind: "source",
      title: "Unlinked claims",
      subtitle: "Claims without exported source cards",
      chips: [`${unsourcedClaims.length} claim(s)`],
      details: [{ label: "State", value: "No source card references were exported for these claims." }],
      children: unsourcedClaims.map((claim) => buildClaimNode(claim, run)),
    });
  }

  return [
    {
      id: `run:${run.run_id}`,
      kind: "run",
      title: deriveRunTitle(run),
      subtitle: run.run_id,
      chips: [run.status_derived, `${run.claims.length} claim(s)`],
      details: compactDetails([
        detail("Created", run.created_at),
        detail("Sensitivity", run.sensitivity ?? run.sensitivity_threshold),
        detail("Verification", run.verification?.passed === true ? "passed" : run.verification?.passed === false ? "failed" : "not exported"),
        detail("Writeback", run.writebacks?.required_fix ?? (run.writebacks?.targets?.length ? `${run.writebacks.targets.length} target(s)` : null)),
        run.claims.length === 0 ? detail("State", "No claims are exported for this run.") : null,
      ]),
      children: sourceNodes,
    },
  ];
}

function buildSourceNode(source: RFResolvedSource, claims: RFClaim[], run: RFRunExport): LineageNode {
  const extractionGroups = new Map<string, { source: RFResolvedSource; claims: RFClaim[] }>();

  for (const claim of claims) {
    const matchingSources = claim.sources.filter((candidate) => candidate.source_card_id === source.source_card_id);
    for (const matchingSource of matchingSources) {
      const key = `${matchingSource.source_card_id}:${matchingSource.evidence_id || "unknown-evidence"}`;
      const existing = extractionGroups.get(key);
      if (existing) existing.claims.push(claim);
      else extractionGroups.set(key, { source: matchingSource, claims: [claim] });
    }
  }

  return {
    id: `source:${source.source_card_id}`,
    kind: "source",
    title: deriveSourceTitle(source),
    subtitle: source.source_card_id,
    chips: [source.source_type ?? "source", source.trust?.source_rank ?? "unknown", source.sensitivity ?? "public"],
    details: compactDetails([
      detail("URL", source.url, source.url ?? undefined),
      detail("Source type", source.source_type),
      detail("Rank", source.trust?.source_rank),
      detail("Sensitivity", source.sensitivity),
      detail("Usage", source.usage?.citation_required ? "Citation required" : source.usage ? "Usage policy exported" : null),
      detail("Limitations", source.trust?.known_limitations?.join("; ")),
      detail("Reliability", source.trust?.reliability_notes),
    ]),
    children: Array.from(extractionGroups.values()).map(({ source: extractionSource, claims: extractionClaims }) => ({
      id: `extraction:${extractionSource.source_card_id}:${extractionSource.evidence_id || "unknown-evidence"}`,
      kind: "extraction",
      title: deriveExtractionTitle(extractionSource),
      subtitle: extractionSource.evidence_id || extractionSource.evidence_locator || extractionSource.locator || "No evidence id",
      chips: [extractionSource.relation, extractionSource.dangling ? "dangling" : "resolved"],
      details: compactDetails([
        detail("Evidence ID", extractionSource.evidence_id),
        detail("Locator", extractionSource.evidence_locator ?? extractionSource.locator),
        detail("Relation", extractionSource.relation),
        detail("State", extractionSource.dangling || extractionSource.resolved === false ? "dangling" : "resolved"),
        detail("Quote", extractionSource.quote),
        detail("Summary", extractionSource.summary),
      ]),
      children: uniqueClaims(extractionClaims).map((claim) => buildClaimNode(claim, run)),
    })),
  };
}

function buildClaimNode(claim: RFClaim, run: RFRunExport): LineageNode {
  const reportNodes: LineageNode[] = (claim.report_locations ?? []).map((location, index) => ({
    id: `report:${claim.claim_id}:${location.paragraph_id ?? location.heading ?? index}`,
    kind: "report",
    title: deriveReportLocationTitle(location),
    subtitle: [location.file, location.paragraph_id].filter(Boolean).join(" / ") || "Report location",
    chips: [],
    details: compactDetails([
      detail("File", location.file),
      detail("Heading", location.heading),
      detail("Paragraph", location.paragraph_id),
      detail("Claim", claim.claim_id),
    ]),
    claimId: claim.claim_id,
    children: [],
  }));

  if (reportNodes.length === 0 && run.report_draft) {
    reportNodes.push({
      id: `report:${claim.claim_id}:draft`,
      kind: "report",
      title: "Draft report",
      subtitle: "No paragraph locator exported",
      chips: [],
      details: compactDetails([
        detail("Claim", claim.claim_id),
        detail("State", "Report text exists, but no paragraph locator was exported for this claim."),
      ]),
      claimId: claim.claim_id,
      children: [],
    });
  }

  const writebackNodes: LineageNode[] = (run.writebacks?.targets ?? []).map((target, index) => ({
    id: `writeback:${claim.claim_id}:${target.destination ?? target.name ?? index}`,
    kind: "writeback",
    title: deriveWritebackTitle(target),
    subtitle: [target.destination, target.status].filter(Boolean).join(" / ") || "Writeback target",
    chips: target.status ? [target.status] : [],
    details: compactDetails([
      detail("Name", target.name),
      detail("Destination", target.destination),
      detail("Status", target.status),
      detail("URL", target.url, target.url ?? undefined),
      detail("Required fix", run.writebacks?.required_fix),
    ]),
    claimId: claim.claim_id,
    children: [],
  }));

  return {
    id: `claim:${claim.claim_id}`,
    kind: "claim",
    title: deriveClaimTitle(claim),
    subtitle: claim.claim_id,
    chips: [claim.status ?? "unknown", claim.claim_type ?? "claim", claim.confidence ?? "unknown", `${claim.sources.length} source(s)`],
    details: compactDetails([
      detail("Claim ID", claim.claim_id),
      detail("Type", claim.claim_type),
      detail("Status", claim.status),
      detail("Materiality", claim.materiality),
      detail("Confidence", claim.confidence),
      detail("Sources", `${claim.sources.length}`),
      detail("Report locations", `${claim.report_locations?.length ?? 0}`),
      claim.sources.some((source) => source.dangling || source.resolved === false) ? detail("Warning", "Dangling source reference") : null,
      (claim.claim_type === "inference" || claim.status === "inference") && (claim.inference_basis?.from_claims ?? []).length === 0
        ? detail("Warning", "Inference basis is empty")
        : null,
      claim.status === "mixed" || claim.status === "contradicted" ? detail("Warning", `Claim status is ${claim.status}`) : null,
    ]),
    claimId: claim.claim_id,
    children: [...reportNodes, ...writebackNodes],
  };
}

function detail(label: string, value?: string | number | null, href?: string): LineageDetail | null {
  if (value == null || value === "") return null;
  return { label, value: String(value), href };
}

function compactDetails(details: (LineageDetail | null)[]): LineageDetail[] {
  return details.filter((item): item is LineageDetail => item != null);
}

function uniqueClaims(claims: RFClaim[]): RFClaim[] {
  const seen = new Set<string>();
  return claims.filter((claim) => {
    if (seen.has(claim.claim_id)) return false;
    seen.add(claim.claim_id);
    return true;
  });
}
