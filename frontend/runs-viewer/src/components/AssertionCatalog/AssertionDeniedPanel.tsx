/**
 * AssertionDeniedPanel — bounded fail-closed catalog state (P6-002, spec §6.C).
 *
 * Replaces the results region AND inspector together; zero candidate-derived
 * remnants (no counts, facets, pagination, previous inspector). Copy is
 * exact per spec; `reasonCode` is the real backend-supplied denial reason
 * (e.g. "workspace_context_missing", "rights_denied" — see
 * assertion_catalog.py) rendered verbatim, never the mockup's illustrative
 * "assertion_ledger_access_denied" placeholder string.
 */
import { useNavigate } from "react-router-dom";

export interface AssertionDeniedPanelProps {
  reasonCode: string;
}

export function AssertionDeniedPanel({ reasonCode }: AssertionDeniedPanelProps) {
  const navigate = useNavigate();

  return (
    <div className="rv-assertion-denied" data-testid="assertion-denied-panel" role="status">
      <span className="rv-assertion-denied__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.6">
          <path d="M12 2 3 6v6c0 5 4 8.5 9 10 5-1.5 9-5 9-10V6l-9-4Z" />
          <rect x="9" y="11" width="6" height="5" rx="1" />
          <path d="M10.5 11V9a1.5 1.5 0 0 1 3 0v2" />
        </svg>
      </span>
      <h2 className="rv-assertion-denied__title">Assertion ledger unavailable</h2>
      <p className="rv-assertion-denied__copy">This workspace cannot access reusable assertion records.</p>
      <hr className="rv-assertion-denied__divider" />
      <p className="rv-assertion-denied__reason">
        Reason: <code>{reasonCode}</code>
      </p>
      <hr className="rv-assertion-denied__divider" />
      <p className="rv-assertion-denied__disclosure">
        No assertion content, counts, facets, suggestions, or prior-use metadata was loaded.
      </p>
      <p className="rv-assertion-denied__recovery">
        Run-local research remains available from <strong>Portfolio</strong>.
      </p>
      <button
        type="button"
        className="it-btn rv-assertion-denied__action"
        onClick={() => navigate("/runs")}
        data-testid="assertion-denied-return"
      >
        <span aria-hidden="true">←</span> Return to Portfolio
      </button>
    </div>
  );
}

export default AssertionDeniedPanel;
