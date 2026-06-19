/**
 * VerificationChecklist — renders named verification checks with status badges.
 *
 * For each check in RFVerification.checks:
 *   - pass → green badge
 *   - fail → red badge + deep-link anchor href="#clm_NNN" (when check.id used as claim_ref)
 *   - skip → neutral/idle badge
 *   - warning severity → orange styling
 *
 * Deep-link logic (AC P3-TRUST-001-1):
 *   The check `id` is the canonical claim_ref. Failing checks render
 *   <a href="#clm_NNN"> where clm_NNN is the check id if it looks like a
 *   claim ref, or a synthetic anchor from the check id otherwise.
 *   If no claim_ref can be derived the check renders without a link (no crash).
 *
 * Empty-state: when verification is absent or checks is empty, renders a
 * single "No verification data" placeholder.
 */

import type { RFVerification, RFVerificationCheck } from "@/types/rf";

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Derive a deep-link href from a check entry, or null when not applicable. */
function deepLinkFor(check: RFVerificationCheck): string | null {
  if (check.status !== "fail") return null;
  // If the check id already looks like clm_NNN use it directly
  if (/^clm_\d+$/.test(check.id)) return `#${check.id}`;
  // Otherwise derive a slugified anchor (consistent with ledger view anchors)
  return `#check-${check.id}`;
}

function checkPillClass(check: RFVerificationCheck): string {
  if (check.status === "pass") return "done";
  if (check.status === "fail") {
    return check.severity === "warning" ? "warn" : "blocked";
  }
  return "idle"; // skip
}

function checkLabel(check: RFVerificationCheck): string {
  if (check.status === "pass") return "Pass";
  if (check.status === "fail") {
    return check.severity === "warning" ? "Warning" : "Fail";
  }
  return "Skip";
}

/** Humanize snake_case check id → readable label. */
function humanizeCheckId(id: string): string {
  return id
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface VerificationChecklistProps {
  verification: RFVerification | null | undefined;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function VerificationChecklist({ verification }: VerificationChecklistProps) {
  // Empty-state: verification absent or no checks
  if (!verification?.present || !verification.checks || verification.checks.length === 0) {
    return (
      <div className="rv-verif-checklist rv-verif-checklist--empty" data-testid="verif-checklist-empty">
        <p className="rv-verif-checklist__empty-msg">No verification data available.</p>
      </div>
    );
  }

  const { checks, passed } = verification;

  return (
    <div className="rv-verif-checklist" data-testid="verif-checklist">
      {/* Summary line */}
      <div className="rv-verif-checklist__summary">
        <span
          className={`it-pill ${passed ? "done" : "blocked"}`}
          data-testid="verif-overall-badge"
        >
          {passed ? "All checks passed" : "Some checks failed"}
        </span>
        <span className="rv-verif-checklist__check-count">
          {checks.length} {checks.length === 1 ? "check" : "checks"}
        </span>
      </div>

      {/* Check list */}
      <ul className="rv-verif-checklist__list" role="list">
        {checks.map((check) => {
          const href = deepLinkFor(check);
          const pillClass = checkPillClass(check);
          const label = checkLabel(check);

          return (
            <li
              key={check.id}
              className={`rv-verif-check rv-verif-check--${check.status}`}
              data-testid={`verif-check-${check.id}`}
              data-check-status={check.status}
              data-check-severity={check.severity}
            >
              <span className={`it-pill ${pillClass} rv-verif-check__badge`}>
                {label}
              </span>
              <span className="rv-verif-check__name">
                {humanizeCheckId(check.id)}
              </span>
              {check.detail && (
                <span className="rv-verif-check__detail">{check.detail}</span>
              )}
              {href && (
                <a
                  href={href}
                  className="rv-verif-check__deeplink"
                  aria-label={`Jump to claim for failed check: ${check.id}`}
                  data-testid={`verif-check-deeplink-${check.id}`}
                >
                  View claim
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default VerificationChecklist;
