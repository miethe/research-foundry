/**
 * AlertsFeed — cross-run attention feed screen (G3).
 *
 * Accessible at /alerts. Fetches the run index and all per-run exports,
 * calls summarizeRunAttention() for each, and renders a feed of alert cards
 * for runs that have at least one non-zero attention signal.
 *
 * Loading: progressive — cards appear as per-run fetches resolve.
 * Error:   per-run fetch failures show a placeholder row; feed continues.
 * Empty:   all-clean message when zero runs have any alert signal.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchRunList, fetchRunDetail } from "@/api/client";
import {
  summarizeRunAttention,
  deriveRunTitle,
  titleFromSlug,
  type RunAttentionSummary,
} from "@/lib/runs";
import type { RFRunExport, RFRunSummary } from "@/types/rf";
import "@/styles/alerts.css";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AlertRunResult {
  runId: string;
  /** Full export, available when fetch succeeded. */
  run?: RFRunExport;
  /** Attention summary, present when run is loaded and has signals. */
  attention?: RunAttentionSummary;
  /** True when this run fetch failed. */
  error?: boolean;
}

// ── Signal definitions ────────────────────────────────────────────────────────

interface SignalDef {
  key: keyof RunAttentionSummary;
  label: (value: number | boolean) => string;
  severity: "critical" | "warning" | "info";
}

const SIGNAL_DEFS: SignalDef[] = [
  {
    key: "failedChecks",
    label: (v) => `Failed verification checks: ${v as number}`,
    severity: "critical",
  },
  {
    key: "warningChecks",
    label: (v) => `Warning checks: ${v as number}`,
    severity: "warning",
  },
  {
    key: "unsupportedClaims",
    label: (v) => `Unsupported claims: ${v as number}`,
    severity: "critical",
  },
  {
    key: "mixedClaims",
    label: (v) => `Mixed/contradicted claims: ${v as number}`,
    severity: "warning",
  },
  {
    key: "danglingSources",
    label: (v) => `Dangling sources: ${v as number}`,
    severity: "warning",
  },
  {
    key: "redactedSources",
    label: (v) => `Redacted sources: ${v as number}`,
    severity: "info",
  },
  {
    key: "emptyInferenceBasis",
    label: (v) => `Inferences with empty basis: ${v as number}`,
    severity: "warning",
  },
  {
    key: "schemaMismatch",
    label: () => "Schema version mismatch",
    severity: "warning",
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function hasAnyAlert(attention: RunAttentionSummary): boolean {
  return (
    attention.failedChecks > 0 ||
    attention.warningChecks > 0 ||
    attention.unsupportedClaims > 0 ||
    attention.mixedClaims > 0 ||
    attention.danglingSources > 0 ||
    attention.redactedSources > 0 ||
    attention.emptyInferenceBasis > 0 ||
    attention.schemaMismatch
  );
}

function resolveTitle(run: RFRunExport): string {
  const derived = deriveRunTitle(run);
  if (derived && derived !== run.run_id) return derived;
  return titleFromSlug(run.run_id) ?? run.run_id;
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface AlertCardProps {
  result: AlertRunResult;
}

function AlertCard({ result }: AlertCardProps) {
  // Error placeholder
  if (result.error) {
    return (
      <div
        className="rv-alert-card rv-alert-card--error"
        data-testid="alert-card-error"
        data-run-id={result.runId}
        role="article"
        aria-label={`Run ${result.runId}: data unavailable`}
      >
        <div className="rv-alert-card__header">
          <h2 className="rv-alert-card__title">
            {titleFromSlug(result.runId) ?? result.runId}
          </h2>
          <span className="rv-alert-card__run-id">{result.runId}</span>
        </div>
        <p className="rv-alert-card__unavailable" data-testid="alert-unavailable-message">
          Run data unavailable.
        </p>
      </div>
    );
  }

  if (!result.run || !result.attention) return null;

  const title = resolveTitle(result.run);
  const attention = result.attention;

  const activeSignals = SIGNAL_DEFS.filter(({ key }) => {
    const val = attention[key];
    return typeof val === "boolean" ? val : val > 0;
  });

  return (
    <div
      className="rv-alert-card"
      data-testid="alert-card"
      data-run-id={result.runId}
      role="article"
      aria-label={`Alerts for run: ${title}`}
    >
      <div className="rv-alert-card__header">
        <h2 className="rv-alert-card__title" data-testid="alert-card-title">
          {title}
        </h2>
        <span className="rv-alert-card__run-id" data-testid="alert-card-run-id">
          {result.runId}
        </span>
      </div>

      <ul className="rv-alert-card__signals" aria-label="Attention signals">
        {activeSignals.map(({ key, label, severity }) => {
          const val = attention[key];
          return (
            <li
              key={key}
              className={`rv-alert-card__signal rv-alert-card__signal--${severity}`}
              data-testid={`alert-signal-${key}`}
            >
              <span className="rv-alert-card__signal-badge">
                {typeof val === "boolean" ? "!" : val}
              </span>
              <span className="rv-alert-card__signal-label">{label(val)}</span>
            </li>
          );
        })}
      </ul>

      <div className="rv-alert-card__footer">
        <Link
          to={`/runs/${encodeURIComponent(result.runId)}`}
          className="rv-alert-card__view-link"
          data-testid="alert-card-view-link"
          aria-label={`View run: ${title}`}
        >
          View run
        </Link>
      </div>
    </div>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export function AlertsFeed() {
  const [indexLoading, setIndexLoading] = useState(true);
  const [results, setResults] = useState<AlertRunResult[]>([]);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadAlerts() {
      let summaries: RFRunSummary[];
      try {
        summaries = await fetchRunList();
      } catch {
        if (!cancelled) {
          setIndexLoading(false);
          setPendingCount(0);
        }
        return;
      }

      if (cancelled) return;
      setIndexLoading(false);

      if (summaries.length === 0) {
        setPendingCount(0);
        return;
      }

      setPendingCount(summaries.length);

      // Fire all per-run fetches in parallel
      const fetchPromises = summaries.map(async (summary) => {
        const runId = summary.run_id;
        try {
          const run = await fetchRunDetail(runId);
          const attention = summarizeRunAttention(run);
          return { runId, run, attention } satisfies AlertRunResult;
        } catch {
          return { runId, error: true } satisfies AlertRunResult;
        }
      });

      // Settle each fetch as it resolves and progressively append to results
      fetchPromises.forEach((promise) => {
        promise.then((result) => {
          if (cancelled) return;
          // Only add to results if there is an alert or an error
          const shouldShow =
            result.error ||
            (result.attention && hasAnyAlert(result.attention));
          if (shouldShow) {
            setResults((prev) => [...prev, result]);
          }
          setPendingCount((prev) => Math.max(0, prev - 1));
        });
      });
    }

    void loadAlerts();

    return () => {
      cancelled = true;
    };
  }, []);

  const isLoading = indexLoading || pendingCount > 0;
  const hasResults = results.length > 0;

  return (
    <div className="rv-alerts" data-testid="alerts-feed">
      <h1 className="rv-alerts__title">Alerts</h1>

      {/* Loading indicator */}
      {isLoading && (
        <div
          className="rv-alerts__loading"
          role="status"
          aria-live="polite"
          aria-label="Loading attention signals"
          data-testid="alerts-loading"
        >
          <span className="rv-alerts__spinner" aria-hidden="true" />
          <span>
            {indexLoading
              ? "Loading run index…"
              : `Checking ${pendingCount} run${pendingCount !== 1 ? "s" : ""}…`}
          </span>
        </div>
      )}

      {/* Alert cards (progressive) */}
      {hasResults && (
        <div className="rv-alerts__feed" role="feed" aria-label="Run attention signals">
          {results.map((result) => (
            <AlertCard key={result.runId} result={result} />
          ))}
        </div>
      )}

      {/* Empty state — show only when all fetches are done and nothing to show */}
      {!isLoading && !hasResults && (
        <div
          className="rv-alerts__empty"
          role="status"
          aria-label="No attention signals"
          data-testid="alerts-empty"
        >
          <span className="rv-alerts__empty-icon" aria-hidden="true">
            &#10003;
          </span>
          <p className="rv-alerts__empty-message">No attention signals</p>
          <p className="rv-alerts__empty-sub">All runs look clean.</p>
        </div>
      )}
    </div>
  );
}

export default AlertsFeed;
