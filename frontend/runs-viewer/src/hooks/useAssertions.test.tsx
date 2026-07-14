import { describe, expect, it, beforeEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { AuthContextValue } from "@/auth/AuthContext";
import type { EvidencePacket } from "@/types/rf/assertions_api.generated";

const mocks = vi.hoisted(() => ({
  fetchEvidencePacket: vi.fn(),
  fetchAssertionImpact: vi.fn(),
  useAuth: vi.fn(),
}));

vi.mock("@/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/client")>();
  return { ...actual, fetchEvidencePacket: mocks.fetchEvidencePacket, fetchAssertionImpact: mocks.fetchAssertionImpact };
});
vi.mock("@/auth/AuthContext", () => ({ useAuth: mocks.useAuth }));

import { ClientError } from "@/api/client";
import {
  selectLegacyMissingFields,
  selectPacketLifecycle,
  useClearAssertionStateOnWorkspaceChange,
  selectPacketObject,
  useAssertionImpact,
  useEvidencePacket,
} from "./useAssertions";

const readyAuth: AuthContextValue = {
  identity: { user_id: "reviewer", workspace_id: "ws-a", roles: ["reviewer"] },
  isLoading: false,
  provider: "local_static",
  authMode: "local_static",
};

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function packet(overrides: Partial<EvidencePacket> = {}): EvidencePacket {
  return {
    packet_version: "1", assertion_id: "a-1", assertion_version: 1,
    assertion: { kind: "source_assertion", lifecycle_state: "eligible" }, passage: {}, source_edition: {},
    qualifiers: {}, qualifier_extensions: {}, evaluations: [], freshness: { lifecycle_state: "eligible" },
    access_scope: "personal", rights_decision: { allowed: true, reason_code: "ok" },
    relationships: [], run_uses: [], report_uses: [], ...overrides,
  };
}

describe("P6-001 assertion hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useAuth.mockReturnValue(readyAuth);
  });

  it("clears candidate-derived state when a packet response is denied", async () => {
    mocks.fetchEvidencePacket.mockRejectedValue(new ClientError(403, "denied", "rights_denied"));
    const clearCandidate = vi.fn();
    const { result } = renderHook(() => useEvidencePacket("a-1", clearCandidate), { wrapper });
    await waitFor(() => expect(result.current.state.kind).toBe("denied"));
    expect(clearCandidate).toHaveBeenCalledTimes(1);
    expect(result.current.state).toMatchObject({ kind: "denied", reasonCode: "rights_denied" });
  });

  it("maps an unknown nested lifecycle enum to unavailable rather than a current state", async () => {
    mocks.fetchEvidencePacket.mockResolvedValue(packet({
      assertion: { kind: "source_assertion", lifecycle_state: "future_state" },
    }));
    const { result } = renderHook(() => useEvidencePacket("a-1"), { wrapper });
    await waitFor(() => expect(result.current.state.kind).toBe("unavailable"));
    expect(result.current.state).toMatchObject({ rawValue: "future_state" });
  });

  it("reads a stale lifecycle from the nested assertion record", async () => {
    mocks.fetchEvidencePacket.mockResolvedValue(packet({
      assertion: { kind: "source_assertion", lifecycle_state: "stale" },
      freshness: { lifecycle_state: "stale" },
    }));
    const { result } = renderHook(() => useEvidencePacket("a-1"), { wrapper });
    await waitFor(() => expect(result.current.state.kind).toBe("stale"));
  });

  it("keeps absent additive packet fields field-granular", () => {
    const legacy = packet({ passage: undefined as unknown as Record<string, unknown> });
    expect(selectPacketObject(legacy, "passage")).toBeUndefined();
    expect(selectLegacyMissingFields(legacy)).toContain("passage");
    expect(selectPacketObject(legacy, "assertion")).toEqual({ kind: "source_assertion", lifecycle_state: "eligible" });
    expect(selectPacketLifecycle(packet())).toBe("eligible");
  });

  it("maps impact 404 to a zero-count impact-unavailable state", async () => {
    mocks.fetchAssertionImpact.mockRejectedValue(new ClientError(404, "not found", "impact_unavailable"));
    const { result } = renderHook(() => useAssertionImpact("a-1"), { wrapper });
    await waitFor(() => expect(result.current.state.kind).toBe("unavailable"));
    expect(result.current.state).toMatchObject({ rawValue: "impact_unavailable", zeroCounts: true });
  });

  it("does not query until workspace/auth resolution completes", () => {
    mocks.useAuth.mockReturnValue({ ...readyAuth, identity: null, isLoading: true });
    const { result } = renderHook(() => useEvidencePacket("a-1"), { wrapper });
    expect(result.current.state.kind).toBe("loading");
    expect(mocks.fetchEvidencePacket).not.toHaveBeenCalled();
  });

  it("clears assertion candidate state when the workspace/auth scope transitions", async () => {
    const clearSelection = vi.fn();
    const { rerender } = renderHook(() => useClearAssertionStateOnWorkspaceChange(clearSelection), { wrapper });
    expect(clearSelection).not.toHaveBeenCalled();

    mocks.useAuth.mockReturnValue({
      ...readyAuth,
      identity: { ...readyAuth.identity!, workspace_id: "ws-b" },
    });
    rerender();

    await waitFor(() => expect(clearSelection).toHaveBeenCalledTimes(1));
  });
});
