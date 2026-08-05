/**
 * clearance-gates-v1 M4 — clinical-attestation UI surfaces.
 *
 * (1) AppShell banner: the falsifying AC for "non-dismissible" is a DOM
 *     query for a dismiss control that asserts it does NOT exist -- "the
 *     banner renders" alone would pass a dismissible implementation and is
 *     therefore explicitly rejected as an AC by the plan this feature
 *     implements (clearance-gates-v1 M4).
 * (2) ClaimLedgerTable badge: present only for a claim whose
 *     `clinical_attestation_status === "unattested"`; absent for every
 *     other claim.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { RFClaim } from "@/types/rf";

// ── (1) AppShell — non-dismissible banner ─────────────────────────────────────

const { mockGetClinicalContentPresent, mockSubscribeClinicalContentPresent } = vi.hoisted(() => ({
  mockGetClinicalContentPresent: vi.fn(() => false),
  mockSubscribeClinicalContentPresent: vi.fn(() => () => {}),
}));

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    getClinicalContentPresent: mockGetClinicalContentPresent,
    subscribeClinicalContentPresent: mockSubscribeClinicalContentPresent,
  };
});

vi.mock("@/auth/AuthContext", () => ({
  useAuth: () => ({ identity: null, authMode: "none" }),
}));

import { AppShell } from "@/app/AppShell";
import { ClaimLedgerTable } from "@/components/ClaimLedger/ClaimLedgerTable";

function renderShell() {
  return render(
    <MemoryRouter initialEntries={["/runs"]}>
      <AppShell />
    </MemoryRouter>,
  );
}

describe("AppShell — clinical-attestation banner (clearance-gates-v1 M4)", () => {
  beforeEach(() => {
    mockGetClinicalContentPresent.mockReset();
    mockGetClinicalContentPresent.mockReturnValue(false);
  });

  it("renders no banner when no clinical content is present", () => {
    const { queryByTestId } = renderShell();
    expect(queryByTestId("rv-clinical-attestation-banner")).toBeNull();
  });

  it("renders the banner, with role=status, when clinical content is present", () => {
    mockGetClinicalContentPresent.mockReturnValue(true);
    const { getByTestId } = renderShell();
    const banner = getByTestId("rv-clinical-attestation-banner");
    expect(banner).not.toBeNull();
    expect(banner.getAttribute("role")).toBe("status");
  });

  it("FALSIFYING AC: the banner contains no dismiss control of any kind", () => {
    mockGetClinicalContentPresent.mockReturnValue(true);
    const { getByTestId } = renderShell();
    const banner = getByTestId("rv-clinical-attestation-banner");

    // No <button> anywhere inside the banner.
    expect(within(banner).queryByRole("button")).toBeNull();
    expect(banner.querySelectorAll("button").length).toBe(0);

    // No element carrying a dismiss/close affordance by any common convention.
    const candidates = banner.querySelectorAll(
      "[aria-label], [title], [data-dismiss], [data-close]",
    );
    for (const el of Array.from(candidates)) {
      const label = `${el.getAttribute("aria-label") ?? ""} ${el.getAttribute("title") ?? ""}`.toLowerCase();
      expect(label).not.toMatch(/dismiss|close|hide/);
    }

    // No aria-hidden escape hatch on the banner itself (that would let a
    // dismiss action hide it from assistive tech while remaining "present").
    expect(banner.getAttribute("aria-hidden")).toBeNull();
  });

  it("clicking the banner does not remove it (no click-to-dismiss)", () => {
    mockGetClinicalContentPresent.mockReturnValue(true);
    const { getByTestId } = renderShell();
    const banner = getByTestId("rv-clinical-attestation-banner");

    fireEvent.click(banner);

    expect(getByTestId("rv-clinical-attestation-banner")).toBe(banner);
  });
});

// ── (2) ClaimLedgerTable — per-claim clinical badge ───────────────────────────

function makeClaim(overrides: Partial<RFClaim> & { claim_id: string; text: string }): RFClaim {
  return {
    sources: [],
    ...overrides,
  };
}

describe("ClaimLedgerTable — clinical-attestation badge (clearance-gates-v1 M4)", () => {
  it("renders the badge for a claim with clinical_attestation_status='unattested'", () => {
    const claims = [
      makeClaim({ claim_id: "clm_clinical", text: "Threshold claim.", clinical_attestation_status: "unattested" }),
    ];
    const { getByTestId } = render(
      <ClaimLedgerTable claims={claims} onClaimSelect={() => {}} />,
    );
    const badge = getByTestId("ledger-clinical-badge-clm_clinical");
    expect(badge).not.toBeNull();
    expect(badge.className).toContain("rv-ledger-clinical-badge");
  });

  it("renders no badge for an ordinary claim (key absent)", () => {
    const claims = [
      makeClaim({ claim_id: "clm_ordinary", text: "Ordinary claim." }),
    ];
    const { queryByTestId } = render(
      <ClaimLedgerTable claims={claims} onClaimSelect={() => {}} />,
    );
    expect(queryByTestId("ledger-clinical-badge-clm_ordinary")).toBeNull();
    // The cell itself still renders (for consistent column structure) --
    // only the badge inside it is conditional.
    expect(queryByTestId("ledger-clinical-clm_ordinary")).not.toBeNull();
  });
});
