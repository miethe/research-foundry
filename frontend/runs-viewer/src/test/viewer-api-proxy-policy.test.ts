import { describe, expect, it } from "vitest";
import { attachViewerApiAuthorization, isViewerReadRequest } from "@/lib/viewerApiProxyPolicy";

describe("viewer API proxy policy", () => {
  it("allows only GET/HEAD requests to viewer read endpoints", () => {
    expect(isViewerReadRequest("GET", "/api/runs?limit=20")).toBe(true);
    expect(isViewerReadRequest("HEAD", "/api/runs/rf_123/context")).toBe(true);
    expect(isViewerReadRequest("GET", "/api/assertions/assertion_1/lineage")).toBe(true);
    expect(isViewerReadRequest("GET", "/api/reports/draft_1/versions")).toBe(true);
  });

  it("denies mutations and paths outside the explicit read allowlist", () => {
    expect(isViewerReadRequest("POST", "/api/runs/rf_123/writeback/approve")).toBe(false);
    expect(isViewerReadRequest("DELETE", "/api/agent-jobs/job_1")).toBe(false);
    expect(isViewerReadRequest("GET", "/api/admin/pats")).toBe(false);
    expect(isViewerReadRequest("GET", "/api/unknown")).toBe(false);
  });

  it("replaces a browser Authorization header with the server-held credential", () => {
    const calls: string[] = [];
    const request = {
      removeHeader: (name: string) => calls.push(`remove:${name}`),
      setHeader: (name: string, value: string) => calls.push(`set:${name}:${value}`),
    };

    attachViewerApiAuthorization(request, "server-only-token");

    expect(calls).toEqual([
      "remove:authorization",
      "set:authorization:Bearer server-only-token",
    ]);
  });
});
