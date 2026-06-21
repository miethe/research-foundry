/**
 * LibraryScreen — Reusable Outputs & Writeback Artifacts Index (G4, Wave-2 Library tab).
 *
 * Accessible at /library. Displays a cross-run index with three labeled sections:
 *   1. Published Reports  — runs where report_draft is non-null and
 *      writebacks.approved_for_writeback === true.
 *   2. Writeback Artifacts — all writebacks.targets[] entries across loaded runs,
 *      grouped by status (published / pending / failed / other).
 *   3. Reusable Outputs / SkillBOM Candidates — entries from
 *      reusable_output_candidates[] when present (post-F5/P7 exports).
 *
 * Graceful empty states:
 *   - Each section shows a non-error explanatory message when its backing data
 *     is absent, null, or empty. No spinner. No crash.
 *   - reusable_output_candidates field is absent on pre-F5 exports; section
 *     must not throw when field is undefined/null on every loaded run.
 *
 * Data pattern: mirrors PoliciesScreen — loads full RFRunExport per summary
 * using the existing React Query cache. Library content reflects whichever
 * runs have been pre-loaded (no forced N+1 waterfall on first visit).
 * For small personal deployments this is acceptable; see Risk Areas in the contract.
 */

import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchRunDetail, fetchRunList } from "@/api/client";
import { deriveRunTitle, titleFromSlug } from "@/lib/runs";
import type { RFRunExport, RFRunSummary, RFWritebackTarget, ReusableOutputCandidate } from "@/types/rf/run-export";
import "@/styles/library.css";

// ── Data aggregation helpers ──────────────────────────────────────────────────

/** An enriched published-report entry combining run metadata with display fields. */
interface PublishedReportEntry {
  runId: string;
  title: string;
  destinations: string[];
  inIndex: boolean;
}

/** A writeback target entry enriched with run context. */
interface WritebackArtifactEntry {
  runId: string;
  runTitle: string;
  target: RFWritebackTarget;
  inIndex: boolean;
}

/** A reusable output candidate enriched with run context. */
interface ReusableOutputEntry {
  runId: string;
  runTitle: string;
  candidate: ReusableOutputCandidate;
  /** Whether the referenced run (source_run_id ?? runId) is in the loaded summary index. */
  inIndex: boolean;
}

/**
 * Derive a display title for a run from its export or fall back to slug humanization.
 * Matches the pattern used in SwarmScreen and RunList.
 */
function getRunDisplayTitle(run: RFRunExport): string {
  return (
    (run.title && run.title !== run.run_id ? run.title : null) ??
    deriveRunTitle(run) ??
    titleFromSlug(run.run_id) ??
    run.run_id
  );
}

/**
 * Aggregate Published Report entries from an array of loaded run exports.
 * A run qualifies when report_draft is non-null AND
 * writebacks.approved_for_writeback === true (treating absent as false, R-P3 resilience).
 */
function aggregatePublishedReports(
  runs: RFRunExport[],
  summaryIds: Set<string>,
): PublishedReportEntry[] {
  return runs
    .filter(
      (run) =>
        run.report_draft != null &&
        run.writebacks?.approved_for_writeback === true,
    )
    .map((run) => ({
      runId: run.run_id,
      title: getRunDisplayTitle(run),
      destinations: (run.writebacks?.targets ?? [])
        .map((t) => t.destination)
        .filter((d): d is string => Boolean(d)),
      inIndex: summaryIds.has(run.run_id),
    }));
}

/**
 * Flatten all writebacks.targets[] entries across loaded runs.
 * Runs with absent/null writebacks contribute no entries.
 */
function aggregateWritebackArtifacts(
  runs: RFRunExport[],
  summaryIds: Set<string>,
): WritebackArtifactEntry[] {
  return runs.flatMap((run) => {
    const targets = run.writebacks?.targets ?? [];
    return targets.map((target) => ({
      runId: run.run_id,
      runTitle: getRunDisplayTitle(run),
      target,
      inIndex: summaryIds.has(run.run_id),
    }));
  });
}

/**
 * Flatten all reusable_output_candidates[] across loaded runs.
 * Runs where the field is absent, null, or empty contribute no entries.
 * Never throws — always returns an array (possibly empty).
 * inIndex is set based on whether candidate.source_run_id (or the run's own run_id
 * as fallback) is present in the loaded summary index — matching the stale-run guard
 * used by the Published Reports and Writeback Artifacts sections (AC G4-7).
 */
function aggregateReusableOutputs(
  runs: RFRunExport[],
  summaryIds: Set<string>,
): ReusableOutputEntry[] {
  return runs.flatMap((run) => {
    const candidates = run.reusable_output_candidates ?? [];
    return candidates.map((candidate) => {
      const refId = candidate.source_run_id ?? run.run_id;
      return {
        runId: run.run_id,
        runTitle: getRunDisplayTitle(run),
        candidate,
        inIndex: summaryIds.has(refId),
      };
    });
  });
}

// ── Status badge helpers ──────────────────────────────────────────────────────

type WritebackStatus = "published" | "pending" | "failed" | "other";

function normalizeWritebackStatus(status: string | null | undefined): WritebackStatus {
  const s = (status ?? "").toLowerCase();
  if (s === "published") return "published";
  if (s === "pending") return "pending";
  if (s === "failed") return "failed";
  return "other";
}

// ── Data-loading hooks ────────────────────────────────────────────────────────

interface LoadedRun {
  runId: string;
  data: RFRunExport | null;
  isLoading: boolean;
}

/**
 * Load full run exports for each summary entry.
 * React Query deduplicates and caches; for small deployments eager batch-load is fine.
 * Mirrors the pattern in PoliciesScreen.useRunGovernanceRows.
 */
function useLoadedRuns(summaries: RFRunSummary[]): LoadedRun[] {
  return summaries.map((s) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const { data, isLoading } = useQuery({
      queryKey: ["rf", "runs", "detail", s.run_id],
      queryFn: () => fetchRunDetail(s.run_id),
      staleTime: 60_000,
    });
    return {
      runId: s.run_id,
      data: data ?? null,
      isLoading,
    };
  });
}

// ── Sub-components ────────────────────────────────────────────────────────────

// ── Published Reports Section ──

interface PublishedReportsSectionProps {
  entries: PublishedReportEntry[];
  isLoading: boolean;
}

function PublishedReportsSection({ entries, isLoading }: PublishedReportsSectionProps) {
  if (isLoading) {
    return (
      <div className="rv-library__panel" data-testid="library-reports-loading">
        <div className="rv-loading">
          <p>Loading runs…</p>
        </div>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div
        className="rv-library__panel rv-library__panel--empty"
        data-testid="library-reports-empty"
        role="note"
      >
        <p className="rv-library__muted">
          No published reports found. Reports appear here when a run has a
          synthesized report_draft and writeback approval (
          <code>approved_for_writeback: true</code>).
        </p>
      </div>
    );
  }

  return (
    <div className="rv-library__panel" data-testid="library-reports-list">
      <ul className="rv-library__card-list" role="list">
        {entries.map((entry) => (
          <li
            key={entry.runId}
            className="rv-library__card"
            data-testid="library-report-card"
            role="article"
          >
            <div className="rv-library__card-title">
              {entry.inIndex ? (
                <Link
                  to={`/runs/${encodeURIComponent(entry.runId)}?view=report`}
                  className="rv-library__run-link"
                  data-testid="library-report-link"
                >
                  {entry.title}
                </Link>
              ) : (
                <span className="rv-library__run-text">{entry.title}</span>
              )}
            </div>
            <div className="rv-library__card-meta">
              <span className="rv-library__run-id" data-testid="library-report-run-id">
                {entry.runId}
              </span>
              {entry.destinations.length > 0 && (
                <span className="rv-library__destinations">
                  Writeback: {entry.destinations.join(", ")}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Writeback Artifacts Section ──

interface WritebackArtifactsSectionProps {
  entries: WritebackArtifactEntry[];
  isLoading: boolean;
}

function WritebackArtifactsSection({ entries, isLoading }: WritebackArtifactsSectionProps) {
  if (isLoading) {
    return (
      <div className="rv-library__panel" data-testid="library-writebacks-loading">
        <div className="rv-loading">
          <p>Loading runs…</p>
        </div>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div
        className="rv-library__panel rv-library__panel--empty"
        data-testid="library-writebacks-empty"
        role="note"
      >
        <p className="rv-library__muted">
          No writeback artifacts found. Run{" "}
          <code>rf run export --all</code> and rebuild if you expect data here.
        </p>
      </div>
    );
  }

  return (
    <div className="rv-library__panel" data-testid="library-writebacks-list">
      <ul className="rv-library__card-list" role="list">
        {entries.map((entry, i) => {
          const status = normalizeWritebackStatus(entry.target.status);
          const targetName = entry.target.name ?? entry.target.destination ?? "Unnamed target";
          return (
            <li
              key={`${entry.runId}-${i}`}
              className="rv-library__card"
              data-testid="library-writeback-card"
              role="article"
            >
              <div className="rv-library__card-header">
                <span className="rv-library__artifact-name">{targetName}</span>
                <span
                  className={`rv-library__status-badge rv-library__status-badge--${status}`}
                  data-testid="library-writeback-status"
                >
                  {entry.target.status ?? "—"}
                </span>
              </div>
              <div className="rv-library__card-meta">
                {entry.target.destination && (
                  <span className="rv-library__destination">
                    {entry.target.destination}
                  </span>
                )}
                {entry.target.url && (
                  <a
                    href={entry.target.url}
                    className="rv-library__run-link"
                    target="_blank"
                    rel="noopener noreferrer"
                    data-testid="library-writeback-url"
                  >
                    {entry.target.url}
                  </a>
                )}
              </div>
              <div className="rv-library__card-run-ref">
                {entry.inIndex ? (
                  <Link
                    to={`/runs/${encodeURIComponent(entry.runId)}`}
                    className="rv-library__run-link rv-library__run-link--secondary"
                    data-testid="library-writeback-run-link"
                  >
                    {entry.runTitle}
                  </Link>
                ) : (
                  <span className="rv-library__run-text rv-library__run-text--secondary">
                    {entry.runTitle}
                  </span>
                )}
                <span className="rv-library__run-id">{entry.runId}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Reusable Outputs Section ──

interface ReusableOutputsSectionProps {
  entries: ReusableOutputEntry[];
  isLoading: boolean;
  anyFieldPresent: boolean;
}

function ReusableOutputsSection({
  entries,
  isLoading,
  anyFieldPresent,
}: ReusableOutputsSectionProps) {
  if (isLoading) {
    return (
      <div className="rv-library__panel" data-testid="library-reusable-loading">
        <div className="rv-loading">
          <p>Loading runs…</p>
        </div>
      </div>
    );
  }

  // Primary resilience path: field absent on all loaded runs (pre-F5 exports)
  if (!anyFieldPresent) {
    return (
      <div
        className="rv-library__panel rv-library__panel--empty"
        data-testid="library-reusable-empty-pref5"
        role="note"
      >
        <p className="rv-library__muted" data-testid="library-reusable-empty-message">
          Reusable output data requires the enriched export from run-metadata-enrichment
          (F5). Re-export runs to populate.
        </p>
      </div>
    );
  }

  // Field is present but empty across loaded runs
  if (entries.length === 0) {
    return (
      <div
        className="rv-library__panel rv-library__panel--empty"
        data-testid="library-reusable-empty"
        role="note"
      >
        <p className="rv-library__muted">
          No reusable output candidates recorded in the loaded runs.
        </p>
      </div>
    );
  }

  return (
    <div className="rv-library__panel" data-testid="library-reusable-list">
      <ul className="rv-library__card-list" role="list">
        {entries.map((entry, i) => (
          <li
            key={`${entry.runId}-${i}`}
            className="rv-library__card"
            data-testid="library-reusable-card"
            role="article"
          >
            <div className="rv-library__card-header">
              <span className="rv-library__artifact-name">
                {entry.candidate.description}
              </span>
              {entry.candidate.is_skillbom_candidate && (
                <span
                  className="rv-library__skillbom-badge"
                  data-testid="library-skillbom-badge"
                >
                  SkillBOM candidate
                </span>
              )}
            </div>
            <div className="rv-library__card-run-ref">
              {/* source_run_id may differ from entry.runId for aggregated views.
                  When the referenced run is not in the loaded index (stale ref),
                  render plain text instead of a broken link (AC G4-7). */}
              {entry.inIndex ? (
                <Link
                  to={`/runs/${encodeURIComponent(entry.candidate.source_run_id ?? entry.runId)}`}
                  className="rv-library__run-link rv-library__run-link--secondary"
                  data-testid="library-reusable-run-link"
                >
                  {entry.runTitle}
                </Link>
              ) : (
                <span
                  className="rv-library__run-text rv-library__run-text--secondary"
                  data-testid="library-reusable-run-text"
                >
                  {entry.runTitle}
                </span>
              )}
              <span className="rv-library__run-id">
                {entry.candidate.source_run_id ?? entry.runId}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

export function LibraryScreen() {
  const {
    data: summaries,
    isLoading: indexLoading,
  } = useQuery<RFRunSummary[], Error>({
    queryKey: ["rf", "runs", "list"],
    queryFn: fetchRunList,
    staleTime: 60_000,
  });

  const runSummaries = useMemo(() => summaries ?? [], [summaries]);
  const summaryIds = useMemo(
    () => new Set(runSummaries.map((s) => s.run_id)),
    [runSummaries],
  );

  // Batch-load all run details (mirrors PoliciesScreen pattern).
  const loadedRuns = useLoadedRuns(runSummaries);
  const anyLoading = indexLoading || loadedRuns.some((r) => r.isLoading);

  // Aggregate from all successfully loaded runs
  const readyRuns = useMemo(
    () => loadedRuns.flatMap((r) => (r.data ? [r.data] : [])),
    [loadedRuns],
  );

  const publishedReports = useMemo(
    () => aggregatePublishedReports(readyRuns, summaryIds),
    [readyRuns, summaryIds],
  );

  const writebackArtifacts = useMemo(
    () => aggregateWritebackArtifacts(readyRuns, summaryIds),
    [readyRuns, summaryIds],
  );

  const reusableOutputs = useMemo(
    () => aggregateReusableOutputs(readyRuns, summaryIds),
    [readyRuns, summaryIds],
  );

  // Determine whether any loaded run has the reusable_output_candidates field at all.
  // Absent on ALL runs = pre-F5 export: show the specific empty-state message.
  const anyReusableFieldPresent = useMemo(
    () => readyRuns.some((run) => run.reusable_output_candidates !== undefined),
    [readyRuns],
  );

  return (
    <div className="rv-library" data-testid="library-screen">
      <header className="rv-library__header">
        <h1 className="rv-library__title">Library</h1>
        <p className="rv-library__subtitle">
          Cross-run index of published reports, writeback artifacts, and reusable outputs.
        </p>
      </header>

      {/* ── Published Reports ── */}
      <section
        className="rv-library__section"
        aria-labelledby="library-reports-title"
        data-testid="library-reports-section"
      >
        <h2 id="library-reports-title" className="rv-library__section-title">
          Published Reports
        </h2>
        <PublishedReportsSection
          entries={publishedReports}
          isLoading={anyLoading}
        />
      </section>

      {/* ── Writeback Artifacts ── */}
      <section
        className="rv-library__section"
        aria-labelledby="library-writebacks-title"
        data-testid="library-writebacks-section"
      >
        <h2 id="library-writebacks-title" className="rv-library__section-title">
          Writeback Artifacts
        </h2>
        <WritebackArtifactsSection
          entries={writebackArtifacts}
          isLoading={anyLoading}
        />
      </section>

      {/* ── Reusable Outputs / SkillBOM Candidates ── */}
      <section
        className="rv-library__section"
        aria-labelledby="library-reusable-title"
        data-testid="library-reusable-section"
      >
        <h2 id="library-reusable-title" className="rv-library__section-title">
          Reusable Outputs / SkillBOM Candidates
        </h2>
        <ReusableOutputsSection
          entries={reusableOutputs}
          isLoading={anyLoading}
          anyFieldPresent={anyReusableFieldPresent}
        />
      </section>
    </div>
  );
}

export default LibraryScreen;
