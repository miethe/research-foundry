/**
 * AssertionPacketFields — shared evidence-packet body sections (P6-002).
 *
 * Renders the complete packet in review order (Edition → Passage → Source
 * assertion/Qualifiers → Evaluation → Freshness/Rights → Relationships → Uses; see
 * .claude/worknotes/reusable-assertion-ledger/p6-design-guidance.md §A) and
 * spec §5.2. Shared by AssertionPacketInspector (Catalog docked inspector)
 * and ReusableAssertionFieldsColumn (ProvenanceModal right column) so the
 * two surfaces stay in lockstep without duplicating packet-derivation logic.
 *
 * Freshness, rights reasoning, and typed relationships remain visible here
 * even when their maps are additive or partially absent.
 */
import { formatDateTime } from "@/lib/runs";
import { selectPacketObject, selectPacketRelationships, selectPacketSubject } from "@/hooks/useAssertions";
import type { EvidencePacket } from "@/types/rf/assertions_api.generated";
import { CopyIdButton } from "./CopyIdButton";
import {
  evaluationKindLabel,
  extensionRows,
  knownQualifierRows,
  passageSelectorLocator,
  readString,
  verdictDisplay,
} from "./assertionDisplay";

export interface AssertionPacketFieldsProps {
  packet: EvidencePacket;
  /** Field names absent from this packet (from useEvidencePacket's legacy-missing discriminant). */
  missingFields?: readonly string[];
  /** Compact spacing for embedding inside ProvenanceModal's right column. */
  compact?: boolean;
}

function isRecordLike(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function AssertionPacketFields({ packet, missingFields = [], compact = false }: AssertionPacketFieldsProps) {
  const isMissing = (field: string) => missingFields.includes(field);

  const sourceEdition = selectPacketObject(packet, "source_edition");
  const editionId = readString(sourceEdition, "source_edition_id", "edition_id", "id");
  const capturedAt = readString(sourceEdition, "captured_at", "captured_date");

  const passage = selectPacketObject(packet, "passage");
  const passageId = readString(passage, "passage_id", "id");
  const normalizedText = readString(passage, "normalized_text", "text", "quote", "excerpt");
  const locator = passageSelectorLocator(passage?.selectors);

  const qualifiers = selectPacketObject(packet, "qualifiers");
  const qualifierRows = knownQualifierRows(qualifiers);
  const extensions = selectPacketObject(packet, "qualifier_extensions");
  const extensionRowsList = extensionRows(extensions);
  const freshness = selectPacketObject(packet, "freshness");
  const freshnessLifecycle = readString(freshness, "lifecycle_state");
  const freshnessReason = readString(freshness, "reason_code", "reason");
  const relationships = selectPacketRelationships(packet);
  const subjectLabel = selectPacketSubject(packet).kind === "inference" ? "Inference" : "Source assertion";

  const sectionClass = compact ? "rv-assertion-section rv-assertion-section--compact" : "rv-assertion-section";

  return (
    <>
      {/* ── Edition ── */}
      <section className={sectionClass} data-testid="assertion-section-edition">
        <h4>Edition</h4>
        {isMissing("source_edition") ? (
          <p className="rv-assertion-legacy-note">Not recorded in this legacy artifact.</p>
        ) : (
          <div className="rv-assertion-edition">
            <div className="rv-assertion-id-row">
              <code>{editionId ?? "Unavailable"}</code>
              {editionId && <CopyIdButton value={editionId} label="Copy source edition ID" />}
            </div>
            {capturedAt && <span className="rv-assertion-muted">captured {formatDateTime(capturedAt)}</span>}
          </div>
        )}
      </section>

      {/* ── Passage ── */}
      <section className={sectionClass} data-testid="assertion-section-passage">
        <h4>Passage</h4>
        {isMissing("passage") ? (
          <p className="rv-assertion-legacy-note">Not recorded in this legacy artifact.</p>
        ) : (
          <div className="rv-assertion-passage-block">
            <div className="rv-assertion-id-row">
              <code>{passageId ?? "Unavailable"}</code>
              {passageId && <CopyIdButton value={passageId} label="Copy passage ID" />}
            </div>
            <span className="rv-assertion-micro-eyebrow">Verbatim passage</span>
            <blockquote className="rv-assertion-blockquote">
              {normalizedText ?? "Passage text not recorded in this legacy artifact."}
            </blockquote>
            <div className="rv-assertion-locator">
              <span className="rv-assertion-locator__label">Locator</span>
              <span className="rv-assertion-locator__value">{locator ?? "No locator recorded."}</span>
              {locator && <CopyIdButton value={locator} label="Copy locator" />}
            </div>
          </div>
        )}
      </section>

      {/* ── Source assertion or inference / qualifiers ── */}
      <section className={sectionClass} data-testid="assertion-section-qualifiers">
        <h4>{subjectLabel}</h4>
        {isMissing("qualifiers") ? (
          <p className="rv-assertion-legacy-note">Not recorded in this legacy artifact.</p>
        ) : (
          <>
            <span className="rv-assertion-micro-eyebrow">Qualifiers</span>
            {qualifierRows.length > 0 ? (
              <dl className="rv-assertion-dl">
                {qualifierRows.map((row) => (
                  <div className="rv-assertion-dl__row" key={row.label}>
                    <dt>{row.label}</dt>
                    <dd>{row.value}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="rv-assertion-muted">No structured qualifiers recorded.</p>
            )}
            {!isMissing("qualifier_extensions") && extensionRowsList.length > 0 && (
              <div className="rv-assertion-extensions">
                <span className="rv-assertion-micro-eyebrow">Additional qualifiers</span>
                <dl className="rv-assertion-dl rv-assertion-dl--compact">
                  {extensionRowsList.map((row) => (
                    <div className="rv-assertion-dl__row" key={row.label}>
                      <dt>{row.label}</dt>
                      <dd>{row.value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </>
        )}
      </section>

      {/* ── Evaluation ── */}
      <section className={sectionClass} data-testid="assertion-section-evaluation">
        <h4>Evaluation</h4>
        {packet.evaluations.length > 0 ? (
          <ul className="rv-assertion-evaluations">
            {packet.evaluations.map((evaluation, idx) => {
              const record = isRecordLike(evaluation) ? evaluation : {};
              const kind = evaluationKindLabel(record.evaluation_kind);
              const verdict = verdictDisplay(record.verdict);
              const evaluator = isRecordLike(record.evaluator) ? record.evaluator : undefined;
              const evaluatorId = readString(evaluator, "id");
              const evaluatedAt = readString(record, "evaluated_at");
              return (
                <li key={idx} className="rv-assertion-evaluation-row">
                  <span className="rv-assertion-evaluation-kind">{kind}</span>
                  <span className={`it-chip ${verdict.color}`.trim()}>{verdict.label}</span>
                  {evaluatorId && <span className="rv-assertion-muted">{evaluatorId}</span>}
                  {evaluatedAt && <span className="rv-assertion-muted">{formatDateTime(evaluatedAt)}</span>}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="rv-assertion-muted">No evaluation recorded.</p>
        )}
      </section>

      <section className={sectionClass} data-testid="assertion-section-freshness">
        <h4>Freshness</h4>
        {isMissing("freshness") || !freshness ? (
          <p className="rv-assertion-legacy-note">Not recorded in this legacy artifact.</p>
        ) : (
          <dl className="rv-assertion-dl">
            <div className="rv-assertion-dl__row"><dt>Lifecycle</dt><dd>{freshnessLifecycle ?? "Unavailable"}</dd></div>
            <div className="rv-assertion-dl__row"><dt>Reason</dt><dd>{freshnessReason ?? "Not recorded"}</dd></div>
          </dl>
        )}
      </section>

      <section className={sectionClass} data-testid="assertion-section-rights">
        <h4>Rights and allowed use</h4>
        {packet.rights_decision ? (
          <dl className="rv-assertion-dl">
            <div className="rv-assertion-dl__row"><dt>Reuse decision</dt><dd>{packet.rights_decision.allowed ? "Eligible for reuse" : "Reuse blocked"}</dd></div>
            <div className="rv-assertion-dl__row"><dt>Reason</dt><dd>{packet.rights_decision.reason_code || "Not recorded"}</dd></div>
          </dl>
        ) : <p className="rv-assertion-legacy-note">Not recorded in this legacy artifact.</p>}
      </section>

      <section className={sectionClass} data-testid="assertion-section-relationships">
        <h4>Relationships</h4>
        {relationships.length === 0 ? (
          <p className="rv-assertion-muted">No typed relationships recorded.</p>
        ) : (
          <ul className="rv-assertion-relationships">
            {relationships.map((relationship, index) => {
              const kind = readString(relationship, "relationship_type", "kind", "record_type", "type") ?? "Unavailable";
              const id = readString(relationship, "relationship_id", "id", "object_id");
              const text = readString(relationship, "text", "summary", "label");
              return <li key={`${id ?? kind}-${index}`}><strong>{kind}</strong>{text ? ` · ${text}` : ""}{id ? <code> · {id}</code> : null}</li>;
            })}
          </ul>
        )}
      </section>

      {/* ── Uses ── */}
      <section className={sectionClass} data-testid="assertion-section-uses">
        <h4>Uses</h4>
        <p className="rv-assertion-uses-summary">
          Used in {packet.run_uses.length} run{packet.run_uses.length === 1 ? "" : "s"} ·{" "}
          {packet.report_uses.length} report revision{packet.report_uses.length === 1 ? "" : "s"}
        </p>
      </section>
    </>
  );
}

export default AssertionPacketFields;
