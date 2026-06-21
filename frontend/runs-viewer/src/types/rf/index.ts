/**
 * RF Types — public barrel for the runs-viewer.
 *
 * Re-exports:
 *   1. run-export.ts  — hand-written RFRunExport / RFClaim / RFResolvedSource etc.
 *      (matches the frozen run.json contract from rf-run-export-schema.md)
 *   2. generated files — auto-generated from all 20 schemas/*.schema.yaml files
 *      (run `pnpm codegen` to regenerate)
 *
 * Consumers should import from "@/types/rf" only, not from sub-files.
 */

// Hand-written run.json contract types (primary import for hooks/screens)
export type {
  RFSensitivity,
  RFStatusDerived,
  RFClaimType,
  RFClaimStatus,
  RFClaimConfidence,
  RFMateriality,
  RFSourceRelation,
  RFSourceType,
  RFSourceRank,
  RFResolvedSource,
  RFInferenceBasis,
  RFReportLocation,
  RFClaim,
  RFClaimCounts,
  RFVerificationCheck,
  RFVerification,
  RFGovernanceBlock,
  RFTimelineEvent,
  RFArtifactSchemaVersions,
  RFWritebackTarget,
  RFRunWritebacksSummary,
  RFRunExport,
  RFRunSummary,
  ReusableOutputCandidate,
} from "./run-export.js";

// Auto-generated schema types (run `pnpm codegen` to regenerate)
export type { SourceCard }                from "./source_card.generated.js";
export type { ClaimLedger }               from "./claim_ledger.generated.js";
export type { EvidenceBundle }            from "./evidence_bundle.generated.js";
export type { ExtractionCard }            from "./extraction_card.generated.js";
export type { FoundryWorkspaceManifest }  from "./foundry.generated.js";
export type { ResearchIntent }            from "./research_intent.generated.js";
export type { ResearchBrief }             from "./research_brief.generated.js";
export type { SwarmPlan }                 from "./swarm_plan.generated.js";
export type { ReviewPacket }              from "./review_packet.generated.js";
export type { ArcReviewRequest }          from "./arc_review_request.generated.js";
export type { CCDashEvent }               from "./ccdash_event.generated.js";
export type { MeatyWikiWriteback }        from "./meatywiki_writeback.generated.js";
export type { NotebookLMUpdateCandidate } from "./notebooklm_update.generated.js";
export type { IBOM }                      from "./ibom.generated.js";
export type { IntentTreeNode }            from "./intenttree_node.generated.js";
export type { IntentTreeUpdateCandidate } from "./intenttree_update.generated.js";
export type { RawIdea }                   from "./raw_idea.generated.js";
export type { ReportFrontMatter }         from "./report_frontmatter.generated.js";
export type { RoutingDecision }           from "./routing_decision.generated.js";
export type { SkillBOMCandidate }         from "./skillbom_candidate.generated.js";
