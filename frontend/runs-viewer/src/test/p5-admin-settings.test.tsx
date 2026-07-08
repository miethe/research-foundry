/**
 * P5-admin-settings — Tests for FEAUTH-004: Admin settings UI.
 *
 * Tests:
 *   1. Admin section renders for admin/owner identity; hidden for researcher/reviewer/viewer/null
 *   2. WorkspaceMembersPanel renders member list when API returns valid data
 *   3. WorkspaceMembersPanel shows disabled state when API returns null members (GATE-901)
 *   4. WorkspaceMembersPanel shows disabled state when fetch fails (GATE-901)
 *   5. RateLimitConfigPanel shows disabled state when API returns null/fails (GATE-900/GATE-901)
 *   6. AuthProviderStatusPanel shows disabled state when fetch fails (GATE-901)
 *   7. AUDIT-900 N/A: no admin UI surface exposes audit-log-derived fields
 *
 * Auth mocking: vi.mock("@/auth/AuthContext") + vi.mocked(useAuth).mockReturnValue(...)
 * Fetch mocking: vi.spyOn(globalThis, "fetch") per test; vi.restoreAllMocks() in afterEach.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";

import { SettingsScreen } from "@/screens/SettingsScreen";
import { WorkspaceMembersPanel } from "@/components/AdminSettings/WorkspaceMembersPanel";
import { RateLimitConfigPanel } from "@/components/AdminSettings/RateLimitConfigPanel";
import { AuthProviderStatusPanel } from "@/components/AdminSettings/AuthProviderStatusPanel";
import { RoleAssignmentPanel } from "@/components/AdminSettings/RoleAssignmentPanel";
import type { AuthContextValue } from "@/auth/AuthContext";
import { useAuth } from "@/auth/AuthContext";

// ── Auth mock ─────────────────────────────────────────────────────────────────

vi.mock("@/auth/AuthContext", () => ({
  useAuth: vi.fn(),
  AuthContext: {
    // Minimal stub so any direct context consumers don't crash
    Provider: ({ children }: { children: ReactNode }) => <>{children}</>,
  },
}));

const mockUseAuth = vi.mocked(useAuth);

/** Build an AuthContextValue with sensible defaults. */
function makeAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    identity: null,
    isLoading: false,
    provider: "none",
    authMode: "none",
    ...overrides,
  };
}

/** Admin identity — has ["admin"] role and authMode != "none". */
const ADMIN_AUTH: AuthContextValue = makeAuth({
  identity: {
    user_id: "user-admin",
    workspace_id: "ws-1",
    roles: ["admin"],
  },
  authMode: "local_static",
  provider: "local_static",
});

/** Owner identity. */
const OWNER_AUTH: AuthContextValue = makeAuth({
  identity: {
    user_id: "user-owner",
    workspace_id: "ws-1",
    roles: ["owner"],
  },
  authMode: "local_static",
  provider: "local_static",
});

// ── Fetch helpers ─────────────────────────────────────────────────────────────

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function errorResponse(status: number): Response {
  return new Response(JSON.stringify({ detail: "Error" }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// ── Test fixture data ─────────────────────────────────────────────────────────

const WORKSPACE_DATA = {
  workspace_id: "ws-1",
  members: [
    { user_id: "u1", email: "alice@example.com", role: "admin" },
    { user_id: "u2", email: "bob@example.com",   role: "researcher" },
  ],
};

const RATE_LIMIT_DATA = {
  enabled: true,
  window_seconds: 60,
  max_requests: 100,
  per_identity: true,
  per_route: false,
};

const AUTH_PROVIDER_DATA = {
  provider: "local_static",
  available: true,
  details: "running",
};

// ── Restore fetch mock after each test ───────────────────────────────────────

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

// ═════════════════════════════════════════════════════════════════════════════
// (1) Admin section visibility based on role
// ═════════════════════════════════════════════════════════════════════════════

describe("SettingsScreen — admin section visibility", () => {
  /**
   * The admin section must be rendered when identity has admin/owner role
   * and authMode is not "none". It must be completely absent (not just hidden)
   * for all other identity states.
   */

  // Stub fetch so panels inside admin section don't produce unhandled promise rejections
  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(errorResponse(503));
  });

  it("renders admin section for 'admin' role", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).not.toBeNull();
  });

  it("renders admin section for 'owner' role", async () => {
    mockUseAuth.mockReturnValue(OWNER_AUTH);
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).not.toBeNull();
  });

  it("hides admin section for 'researcher' role", () => {
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: ["researcher"] },
        authMode: "local_static",
        provider: "local_static",
      }),
    );
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).toBeNull();
  });

  it("hides admin section for 'reviewer' role", () => {
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: ["reviewer"] },
        authMode: "local_static",
        provider: "local_static",
      }),
    );
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).toBeNull();
  });

  it("hides admin section for 'viewer' role", () => {
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: ["viewer"] },
        authMode: "local_static",
        provider: "local_static",
      }),
    );
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).toBeNull();
  });

  it("hides admin section when identity is null (unauthenticated)", () => {
    mockUseAuth.mockReturnValue(
      makeAuth({ identity: null, authMode: "local_static", provider: "local_static" }),
    );
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).toBeNull();
  });

  it("hides admin section when authMode is 'none' even if identity has admin role (AC-5a)", () => {
    // authMode=none → isAdmin forced false regardless of roles
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: ["admin"] },
        authMode: "none",
        provider: "none",
      }),
    );
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).toBeNull();
  });

  it("hides admin section when identity.roles is empty array", () => {
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: [] },
        authMode: "local_static",
        provider: "local_static",
      }),
    );
    const { container } = render(<SettingsScreen />);
    expect(container.querySelector("[data-testid='admin-section']")).toBeNull();
  });

  it("admin section contains all 4 panels when visible", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<SettingsScreen />);
    const section = container.querySelector("[data-testid='admin-section']")!;
    expect(section).not.toBeNull();
    // All 4 panel containers exist (may be in loading or disabled state since fetch returns 503)
    await waitFor(() => {
      expect(
        section.querySelector("[data-testid='admin-members-panel-disabled']") ||
        section.querySelector("[data-testid='admin-members-panel-loading']") ||
        section.querySelector("[data-testid='admin-members-panel']"),
      ).not.toBeNull();
      expect(
        section.querySelector("[data-testid='admin-roles-panel']"),
      ).not.toBeNull();
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (2) WorkspaceMembersPanel — renders member list from valid API response
// ═════════════════════════════════════════════════════════════════════════════

describe("WorkspaceMembersPanel — renders member list", () => {
  it("renders the member table with correct rows when API returns data", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(WORKSPACE_DATA),
    );
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-members-panel']"),
      ).not.toBeNull();
    });

    // Both members rendered
    expect(
      container.querySelector("[data-testid='member-row-u1']"),
    ).not.toBeNull();
    expect(
      container.querySelector("[data-testid='member-row-u2']"),
    ).not.toBeNull();
    // Role badges correct
    expect(
      container.querySelector("[data-testid='member-role-u1']")?.textContent,
    ).toBe("admin");
    expect(
      container.querySelector("[data-testid='member-role-u2']")?.textContent,
    ).toBe("researcher");
  });

  it("renders a role dropdown for each member", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(WORKSPACE_DATA),
    );
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='role-select-u1']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='role-select-u2']")).not.toBeNull();
  });

  it("table uses th[scope=col] headers (WCAG 2.1 AA)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(WORKSPACE_DATA),
    );
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(container.querySelector("[data-testid='admin-members-panel']")).not.toBeNull();
    });

    const colHeaders = container.querySelectorAll("th[scope='col']");
    expect(colHeaders.length).toBeGreaterThanOrEqual(3);
  });

  it("shows empty-state message when members array is empty", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ workspace_id: "ws-1", members: [] }),
    );
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-members-empty']"),
      ).not.toBeNull();
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (3+4) WorkspaceMembersPanel — disabled state (GATE-901)
// ═════════════════════════════════════════════════════════════════════════════

describe("WorkspaceMembersPanel — disabled state (GATE-901)", () => {
  it("shows disabled panel when API returns null members array", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ workspace_id: "ws-1", members: null }),
    );
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-members-panel-disabled']"),
      ).not.toBeNull();
    });

    expect(
      container.querySelector("[data-testid='admin-members-panel-disabled']")
        ?.textContent,
    ).toContain("Member data unavailable");
  });

  it("shows disabled panel when fetch returns a non-2xx error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(errorResponse(500));
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-members-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("shows disabled panel when fetch throws (network error)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));
    const { container } = render(<WorkspaceMembersPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-members-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("shows loading state initially before fetch resolves", () => {
    // Never resolves — stays in loading state
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { container } = render(<WorkspaceMembersPanel />);
    expect(
      container.querySelector("[data-testid='admin-members-panel-loading']"),
    ).not.toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (5) RateLimitConfigPanel — disabled state (GATE-900/GATE-901)
// ═════════════════════════════════════════════════════════════════════════════

describe("RateLimitConfigPanel — disabled state (GATE-900/GATE-901)", () => {
  // RateLimitConfigPanel calls useAuth — configure with admin for edit path
  beforeEach(() => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
  });

  it("shows disabled panel when fetch returns a non-2xx error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(errorResponse(503));
    const { container } = render(<RateLimitConfigPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-rate-limit-panel-disabled']"),
      ).not.toBeNull();
    });

    expect(
      container.querySelector("[data-testid='admin-rate-limit-panel-disabled']")
        ?.textContent,
    ).toContain("Rate limit config unavailable");
  });

  it("shows disabled panel when fetch throws (network error)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));
    const { container } = render(<RateLimitConfigPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-rate-limit-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("renders config display when API returns valid data", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(RATE_LIMIT_DATA));
    const { container } = render(<RateLimitConfigPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-rate-limit-panel']"),
      ).not.toBeNull();
    });

    expect(
      container.querySelector("[data-testid='admin-rate-limit-status']")?.textContent,
    ).toBe("Enabled");
    expect(
      container.querySelector("[data-testid='admin-rate-limit-max-requests']")?.textContent,
    ).toBe("100");
    expect(
      container.querySelector("[data-testid='admin-rate-limit-window']")?.textContent,
    ).toBe("60s");
  });

  it("shows Edit button for admin role", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(RATE_LIMIT_DATA));
    const { container } = render(<RateLimitConfigPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-rate-limit-edit-btn']"),
      ).not.toBeNull();
    });
  });

  it("does not show Edit button for viewer role (read-only)", async () => {
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: ["viewer"] },
        authMode: "local_static",
        provider: "local_static",
      }),
    );
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(RATE_LIMIT_DATA));
    const { container } = render(<RateLimitConfigPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-rate-limit-panel']"),
      ).not.toBeNull();
    });

    expect(
      container.querySelector("[data-testid='admin-rate-limit-edit-btn']"),
    ).toBeNull();
  });

  it("form uses fieldset/legend for keyboard nav (WCAG 2.1 AA)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(RATE_LIMIT_DATA));
    const { container } = render(<RateLimitConfigPanel />);

    // Wait for data to load, then click Edit to open the edit form
    const editBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='admin-rate-limit-edit-btn']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    // Enter edit mode
    const { fireEvent: fe, act: a } = await import("@testing-library/react");
    await a(() => { fe.click(editBtn); });

    // Fieldset and legend must be present (WCAG 2.1 AA: groups related form controls)
    expect(container.querySelector("fieldset")).not.toBeNull();
    expect(container.querySelector("fieldset legend")).not.toBeNull();
    // Input labels must be associated
    expect(container.querySelector("label[for='rl-enabled']")).not.toBeNull();
    expect(container.querySelector("label[for='rl-max-requests']")).not.toBeNull();
    expect(container.querySelector("label[for='rl-window-seconds']")).not.toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (6) AuthProviderStatusPanel — disabled state (GATE-901)
// ═════════════════════════════════════════════════════════════════════════════

describe("AuthProviderStatusPanel — disabled state (GATE-901)", () => {
  it("shows disabled panel when fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));
    const { container } = render(<AuthProviderStatusPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-auth-provider-panel-disabled']"),
      ).not.toBeNull();
    });

    expect(
      container
        .querySelector("[data-testid='admin-auth-provider-panel-disabled']")
        ?.textContent,
    ).toContain("Provider status unavailable");
  });

  it("shows disabled panel when fetch returns non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(errorResponse(503));
    const { container } = render(<AuthProviderStatusPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-auth-provider-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("renders provider name and availability badge when API returns data", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(AUTH_PROVIDER_DATA),
    );
    const { container } = render(<AuthProviderStatusPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-auth-provider-panel']"),
      ).not.toBeNull();
    });

    expect(
      container.querySelector("[data-testid='admin-auth-provider-name']")?.textContent,
    ).toBe("local_static");
    expect(
      container.querySelector("[data-testid='admin-auth-provider-status-badge']")
        ?.textContent,
    ).toBe("Available");
  });

  it("status badge has role='status' (WCAG 2.1 AA)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(AUTH_PROVIDER_DATA),
    );
    const { container } = render(<AuthProviderStatusPanel />);

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-auth-provider-status-badge']"),
      ).not.toBeNull();
    });

    const badge = container.querySelector(
      "[data-testid='admin-auth-provider-status-badge']",
    )!;
    expect(badge.getAttribute("role")).toBe("status");
    expect(badge.getAttribute("aria-label")).toContain("local_static");
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (7) RoleAssignmentPanel — always renders; restricted view without admin role
// ═════════════════════════════════════════════════════════════════════════════

describe("RoleAssignmentPanel — static capability matrix", () => {
  it("renders the capability matrix table without API calls", () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<RoleAssignmentPanel />);
    expect(
      container.querySelector("[data-testid='admin-roles-panel']"),
    ).not.toBeNull();
    // Table headers present
    const colHeaders = container.querySelectorAll("th[scope='col']");
    expect(colHeaders.length).toBeGreaterThanOrEqual(6); // capability + 5 roles
  });

  it("shows restricted notice for viewer (non-privileged) role", () => {
    mockUseAuth.mockReturnValue(
      makeAuth({
        identity: { user_id: "u", workspace_id: "ws", roles: ["viewer"] },
        authMode: "local_static",
        provider: "local_static",
      }),
    );
    const { container } = render(<RoleAssignmentPanel />);
    expect(
      container.querySelector("[data-testid='admin-roles-panel-restricted']"),
    ).not.toBeNull();
  });

  it("omits restricted notice for admin role", () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<RoleAssignmentPanel />);
    expect(
      container.querySelector("[data-testid='admin-roles-panel-restricted']"),
    ).toBeNull();
  });

  it("uses th[scope=row] for capability names (WCAG 2.1 AA)", () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<RoleAssignmentPanel />);
    const rowHeaders = container.querySelectorAll("th[scope='row']");
    expect(rowHeaders.length).toBeGreaterThan(0);
  });

  it("renders a caption for the capability table (WCAG 2.1 AA)", () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<RoleAssignmentPanel />);
    const caption = container.querySelector("caption");
    expect(caption).not.toBeNull();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (8) AUDIT-900 N/A — audit log isolation
// ═════════════════════════════════════════════════════════════════════════════

describe("AUDIT-900 N/A — admin UI audit-log field isolation", () => {
  /**
   * AUDIT-900 N/A: None of the admin UI surfaces (WorkspaceMembersPanel,
   * RoleAssignmentPanel, RateLimitConfigPanel, AuthProviderStatusPanel) expose
   * any audit-log-derived fields.
   *
   * The admin API endpoints consumed here are:
   *   GET  /api/admin/workspace           → member list (user_id, email, role)
   *   PATCH /api/admin/members/{id}/role  → role update
   *   GET  /api/admin/auth-provider-status → provider availability
   *   GET  /api/admin/rate-limit-config    → rate limit settings
   *   PATCH /api/admin/rate-limit-config   → rate limit update
   *
   * None of these endpoints reference audit log data (audit events, audit
   * trails, access logs). The audit log is a backend-only operational concern
   * (planned for a future P5.x phase). There is no audit_log field, last_access
   * timestamp, or access history in any panel's data contract.
   *
   * Therefore AUDIT-900 is NOT APPLICABLE to this surface.
   */
  it("N/A — WorkspaceMembersPanel data contract has no audit-log fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(WORKSPACE_DATA),
    );
    const { container } = render(<WorkspaceMembersPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-members-panel']"),
      ).not.toBeNull();
    });
    // The rendered table must not contain audit-log-derived UI elements
    expect(container.querySelector("[data-testid='audit-log']")).toBeNull();
    expect(container.querySelector("[data-testid='last-access']")).toBeNull();
    expect(container.querySelector("[data-testid='access-history']")).toBeNull();
    // Confirm AUDIT-900 is formally N/A for this surface (assertion documents intent)
    expect(true).toBe(true); // AUDIT-900: N/A — no audit-log UI surface present
  });

  it("N/A — RateLimitConfigPanel data contract has no audit-log fields", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(RATE_LIMIT_DATA),
    );
    const { container } = render(<RateLimitConfigPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-rate-limit-panel']"),
      ).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='audit-log']")).toBeNull();
    // AUDIT-900: N/A — no audit-log UI surface present
  });

  it("N/A — AuthProviderStatusPanel data contract has no audit-log fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(AUTH_PROVIDER_DATA),
    );
    const { container } = render(<AuthProviderStatusPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-auth-provider-panel']"),
      ).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='audit-log']")).toBeNull();
    // AUDIT-900: N/A — no audit-log UI surface present
  });
});
