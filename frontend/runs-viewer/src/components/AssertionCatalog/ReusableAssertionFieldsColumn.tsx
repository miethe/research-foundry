/**
 * ReusableAssertionFieldsColumn — ProvenanceModal's right-hand "Reusable
 * assertion fields" column (P6-002, spec §5.2, §6.B, design guidance §B).
 *
 * Links a run-local RFClaim to its durable source assertion via
 * `claim.persistent_references.source_assertion_id` (run-export schema
 * v1.5, §6.2 — documented and populated by export_service.py, though the
 * sibling P6-003 ClaimAuditWorkbench currently treats this linkage as
 * undiscoverable; see the P6-002 completion report). When absent, this run
 * predates persistent assertion fields and renders the exact seven-row
 * legacy explainer from spec §6.B — field-granular, never inferred.
 *
 * Does not alter the existing left "Run-local provenance" column or the
 * imperative ProvenanceModal open(claimId) handle.
 */
import { useEvidencePacket } from "@/hooks/useAssertions";
import type { RFClaim } from "@/types/rf";
import { AssertionPacketFields } from "./AssertionPacketFields";

const LEGACY_FIELD_LABELS = [
  "Persistent assertion ID",
  "Immutable source edition",
  "Exact passage selector",
  "Structured qualifiers",
  "Rights decision",
  "Freshness",
  "Impact data",
] as const;

export interface ReusableAssertionFieldsColumnProps {
  claim: RFClaim;
}

export function ReusableAssertionFieldsColumn({ claim }: ReusableAssertionFieldsColumnProps) {
  const sourceAssertionId = claim.persistent_references?.source_assertion_id ?? null;
  const packet = useEvidencePacket(sourceAssertionId ?? undefined);

  if (!sourceAssertionId) {
    return (
      <div className="rv-modal__reusable-fields" data-testid="reusable-assertion-fields-legacy">
        <h3 className="rv-modal__section-title">Reusable assertion fields</h3>
        <p className="rv-assertion-legacy-explainer">
          This run predates persistent assertion fields. Run-local provenance remains available.
        </p>
        <dl className="rv-assertion-legacy-dl">
          {LEGACY_FIELD_LABELS.map((label) => (
            <div className="rv-assertion-legacy-dl__row" key={label}>
              <dt>
                <span className="rv-assertion-legacy-dl__icon" aria-hidden="true">
                  ⚠
                </span>
                {label}
              </dt>
              <dd>
                <span className="rv-assertion-legacy-dl__unavailable">Unavailable</span>{" "}
                <span className="rv-assertion-legacy-dl__scope">in this export</span>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    );
  }

  const { state } = packet;

  if (state.kind === "loading") {
    return (
      <div className="rv-modal__reusable-fields" data-testid="reusable-assertion-fields-loading">
        <h3 className="rv-modal__section-title">Reusable assertion fields</h3>
        <p className="rv-assertion-muted" role="status">
          Loading source assertion…
        </p>
      </div>
    );
  }

  if (state.kind === "denied") {
    return (
      <div className="rv-modal__reusable-fields" data-testid="reusable-assertion-fields-denied">
        <h3 className="rv-modal__section-title">Reusable assertion fields</h3>
        <p className="rv-assertion-denied-inline">
          <strong>Assertion unavailable.</strong> {state.reasonCopy}
        </p>
        <p className="rv-assertion-reason-code">
          Reason: <code>{state.reasonCode}</code>
        </p>
      </div>
    );
  }

  if (state.kind === "error-with-retry") {
    return (
      <div className="rv-modal__reusable-fields" data-testid="reusable-assertion-fields-error">
        <h3 className="rv-modal__section-title">Reusable assertion fields</h3>
        <p className="rv-assertion-muted">This source assertion could not be loaded.</p>
        <button type="button" className="it-btn ghost xs" onClick={() => void state.retry()}>
          Retry
        </button>
      </div>
    );
  }

  const packetData = state.data;
  if (!packetData) {
    return (
      <div className="rv-modal__reusable-fields" data-testid="reusable-assertion-fields-unavailable">
        <h3 className="rv-modal__section-title">Reusable assertion fields</h3>
        <p className="rv-assertion-muted">
          Source assertion unavailable{"rawValue" in state && state.rawValue ? ` (${state.rawValue})` : ""}.
        </p>
      </div>
    );
  }

  return (
    <div className="rv-modal__reusable-fields" data-testid="reusable-assertion-fields">
      <h3 className="rv-modal__section-title">Reusable assertion fields</h3>
      <AssertionPacketFields
        packet={packetData}
        missingFields={state.kind === "legacy-missing" ? state.missingFields : []}
        compact
      />
    </div>
  );
}

export default ReusableAssertionFieldsColumn;
