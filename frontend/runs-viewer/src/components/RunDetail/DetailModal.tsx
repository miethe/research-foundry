/**
 * DetailModal — generic item-expand overlay (F2 feature, v2.2).
 *
 * Accepts a discriminated union payload:
 *   - { kind: 'claim'; claimId: string; claims: RFClaim[] }
 *   - { kind: 'node'; node: LineageNode }
 *
 * Overlay conventions mirror ProvenanceModal:
 *   - .rv-modal-overlay / .rv-modal-overlay--stacked
 *   - .rv-modal / .rv-modal__header / .rv-modal__body
 *   - role="dialog", aria-modal="true"
 *   - Escape-to-close (via useEffect keydown listener)
 *   - backdrop click closes; dialog content click does not
 *   - stacked prop for z-index layering
 *   - onOpenChange callback for parent Escape suppression
 *
 * Entry points:
 *   - Double-click on RunCard (dispatches onExpandRun → opens RunDetailModal, not this)
 *   - ⤢ button in LineageDetailPanel header (onExpandNode → DetailModal with node payload)
 *   - Double-click on LineageList rows (onExpandNode → DetailModal with node payload)
 *   - Double-click on ClaimLedgerTable row (onExpandClaim → DetailModal with claim payload)
 *   - ⤢ button in ClaimInspector (onExpandClaim → DetailModal with claim payload)
 *
 * Resilience:
 *   - node.claimId === undefined → renders node metadata only + "No provenance available" note
 *   - claimId not found in claims array → renders "Claim not found" (mirrors ProvenanceModal:127-132)
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { RFClaim, RFResolvedSource } from "@/types/rf";
import type { LineageNode, LineageNodeKind } from "@/components/LineageGraph/lineageTree";
import { LINEAGE_KIND_META } from "@/components/LineageGraph/lineageTree";
import { KindIcon } from "@/components/LineageGraph/kindIcons";
import { SourceCard } from "@/components/SourceCard/SourceCard";
import type { DetailTab } from "./detailTabs";

// ── Payload types ─────────────────────────────────────────────────────────────

export type DetailModalPayload =
  | { kind: "claim"; claimId: string; claims: RFClaim[] }
  | { kind: "node"; node: LineageNode }
  | { kind: "source"; source: RFResolvedSource }
  | {
      kind: "issues";
      category: { key: string; label: string; severity: string; count: number };
      issueItems: IssueDetail[];
    };

export interface IssueDetail {
  id: string;
  block_id?: string;
  claim_id?: string;
  message: string;
  severity: "error" | "warning" | "info";
  hint?: string;
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface DetailModalProps {
  payload: DetailModalPayload | null;
  /** Adds a higher stacking layer when opened from inside another modal. */
  stacked?: boolean;
  /** Allows parent modals to suppress their own Escape/overlay close while this is open. */
  onOpenChange?: (open: boolean) => void;
  /** Called when the modal requests close. Parent sets payload to null. */
  onClose?: () => void;
  /**
   * D4: Called when the user clicks the primary navigate action in the node modal footer.
   * Navigates to the relevant detail tab (and optionally highlights a specific claim).
   * When omitted the navigate action button is not rendered (graceful degradation).
   */
  onNavigate?: (tab: DetailTab, claimId?: string) => void;
  /** Called from the issues modal action to pivot into related claims. */
  onFindClaimsForIssue?: (issue: IssueDetail) => void;
}

// ── Status chip map (mirrors ProvenanceModal) ─────────────────────────────────

const STATUS_CHIP: Record<string, string> = {
  supported:    "green",
  mixed:        "gold",
  contradicted: "red",
  inference:    "blue",
  speculation:  "orange",
  unsupported:  "red",
};

const ISSUE_SEVERITY_CHIP: Record<IssueDetail["severity"], string> = {
  error:   "red",
  warning: "orange",
  info:    "blue",
};

// ── Component ─────────────────────────────────────────────────────────────────

export function DetailModal({
  payload,
  stacked = false,
  onOpenChange,
  onClose,
  onNavigate,
  onFindClaimsForIssue,
}: DetailModalProps) {
  // Focus management: move focus into the modal when it opens
  const dialogRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    onClose?.();
    onOpenChange?.(false);
  }, [onClose, onOpenChange]);

  // Notify parent when open state changes
  useEffect(() => {
    if (payload) {
      onOpenChange?.(true);
    }
  }, [payload, onOpenChange]);

  // Escape key handler — active only while payload is set
  useEffect(() => {
    if (!payload) return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [close, payload]);

  // Focus management: move focus into the dialog when it opens (a11y)
  useEffect(() => {
    if (payload && dialogRef.current) {
      // Focus the close button (first interactive element) or the dialog itself
      const focusTarget =
        dialogRef.current.querySelector<HTMLElement>(
          '[data-testid="detail-modal-close"], button, [href], [tabindex]:not([tabindex="-1"])',
        ) ?? dialogRef.current;
      focusTarget.focus();
    }
  }, [payload]);

  if (!payload) return null;

  return (
    <div
      className={`rv-modal-overlay${stacked ? " rv-modal-overlay--stacked" : ""}`}
      data-testid="detail-modal-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) close(); }}
      role="presentation"
    >
      <div
        ref={dialogRef}
        className="rv-modal rv-detail-modal"
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        aria-label={getPayloadAriaLabel(payload)}
        data-testid="detail-modal"
      >
        {/* ── Header ── */}
        <div className="rv-modal__header">
          <div className="rv-modal__title-row">
            <ModalTitle payload={payload} />
          </div>
          <button
            type="button"
            className="it-btn ghost sm rv-modal__close"
            data-testid="detail-modal-close"
            onClick={close}
            aria-label="Close detail modal"
          >
            ✕
          </button>
        </div>

        {/* ── Body ── */}
        <div className="rv-modal__body" data-testid="detail-modal-body">
          <ModalBody
            payload={payload}
            onNavigate={onNavigate}
            onClose={close}
            onFindClaimsForIssue={onFindClaimsForIssue}
          />
        </div>
      </div>
    </div>
  );
}

function assertNever(value: never): never {
  throw new Error(`Unhandled detail modal payload kind: ${JSON.stringify(value)}`);
}

function getPayloadAriaLabel(payload: DetailModalPayload): string {
  switch (payload.kind) {
    case "claim":
      return `Detail for ${payload.claimId}`;
    case "node":
      return `Detail for ${payload.node.title}`;
    case "source":
      return `Detail for ${payload.source.source_card_id}`;
    case "issues":
      return `Issue details for ${payload.category.label}`;
    default:
      return assertNever(payload);
  }
}

function ModalTitle({ payload }: { payload: DetailModalPayload }) {
  switch (payload.kind) {
    case "claim":
      return (
        <>
          <span className="it-chip rv-modal__kind-label">Claim</span>
          <code className="rv-modal__claim-id" data-testid="detail-modal-id">
            {payload.claimId}
          </code>
        </>
      );
    case "node":
      return (
        <>
          <span
            className="rv-detail-modal__kind-icon"
            style={{ color: LINEAGE_KIND_META[payload.node.kind].accent }}
            aria-hidden="true"
          >
            <KindIcon kind={payload.node.kind} size={16} />
          </span>
          <span className="it-chip rv-modal__kind-label">
            {LINEAGE_KIND_META[payload.node.kind].label}
          </span>
          <strong className="rv-modal__node-title" data-testid="detail-modal-id">
            {payload.node.title}
          </strong>
        </>
      );
    case "source":
      return (
        <>
          <span className="it-chip rv-modal__kind-label">Source</span>
          <code className="rv-modal__claim-id" data-testid="detail-modal-id">
            {payload.source.source_card_id}
          </code>
        </>
      );
    case "issues":
      return (
        <>
          <span className="it-chip rv-modal__kind-label">Issues</span>
          <strong className="rv-modal__node-title" data-testid="detail-modal-id">
            {payload.category.label} ({payload.category.count})
          </strong>
        </>
      );
    default:
      return assertNever(payload);
  }
}

interface ModalBodyProps {
  payload: DetailModalPayload;
  onNavigate?: (tab: DetailTab, claimId?: string) => void;
  onClose: () => void;
  onFindClaimsForIssue?: (issue: IssueDetail) => void;
}

function ModalBody({ payload, onNavigate, onClose, onFindClaimsForIssue }: ModalBodyProps) {
  switch (payload.kind) {
    case "claim":
      return <ClaimModalBody claimId={payload.claimId} claims={payload.claims} />;
    case "node":
      return <NodeModalBody node={payload.node} onNavigate={onNavigate} onClose={onClose} />;
    case "source":
      return <SourceModalBody source={payload.source} />;
    case "issues":
      return (
        <IssuesModalBody
          category={payload.category}
          issueItems={payload.issueItems}
          onFindClaimsForIssue={onFindClaimsForIssue}
        />
      );
    default:
      return assertNever(payload);
  }
}

// ── Claim body ────────────────────────────────────────────────────────────────

function ClaimModalBody({ claimId, claims }: { claimId: string; claims: RFClaim[] }) {
  const claim = claims.find((c) => c.claim_id === claimId);

  if (!claim) {
    return (
      <p className="rv-modal__not-found" data-testid="detail-modal-claim-not-found">
        Claim <code>{claimId}</code> not found in the ledger.
      </p>
    );
  }

  return (
    <>
      {/* Status + confidence chips */}
      <div className="rv-modal__meta">
        {claim.status && (
          <span
            className={`it-chip ${STATUS_CHIP[claim.status] ?? ""} rv-modal__status`}
            data-testid="detail-modal-status"
          >
            {claim.status}
          </span>
        )}
        {claim.confidence && (
          <span className="it-chip rv-modal__confidence" data-testid="detail-modal-confidence">
            {claim.confidence} confidence
          </span>
        )}
        {claim.materiality && (
          <span className="it-chip rv-modal__meta-chip">{claim.materiality}</span>
        )}
        {claim.claim_type && (
          <span className="it-chip rv-modal__meta-chip">{claim.claim_type}</span>
        )}
      </div>

      {/* Claim text */}
      <div className="rv-modal__claim-text" data-testid="detail-modal-claim-text">
        <p>{claim.text}</p>
      </div>

      {/* Sources */}
      {claim.sources.length > 0 ? (
        <div className="rv-modal__sources-section" data-testid="detail-modal-sources">
          <h3 className="rv-modal__section-title">Sources ({claim.sources.length})</h3>
          <div className="rv-modal__source-list">
            {claim.sources.map((src) => (
              <SourceCard key={`${src.source_card_id}-${src.evidence_id}`} source={src} />
            ))}
          </div>
        </div>
      ) : (
        <p className="rv-muted" data-testid="detail-modal-no-sources">
          No source cards linked to this claim.
        </p>
      )}
    </>
  );
}

// ── Source body ───────────────────────────────────────────────────────────────

function optionalSourceRunId(source: RFResolvedSource): string | null {
  const withRun = source as RFResolvedSource & { run_id?: unknown };
  return typeof withRun.run_id === "string" && withRun.run_id ? withRun.run_id : null;
}

function SourceModalBody({ source }: { source: RFResolvedSource }) {
  const originRunId = optionalSourceRunId(source);
  return (
    <div className="rv-modal__sources-section" data-testid="detail-modal-source">
      <h3 className="rv-modal__section-title">{source.title || source.source_card_id}</h3>
      {originRunId && (
        <div className="rv-detail-modal__claim-ref">
          <span className="rv-muted">Origin run:</span>{" "}
          <a href={`/runs/${encodeURIComponent(originRunId)}`}>{originRunId}</a>
        </div>
      )}
      <SourceCard source={source} compact={false} />
    </div>
  );
}

// ── Issues body ───────────────────────────────────────────────────────────────

function clampIndex(index: number, length: number): number {
  if (length <= 0) return 0;
  return Math.min(Math.max(index, 0), length - 1);
}

interface IssuesModalBodyProps {
  category: { key: string; label: string; severity: string; count: number };
  issueItems: IssueDetail[];
  onFindClaimsForIssue?: (issue: IssueDetail) => void;
}

function IssuesModalBody({ category, issueItems, onFindClaimsForIssue }: IssuesModalBodyProps) {
  const [activeIndex, setActiveIndex] = useState(() => clampIndex(0, issueItems.length));

  useEffect(() => {
    setActiveIndex(clampIndex(0, issueItems.length));
  }, [issueItems]);

  if (issueItems.length === 0) {
    return (
      <div className="rv-modal__sources-section" data-testid="detail-modal-issues">
        <h3 className="rv-modal__section-title">{category.label} ({category.count})</h3>
        <p className="rv-muted">No issues to iterate.</p>
        <IssueNavigation
          activeIndex={0}
          issueCount={0}
          onPrev={() => undefined}
          onNext={() => undefined}
        />
      </div>
    );
  }

  const activeIssue = issueItems[activeIndex] ?? issueItems[0];

  function move(delta: number) {
    setActiveIndex((current) => (current + delta + issueItems.length) % issueItems.length);
  }

  return (
    <div className="rv-modal__sources-section" data-testid="detail-modal-issues">
      <h3 className="rv-modal__section-title">{category.label} ({category.count})</h3>
      <IssueNavigation
        activeIndex={activeIndex}
        issueCount={issueItems.length}
        onPrev={() => move(-1)}
        onNext={() => move(1)}
      />

      <div className="rv-modal__meta">
        <span
          className={`it-chip ${ISSUE_SEVERITY_CHIP[activeIssue.severity]} rv-modal__status`}
          data-testid="detail-modal-status"
        >
          {activeIssue.severity}
        </span>
        {activeIssue.block_id && <span className="it-chip rv-modal__meta-chip">{activeIssue.block_id}</span>}
        {activeIssue.claim_id && <span className="it-chip rv-modal__meta-chip">{activeIssue.claim_id}</span>}
      </div>

      <div className="rv-modal__claim-text">
        <p>{activeIssue.message}</p>
      </div>

      {activeIssue.hint && (
        <p className="rv-muted" data-testid="detail-modal-issue-hint">
          {activeIssue.hint}
        </p>
      )}

      {onFindClaimsForIssue && (
        <div className="rv-detail-modal__footer">
          <span className="rv-muted">Iterate and find claims</span>
          <button
            type="button"
            className="it-btn secondary sm rv-detail-modal__navigate-action"
            onClick={() => onFindClaimsForIssue(activeIssue)}
          >
            Find claims for this issue
          </button>
        </div>
      )}
    </div>
  );
}

interface IssueNavigationProps {
  activeIndex: number;
  issueCount: number;
  onPrev: () => void;
  onNext: () => void;
}

function IssueNavigation({ activeIndex, issueCount, onPrev, onNext }: IssueNavigationProps) {
  const disabled = issueCount <= 1;
  return (
    <div className="rv-detail-modal__footer">
      <button
        type="button"
        className="it-btn ghost sm"
        data-testid="detail-modal-issues-prev"
        onClick={onPrev}
        disabled={disabled}
        aria-label="Previous issue"
      >
        ←
      </button>
      <span className="rv-muted" data-testid="detail-modal-issues-counter">
        {issueCount === 0 ? "0 / 0" : `${activeIndex + 1} / ${issueCount}`}
      </span>
      <button
        type="button"
        className="it-btn ghost sm"
        data-testid="detail-modal-issues-next"
        onClick={onNext}
        disabled={disabled}
        aria-label="Next issue"
      >
        →
      </button>
    </div>
  );
}

// ── Node body ─────────────────────────────────────────────────────────────────

interface NodeModalBodyProps {
  node: LineageNode;
  onNavigate?: (tab: DetailTab, claimId?: string) => void;
  onClose?: () => void;
}

/**
 * Derives the navigate action for a lineage node.
 * Returns { tab, claimId, label } — or null when no obvious target exists.
 *
 * Mapping:
 *   claim      → ledger tab, highlight claimId
 *   report     → report tab (+ claimId if available)
 *   writeback  → writeback tab
 *   source / extraction → lineage tab (source-first lineage view)
 *   run        → overview tab (omitted — we're already on the run detail surface)
 */
function deriveNavigateAction(
  node: LineageNode,
): { tab: DetailTab; claimId?: string; label: string } | null {
  const kind: LineageNodeKind = node.kind;
  switch (kind) {
    case "claim":
      return {
        tab: "ledger",
        claimId: node.claimId ?? node.subtitle,
        label: "View in Claim Ledger",
      };
    case "report":
      return {
        tab: "report",
        claimId: node.claimId,
        label: "View in Report",
      };
    case "writeback":
      return {
        tab: "writeback",
        label: "View Writeback",
      };
    case "source":
    case "extraction":
      return {
        tab: "lineage",
        label: "View in Lineage",
      };
    case "run":
      // Already on the run detail surface; omit the action
      return null;
    default:
      return assertNever(kind);
  }
}

function NodeModalBody({ node, onNavigate, onClose }: NodeModalBodyProps) {
  const meta = LINEAGE_KIND_META[node.kind];
  const navigateAction = deriveNavigateAction(node);

  function handleNavigate() {
    if (!navigateAction || !onNavigate) return;
    onNavigate(navigateAction.tab, navigateAction.claimId);
    onClose?.();
  }

  return (
    <>
      {/* Subtitle */}
      {node.subtitle && (
        <code className="rv-detail-modal__subtitle" data-testid="detail-modal-subtitle">
          {node.subtitle}
        </code>
      )}

      {/* Chips */}
      {node.chips && node.chips.length > 0 && (
        <div className="rv-detail-modal__chips" data-testid="detail-modal-chips">
          {node.chips.map((chip) => (
            <span key={chip} className="it-chip">{chip}</span>
          ))}
        </div>
      )}

      {/* Details table */}
      {node.details && node.details.length > 0 && (
        <dl className="rv-lineage-detail__dl rv-detail-modal__dl" data-testid="detail-modal-details">
          {node.details.map((item) => (
            <div key={`${item.label}-${item.value}`} className="rv-lineage-detail__dl-row">
              <dt>{item.label}</dt>
              <dd>
                {item.href ? (
                  <a href={item.href} target="_blank" rel="noreferrer">{item.value}</a>
                ) : (
                  item.value
                )}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {/* Claim link — or graceful absence note */}
      {node.claimId ? (
        <div className="rv-detail-modal__claim-ref" data-testid="detail-modal-claim-ref">
          <span className="rv-muted">Associated claim:</span>{" "}
          <code>{node.claimId}</code>
        </div>
      ) : (
        <p className="rv-muted" data-testid="detail-modal-no-provenance">
          No provenance available for this node type.
        </p>
      )}

      {/* Kind accent indicator */}
      <div className="rv-detail-modal__kind-footer" aria-hidden="true">
        <span style={{ color: meta.accent }}>
          <KindIcon kind={node.kind} size={12} />
        </span>
        <span className="rv-muted">{meta.label} node</span>
      </div>

      {/* D4: Primary navigate action — only rendered when onNavigate provided + action exists */}
      {onNavigate && navigateAction && (
        <div className="rv-detail-modal__footer" data-testid="detail-modal-footer">
          <button
            type="button"
            className="it-btn secondary sm rv-detail-modal__navigate-action"
            data-testid="detail-modal-navigate"
            onClick={handleNavigate}
          >
            {navigateAction.label} →
          </button>
        </div>
      )}
    </>
  );
}

export default DetailModal;
