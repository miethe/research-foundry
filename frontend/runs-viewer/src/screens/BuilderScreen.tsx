/**
 * BuilderScreen — Report Builder workspace (public-multiuser-p2p3, Phase 3 / Wave F).
 *
 * Accessible at /builder (AppShell nav flipped disabled -> enabled by this
 * wave). Layout mirrors
 * docs/project_plans/design-specs/assets/public-multiuser-release/mockup-report-builder.png:
 *   LEFT   BuilderCatalogPane — catalog search (reuses useCatalog hooks)
 *   CENTER BuilderDraftCard   — ONE card: shared header + title, with
 *                               BuilderOutline as its left sub-column and
 *                               BuilderBlockEditor as its content pane
 *                               (F2 polish-pass fix — these used to render
 *                               as two separate cards)
 *   RIGHT  BuilderAuditInspector — coverage/issues/sources + verify/publish gate
 *   BOTTOM ClaimBasket           — staged claims/sources pending insertion
 *
 * DUAL-MODE / LOOPBACK-ONLY (see api/reportsClient.ts header for the full
 * rationale): in static mode every mutation is rejected client-side, so this
 * screen renders a persistent read-only banner and hydrates from the bundled
 * demo draft (lib/builderMocks.ts) instead of a live draft — that is this
 * feature's "read-only published drafts or a disabled state" choice.
 *
 * CONTRACT CAVEAT: the Builder HTTP API (Wave E) has not landed yet. This
 * screen is built and tested entirely against the typed client in
 * api/reportsClient.ts + the mock draft; wire-format assumptions are
 * documented there and in types/rf/report_draft.ts.
 */
import { useEffect, useMemo, useState } from "react";
import {
  isBuilderLoopbackEnabled,
  useAddReportBlock,
  useAddReportClaimLink,
  useAddReportSourceLink,
  useCreateReportDraft,
  usePublishPreviewReportDraft,
  useRemoveReportClaimLink,
  useReportDraft,
  useReportDraftList,
  useUpdateReportBlock,
  useVerifyReportDraft,
} from "@/hooks";
import { BuilderCatalogPane } from "@/components/Builder/BuilderCatalogPane";
import { BuilderDraftCard } from "@/components/Builder/BuilderDraftCard";
import { BuilderAuditInspector } from "@/components/Builder/BuilderAuditInspector";
import { ClaimBasket } from "@/components/Builder/ClaimBasket";
import { DetailModal } from "@/components/RunDetail/DetailModal";
import type { DetailModalPayload, IssueDetail } from "@/components/RunDetail/DetailModal";
import { buildOutline, computeBlockAuditSummary, computeDraftAuditSummary, computeDraftIssues } from "@/lib/builderCoverage";
import type { BuilderIssue, BuilderOutlineSection } from "@/lib/builderCoverage";
import { CLAIM_PREVIEW_UNKNOWN, MOCK_REPORT_DRAFT } from "@/lib/builderMocks";
import { useBuilderClaimPreviewResolver } from "@/hooks";
import { formatRelativeTime } from "@/lib/format";
import type { RFClaim, RFResolvedSource } from "@/types/rf";
import type { CatalogItemSummary } from "@/types/rf/catalog";
import type { ReportBlockType } from "@/types/rf/report_draft";
import "@/styles/builder.css";

const assertNever = (value: never): never => {
  throw new Error(`Unhandled builder issue key: ${String(value)}`);
};

export function BuilderScreen() {
  const loopback = isBuilderLoopbackEnabled();

  // ── Draft selection ──────────────────────────────────────────────────────
  const draftList = useReportDraftList();
  const createDraft = useCreateReportDraft();
  const [activeDraftId, setActiveDraftId] = useState<string | null>(loopback ? null : MOCK_REPORT_DRAFT.report_draft_id);

  useEffect(() => {
    if (!loopback || activeDraftId) return;
    if (draftList.data && draftList.data.length > 0) setActiveDraftId(draftList.data[0].report_draft_id);
  }, [loopback, activeDraftId, draftList.data]);

  const draftQuery = useReportDraft(activeDraftId);
  const draft = draftQuery.data;

  // ── Mutations ────────────────────────────────────────────────────────────
  const updateBlock = useUpdateReportBlock();
  const addBlock = useAddReportBlock();
  const addClaimLink = useAddReportClaimLink();
  const removeClaimLink = useRemoveReportClaimLink();
  const addSourceLink = useAddReportSourceLink();
  const verifyMutation = useVerifyReportDraft();
  const publishMutation = usePublishPreviewReportDraft();

  const disabled = !loopback;

  // ── Local UI state ───────────────────────────────────────────────────────
  const [activeHeadingBlockId, setActiveHeadingBlockId] = useState<string | null>(null);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [basket, setBasket] = useState<CatalogItemSummary[]>([]);
  const [basketCollapsed, setBasketCollapsed] = useState(false);
  const [showClaimChips, setShowClaimChips] = useState(true);
  const [detailPayload, setDetailPayload] = useState<DetailModalPayload | null>(null);

  const outline: BuilderOutlineSection[] = useMemo(() => (draft ? buildOutline(draft.blocks) : []), [draft]);

  useEffect(() => {
    if (outline.length === 0) return;
    if (!activeHeadingBlockId || !outline.some((s) => s.headingBlockId === activeHeadingBlockId)) {
      setActiveHeadingBlockId(outline[0].headingBlockId);
      setSelectedBlockId(outline[0].bodyBlockIds[0] ?? outline[0].headingBlockId);
    }
  }, [outline, activeHeadingBlockId]);

  const blocksById = useMemo(() => new Map((draft?.blocks ?? []).map((b) => [b.block_id, b])), [draft]);
  const activeSection = outline.find((s) => s.headingBlockId === activeHeadingBlockId) ?? null;
  const selectedBlock = selectedBlockId ? blocksById.get(selectedBlockId) ?? null : null;

  // Mode-aware claim-preview resolver (runs-viewer-builder-live-claim-previews):
  // static mode delegates to the synchronous mock dict unchanged; loopback
  // mode fetches GET /catalog/items/{catalog_item_id} per distinct claim.
  // Threaded into builderCoverage.ts's pure functions AND the two components
  // below instead of each importing resolveBuilderClaimPreview() directly.
  //
  // builder-claim-previews-loading-affordance: previously `isLoading` was
  // dropped here, so a claim mid-fetch resolved to the SAME "unknown"
  // sentinel as a genuinely unresolvable claim and the audit surfaces
  // rendered confident-looking-but-wrong coverage/issue counts for the
  // duration of the fetch. Both `previewsLoading` (draft-wide, for
  // section-level affordances) and `isPending` (per-claim, for chip-level
  // affordances) are threaded into BuilderDraftCard/BuilderAuditInspector so
  // pending can render as pending instead of as unresolved.
  const {
    resolve: resolveClaimPreview,
    isLoading: previewsLoading,
    isPending: isClaimPreviewPending,
  } = useBuilderClaimPreviewResolver(draft?.claim_links ?? []);

  const sectionCoverage = useMemo(() => {
    if (!draft || !activeSection) return computeDraftAuditSummary([], [], resolveClaimPreview);
    const scoped = activeSection.bodyBlockIds.map((id) => blocksById.get(id)).filter((b): b is NonNullable<typeof b> => Boolean(b));
    return computeDraftAuditSummary(scoped, draft.claim_links, resolveClaimPreview);
  }, [draft, activeSection, blocksById, resolveClaimPreview]);

  const paragraphSummary = useMemo(() => {
    if (!draft) return computeDraftAuditSummary([], [], resolveClaimPreview);
    return selectedBlock
      ? computeBlockAuditSummary(selectedBlock, draft.claim_links, resolveClaimPreview)
      : computeDraftAuditSummary(draft.blocks, draft.claim_links, resolveClaimPreview);
  }, [draft, selectedBlock, resolveClaimPreview]);

  const issues = useMemo(
    () => (draft ? computeDraftIssues(draft.blocks, draft.claim_links, resolveClaimPreview) : []),
    [draft, resolveClaimPreview],
  );

  const draftClaims = useMemo<RFClaim[]>(() => {
    if (!draft) return [];
    const claimIds = Array.from(new Set(draft.claim_links.map((link) => link.claim_id)));
    return claimIds.flatMap((claimId) => {
      const preview = resolveClaimPreview(claimId);
      if (preview === CLAIM_PREVIEW_UNKNOWN) return [];
      // Coerce builder-preview materiality ("narrative"|"material"|"background") to
      // RFMateriality ("core"|"background"|"style"|"material"): narrative → background.
      const materiality = preview.materiality === "narrative" ? "background" : preview.materiality;
      return [{
        claim_id: preview.claim_id,
        text: preview.text,
        materiality,
        claim_type: preview.status === "inference" || preview.status === "speculation" ? preview.status : "factual",
        status: preview.status,
        // Fix pass: RFClaimConfidence has no "unknown" member, and the detail
        // modal already renders `claim.confidence ?? "unknown"` (see
        // ClaimAuditWorkbench.tsx) — omit rather than fabricate.
        confidence: preview.confidence === "unknown" ? undefined : preview.confidence,
        sources: preview.sources,
      } satisfies RFClaim];
    });
  }, [draft, resolveClaimPreview]);

  const linkedRefsByItemId = useMemo(() => {
    const refs = new Map<string, string[]>();
    function add(refId: string | null | undefined, blockId: string | null | undefined) {
      if (!refId || !blockId) return;
      const current = refs.get(refId) ?? [];
      if (!current.includes(blockId)) refs.set(refId, [...current, blockId]);
    }
    for (const link of draft?.claim_links ?? []) {
      add(link.claim_id, link.block_id);
      add(link.catalog_item_id, link.block_id);
    }
    for (const link of draft?.source_links ?? []) {
      add(link.source_card_id, link.block_id);
      add(link.catalog_item_id, link.block_id);
    }
    return refs;
  }, [draft]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  function handleSelectSection(headingBlockId: string) {
    setActiveHeadingBlockId(headingBlockId);
    const section = outline.find((s) => s.headingBlockId === headingBlockId);
    setSelectedBlockId(section?.bodyBlockIds[0] ?? headingBlockId);
  }

  function handleCommitMarkdown(blockId: string, markdown: string) {
    if (disabled || !draft) return;
    updateBlock.mutate({ reportDraftId: draft.report_draft_id, args: { blockId, payload: { markdown } } });
  }

  function handleRemoveClaimLink(claimLinkId: string) {
    if (disabled || !draft) return;
    removeClaimLink.mutate({ reportDraftId: draft.report_draft_id, args: claimLinkId });
  }

  function handleInsertBlock(blockType: ReportBlockType) {
    if (disabled || !draft) return;
    addBlock.mutate({ reportDraftId: draft.report_draft_id, args: { block_type: blockType, markdown: "" } });
  }

  function handleAddSection() {
    if (disabled || !draft) return;
    addBlock.mutate({ reportDraftId: draft.report_draft_id, args: { block_type: "heading", markdown: "## New section" } });
  }

  function handleToggleBasket(item: CatalogItemSummary) {
    setBasket((prev) =>
      prev.some((i) => i.catalog_item_id === item.catalog_item_id)
        ? prev.filter((i) => i.catalog_item_id !== item.catalog_item_id)
        : [...prev, item],
    );
  }

  function handleInsertFromBasket(item: CatalogItemSummary) {
    if (disabled || !draft || !selectedBlockId) return;
    if (item.item_type === "source") {
      addSourceLink.mutate({
        reportDraftId: draft.report_draft_id,
        args: { source_card_id: item.local_ref, block_id: selectedBlockId, catalog_item_id: item.catalog_item_id },
      });
    } else {
      addClaimLink.mutate({
        reportDraftId: draft.report_draft_id,
        args: { block_id: selectedBlockId, claim_id: item.local_ref, catalog_item_id: item.catalog_item_id },
      });
    }
  }

  function handleCreateDraft() {
    createDraft.mutate({ origin: "blank", title: "Untitled Report" }, { onSuccess: (d) => setActiveDraftId(d.report_draft_id) });
  }

  function handleOpenClaim(claimId: string) {
    setDetailPayload({ kind: "claim", claimId, claims: draftClaims });
  }

  function handleOpenSource(source: RFResolvedSource) {
    setDetailPayload({ kind: "source", source });
  }

  function issueSeverity(category: BuilderIssue): IssueDetail["severity"] {
    return category.severity === "critical" ? "error" : "warning";
  }

  function deriveIssueItems(category: BuilderIssue): IssueDetail[] {
    if (!draft) return [];
    switch (category.key) {
      case "contradictions":
        return draft.claim_links
          .filter((link) => link.relation === "contradicts")
          .map((link) => ({
            id: link.claim_link_id,
            block_id: link.block_id,
            claim_id: link.claim_id,
            message: `Claim ${link.claim_id} is linked as contradicting this block.`,
            severity: "error",
            hint: "Review whether the block should be revised or the contradictory claim should be removed.",
          }));
      case "weak_confidence": {
        const byLink = draft.claim_links
          .filter((link) => {
            const preview = resolveClaimPreview(link.claim_id);
            return preview !== CLAIM_PREVIEW_UNKNOWN && preview.confidence === "low";
          })
          .map((link) => ({
            id: link.claim_link_id,
            block_id: link.block_id,
            claim_id: link.claim_id,
            message: `Claim ${link.claim_id} has low confidence.`,
            severity: "warning" as const,
            hint: "Look for stronger corroborating evidence before publishing.",
          }));
        const byBlock = draft.blocks
          .filter((block) => block.risk_flags.includes("weak_confidence"))
          .map((block) => ({
            id: `${block.block_id}:weak_confidence`,
            block_id: block.block_id,
            message: "This block is flagged for weak confidence.",
            severity: "warning" as const,
            hint: "Review the linked evidence and claim confidence before publishing.",
          }));
        return [...byLink, ...byBlock];
      }
      case "unresolved_claim":
        return draft.claim_links
          .filter((link) => resolveClaimPreview(link.claim_id) === CLAIM_PREVIEW_UNKNOWN)
          .map((link) => ({
            id: link.claim_link_id,
            block_id: link.block_id,
            claim_id: link.claim_id,
            message: `Claim ${link.claim_id} could not be resolved from the catalog.`,
            severity: "warning" as const,
            hint: "The linked claim id may be stale, or the catalog item may have been removed.",
          }));
      case "confidence_unknown":
        return draft.claim_links
          .filter((link) => {
            const preview = resolveClaimPreview(link.claim_id);
            return preview !== CLAIM_PREVIEW_UNKNOWN && preview.confidence === "unknown";
          })
          .map((link) => ({
            id: link.claim_link_id,
            block_id: link.block_id,
            claim_id: link.claim_id,
            message: `Claim ${link.claim_id} resolved, but has no recorded confidence score.`,
            severity: "warning" as const,
            hint: "The catalog item has no confidence value — treat this claim as unscored, not as medium confidence.",
          }));
      case "citation_needed":
        return draft.blocks
          .filter((block) => block.materiality === "material" && !draft.claim_links.some((link) => link.block_id === block.block_id))
          .map((block) => ({
            id: `${block.block_id}:citation_needed`,
            block_id: block.block_id,
            message: "This material block has no linked claims.",
            severity: "warning" as const,
            hint: "Add a supporting claim or mark the block as narrative/background.",
          }));
      default:
        return assertNever(category.key);
    }
  }

  function handleOpenIssueCategory(category: BuilderIssue) {
    setDetailPayload({
      kind: "issues",
      category,
      issueItems: deriveIssueItems(category).map((item) => ({ ...item, severity: item.severity ?? issueSeverity(category) })),
    });
  }

  function sourceFromCatalogItem(item: CatalogItemSummary): RFResolvedSource {
    const source = {
      source_card_id: item.local_ref,
      evidence_id: item.local_ref,
      relation: "context",
      resolved: true,
      dangling: false,
      title: item.title,
      source_type: null,
      url: null,
      trust: null,
      usage: null,
      sensitivity: item.sensitivity,
      summary: item.summary,
      quote: null,
      run_id: item.run_id,
    } satisfies RFResolvedSource & { run_id: string };
    return source;
  }

  function findSourceByCardId(sourceCardId: string): RFResolvedSource | null {
    for (const claim of draftClaims) {
      const source = claim.sources.find((s) => s.source_card_id === sourceCardId);
      if (source) return source;
    }
    return null;
  }

  function handleOpenCatalogItem(item: CatalogItemSummary) {
    if (item.item_type === "claim" || item.item_type === "inference") {
      handleOpenClaim(item.local_ref);
      return;
    }
    if (item.item_type === "source") {
      handleOpenSource(findSourceByCardId(item.local_ref) ?? sourceFromCatalogItem(item));
      return;
    }
    handleOpenClaim(item.local_ref);
  }

  function handleFindClaimsForIssue(issue: IssueDetail) {
    if (issue.block_id) setSelectedBlockId(issue.block_id);
    if (issue.claim_id) handleOpenClaim(issue.claim_id);
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (loopback && !activeDraftId && !draftList.isLoading) {
    return (
      <div className="rv-builder rv-builder--empty" data-testid="builder-screen-empty">
        <div className="rv-builder-empty-state it-card">
          <h2>No report drafts yet</h2>
          <p className="rv-muted">Start a report from a blank draft, a run, or a catalog collection.</p>
          <button type="button" className="it-btn primary" onClick={handleCreateDraft} data-testid="builder-create-draft">
            + Blank draft
          </button>
        </div>
      </div>
    );
  }

  if (draftQuery.isLoading || !draft) {
    return (
      <div className="rv-builder rv-builder--loading" data-testid="builder-screen-loading">
        <p className="rv-loading">Loading draft…</p>
      </div>
    );
  }

  return (
    <div className="rv-builder" data-testid="builder-screen">
      <header className="rv-builder__topbar">
        <h1>Report Builder</h1>
        <label className="rv-builder__project-select" data-testid="builder-project-select">
          <span className="rv-builder__project-select-label">Project</span>
          <span className="rv-builder__project-select-value">{draft.project_id ?? "No project"}</span>
          <span aria-hidden="true">▾</span>
        </label>
        <span className="rv-builder__saved" data-testid="builder-saved-indicator">
          <span aria-hidden="true">✓</span> Saved {formatRelativeTime(draft.updated_at)}
        </span>
        <span className="rv-builder__topbar-spacer" />
        <div className="rv-builder__run-context" data-testid="builder-run-context">
          <span className="rv-builder__run-context-label">Run context</span>
          <span className="rv-builder__run-context-value" title={draft.source_run_id ?? undefined}>
            <code>{draft.source_run_id ?? "No linked run"}</code>
            <span aria-hidden="true">▾</span>
          </span>
        </div>
      </header>

      {disabled && (
        <div className="rv-builder__static-banner" role="note" data-testid="builder-static-banner">
          Report Builder is read-only in static mode — showing a bundled demo draft. Run against a loopback RF API
          (<code>VITE_RUNS_FRONTEND_LOOPBACK_API=true</code>) to create and edit drafts.
        </div>
      )}

      <div className="rv-builder__main">
        <BuilderCatalogPane
          basketIds={new Set(basket.map((i) => i.catalog_item_id))}
          onToggleBasket={handleToggleBasket}
          onExpand={handleOpenCatalogItem}
          linkedRefsByItemId={linkedRefsByItemId}
        />

        <BuilderDraftCard
          title={draft.title}
          schemaVersion={draft.schema_version}
          sensitivity={draft.sensitivity}
          outlineSections={outline}
          activeHeadingBlockId={activeHeadingBlockId}
          onSelectSection={handleSelectSection}
          onAddSection={handleAddSection}
          section={activeSection}
          blocksById={blocksById}
          claimLinks={draft.claim_links}
          selectedBlockId={selectedBlockId}
          sectionCoverage={sectionCoverage}
          showClaimChips={showClaimChips}
          disabled={disabled}
          resolveClaimPreview={resolveClaimPreview}
          previewsLoading={previewsLoading}
          isClaimPreviewPending={isClaimPreviewPending}
          onSelectBlock={setSelectedBlockId}
          onCommitBlockMarkdown={handleCommitMarkdown}
          onRemoveClaimLink={handleRemoveClaimLink}
          onOpenClaim={handleOpenClaim}
          onInsertBlock={handleInsertBlock}
          onToggleShowClaimChips={() => setShowClaimChips((v) => !v)}
        />

        <BuilderAuditInspector
          selectedBlock={selectedBlock}
          claimLinks={draft.claim_links}
          summary={paragraphSummary}
          issues={issues}
          resolveClaimPreview={resolveClaimPreview}
          previewsLoading={previewsLoading}
          onOpenIssueCategory={handleOpenIssueCategory}
          onOpenSource={handleOpenSource}
          disabled={disabled}
          onVerify={() => verifyMutation.mutate(draft.report_draft_id)}
          verifyPending={verifyMutation.isPending}
          verifyResult={verifyMutation.data ?? null}
          onPublishPreview={() => publishMutation.mutate(draft.report_draft_id)}
          publishPending={publishMutation.isPending}
          publishResult={publishMutation.data ?? null}
          currentVersionId={draft.current_version_id}
          updatedAt={draft.updated_at}
        />
      </div>

      <ClaimBasket
        items={basket}
        collapsed={basketCollapsed}
        onToggleCollapse={() => setBasketCollapsed((v) => !v)}
        onRemove={(id) => setBasket((prev) => prev.filter((i) => i.catalog_item_id !== id))}
        onInsert={handleInsertFromBasket}
        canInsert={Boolean(selectedBlockId)}
        disabled={disabled}
      />

      <DetailModal
        payload={detailPayload}
        onOpenChange={(open) => {
          if (!open) setDetailPayload(null);
        }}
        onFindClaimsForIssue={handleFindClaimsForIssue}
      />
    </div>
  );
}

export default BuilderScreen;
