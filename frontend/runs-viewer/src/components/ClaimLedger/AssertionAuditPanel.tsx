/**
 * AssertionAuditPanel.tsx — P6-003 stale-impact additions to the Claim Audit
 * Workbench (reusable assertion ledger reviewer experience v1, §5.3, §6.D).
 *
 * Two presentational, prop-driven exports so P6-004 can fixture-test every
 * state without mocking React Query:
 *   - AssertionStatusBand: full-width authoritative reuse-block banner.
 *   - AssertionInspector: the "Selected assertion" panel that replaces the
 *     claim/paragraph inspector when a source assertion is the active
 *     audit subject.
 *
 * Domain-language contract (spec §4.1): "Impact operation" not
 * cascade/deletion job; "Reuse decision" not trust score; "Source
 * assertion" never Fact/Truth/Canonical fact. Object signatures use
 * --it-font-mono and omit absent segments rather than fabricating v0/
 * unknown/latest (spec §4.3). Unknown enum values render
 * `Unavailable (<value>)` and never default to eligible/current (spec §8).
 */
import { useEffect, useRef, useState, type ReactNode, type Ref } from "react";
import type {
  AssertionImpactAction,
  AssertionImpactSummary,
  EvidencePacket,
} from "@/types/rf/assertions_api.generated";
import type { AssertionViewState } from "@/hooks/useAssertions";
import { selectPacketLifecycle, selectPacketObject, selectPacketSubject } from "@/hooks/useAssertions";
import { safeReasonCopy, safeReasonHeadline } from "@/lib/assertionReasonCopy";
import { lifecycleDisplay } from "@/components/AssertionCatalog/assertionDisplay";

// ── Shared field helpers ───────────────────────────────────────────────────

/** Narrow, defensive string read from a Record<string, unknown> packet map. */
function readString(obj: Record<string, unknown> | undefined, ...keys: string[]): string | undefined {
  if (!obj) return undefined;
  for (const key of keys) {
    const value = obj[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return undefined;
}

function readStringArray(obj: Record<string, unknown> | undefined, ...keys: string[]): readonly string[] {
  if (!obj) return [];
  for (const key of keys) {
    const value = obj[key];
    if (Array.isArray(value)) return value.filter((v): v is string => typeof v === "string");
  }
  return [];
}

/** `<Object type> · <id> · v<version>` — omits the version delimiter when absent (spec §4.3). */
export function assertionSignature(assertionId: string, version?: number | null): string {
  return version != null ? `${assertionId} · v${version}` : assertionId;
}

// ── AssertionStatusBand ─────────────────────────────────────────────────────

export interface AssertionStatusBandProps {
  /** Renders nothing when false — callers gate on the authoritative impact receipt. */
  visible: boolean;
  /** The governed impact receipt's reason code. */
  reasonCode?: string | null;
  onViewImpactReceipt?: () => void;
  /**
   * True only when the block transitioned to blocked during the current
   * interaction (not on initial load of an already-stale assertion) — this
   * is the sole condition under which role="alert" replaces role="status"
   * (spec §10, §7 "Loading, stale, denied, and error behavior").
   */
  justBecameBlocked?: boolean;
}

export function AssertionStatusBand({ visible, reasonCode, onViewImpactReceipt, justBecameBlocked }: AssertionStatusBandProps) {
  if (!visible) return null;
  const headline = safeReasonHeadline(reasonCode);
  const reason = reasonCode ?? "impact_reason_unavailable";
  return (
    <div
      className="rv-assertion-band"
      role={justBecameBlocked ? "alert" : "status"}
      data-testid="assertion-status-band"
    >
      <span className="rv-assertion-band__icon" aria-hidden="true">
        <WarningIcon />
      </span>
      <div className="rv-assertion-band__copy">
        <strong>{headline}</strong>
        <span>{safeReasonCopy(reason)}</span>
        <code className="rv-assertion-band__reason">{reason}</code>
      </div>
      <button
        type="button"
        className="it-btn ghost sm rv-assertion-band__action"
        data-testid="view-impact-receipt-btn"
        onClick={onViewImpactReceipt}
      >
        View impact receipt
      </button>
    </div>
  );
}

// ── AssertionInspector ──────────────────────────────────────────────────────

export interface AssertionInspectorProps {
  packet: EvidencePacket;
  impactState: AssertionViewState<AssertionImpactSummary>;
  onOpenReplacementEdition?: (editionId: string) => void;
  /** Ref target for the "View impact receipt" band action to scroll/focus into. */
  impactSectionRef?: Ref<HTMLDivElement>;
}

export function AssertionInspector({ packet, impactState, onOpenReplacementEdition, impactSectionRef }: AssertionInspectorProps) {
  const subject = selectPacketSubject(packet);
  const assertionText =
    subject.kind === "source-assertion" ? readString(subject.assertion, "text", "assertion_text") : undefined;
  const lifecycleState = selectPacketLifecycle(packet);
  const isNonCurrent = lifecycleState === "stale" || lifecycleState === "invalidated" || lifecycleState === "tombstoned";
  const impact = "data" in impactState ? impactState.data : undefined;
  // Reuse is governed by the receipt DTO, not the immutable packet's
  // lifecycle. Those values can intentionally differ during remediation.
  const isAuthoritativelyBlocked = impact?.authoritative_reuse_blocked === true;
  const sourceEdition = selectPacketObject(packet, "source_edition");
  const freshness = selectPacketObject(packet, "freshness");
  const passage = selectPacketObject(packet, "passage");

  const editionId = readString(sourceEdition, "edition_id", "id", "source_edition_id");
  const editionCaptured = readString(sourceEdition, "captured_at", "captured_date", "capture_date");

  const freshnessReason = readString(freshness, "reason_code", "reason");
  const previousEdition = readString(freshness, "previous_edition_id", "superseded_edition_id", "from_edition_id");
  const nextEdition = readString(freshness, "current_edition_id", "new_edition_id", "to_edition_id");
  const detectedAt = readString(freshness, "detected_at", "evaluated_at", "detected_timestamp");

  const passageText = readString(passage, "text", "quote", "excerpt");

  return (
    <aside className="rv-claim-inspector it-card" data-testid="assertion-inspector" data-assertion-id={packet.assertion_id}>
      <div className="rv-pane-title">
        <h3>Selected assertion</h3>
      </div>

      <div className="rv-inspector-title">
        <h4>{assertionText ?? "Source assertion"}</h4>
        <code>{assertionSignature(packet.assertion_id, packet.assertion_version)}</code>
      </div>

      {passageText && (
        <section className="rv-inspector-section">
          <h4>Passage</h4>
          <blockquote className="rv-assertion-passage">
            {passageText}
            {isNonCurrent && <span className="it-chip gold rv-assertion-passage__chip">Historical · non-reusable</span>}
          </blockquote>
        </section>
      )}

      {/* Lifecycle — Stale and Reuse blocked are two separate labeled facts, never merged (spec §6.D). */}
      <section className="rv-inspector-section">
        <h4>Lifecycle</h4>
        <div className="rv-assertion-lifecycle-facts">
          <span className="rv-assertion-fact">
            <span className="it-chip gold">
              <span className="dot" aria-hidden="true" />
              {lifecycleState ?? "Unavailable"}
            </span>
          </span>
          {isAuthoritativelyBlocked && (
            <span className="rv-assertion-fact">
              <span className="it-chip red">
                <LockIcon className="icon" />
                Reuse blocked
              </span>
            </span>
          )}
        </div>
      </section>

      <section className="rv-inspector-section">
        <h4>Exact provenance</h4>
        {editionId ? (
          <dl className="rv-inspector-dl">
            <div>
              <dt>Source edition</dt>
              <dd><code>{editionId}</code></dd>
            </div>
            {editionCaptured && (
              <div>
                <dt>Captured</dt>
                <dd>{editionCaptured}</dd>
              </div>
            )}
          </dl>
        ) : (
          <p className="rv-muted">Source edition not recorded in this packet.</p>
        )}
      </section>

      <section className="rv-inspector-section">
        <h4>Freshness receipt</h4>
        <dl className="rv-inspector-dl">
          {freshnessReason && (
            <div>
              <dt>Reason</dt>
              <dd><code>{freshnessReason}</code></dd>
            </div>
          )}
          {previousEdition && nextEdition && (
            <div>
              <dt>Edition transition</dt>
              <dd className="rv-assertion-edition-transition">
                <code>{previousEdition}</code>
                <span aria-hidden="true">→</span>
                <code>{nextEdition}</code>
              </dd>
            </div>
          )}
          {detectedAt && (
            <div>
              <dt>Detected</dt>
              <dd>{detectedAt}</dd>
            </div>
          )}
          {!freshnessReason && !detectedAt && (
            <div>
              <dt>State</dt>
              <dd>Not recorded in this legacy artifact</dd>
            </div>
          )}
        </dl>
      </section>

      <div ref={impactSectionRef} tabIndex={-1}>
        <ImpactSection impactState={impactState} onOpenReplacementEdition={onOpenReplacementEdition} />
      </div>
    </aside>
  );
}

// ── Impact operation / affected uses / reconciliation ──────────────────────

const OBJECT_CLASS_LABELS: Readonly<Record<string, string>> = {
  source_edition: "Source editions",
  passage: "Passages",
  assertion_version: "Assertion versions",
  canonical_claim_edge: "Relationships / inferences",
  inference: "Relationships / inferences",
  report_revision: "Report revisions",
  run: "Runs",
  export: "Exports / projections",
  derived_cache_or_index: "Indexes / caches",
  assertion_regeneration: "Assertion regeneration",
  mock_writeback_receipt: "Writebacks",
};

/** Groups the DTO action list by object_class, preserving first-seen order and in-group order (never reordered/invented — spec §8). */
function groupActionsByObjectClass(
  actions: readonly AssertionImpactAction[],
): Array<{ objectClass: string; label: string; actions: AssertionImpactAction[] }> {
  const order: string[] = [];
  const groups = new Map<string, AssertionImpactAction[]>();
  for (const action of actions) {
    if (!groups.has(action.object_class)) {
      groups.set(action.object_class, []);
      order.push(action.object_class);
    }
    groups.get(action.object_class)!.push(action);
  }
  return order.map((objectClass) => ({
    objectClass,
    // Unknown classes remain their own safely rendered raw-value bucket; do
    // not invent an object vocabulary for a future generated DTO value.
    label: OBJECT_CLASS_LABELS[objectClass] ?? objectClass,
    actions: groups.get(objectClass)!,
  }));
}

function writebackStatusDisplay(action: AssertionImpactAction): string {
  switch (action.writeback_status) {
    case "default_denied":
      return "default_denied";
    case "denied":
      return "denied";
    case "queued":
      return "queued";
    default:
      return "Unavailable";
  }
}

/** Writebacks render as "1 denied · 1 queued" (per-status breakdown), never a bare count (spec §6.D). */
function summarizeWriteback(actions: readonly AssertionImpactAction[]): string {
  const counts = new Map<string, number>();
  for (const action of actions) {
    // The impact action's status describes the operation. Writeback
    // disposition is a separate frozen DTO field and is the only authority
    // for the writeback breakdown.
    const word = action.writeback_status === "default_denied" || action.writeback_status === "denied"
      ? "denied"
      : action.writeback_status ?? "Unavailable";
    counts.set(word, (counts.get(word) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([word, count]) => `${count} ${word}`)
    .join(" · ");
}

function ImpactSection({
  impactState,
  onOpenReplacementEdition,
}: {
  impactState: AssertionViewState<AssertionImpactSummary>;
  onOpenReplacementEdition?: (editionId: string) => void;
}) {
  if (impactState.kind === "loading") {
    return (
      <section className="rv-inspector-section" data-testid="impact-loading">
        <h4>Impact operation</h4>
        <p className="rv-muted">Loading impact receipt…</p>
      </section>
    );
  }

  // Hard rule: impact 'unavailable' renders a labeled panel with NO counts and no mutation control.
  if (impactState.kind === "unavailable") {
    return (
      <section className="rv-inspector-section" data-testid="impact-unavailable">
        <h4>Impact operation</h4>
        <div className="rv-assertion-impact-unavailable">
          <span className="it-chip">Impact data unavailable</span>
        </div>
      </section>
    );
  }

  if (impactState.kind === "denied") {
    return (
      <section className="rv-inspector-section" data-testid="impact-denied">
        <h4>Impact operation</h4>
        <div className="rv-assertion-impact-unavailable">
          <span className="it-chip red">Impact data unavailable</span>
          <p className="rv-muted">{impactState.reasonCopy}</p>
        </div>
      </section>
    );
  }

  if (impactState.kind === "error-with-retry") {
    return (
      <section className="rv-inspector-section" data-testid="impact-error">
        <h4>Impact operation</h4>
        <p className="rv-muted">Impact receipt could not be loaded.</p>
        <button type="button" className="it-btn ghost xs" onClick={() => void impactState.retry()}>
          Retry
        </button>
      </section>
    );
  }

  const impact = impactState.data;
  const impactLifecycle = lifecycleDisplay(impact.lifecycle_state);
  const groups = groupActionsByObjectClass(impact.actions);
  const completedActions = impact.actions.filter((action) => action.status === "completed").length;
  // interrupted/unknown must never render as completed/safe (spec §8, §6.D)
  // Treat generated unions as an open runtime value: a newer DTO must never
  // silently inherit the completed tone.
  const operationStatus: string = impact.operation_status;
  const operationTone = operationStatus === "completed" ? "green" : operationStatus === "blocked" || operationStatus === "interrupted" ? "red" : "orange";
  const reconciliationLine =
    operationStatus === "pending"
      ? "Deterministic reconciliation pending"
      : operationStatus === "completed"
        ? "Deterministic reconciliation complete — reuse remains blocked pending a separate governed restore decision"
        : `Deterministic reconciliation ${operationStatus}`;

  return (
    <>
      <section className="rv-inspector-section" data-testid="impact-operation">
        <h4>Impact operation</h4>
        <div className="rv-assertion-impact-signature">
          <code>{impact.event_id}</code>
          <span className={`it-chip ${impactLifecycle.color}`.trim()} data-testid="impact-lifecycle-chip">
            {impactLifecycle.label}
          </span>
          <span className={`it-chip ${operationTone}`}>{operationStatus}</span>
        </div>
        <dl className="rv-inspector-dl rv-assertion-impact-facts">
          <div>
            <dt>Authoritative state</dt>
            <dd>Reuse blocked</dd>
          </div>
          <div>
            <dt>Reason</dt>
            <dd>{safeReasonCopy(impact.reason_code ?? "impact_reason_unavailable")} {impact.reason_code && <code>{impact.reason_code}</code>}</dd>
          </div>
        </dl>
      </section>

      <section className="rv-inspector-section" data-testid="affected-uses">
        <h4>Affected uses</h4>
        <ul className="rv-assertion-affected-uses">
          {groups.map((group) => (
            <li key={group.objectClass} className="rv-assertion-affected-uses__row" data-testid={`affected-use-${group.objectClass}`}>
              <span className="rv-assertion-affected-uses__label">{group.label}</span>
              {group.objectClass === "mock_writeback_receipt" ? (
                <span className="rv-assertion-affected-uses__badge rv-assertion-affected-uses__badge--compound">
                  {summarizeWriteback(group.actions)}
                </span>
              ) : (
                <span className="rv-assertion-affected-uses__badge">{group.actions.length}</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="rv-inspector-section" data-testid="impact-actions">
        <h4>Impact actions</h4>
        <p className="rv-assertion-action-progress" role="status" aria-live="polite">
          {completedActions} of {impact.actions.length} actions completed
        </p>
        <ol className="rv-assertion-action-list">
          {impact.actions.map((action, index) => (
            <li
              key={`${action.object_id}:${action.object_class}:${action.action}:${index}`}
              className="rv-assertion-action-list__item"
              data-testid={`impact-action-${index}`}
            >
              <code>{action.object_id}</code>
              <span>{action.action}</span>
              {action.object_class === "mock_writeback_receipt" ? (
                <span className="rv-assertion-action-list__writeback-facts">
                  <span className="rv-assertion-action-list__status">
                    <span className="rv-assertion-action-list__fact-label">Action status</span>
                    {action.status}
                  </span>
                  <span className="rv-assertion-action-list__status">
                    <span className="rv-assertion-action-list__fact-label">Writeback disposition</span>
                    {writebackStatusDisplay(action)}
                  </span>
                </span>
              ) : (
                <span className="rv-assertion-action-list__status">{action.status}</span>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section className="rv-inspector-section" data-testid="reconciliation">
        <h4>Reconciliation</h4>
        <p className="rv-assertion-reconciliation">{reconciliationLine}</p>
      </section>

      {/* Frozen seam note: replacement_edition_id is currently always null from the backend.
          This action must render only when the typed receipt supplies a target — never a
          disabled-visible button (spec §5.3, §7 "Optional merge review"). */}
      {impact.replacement_edition_id && (
        <button
          type="button"
          className="it-btn secondary sm rv-assertion-replacement-btn"
          data-testid="open-replacement-edition-btn"
          onClick={() => onOpenReplacementEdition?.(impact.replacement_edition_id as string)}
        >
          Open replacement edition
        </button>
      )}
    </>
  );
}

// ── Hooks: transition detection for role=status vs role=alert ─────────────

/**
 * Tracks whether the assertion's lifecycle just transitioned into "stale"
 * during the current mounted interaction (vs. arriving already-stale on
 * first load/selection) — spec §7 and §10 distinguish role="status" (passive)
 * from role="alert" (reuse became blocked during this interaction).
 */
export function useJustBecameBlocked(isBlocked: boolean): boolean {
  const previous = useRef<boolean | undefined>(undefined);
  const seenFirstResolved = useRef(false);
  const [justBecameBlocked, setJustBecameBlocked] = useState(false);

  useEffect(() => {
    if (seenFirstResolved.current && !previous.current && isBlocked) {
      setJustBecameBlocked(true);
    } else if (!isBlocked) {
      setJustBecameBlocked(false);
    }
    seenFirstResolved.current = true;
    previous.current = isBlocked;
  }, [isBlocked]);

  return justBecameBlocked;
}

// ── Minimal inline icons (module scope, no external icon library) ─────────

function WarningIcon(): ReactNode {
  return (
    <svg width={18} height={18} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M8 1.5 14.5 13.5H1.5Z" strokeLinejoin="round" />
      <line x1="8" y1="6" x2="8" y2="9.5" strokeLinecap="round" />
      <circle cx="8" cy="11.6" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

function LockIcon({ className }: { className?: string }): ReactNode {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="3" y="7" width="10" height="7" rx="1.4" />
      <path d="M5 7V4.7a3 3 0 0 1 6 0V7" />
    </svg>
  );
}

export { readString, readStringArray };
