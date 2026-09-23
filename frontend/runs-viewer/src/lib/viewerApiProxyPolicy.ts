/**
 * Narrow policy for the server-held credential used by the LAN runs viewer.
 * This is imported by Vite's Node-side configuration only; it is not a client
 * transport and grants no browser access to the credential.
 */

const READ_PATHS = [
  /^\/api\/runs(?:\/[^/?]+(?:\/(?:claims|context|sources\/[^/?]+))?)?$/,
  /^\/api\/catalog(?:\/(?:stats|search|items\/[^/?]+))?$/,
  /^\/api\/assertions(?:\/(?:search|[^/?]+(?:\/(?:lineage|impact))?))?$/,
  /^\/api\/reports(?:\/[^/?]+(?:\/versions)?)?$/,
  /^\/api\/admin\/rbac-status$/,
];

export function isViewerReadRequest(method: string | undefined, url: string | undefined): boolean {
  if (method !== "GET" && method !== "HEAD") return false;
  const pathname = (url ?? "").split("?", 1)[0] ?? "";
  return READ_PATHS.some((pattern) => pattern.test(pathname));
}

type ProxyRequest = {
  removeHeader(name: string): void;
  setHeader(name: string, value: string): void;
};

/** Replace, rather than forward, any browser Authorization header. */
export function attachViewerApiAuthorization(request: ProxyRequest, token: string | undefined): void {
  request.removeHeader("authorization");
  if (token) request.setHeader("authorization", `Bearer ${token}`);
}
