/**
 * AssertionResultsTable — "Source assertions" catalog results (P6-002).
 *
 * Columns are deliberately narrower than the conceptual mockup/spec §5.1
 * ("Assertion, Edition, Lifecycle, Reuse decision, Updated"): the frozen
 * `AssertionSummary` DTO (assertions_api.generated.ts) only carries
 * assertion_id, assertion_version, lifecycle_state, access_scope, and
 * rights_decision — no assertion text, source edition id, updated_at, or
 * prior-use counts. Those require a full packet fetch (one per row would
 * defeat the search list). See the P6-002 completion report for the
 * backend follow-up this implies.
 *
 * Row click and Enter/Space select without opening a modal (spec §7);
 * aria-selected marks the active row.
 */
import type { AssertionSummary } from "@/types/rf/assertions_api.generated";
import { EmptyState } from "@/components/shared/EmptyState";
import { safeReasonCopy } from "@/lib/assertionReasonCopy";
import { accessScopeDisplay, lifecycleDisplay, reuseDecisionDisplay } from "./assertionDisplay";

export interface AssertionResultsTableProps {
  items: AssertionSummary[];
  selectedId: string | null;
  onSelect: (assertionId: string) => void;
  isFetching?: boolean;
}

export function AssertionResultsTable({ items, selectedId, onSelect, isFetching = false }: AssertionResultsTableProps) {
  if (items.length === 0) {
    return <EmptyState label="Source assertions" message="No source assertions match the current filters." />;
  }

  return (
    <div
      className={`rv-catalog-table-wrap rv-assertion-table-wrap${isFetching ? " is-fetching" : ""}`}
      data-testid="assertion-results-table"
      role="region"
      aria-label="Source assertion results table; scroll horizontally to view all columns"
      tabIndex={0}
    >
      <table className="rv-catalog-table" aria-label="Source assertion results">
        <thead>
          <tr>
            <th scope="col">Assertion</th>
            <th scope="col">Lifecycle</th>
            <th scope="col">Access</th>
            <th scope="col">Reuse decision</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const isSelected = item.assertion_id === selectedId;
            const lifecycle = lifecycleDisplay(item.lifecycle_state);
            const access = accessScopeDisplay(item.access_scope);
            const reuse = reuseDecisionDisplay(item.rights_decision);
            return (
              <tr
                key={item.assertion_id}
                className={`rv-catalog-row${isSelected ? " rv-catalog-row--selected" : ""}`}
                data-testid={`assertion-row-${item.assertion_id}`}
                onClick={() => onSelect(item.assertion_id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(item.assertion_id);
                  }
                }}
                tabIndex={0}
                role="row"
                aria-selected={isSelected}
              >
                <td className="rv-catalog-td rv-catalog-td--id">
                  <div className="rv-assertion-id-cell">
                    <code>{item.assertion_id}</code>
                    <span className="it-chip" data-testid="assertion-version-chip">
                      v{item.assertion_version}
                    </span>
                  </div>
                </td>
                <td className="rv-catalog-td">
                  <span className={`it-chip ${lifecycle.color}`.trim()}>
                    <span className="dot" aria-hidden="true" />
                    {lifecycle.label}
                  </span>
                </td>
                <td className="rv-catalog-td">
                  <span className={`it-chip ${access.color}`.trim()}>{access.label}</span>
                </td>
                <td className="rv-catalog-td">
                  <span
                    className={`it-chip ${reuse.color}`.trim()}
                    title={reuse.reasonCode ? safeReasonCopy(reuse.reasonCode) : undefined}
                  >
                    {reuse.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default AssertionResultsTable;
