/**
 * EmptyState — shared placeholder for absent optional entities.
 *
 * Renders a labelled "not available" block. All 9 optional entity slots in
 * RunDetailScreen use this component so the user sees a consistent, non-crashing
 * placeholder rather than nothing (or a runtime error).
 */

interface EmptyStateProps {
  /** Short label for the absent entity, e.g. "Report" or "Governance Review". */
  label: string;
  /** Optional detail message. Defaults to "Not available for this run." */
  message?: string;
  /** Additional CSS class names for the wrapper. */
  className?: string;
}

export function EmptyState({
  label,
  message = "Not available for this run.",
  className = "",
}: EmptyStateProps) {
  return (
    <div className={`rv-empty-state ${className}`.trim()} data-testid="empty-state">
      <span className="rv-empty-state__label">{label}</span>
      <span className="rv-empty-state__msg">{message}</span>
    </div>
  );
}

export default EmptyState;
