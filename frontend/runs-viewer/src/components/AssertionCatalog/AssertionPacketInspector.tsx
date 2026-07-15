/**
 * AssertionPacketInspector — CatalogScreen's docked "Source assertions"
 * inspector (P6-002, spec §5.1–5.2, design guidance §A).
 *
 * Loads only after an authorized selection (backed by useEvidencePacket).
 * Consumes the frozen AssertionViewState discriminant from
 * useAssertions.ts; never bypasses its loading/denied/error gating.
 */
import { selectPacketLifecycle, selectPacketSubject, type AssertionViewState } from "@/hooks/useAssertions";
import { safeReasonCopy } from "@/lib/assertionReasonCopy";
import type { EvidencePacket } from "@/types/rf/assertions_api.generated";
import { AssertionPacketFields } from "./AssertionPacketFields";
import {
  accessScopeDisplay,
  lifecycleDisplay,
  readString,
  reuseDecisionDisplay,
} from "./assertionDisplay";

export interface AssertionPacketInspectorProps {
  state: AssertionViewState<EvidencePacket>;
  onClose?: () => void;
}

export function AssertionPacketInspector({ state, onClose }: AssertionPacketInspectorProps) {
  if (state.kind === "loading") {
    return (
      <aside className="rv-catalog-inspector rv-assertion-packet" data-testid="assertion-packet-loading" role="status">
        <p className="rv-assertion-muted">Loading source assertion…</p>
      </aside>
    );
  }

  if (state.kind === "denied") {
    return (
      <aside className="rv-catalog-inspector rv-assertion-packet" data-testid="assertion-packet-denied" role="status">
        <p className="rv-assertion-denied-inline">
          <strong>Assertion unavailable.</strong> {state.reasonCopy}
        </p>
        <p className="rv-assertion-reason-code">
          Reason: <code>{state.reasonCode}</code>
        </p>
      </aside>
    );
  }

  if (state.kind === "error-with-retry") {
    return (
      <aside className="rv-catalog-inspector rv-assertion-packet" data-testid="assertion-packet-error">
        <p className="rv-assertion-muted">This source assertion could not be loaded.</p>
        <button
          type="button"
          className="it-btn secondary sm"
          onClick={() => void state.retry()}
          data-testid="assertion-packet-retry"
        >
          Retry
        </button>
      </aside>
    );
  }

  // ready | stale | invalid | legacy-missing | unavailable(with data)
  const packet = state.data;
  if (!packet) {
    return (
      <aside className="rv-catalog-inspector rv-assertion-packet" data-testid="assertion-packet-unavailable">
        <p className="rv-assertion-muted">
          Source assertion unavailable{"rawValue" in state && state.rawValue ? ` (${state.rawValue})` : ""}.
        </p>
      </aside>
    );
  }

  const missingFields = state.kind === "legacy-missing" ? state.missingFields : [];
  const subject = selectPacketSubject(packet);
  const assertionText =
    subject.kind === "source-assertion"
      ? readString(subject.assertion, "assertion_text", "text")
      : subject.kind === "inference"
        ? readString(subject.inference, "assertion_text", "text")
        : undefined;

  const lifecycleState = selectPacketLifecycle(packet);
  const lifecycle = lifecycleDisplay(
    lifecycleState ?? (state.kind === "unavailable" ? state.rawValue : undefined),
  );
  const access = accessScopeDisplay(packet.access_scope);
  const reuse = reuseDecisionDisplay(packet.rights_decision);
  const subjectLabel = subject.kind === "inference" ? "Inference" : "Source assertion";

  return (
    <aside className="rv-catalog-inspector rv-assertion-packet" data-testid="assertion-packet-inspector" aria-label={subjectLabel}>
      <header className="rv-assertion-packet__header">
        <div className="rv-assertion-packet__eyebrow-row">
          <span className="rv-assertion-eyebrow">{subjectLabel}</span>
          {onClose && (
            <button
              type="button"
              className="it-btn ghost xs"
              onClick={onClose}
              aria-label={`Close ${subjectLabel.toLowerCase()} inspector`}
              data-testid="assertion-packet-close"
            >
              close
            </button>
          )}
        </div>
        <div className="rv-assertion-packet__signature-row">
          <span className="rv-assertion-signature">
            <code>{packet.assertion_id}</code> · v{packet.assertion_version}
          </span>
          <span className={`it-chip ${lifecycle.color}`.trim()}>
            <span className="dot" aria-hidden="true" />
            {lifecycle.label}
          </span>
          <span className={`it-chip ${reuse.color}`.trim()} title={reuse.reasonCode ? safeReasonCopy(reuse.reasonCode) : undefined}>
            {reuse.label}
          </span>
        </div>
        <h3 className="rv-assertion-packet__text">
          {assertionText ?? "Assertion text not recorded in this legacy artifact."}
        </h3>
      </header>

      {state.kind === "legacy-missing" && (
        <p className="rv-assertion-legacy-note" data-testid="assertion-packet-legacy-missing" role="status">
          Legacy packet: some fields were not recorded.
        </p>
      )}

      <AssertionPacketFields packet={packet} missingFields={missingFields} />

      <footer className="rv-assertion-packet__footer">
        <span className="rv-assertion-footer-label">Access &amp; reuse</span>
        <div className="rv-assertion-footer-chips">
          <span className={`it-chip ${access.color}`.trim()}>{access.label}</span>
          <span className={`it-chip ${reuse.color}`.trim()} title={reuse.reasonCode ? safeReasonCopy(reuse.reasonCode) : undefined}>
            {reuse.label}
          </span>
        </div>
      </footer>
    </aside>
  );
}

export default AssertionPacketInspector;
