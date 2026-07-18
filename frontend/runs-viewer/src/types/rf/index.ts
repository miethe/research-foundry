/**
 * RF Types — public barrel for the runs-viewer.
 *
 * Re-exports:
 *   1. run-export.ts  — hand-written RFRunExport / RFClaim / RFResolvedSource etc.
 *      (matches the frozen run.json contract from rf-run-export-schema.md)
 *   2. generated files — auto-generated from all 27 viewer-consumed schemas/*.schema.yaml files
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
  RFReportAnchorRelation,
  RFReportAnchorClaimLink,
  RFReportAnchorBlock,
  RFClaim,
  RFPersistentReferences,
  RFClaimCounts,
  RFVerificationCheck,
  RFVerification,
  RFGovernanceBlock,
  RFTimelineEvent,
  RFArtifactSchemaVersions,
  RFWritebackTarget,
  RFWritebackPreview,
  RFRunWritebacksSummary,
  RFRunExport,
  RFRunSummary,
  ReusableOutputCandidate,
} from "./run-export.js";

// Evidence Catalog types (public-multiuser-p0p1, Phase 1)
export type {
  CatalogItemType,
  CatalogItemSummary,
  CatalogLinkEdge,
  CatalogItemLinks,
  CatalogItemDetail,
  CatalogSortKey,
  CatalogSearchParams,
  CatalogSearchFacets,
  CatalogSearchResult,
  CatalogStats,
} from "./catalog.js";

// Report Builder draft types (public-multiuser-p2p3, Phase 3 / Wave F)
export type {
  ReportDraftOrigin,
  ReportAudience,
  ReportDraftStatus,
  ReportBlockType,
  ReportBlockMateriality,
  ReportCoverageStatus,
  ReportClaimRelation,
  ReportLinkStatus,
  ReportBlock,
  ReportClaimLink,
  ReportSourceLink,
  ReportRevisionPointer,
  ReportReviewState,
  ReportDraft,
  ReportDraftSummary,
  ReportVerifyCheck,
  ReportVerifyResult,
  ReportPublishPreviewResult,
  CreateDraftRequest,
  AddBlockRequest,
  UpdateBlockRequest,
  AddClaimLinkRequest,
  AddSourceLinkRequest,
  CreateRevisionRequest,
} from "./report_draft.js";

// Auto-generated schema types (run `pnpm codegen` to regenerate)
export type { SourceCard }                from "./source_card.generated.js";
export type {
  AssertionSearchRequest,
  AssertionSearchResponse,
  AssertionSearchDenialResponse,
  AssertionSummary,
  AssertionFacets,
  EvidencePacket,
  AssertionLineage,
  AssertionImpactSummary,
  AssertionImpactAction,
  RightsDecision,
} from "./assertions_api.generated.js";
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
export type { AssertionEvaluation }        from "./assertion_evaluation.generated.js";
export type { AssertionLifecycleEvent }    from "./assertion_lifecycle_event.generated.js";
export type { CanonicalClaim }             from "./canonical_claim.generated.js";
export type { InferenceRecord }            from "./inference_record.generated.js";
export type { Passage }                    from "./passage.generated.js";
export type { SourceAssertion }            from "./source_assertion.generated.js";
export type { SourceEdition }              from "./source_edition.generated.js";
