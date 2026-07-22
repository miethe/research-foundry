/**
 * p5-service-accounts-pats — Tests for ACT-501/ACT-502/ACT-503
 * (Phase 5: Admin UI — Service accounts, Personal access tokens, AuthContext
 * principalType extension).
 *
 * Covers AC-1 (phase-5-admin-ui.md):
 *   - AuthContext.derivePrincipalType() resolves "human" | "service" | "user_pat"
 *     and defaults to "human" when principal_type is absent/unrecognized.
 *   - ServiceAccountsPanel: list / create / issue-or-rotate token / revoke
 *     token / disable account, against the live admin API shape.
 *   - PersonalAccessTokensPanel: list / issue / revoke (self-service only),
 *     and the principalType signed-in-as indicator.
 *   - One-time-secret UX: the plaintext token is rendered exactly once, is
 *     cleared on Dismiss (never re-fetchable), and is never written to
 *     localStorage/sessionStorage.
 *   - WCAG 2.1 AA automated pass (jest-axe) — zero violations on both new
 *     panels with data loaded, matching the RoleAssignmentPanel /
 *     AuthProviderStatusPanel baseline (ACT-503).
 *
 * Auth mocking: vi.mock("@/auth/AuthContext") + vi.mocked(useAuth).mockReturnValue(...)
 * Fetch mocking: vi.spyOn(globalThis, "fetch") per test; vi.restoreAllMocks() in afterEach.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, waitFor, fireEvent, act } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ReactNode } from "react";

import { ServiceAccountsPanel } from "@/components/AdminSettings/ServiceAccountsPanel";
import { PersonalAccessTokensPanel } from "@/components/AdminSettings/PersonalAccessTokensPanel";
import { RoleAssignmentPanel } from "@/components/AdminSettings/RoleAssignmentPanel";
import { AuthProviderStatusPanel } from "@/components/AdminSettings/AuthProviderStatusPanel";
import {
  derivePrincipalType,
  type AuthContextValue,
  type AuthIdentity,
} from "@/auth/AuthContext";
import { useAuth } from "@/auth/AuthContext";

// ── Auth mock ─────────────────────────────────────────────────────────────────

vi.mock("@/auth/AuthContext", async () => {
  const actual = await vi.importActual<typeof import("@/auth/AuthContext")>(
    "@/auth/AuthContext",
  );
  return {
    ...actual,
    useAuth: vi.fn(),
    AuthContext: {
      Provider: ({ children }: { children: ReactNode }) => <>{children}</>,
    },
  };
});

const mockUseAuth = vi.mocked(useAuth);

function makeAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    identity: null,
    isLoading: false,
    provider: "none",
    authMode: "none",
    principalType: "human",
    ...overrides,
  };
}

const ADMIN_AUTH: AuthContextValue = makeAuth({
  identity: { user_id: "user-admin", workspace_id: "ws-1", roles: ["admin"] },
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

function errorResponse(status: number, detail = "Error"): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  mockUseAuth.mockReset();
});

// ═════════════════════════════════════════════════════════════════════════════
// (1) AuthContext.derivePrincipalType — AC-1 resilience contract
// ═════════════════════════════════════════════════════════════════════════════

describe("derivePrincipalType — AC-1 resilience contract", () => {
  it("returns 'human' when identity is null", () => {
    expect(derivePrincipalType(null)).toBe("human");
  });

  it("returns 'human' when identity has no principal_type field", () => {
    const identity: AuthIdentity = {
      user_id: "u1",
      workspace_id: "ws-1",
      roles: ["admin"],
    };
    expect(derivePrincipalType(identity)).toBe("human");
  });

  it("returns 'human' when principal_type is an unrecognized value (never errors)", () => {
    const identity: AuthIdentity = {
      user_id: "u1",
      workspace_id: "ws-1",
      roles: [],
      principal_type: "bogus",
    };
    expect(derivePrincipalType(identity)).toBe("human");
  });

  it("returns 'service' when principal_type is 'service'", () => {
    const identity: AuthIdentity = {
      user_id: "svc_abc",
      workspace_id: "ws-1",
      roles: ["researcher"],
      principal_type: "service",
    };
    expect(derivePrincipalType(identity)).toBe("service");
  });

  it("returns 'user_pat' when principal_type is 'user_pat'", () => {
    const identity: AuthIdentity = {
      user_id: "u1",
      workspace_id: "ws-1",
      roles: ["viewer"],
      principal_type: "user_pat",
    };
    expect(derivePrincipalType(identity)).toBe("user_pat");
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (2) ServiceAccountsPanel — list / disabled / loading
// ═════════════════════════════════════════════════════════════════════════════

const SERVICE_ACCOUNTS_DATA = {
  items: [
    {
      id: "svc_1",
      name: "ci-bot",
      workspace_id: "ws-1",
      role: "researcher",
      description: "CI pipeline",
      created_by: "user-admin",
      created_at: "2026-07-01T00:00:00Z",
      disabled_at: null,
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const ISSUED_TOKEN = {
  token_id: "tok_1",
  plaintext: "rf_live_supersecretvalue123",
  token_prefix: "rf_live_supe",
  principal_type: "service",
  principal_id: "svc_1",
  workspace_id: "ws-1",
  role: "researcher",
  expires_at: null,
};

describe("ServiceAccountsPanel — list / disabled / loading", () => {
  it("shows loading state initially before fetch resolves", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { container } = render(<ServiceAccountsPanel />);
    expect(
      container.querySelector("[data-testid='admin-service-accounts-panel-loading']"),
    ).not.toBeNull();
  });

  it("shows disabled panel when fetch returns a non-2xx error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(errorResponse(500));
    const { container } = render(<ServiceAccountsPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-service-accounts-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("shows disabled panel when fetch throws (network error)", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));
    const { container } = render(<ServiceAccountsPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-service-accounts-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("renders the account table with correct row when API returns data", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(SERVICE_ACCOUNTS_DATA));
    const { container } = render(<ServiceAccountsPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='service-account-row-svc_1']"),
      ).not.toBeNull();
    });
    expect(
      container.querySelector("[data-testid='service-account-role-svc_1']")?.textContent,
    ).toBe("researcher");
    expect(
      container.querySelector("[data-testid='service-account-status-svc_1']")?.textContent,
    ).toBe("Active");
  });

  it("shows empty-state message when items array is empty", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }),
    );
    const { container } = render(<ServiceAccountsPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-service-accounts-empty']"),
      ).not.toBeNull();
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (3) ServiceAccountsPanel — create / issue-token one-time-secret UX (AC-1)
// ═════════════════════════════════════════════════════════════════════════════

describe("ServiceAccountsPanel — create account", () => {
  it("POSTs a new account and prepends it to the list", async () => {
    const created = {
      id: "svc_2",
      name: "new-bot",
      workspace_id: "ws-1",
      role: "viewer",
      description: null,
      created_by: "user-admin",
      created_at: "2026-07-22T00:00:00Z",
      disabled_at: null,
    };
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(created, 201));
      return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }));
    });

    const { container } = render(<ServiceAccountsPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-service-accounts-create-form']"),
      ).not.toBeNull();
    });

    const nameInput = container.querySelector(
      "[data-testid='admin-service-accounts-name-input']",
    ) as HTMLInputElement;
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "new-bot" } });
    });

    const form = container.querySelector(
      "[data-testid='admin-service-accounts-create-form']",
    ) as HTMLFormElement;
    await act(async () => {
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='service-account-row-svc_2']"),
      ).not.toBeNull();
    });
  });
});

describe("ServiceAccountsPanel — one-time-secret UX (AC-1)", () => {
  it("shows the plaintext token exactly once after issuing, then clears it on Dismiss", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_TOKEN, 201));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });

    const { container } = render(<ServiceAccountsPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-issue-token-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(issueBtn);
    });

    // Plaintext appears in the one-time callout.
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='svc-token-plaintext']")?.textContent,
      ).toBe(ISSUED_TOKEN.plaintext);
    });

    // Never persisted to localStorage.
    expect(JSON.stringify(localStorage)).not.toContain(ISSUED_TOKEN.plaintext);

    const dismissBtn = container.querySelector(
      "[data-testid='svc-token-dismiss-btn']",
    ) as HTMLButtonElement;
    await act(async () => {
      fireEvent.click(dismissBtn);
    });

    // AC-1: dismissed → cleared from the DOM entirely; nothing re-fetches it.
    expect(container.querySelector("[data-testid='svc-token-callout']")).toBeNull();
    expect(container.textContent).not.toContain(ISSUED_TOKEN.plaintext);
  });

  it("revokes a listed token via the tokens list panel", async () => {
    const tokenMeta = {
      token_id: "tok_1",
      principal_type: "service",
      principal_id: "svc_1",
      workspace_id: "ws-1",
      role: "researcher",
      token_prefix: "rf_live_supe",
      created_at: "2026-07-01T00:00:00Z",
      expires_at: null,
      revoked_at: null,
      last_used_at: null,
    };
    vi.spyOn(globalThis, "fetch").mockImplementation((url, init) => {
      const urlStr = String(url);
      if (init?.method === "DELETE") return Promise.resolve(jsonResponse({ token_id: "tok_1", revoked: true }));
      if (urlStr.endsWith("/tokens")) return Promise.resolve(jsonResponse({ items: [tokenMeta], total: 1, limit: 50, offset: 0 }));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });

    const { container } = render(<ServiceAccountsPanel />);
    const viewBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-view-tokens-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(viewBtn);
    });

    const revokeBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-revoke-token-tok_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(revokeBtn);
    });

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='service-account-revoke-token-tok_1']"),
      ).toHaveProperty("disabled", true);
    });
  });

  it("disables an account via the Disable button", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "DELETE") return Promise.resolve(jsonResponse({ id: "svc_1", disabled: true }));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });

    const { container } = render(<ServiceAccountsPanel />);
    const disableBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='service-account-disable-svc_1']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(disableBtn);
    });

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='service-account-status-svc_1']")?.textContent,
      ).toBe("Disabled");
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (4) PersonalAccessTokensPanel — list / disabled / loading / principalType
// ═════════════════════════════════════════════════════════════════════════════

const PAT_LIST_DATA = {
  items: [
    {
      token_id: "pat_1",
      principal_type: "user_pat",
      principal_id: "user-admin",
      workspace_id: "ws-1",
      role: "viewer",
      token_prefix: "rf_pat_abcd",
      created_at: "2026-07-10T00:00:00Z",
      expires_at: null,
      revoked_at: null,
      last_used_at: null,
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const ISSUED_PAT = {
  token_id: "pat_2",
  plaintext: "rf_pat_supersecretvalue456",
  token_prefix: "rf_pat_supe",
  principal_type: "user_pat",
  principal_id: "user-admin",
  workspace_id: "ws-1",
  role: "viewer",
  expires_at: null,
};

describe("PersonalAccessTokensPanel — list / disabled / loading", () => {
  it("shows loading state initially before fetch resolves", () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    const { container } = render(<PersonalAccessTokensPanel />);
    expect(
      container.querySelector("[data-testid='admin-pats-panel-loading']"),
    ).not.toBeNull();
  });

  it("shows disabled panel when fetch returns a non-2xx error", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(errorResponse(503));
    const { container } = render(<PersonalAccessTokensPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-pats-panel-disabled']"),
      ).not.toBeNull();
    });
  });

  it("renders the PAT table with correct row when API returns data", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(PAT_LIST_DATA));
    const { container } = render(<PersonalAccessTokensPanel />);
    await waitFor(() => {
      expect(container.querySelector("[data-testid='pat-row-pat_1']")).not.toBeNull();
    });
    expect(container.querySelector("[data-testid='pat-role-pat_1']")?.textContent).toBe(
      "viewer",
    );
    expect(container.querySelector("[data-testid='pat-status-pat_1']")?.textContent).toBe(
      "Active",
    );
  });

  it("renders the principalType signed-in-as indicator (human default)", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH); // principalType: "human" (default)
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(PAT_LIST_DATA));
    const { container } = render(<PersonalAccessTokensPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-pats-principal-type']")?.textContent,
      ).toContain("Human session");
    });
  });

  it("renders 'Personal access token' when principalType is user_pat", async () => {
    mockUseAuth.mockReturnValue(makeAuth({ principalType: "user_pat" }));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(PAT_LIST_DATA));
    const { container } = render(<PersonalAccessTokensPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-pats-principal-type']")?.textContent,
      ).toContain("Personal access token");
    });
  });
});

describe("PersonalAccessTokensPanel — issue / revoke / one-time-secret UX (AC-1)", () => {
  it("issues a new PAT, shows the plaintext once, then clears it on Dismiss", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_PAT, 201));
      return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }));
    });

    const { container } = render(<PersonalAccessTokensPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='admin-pats-issue-btn']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    const form = container.querySelector(
      "[data-testid='admin-pats-issue-form']",
    ) as HTMLFormElement;
    await act(async () => {
      fireEvent.submit(form);
    });
    void issueBtn;

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='pat-token-plaintext']")?.textContent,
      ).toBe(ISSUED_PAT.plaintext);
    });

    expect(JSON.stringify(localStorage)).not.toContain(ISSUED_PAT.plaintext);

    const dismissBtn = container.querySelector(
      "[data-testid='pat-token-dismiss-btn']",
    ) as HTMLButtonElement;
    await act(async () => {
      fireEvent.click(dismissBtn);
    });

    expect(container.querySelector("[data-testid='pat-token-callout']")).toBeNull();
    expect(container.textContent).not.toContain(ISSUED_PAT.plaintext);
  });

  it("shows the RoleCeilingError message verbatim on a 403 issue failure", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") {
        return Promise.resolve(errorResponse(403, "Requested role exceeds caller's role ceiling"));
      }
      return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }));
    });

    const { container } = render(<PersonalAccessTokensPanel />);
    await waitFor(() => {
      expect(container.querySelector("[data-testid='admin-pats-issue-form']")).not.toBeNull();
    });

    const form = container.querySelector(
      "[data-testid='admin-pats-issue-form']",
    ) as HTMLFormElement;
    await act(async () => {
      fireEvent.submit(form);
    });

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-pats-issue-error']")?.textContent,
      ).toContain("role ceiling");
    });
  });

  it("revokes an active PAT via the Revoke button", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "DELETE") return Promise.resolve(jsonResponse({ token_id: "pat_1", revoked: true }));
      return Promise.resolve(jsonResponse(PAT_LIST_DATA));
    });

    const { container } = render(<PersonalAccessTokensPanel />);
    const revokeBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='pat-revoke-pat_1']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(revokeBtn);
    });

    await waitFor(() => {
      expect(container.querySelector("[data-testid='pat-status-pat_1']")?.textContent).toBe(
        "Revoked",
      );
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (5) WCAG 2.1 AA automated pass (jest-axe) — ACT-503
// ═════════════════════════════════════════════════════════════════════════════

describe("WCAG 2.1 AA (jest-axe) — new admin panels + baseline reference panels", () => {
  it("ServiceAccountsPanel has zero axe violations with data loaded", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(SERVICE_ACCOUNTS_DATA));
    const { container } = render(<ServiceAccountsPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-service-accounts-panel']"),
      ).not.toBeNull();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("ServiceAccountsPanel one-time-secret callout has zero axe violations", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_TOKEN, 201));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });
    const { container } = render(<ServiceAccountsPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-issue-token-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });
    await act(async () => {
      fireEvent.click(issueBtn);
    });
    await waitFor(() => {
      expect(container.querySelector("[data-testid='svc-token-callout']")).not.toBeNull();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("PersonalAccessTokensPanel has zero axe violations with data loaded", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(PAT_LIST_DATA));
    const { container } = render(<PersonalAccessTokensPanel />);
    await waitFor(() => {
      expect(container.querySelector("[data-testid='admin-pats-panel']")).not.toBeNull();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("RoleAssignmentPanel (baseline reference) has zero axe violations", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    const { container } = render(<RoleAssignmentPanel />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("AuthProviderStatusPanel (baseline reference) has zero axe violations", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ provider: "local_static", available: true }),
    );
    const { container } = render(<AuthProviderStatusPanel />);
    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='admin-auth-provider-panel']"),
      ).not.toBeNull();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// (6) Focus management regression — a11y-sheriff P5 review (WCAG 2.4.3 / 4.1.2 / 4.1.3)
// ═════════════════════════════════════════════════════════════════════════════

/** Stub navigator.clipboard.writeText for this describe block's Copy tests. */
function stubClipboard(): void {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText: vi.fn().mockResolvedValue(undefined) },
    configurable: true,
  });
}

describe("OneTimeSecretCallout — focus management + copy announcement (regression)", () => {
  it("ServiceAccountsPanel: Dismiss restores focus to the triggering 'Issue / rotate token' button, never <body>", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_TOKEN, 201));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });

    const { container } = render(<ServiceAccountsPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-issue-token-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(issueBtn);
    });

    const dismissBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='svc-token-dismiss-btn']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(dismissBtn);
    });

    // Hard requirement: activeElement is the trigger button, never <body>.
    expect(document.activeElement).toBe(issueBtn);
    expect(document.activeElement).not.toBe(document.body);
  });

  it("PersonalAccessTokensPanel: Dismiss restores focus to the 'Issue token' button, never <body>", async () => {
    mockUseAuth.mockReturnValue(ADMIN_AUTH);
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_PAT, 201));
      return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }));
    });

    const { container } = render(<PersonalAccessTokensPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='admin-pats-issue-btn']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    const form = container.querySelector(
      "[data-testid='admin-pats-issue-form']",
    ) as HTMLFormElement;
    await act(async () => {
      fireEvent.submit(form);
    });

    const dismissBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='pat-token-dismiss-btn']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    await act(async () => {
      fireEvent.click(dismissBtn);
    });

    expect(document.activeElement).toBe(issueBtn);
    expect(document.activeElement).not.toBe(document.body);
  });

  it("the callout uses role='region' (non-modal), not role='alertdialog' (no unimplemented focus-trap contract)", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_TOKEN, 201));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });

    const { container } = render(<ServiceAccountsPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-issue-token-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });
    await act(async () => {
      fireEvent.click(issueBtn);
    });

    const callout = await waitFor(() => {
      const el = container.querySelector("[data-testid='svc-token-callout']");
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });

    expect(callout.getAttribute("role")).toBe("region");
    expect(callout.getAttribute("aria-label")).toBeTruthy();
    expect(container.querySelector("[role='alertdialog']")).toBeNull();
  });

  it("copying the secret announces success via a role='status' aria-live region", async () => {
    stubClipboard();
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_TOKEN, 201));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });

    const { container } = render(<ServiceAccountsPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-issue-token-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });
    await act(async () => {
      fireEvent.click(issueBtn);
    });

    const copyBtn = await waitFor(() => {
      const btn = container.querySelector("[data-testid='svc-token-copy-btn']");
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });

    const statusRegion = container.querySelector(
      "[data-testid='svc-token-copy-status']",
    ) as HTMLElement;
    expect(statusRegion).not.toBeNull();
    expect(statusRegion.getAttribute("role")).toBe("status");
    expect(statusRegion.getAttribute("aria-live")).toBe("polite");
    // Before copying, the live region carries no confirmation text.
    expect(statusRegion.textContent).toBe("");

    await act(async () => {
      fireEvent.click(copyBtn);
    });

    await waitFor(() => {
      expect(
        container.querySelector("[data-testid='svc-token-copy-status']")?.textContent,
      ).toBe("Copied to clipboard");
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(ISSUED_TOKEN.plaintext);
  });

  it("ServiceAccountsPanel one-time-secret callout still has zero axe violations after the region/live-region fix", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse(ISSUED_TOKEN, 201));
      return Promise.resolve(jsonResponse(SERVICE_ACCOUNTS_DATA));
    });
    const { container } = render(<ServiceAccountsPanel />);
    const issueBtn = await waitFor(() => {
      const btn = container.querySelector(
        "[data-testid='service-account-issue-token-svc_1']",
      );
      expect(btn).not.toBeNull();
      return btn as HTMLButtonElement;
    });
    await act(async () => {
      fireEvent.click(issueBtn);
    });
    await waitFor(() => {
      expect(container.querySelector("[data-testid='svc-token-callout']")).not.toBeNull();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
