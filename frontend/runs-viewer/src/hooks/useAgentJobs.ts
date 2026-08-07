/**
 * useAgentJobs — React Query hooks + SSE streaming hook for Agent Jobs (P4.5).
 *
 * Loopback-only: all hooks gate on isAgentsLoopbackEnabled(). Reads that
 * reach the server throw AgentsStaticModeError in static mode — callers get
 * an isError=true state they can render.
 *
 * useAgentJobEvents is a custom SSE hook (not React Query): it opens a
 * persistent `fetch` + `ReadableStream` connection against
 * GET /api/agent-jobs/{id}/events, accumulates pre-redacted event frames in
 * local state, and reconnects from the last known sequence number on error.
 *
 * AUTH (ARLS M1): the stream authenticates with an `Authorization: Bearer`
 * header resolved through the shared buildAuthHeaders() precedence in
 * api/client.ts (runtime resolver → build-time env → no header). It used to
 * ride an `EventSource`, which cannot send custom headers, so the credential
 * was passed as a `?token=` query param that NO server auth surface reads —
 * the stream 401'd under token-store / local_static auth. Credentials must
 * never appear in a URL (logs, history, Referer); do not reintroduce one.
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
import { getLoopbackAuthHeaders, getLoopbackBase } from "@/api/client";
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
 * Build the events SSE URL. Carries ONLY the resume id (`last_event_id`) —
 * never a credential.
 *
 * OQ-1 resolution: `stream_events()`
 * (src/research_foundry/api/routers/agent_jobs.py:396-428) reads the resume id
 * from NEITHER a query param NOR a `Last-Event-ID` header — `_sse_event_generator`
 * always replays `events.jsonl` from offset 0 (`yielded_count = 0`), and
 * `rg 'last_event_id|Last-Event' src/research_foundry/` has zero hits. So the
 * pre-existing `?last_event_id=` param is server-side inert today. It is kept
 * byte-identical (same name, same value, same position) for wire parity, and no
 * `Last-Event-ID` header is added: real `EventSource` only sends that header
 * when the stream emitted `id:` fields, and this server emits none — sending it
 * would imply resume support the server does not have. Fixing the server-side
 * resume is out of scope (Mode-D boundary: zero diff under src/research_foundry/).
 */
function buildEventsUrl(jobId: string, lastSeq: number | null): string {
  const base = getLoopbackBase();
  const params = new URLSearchParams();
  if (lastSeq !== null) params.set("last_event_id", String(lastSeq));
  const qs = params.toString();
  return `${base}/agent-jobs/${encodeURIComponent(jobId)}/events${qs ? `?${qs}` : ""}`;
}

/**
 * Headers for the SSE request.
 *
 * Delegates to getLoopbackAuthHeaders() → buildAuthHeaders() (api/client.ts) so
 * the stream shares the SINGLE auth-header precedence with every other loopback
 * call: runtime resolver (clerk / local_static session) → build-time
 * VITE_RUNS_LOOPBACK_API_TOKEN → no Authorization header at all. Only `Accept`
 * differs (this endpoint returns text/event-stream, not JSON).
 *
 * SECURITY: never inline a credential here, and never move one into the URL.
 */
function buildEventsHeaders(): Record<string, string> {
  return { ...getLoopbackAuthHeaders(), Accept: "text/event-stream" };
}

const SSE_RECONNECT_DELAY_MS = 3_000;

// ── SSE wire-format parser ────────────────────────────────────────────────────

/** One dispatched SSE event (the subset of the wire format this stream uses). */
export interface SseFrame {
  /** Concatenated `data:` lines, joined by "\n" with no trailing newline. */
  data: string;
  /** `event:` field, or null when the frame did not set one. */
  event: string | null;
  /** `id:` field, or null when the frame did not set one. */
  id: string | null;
}

/**
 * Incremental, partial-chunk-safe SSE parser.
 *
 * `fetch` + `ReadableStream` hands us arbitrary byte chunks: a single `read()`
 * may deliver half a frame, three frames, or a line split mid-field. Frames are
 * therefore accumulated in an internal buffer and `push()` emits ONLY complete
 * frames (a frame ends at a blank line). An unterminated tail stays buffered
 * until more bytes arrive, and is intentionally DROPPED if the stream ends —
 * matching `EventSource`, which never dispatches a partial frame.
 *
 * Handles LF, CRLF and lone-CR line endings per the SSE spec, including a "\r"
 * that lands at the very end of a chunk (held back, because the next chunk may
 * begin with the "\n" that completes a CRLF pair). Comment lines (":" prefix,
 * used for heartbeats) are ignored.
 */
export class SseFrameParser {
  private buffer = "";
  private dataLines: string[] = [];
  private eventName: string | null = null;
  private eventId: string | null = null;
  private sawField = false;

  /** Feed a decoded text chunk; returns every frame completed by it, in order. */
  push(chunk: string): SseFrame[] {
    this.buffer += chunk;
    const frames: SseFrame[] = [];

    for (;;) {
      const match = /\r\n|\n|\r/.exec(this.buffer);
      if (!match) break;
      // A lone trailing "\r" may be the first half of a CRLF split across
      // reads — wait for the next chunk before treating it as a line break.
      if (match[0] === "\r" && match.index + 1 === this.buffer.length) break;

      const line = this.buffer.slice(0, match.index);
      this.buffer = this.buffer.slice(match.index + match[0].length);
      const frame = this.consumeLine(line);
      if (frame) frames.push(frame);
    }

    return frames;
  }

  /** Process one complete line; returns a frame when the line dispatched one. */
  private consumeLine(line: string): SseFrame | null {
    if (line === "") {
      // Blank line = frame boundary. Per spec, dispatch only when the frame
      // carried data; otherwise just reset the field buffers.
      if (this.dataLines.length === 0) {
        this.reset();
        return null;
      }
      const frame: SseFrame = {
        data: this.dataLines.join("\n"),
        event: this.eventName,
        id: this.eventId,
      };
      this.reset();
      return frame;
    }

    if (line.startsWith(":")) return null; // comment / heartbeat

    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    switch (field) {
      case "data":
        this.dataLines.push(value);
        this.sawField = true;
        break;
      case "event":
        this.eventName = value;
        this.sawField = true;
        break;
      case "id":
        // Per spec an id containing NUL is ignored.
        if (!value.includes("\u0000")) this.eventId = value;
        this.sawField = true;
        break;
      default:
        // `retry:` and unknown fields are ignored (reconnect delay is fixed
        // client-side at SSE_RECONNECT_DELAY_MS for parity with the old hook).
        break;
    }
    return null;
  }

  /** True when a partial frame is still buffered (test/diagnostic aid). */
  hasPendingFrame(): boolean {
    return this.buffer.length > 0 || this.sawField;
  }

  private reset(): void {
    this.dataLines = [];
    this.eventName = null;
    this.eventId = null;
    this.sawField = false;
  }
}

/**
 * useAgentJobEvents — SSE streaming hook for live agent job events (AC-2.3).
 *
 * Opens a `fetch` stream against GET /api/agent-jobs/{jobId}/events when
 * `enabled` is true and `jobId` is non-null, sending an `Authorization: Bearer`
 * header (see buildEventsHeaders). Accumulates pre-redacted event frames in
 * state. On connection error — including a 401/403, which is what a missing or
 * rejected credential looks like — reconnects after 3 s passing
 * `?last_event_id=<N>`, exactly as the previous `EventSource` implementation did.
 *
 * Parity contract with the retired EventSource version (unchanged behaviour):
 *   - status transitions idle → connecting → live → error → connecting → …,
 *     and "closed" on unmount;
 *   - reconnect delay is SSE_RECONNECT_DELAY_MS (3000 ms);
 *   - `last_event_id` carries the last observed `event.sequence`;
 *   - malformed frames are skipped silently;
 *   - a clean server-side close is treated like a drop (reconnect), which the
 *     panel bounds by flipping `enabled` to false on terminal job states;
 *   - return shape is `{ events, status }`.
 *
 * DUP-01 (client-side dedup, deliberate departure from strict byte-parity):
 * the server always replays events.jsonl from offset 0 on every new
 * connection (`_sse_event_generator`, ignores `?last_event_id=`), so a
 * reconnect — including the ordinary "server closed the stream" path above,
 * not just an error — re-delivers every event already seen. `handleFrame`
 * drops any frame whose `sequence` is <= the last one appended, so the
 * accumulated `events` list never duplicates across a reconnect. Events with
 * a null/absent `sequence` carry no ordering signal and are never deduped.
 * The server-side replay-from-zero behaviour itself is unchanged (Mode-D:
 * zero diff under src/research_foundry/).
 *
 * CAST-01 (payload normalisation): a parsed frame's `payload` is validated,
 * not just cast — a frame whose `payload` key is absent or `null` is
 * normalised to `{}` before it ever reaches `events`, so no consumer can
 * crash on `Object.entries(undefined/null)`.
 *
 * SECURITY: event.payload values are already-redacted. Never log or display
 * raw payload content. Never log the request headers (they carry the bearer).
 */
export function useAgentJobEvents(
  jobId: string | null,
  enabled: boolean,
): { events: AgentJobEvent[]; status: AgentJobEventsStatus } {
  const [events, setEvents] = useState<AgentJobEvent[]>([]);
  const [status, setStatus] = useState<AgentJobEventsStatus>("idle");
  const lastSequenceRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // JOBID-LEAK-01: tracks the jobId this hook instance last streamed, so a
  // jobId change can be distinguished from any other reason the effect below
  // re-runs (e.g. `enabled` flipping on a terminal-state transition). Callers
  // such as AgentsScreen render AgentJobEventPanel without a `key`, so React
  // reuses this hook instance across jobs — lastSequenceRef and `events` are
  // per-job state that must not survive a jobId change, or a low-sequence
  // event from the NEW job gets silently dropped by the DUP-01 dedup guard as
  // if it were a stale replay of the OLD job (see handleFrame below).
  const prevJobIdRef = useRef<string | null>(null);

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

    // JOBID-LEAK-01: only reset per-job state when jobId itself changed from
    // the last run that actually streamed — never on an `enabled`/`clearTimer`
    // identity change with the same jobId, which would wipe a live job's
    // event history mid-stream.
    if (prevJobIdRef.current !== null && prevJobIdRef.current !== jobId) {
      lastSequenceRef.current = null;
      setEvents([]);
      setStatus("idle");
    }
    prevJobIdRef.current = jobId;

    let active = true;

    /** Append one parsed frame, tracking sequence for reconnect continuity. */
    function handleFrame(frame: SseFrame): void {
      if (!active || frame.data === "") return;
      try {
        const parsed = JSON.parse(frame.data) as Partial<AgentJobEvent>;
        // CAST-01: `JSON.parse(...) as AgentJobEvent` is a compile-time-only
        // assertion — nothing validates that a server frame actually carries
        // a `payload` object at the wire boundary. A frame whose `payload` is
        // absent or null previously reached the panel as-is and crashed
        // `formatPayloadSummary`'s `Object.entries(payload)` at render time.
        // Normalise here so no consumer downstream of this hook ever sees a
        // non-object payload.
        const payload =
          parsed.payload != null && typeof parsed.payload === "object"
            ? (parsed.payload as Record<string, unknown>)
            : {};
        const event: AgentJobEvent = { ...parsed, payload } as AgentJobEvent;

        // DUP-01: the server's `_sse_event_generator` resets `yielded_count = 0`
        // on every new connection and replays events.jsonl from offset 0 — the
        // client's `?last_event_id=` is inert server-side (see buildEventsUrl's
        // OQ-1 comment above). A clean server close also triggers
        // scheduleReconnect() below, so this fires on ordinary job completion /
        // keep-alive expiry, not just transient drops. Drop any frame whose
        // sequence we've already appended instead of doubling the event history
        // on every reconnect. Events with a null/absent sequence (no ordering
        // signal) are never deduped — always appended.
        if (event.sequence != null) {
          if (lastSequenceRef.current !== null && event.sequence <= lastSequenceRef.current) {
            return;
          }
          lastSequenceRef.current = event.sequence;
        }
        // SECURITY: append pre-redacted event frame — do not inspect payload values
        setEvents((prev) => [...prev, event]);
      } catch {
        // Malformed SSE frame — skip silently per AC-2.3 contract
      }
    }

    /** EventSource-parity error path: surface "error", retry after 3 s. */
    function scheduleReconnect(): void {
      if (!active) return;
      setStatus("error");
      clearTimer();
      reconnectTimerRef.current = setTimeout(() => {
        if (active) void connect();
      }, SSE_RECONNECT_DELAY_MS);
    }

    async function connect(): Promise<void> {
      if (!active) return;
      clearTimer();

      const controller = new AbortController();
      abortRef.current = controller;
      setStatus("connecting");

      let response: Response;
      try {
        response = await fetch(buildEventsUrl(jobId!, lastSequenceRef.current), {
          method: "GET",
          // AUTH: bearer travels in the header, never in the URL.
          headers: buildEventsHeaders(),
          signal: controller.signal,
          cache: "no-store",
        });
      } catch {
        // Network failure or abort — abort during teardown must not reconnect.
        if (active) scheduleReconnect();
        return;
      }

      if (!active) return;
      if (!response.ok || !response.body) {
        // 401/403 (unauthenticated), 404, or a bodyless response: same
        // observable outcome as EventSource's onerror.
        scheduleReconnect();
        return;
      }

      setStatus("live");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const parser = new SseFrameParser();

      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (!active) {
            void reader.cancel().catch(() => undefined);
            return;
          }
          if (done) break;
          if (value !== undefined) {
            for (const frame of parser.push(decoder.decode(value, { stream: true }))) {
              handleFrame(frame);
            }
          }
        }
      } catch {
        // Mid-stream read failure — reconnect with last-sequence continuity.
        if (active) scheduleReconnect();
        return;
      }

      // Server closed the stream. EventSource reconnects here too; the panel
      // stops that loop by disabling the hook once the job is terminal.
      scheduleReconnect();
    }

    void connect();

    return () => {
      active = false;
      clearTimer();
      abortRef.current?.abort();
      abortRef.current = null;
      setStatus("closed");
    };
  }, [jobId, enabled, clearTimer]);

  return { events, status };
}
