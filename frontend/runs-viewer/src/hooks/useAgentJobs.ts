/**
 * useAgentJobs — React Query hooks + SSE streaming hook for Agent Jobs (P4.5).
 *
 * Loopback-only: all hooks gate on isAgentsLoopbackEnabled(). Reads that
 * reach the server throw AgentsStaticModeError in static mode — callers get
 * an isError=true state they can render.
 *
 * useAgentJobEvents is a custom EventSource hook (not React Query): it opens
 * a persistent SSE connection against GET /api/agent-jobs/{id}/events,
 * accumulates pre-redacted event frames in local state, and reconnects from
 * the last known sequence number on error.
 *
 * SECURITY (AC-2.3): event payloads are already-redacted by the server
 * (P4.4 redact_payload gate). Never log, display, or store raw payload values.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acceptAgentJobArtifacts,
  cancelAgentJob,
  getAgentJob,
  isAgentsLoopbackEnabled,
  launchAgentJob,
  listAgentJobArtifacts,
} from "@/api/agentJobsClient";
import { getLoopbackBase } from "@/api/client";
import type { AcceptRequest, AgentJobEvent, LaunchAgentJobRequest } from "@/api/agentJobsClient";

export { isAgentsLoopbackEnabled };

// ── Query keys ────────────────────────────────────────────────────────────────

export const agentJobQueryKey = (jobId: string) =>
  ["rf", "agentJobs", "detail", jobId] as const;

export const agentJobArtifactsQueryKey = (jobId: string) =>
  ["rf", "agentJobs", "artifacts", jobId] as const;

// ── Reads (React Query) ───────────────────────────────────────────────────────

/** Fetch agent job detail including policy_snapshot (AC-4.5). */
export function useAgentJob(jobId: string) {
  return useQuery({
    queryKey: agentJobQueryKey(jobId),
    queryFn: () => getAgentJob(jobId),
    enabled: Boolean(jobId) && isAgentsLoopbackEnabled(),
    staleTime: 10_000,
  });
}

/** Fetch staged artifacts for an agent job (AC-3.5). */
export function useAgentJobArtifacts(jobId: string) {
  return useQuery({
    queryKey: agentJobArtifactsQueryKey(jobId),
    queryFn: () => listAgentJobArtifacts(jobId),
    enabled: Boolean(jobId) && isAgentsLoopbackEnabled(),
    staleTime: 10_000,
  });
}

// ── Mutations (React Query) ───────────────────────────────────────────────────

/**
 * Launch a new agent job.
 * On governance rejection (HTTP 422/400), isError=true and error is
 * AgentJobsApiError — use isGovernanceRejection(err.body) to discriminate
 * (AC-4.4). Form must NOT clear on governance error.
 */
export function useLaunchAgentJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: LaunchAgentJobRequest) => launchAgentJob(req),
    onSuccess: (job) => {
      queryClient.setQueryData(agentJobQueryKey(job.agent_job_id), job);
    },
  });
}

/** Cancel a running agent job. */
export function useCancelAgentJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => cancelAgentJob(jobId),
    onSuccess: (_void, jobId) => {
      queryClient.invalidateQueries({ queryKey: agentJobQueryKey(jobId) });
    },
  });
}

/**
 * Accept staged artifacts from a completed agent job (AC-3.5).
 * Invalidates both the artifact list and job detail on success.
 */
export function useAcceptAgentJobArtifacts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, req }: { jobId: string; req: AcceptRequest }) =>
      acceptAgentJobArtifacts(jobId, req),
    onSuccess: (_response, { jobId }) => {
      queryClient.invalidateQueries({ queryKey: agentJobArtifactsQueryKey(jobId) });
      queryClient.invalidateQueries({ queryKey: agentJobQueryKey(jobId) });
    },
  });
}

// ── SSE event streaming (custom hook) ────────────────────────────────────────

export type AgentJobEventsStatus = "idle" | "connecting" | "live" | "closed" | "error";

/**
 * Build the events SSE URL, including token (as query param — EventSource
 * does not support custom headers) and last sequence for reconnect continuity.
 */
function buildEventsUrl(jobId: string, lastSeq: number | null): string {
  const base = getLoopbackBase();
  // Token is a Vite build-time constant; access same env var as client.ts.
  const token: string =
    typeof import.meta !== "undefined"
      ? ((import.meta.env?.VITE_RUNS_LOOPBACK_API_TOKEN as string | undefined) ?? "")
      : "";
  const params = new URLSearchParams();
  if (token) params.set("token", token);
  if (lastSeq !== null) params.set("last_event_id", String(lastSeq));
  const qs = params.toString();
  return `${base}/agent-jobs/${encodeURIComponent(jobId)}/events${qs ? `?${qs}` : ""}`;
}

const SSE_RECONNECT_DELAY_MS = 3_000;

/**
 * useAgentJobEvents — SSE streaming hook for live agent job events (AC-2.3).
 *
 * Opens an EventSource against GET /api/agent-jobs/{jobId}/events when
 * `enabled` is true and `jobId` is non-null. Accumulates pre-redacted event
 * frames in state. On connection error, reconnects after 3 s passing
 * `?last_event_id=<N>` so the server can resume from the last known sequence.
 *
 * SECURITY: event.payload values are already-redacted. Never log or display
 * raw payload content.
 */
export function useAgentJobEvents(
  jobId: string | null,
  enabled: boolean,
): { events: AgentJobEvent[]; status: AgentJobEventsStatus } {
  const [events, setEvents] = useState<AgentJobEvent[]>([]);
  const [status, setStatus] = useState<AgentJobEventsStatus>("idle");
  const lastSequenceRef = useRef<number | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId || !enabled || !isAgentsLoopbackEnabled()) {
      setStatus("idle");
      return;
    }

    let active = true;

    function connect() {
      if (!active) return;
      clearTimer();

      const url = buildEventsUrl(jobId!, lastSequenceRef.current);
      const es = new EventSource(url);
      esRef.current = es;
      setStatus("connecting");

      es.onopen = () => {
        if (active) setStatus("live");
      };

      es.onmessage = (e: MessageEvent<string>) => {
        if (!active) return;
        try {
          const event = JSON.parse(e.data) as AgentJobEvent;
          // Track last sequence for reconnect continuity
          if (event.sequence != null) {
            lastSequenceRef.current = event.sequence;
          }
          // SECURITY: append pre-redacted event frame — do not inspect payload values
          setEvents((prev) => [...prev, event]);
        } catch {
          // Malformed SSE frame — skip silently per AC-2.3 contract
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        if (!active) return;
        setStatus("error");
        // Schedule reconnect with last-sequence continuity
        reconnectTimerRef.current = setTimeout(() => {
          if (active) connect();
        }, SSE_RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      active = false;
      clearTimer();
      esRef.current?.close();
      esRef.current = null;
      setStatus("closed");
    };
  }, [jobId, enabled, clearTimer]);

  return { events, status };
}
