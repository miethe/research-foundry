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
import { buildOutline, computeBlockAuditSummary, computeDraftAuditSummary, computeDraftIssues } from "@/lib/builderCoverage";
import type { BuilderOutlineSection } from "@/lib/builderCoverage";
import { MOCK_REPORT_DRAFT } from "@/lib/builderMocks";
import { formatRelativeTime } from "@/lib/format";
import type { CatalogItemSummary } from "@/types/rf/catalog";
import type { ReportBlockType } from "@/types/rf/report_draft";
import "@/styles/builder.css";

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

  const sectionCoverage = useMemo(() => {
    if (!draft || !activeSection) return computeDraftAuditSummary([], []);
    const scoped = activeSection.bodyBlockIds.map((id) => blocksById.get(id)).filter((b): b is NonNullable<typeof b> => Boolean(b));
    return computeDraftAuditSummary(scoped, draft.claim_links);
  }, [draft, activeSection, blocksById]);

  const paragraphSummary = useMemo(() => {
    if (!draft) return computeDraftAuditSummary([], []);
    return selectedBlock ? computeBlockAuditSummary(selectedBlock, draft.claim_links) : computeDraftAuditSummary(draft.blocks, draft.claim_links);
  }, [draft, selectedBlock]);

  const issues = useMemo(() => (draft ? computeDraftIssues(draft.blocks, draft.claim_links) : []), [draft]);

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
        <BuilderCatalogPane basketIds={new Set(basket.map((i) => i.catalog_item_id))} onToggleBasket={handleToggleBasket} />

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
          onSelectBlock={setSelectedBlockId}
          onCommitBlockMarkdown={handleCommitMarkdown}
          onRemoveClaimLink={handleRemoveClaimLink}
          onInsertBlock={handleInsertBlock}
          onToggleShowClaimChips={() => setShowClaimChips((v) => !v)}
        />

        <BuilderAuditInspector
          selectedBlock={selectedBlock}
          claimLinks={draft.claim_links}
          summary={paragraphSummary}
          issues={issues}
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
    </div>
  );
}

export default BuilderScreen;
