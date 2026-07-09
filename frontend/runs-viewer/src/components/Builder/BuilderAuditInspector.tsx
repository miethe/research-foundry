/**
 * BuilderAuditInspector — right panel of the Report Builder (P3 Wave F).
 *
 * Reuses the P2 Wave C audit surface's ideas (ReportCoverageStrip's overall-
 * score treatment, ClaimAuditWorkbench's ParagraphInspector "union of source
 * cards across linked claims" pattern, and SourceCard itself) but reads from
 * the DRAFT's own `claim_links`/`coverage_status` (already backend-computed
 * by builder_service.py) instead of run.json's `report_anchors` — a builder
 * draft is not an exported run, so lib/reportAnchors.ts's aggregation isn't
 * applicable here; lib/builderCoverage.ts is the draft-shaped equivalent.
 *
 * Verify Draft / Publish Preview call the D13 checks (services/verification.py
 * verify_draft) via the Builder API client and render the same
 * {id, severity, status, detail} check shape the backend already emits.
 *
 * F3 polish-pass overhaul: this panel is the signature surface of the
 * Builder, and the first pass read as flat/wireframe-grade. Fixes:
 *   - Each section is now a bordered, collapsible card with a bold header +
 *     a count/percent badge (not a flat uppercase micro-label).
 *   - Stat rows carry a 3px colored left-edge tick (green/blue/red/amber).
 *   - Issue rows use CORRECT severity: red only for Contradictions; amber ⚠
 *     for Weak/Low-confidence and Citation-needed (BuilderIssue.severity).
 *   - Verify Draft = outlined teal button w/ check icon. Publish Preview =
 *     green split-button w/ eye icon + a caret (visual affordance only; no
 *     secondary publish actions exist yet).
 *   - "Selected paragraph" header carries an "N% supported" pill; the
 *     coverage bar reads "—" (not a misleading 0%-filled bar) when the
 *     selected block has no chips to score (ParagraphAuditSummary.isApplicable).
 */
import { useState } from "react";
import { SourceCard } from "@/components/SourceCard/SourceCard";
import type { BuilderIssue, ParagraphAuditSummary } from "@/lib/builderCoverage";
import { resolveBuilderClaimPreview } from "@/lib/builderMocks";
import type { RFResolvedSource } from "@/types/rf";
import type { ReportBlock, ReportClaimLink, ReportPublishPreviewResult, ReportVerifyResult } from "@/types/rf/report_draft";

export interface BuilderAuditInspectorProps {
  selectedBlock: ReportBlock | null;
  claimLinks: ReportClaimLink[];
  summary: ParagraphAuditSummary;
  issues: BuilderIssue[];
  onOpenIssueCategory?: (category: { key: string; label: string; severity: string; count: number }) => void;
  onOpenSource?: (source: RFResolvedSource) => void;
  disabled: boolean;
  onVerify: () => void;
  verifyPending: boolean;
  verifyResult: ReportVerifyResult | null;
  onPublishPreview: () => void;
  publishPending: boolean;
  publishResult: ReportPublishPreviewResult | null;
  currentVersionId: string | null;
  updatedAt: string | null;
}

// ── Collapsible carded section ────────────────────────────────────────────────

function InspectorSection({
  title,
  badge,
  defaultOpen = true,
  testId,
  children,
}: {
  title: string;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  testId: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rv-builder-inspector__card" data-testid={testId}>
      <button
        type="button"
        className="rv-builder-inspector__card-header"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        data-testid={`${testId}-toggle`}
      >
        <span className="rv-builder-inspector__card-title">{title}</span>
        {badge}
        <span className={`rv-builder-inspector__caret${open ? " rv-builder-inspector__caret--open" : ""}`} aria-hidden="true">
          ▾
        </span>
      </button>
      {open && <div className="rv-builder-inspector__card-body">{children}</div>}
    </section>
  );
}

function StatRow({ tone, label, value }: { tone: "green" | "blue" | "red" | "amber"; label: string; value: number }) {
  return (
    <div className={`rv-builder-inspector__stat-row rv-builder-inspector__stat-row--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function coveragePillTone(pct: number): "green" | "amber" | "red" {
  if (pct >= 70) return "green";
  if (pct >= 40) return "amber";
  return "red";
}

const ISSUE_ICON: Record<BuilderIssue["severity"], string> = { critical: "⛔", warning: "⚠" };

function CheckList({ checks }: { checks: { id: string; severity: string; status: string; detail: string }[] }) {
  return (
    <ul className="rv-builder-check-list" data-testid="builder-check-list">
      {checks.map((c) => (
        <li key={c.id} className={`rv-builder-check-list__item rv-builder-check-list__item--${c.status}`}>
          <span className={`it-chip ${c.status === "pass" ? "green" : c.status === "fail" ? "red" : "orange"}`}>{c.status}</span>
          <span className="rv-builder-check-list__id">{c.id}</span>
          <span className="rv-builder-check-list__detail">{c.detail}</span>
        </li>
      ))}
    </ul>
  );
}

export function BuilderAuditInspector({
  selectedBlock,
  claimLinks,
  summary,
  issues,
  onOpenIssueCategory,
  onOpenSource,
  disabled,
  onVerify,
  verifyPending,
  verifyResult,
  onPublishPreview,
  publishPending,
  publishResult,
  currentVersionId,
  updatedAt,
}: BuilderAuditInspectorProps) {
  const [publishMenuOpen, setPublishMenuOpen] = useState(false);
  const blockLinks = selectedBlock ? claimLinks.filter((cl) => cl.block_id === selectedBlock.block_id) : [];
  const sourcesByCardId = new Map<string, RFResolvedSource>();
  for (const link of blockLinks) {
    for (const s of resolveBuilderClaimPreview(link.claim_id)?.sources ?? []) {
      if (!sourcesByCardId.has(s.source_card_id)) sourcesByCardId.set(s.source_card_id, s);
    }
  }
  const inferenceLinks = blockLinks.filter((l) => l.relation === "inferred_from");
  const totalIssues = issues.reduce((n, i) => n + i.count, 0);

  return (
    <aside className="rv-builder-inspector" aria-label="Audit inspector" data-testid="builder-audit-inspector">
      <div className="rv-pane-title">
        <h3>Audit Inspector</h3>
      </div>

      <InspectorSection
        title={selectedBlock ? "Selected paragraph" : "Draft overview"}
        testId="builder-inspector-selected"
        badge={
          summary.isApplicable ? (
            <span className={`it-chip ${coveragePillTone(summary.coveragePct)}`} data-testid="builder-inspector-pct-pill">
              {summary.coveragePct}% supported
            </span>
          ) : (
            <span className="it-chip" data-testid="builder-inspector-pct-pill">
              N/A
            </span>
          )
        }
      >
        <div className="rv-builder-inspector__stat-list">
          <StatRow tone="green" label="Supported claims" value={summary.supported} />
          <StatRow tone="blue" label="Inferences" value={summary.inferences} />
          <StatRow tone="red" label="Unsupported" value={summary.unsupported + summary.contradicted} />
          <StatRow tone="amber" label="Citation needed" value={summary.citationNeeded} />
        </div>
        <div className="rv-builder-inspector__coverage-score">
          <span>Coverage score</span>
          {summary.isApplicable ? (
            <>
              <span className="rv-builder-editor__coverage-bar">
                <span className="rv-builder-editor__coverage-fill" style={{ width: `${summary.coveragePct}%` }} />
              </span>
              <span>{summary.coveragePct}%</span>
            </>
          ) : (
            <span className="rv-muted">— not scored (narrative)</span>
          )}
        </div>
      </InspectorSection>

      <InspectorSection
        title="Issues"
        testId="builder-inspector-issues"
        badge={totalIssues > 0 ? <span className="it-chip orange">{totalIssues}</span> : <span className="it-chip green">0</span>}
      >
        <ul className="rv-builder-inspector__issue-list">
          {issues.map((issue) => {
            const rowContent = (
              <>
                <span className={`rv-builder-inspector__issue-icon rv-builder-inspector__issue-icon--${issue.severity}`} aria-hidden="true">
                  {issue.count > 0 ? ISSUE_ICON[issue.severity] : "•"}
                </span>
                <span className={issue.count > 0 ? `rv-builder-inspector__issue-flag rv-builder-inspector__issue-flag--${issue.severity}` : "rv-muted"}>
                  {issue.label}
                </span>
                <strong>{issue.count}</strong>
              </>
            );
            return (
              <li key={issue.key} data-severity={issue.severity} className={issue.count === 0 ? "rv-builder-inspector__issue--empty" : undefined}>
                {issue.count > 0 && onOpenIssueCategory ? (
                  <button
                    type="button"
                    className="rv-builder-inspector__issue-btn"
                    onClick={() => onOpenIssueCategory(issue)}
                    aria-label={`Open ${issue.label} issue group`}
                    data-testid={`builder-inspector-issue-${issue.key}`}
                  >
                    {rowContent}
                  </button>
                ) : (
                  <span className="rv-builder-inspector__issue-row">{rowContent}</span>
                )}
              </li>
            );
          })}
        </ul>
      </InspectorSection>

      <InspectorSection
        title="Source cards"
        testId="builder-inspector-sources"
        badge={<span className="it-chip">{sourcesByCardId.size}</span>}
      >
        {sourcesByCardId.size > 0 ? (
          <div className="rv-catalog-inspector__source-list">
            {Array.from(sourcesByCardId.values()).map((s) => (
              <button
                key={s.source_card_id}
                type="button"
                className="rv-builder-inspector__source-btn"
                onClick={() => onOpenSource?.(s)}
                disabled={!onOpenSource}
                aria-label={`Open source card ${s.source_card_id}`}
                data-testid={`builder-inspector-source-card-${s.source_card_id}`}
              >
                <SourceCard source={s} compact />
              </button>
            ))}
          </div>
        ) : (
          <p className="rv-muted">Select a paragraph with linked claims to see its source cards.</p>
        )}
      </InspectorSection>

      <InspectorSection
        title="Inference basis"
        testId="builder-inspector-inference-basis"
        badge={<span className="it-chip blue">{inferenceLinks.length}</span>}
      >
        {inferenceLinks.length > 0 ? (
          <div className="rv-catalog-inspector__basis-chips">
            {inferenceLinks.map((l) => (
              <span key={l.claim_link_id} className="it-chip blue">{l.claim_id}</span>
            ))}
          </div>
        ) : (
          <p className="rv-muted">No inferences in this paragraph.</p>
        )}
      </InspectorSection>

      <div className="rv-builder-inspector__actions">
        <button
          type="button"
          className="rv-builder-btn-verify"
          onClick={onVerify}
          disabled={disabled || verifyPending}
          title={disabled ? "Read-only in static mode" : "Run D13 verification checks"}
          data-testid="builder-verify-draft"
        >
          <span aria-hidden="true">✓</span> {verifyPending ? "Verifying…" : "Verify Draft"}
        </button>
        <div className="rv-builder-split-btn">
          <button
            type="button"
            className="rv-builder-split-btn__main"
            onClick={onPublishPreview}
            disabled={disabled || publishPending}
            title={disabled ? "Read-only in static mode" : "Preview the fail-closed publish gate"}
            data-testid="builder-publish-preview"
          >
            <span aria-hidden="true">👁</span> {publishPending ? "Checking…" : "Publish Preview"}
          </button>
          <button
            type="button"
            className="rv-builder-split-btn__caret"
            disabled={disabled || publishPending}
            aria-haspopup="menu"
            aria-expanded={publishMenuOpen}
            aria-label="More publish options"
            onClick={() => setPublishMenuOpen((o) => !o)}
            data-testid="builder-publish-preview-caret"
          >
            ▾
          </button>
          {publishMenuOpen && (
            <div className="rv-builder-toolbar__menu rv-builder-split-btn__menu" role="menu">
              <button type="button" role="menuitem" disabled title="Planned">
                Publish to workspace (coming soon)
              </button>
            </div>
          )}
        </div>
      </div>

      {verifyResult && (
        <InspectorSection title="Verify result" testId="builder-verify-result">
          <span className={`it-pill ${verifyResult.passed ? "done" : "blocked"}`}>{verifyResult.passed ? "Passed" : "Failed"}</span>
          <CheckList checks={verifyResult.checks} />
        </InspectorSection>
      )}

      {publishResult && (
        <InspectorSection title="Publish preview" testId="builder-publish-result">
          <span className={`it-pill ${publishResult.publishable ? "done" : "blocked"}`}>
            {publishResult.publishable ? "Publishable" : "Blocked (fail-closed)"}
          </span>
          {!publishResult.publishable && publishResult.blocking_reasons.length > 0 && (
            <ul className="rv-builder-inspector__blocking-list">
              {publishResult.blocking_reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          <CheckList checks={publishResult.checks} />
        </InspectorSection>
      )}

      <footer className="rv-builder-inspector__footer">
        <span>{updatedAt ? `Autosaved ${new Date(updatedAt).toLocaleTimeString()}` : "Not saved yet"}</span>
        {currentVersionId && <span className="rv-builder-inspector__version">{currentVersionId}</span>}
      </footer>
    </aside>
  );
}

export default BuilderAuditInspector;
