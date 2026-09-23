/// <reference types="node" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

const LOOPBACK_API = process.env.RUNS_LOOPBACK_API_URL ?? "http://127.0.0.1:8765";
const VIEWER_API = process.env.RUNS_VIEWER_API_URL ?? "http://127.0.0.1:7432";
const VIEWER_API_TOKEN = process.env.RUNS_VIEWER_API_TOKEN;

if (process.env.VITE_RUNS_LOOPBACK_API_TOKEN) {
  throw new Error(
    "VITE_RUNS_LOOPBACK_API_TOKEN is forbidden: configure RUNS_VIEWER_API_TOKEN on the Vite server instead",
  );
}

/** Keep the RF bearer credential in the Vite process, never in the SPA. */
function viewerApiProxy() {
  return {
    target: VIEWER_API,
    changeOrigin: true,
    configure: (proxy: { on: (event: string, handler: (request: { removeHeader: (name: string) => void; setHeader: (name: string, value: string) => void }) => void) => void }) => {
      proxy.on("proxyReq", (request) => {
        request.removeHeader("authorization");
        if (VIEWER_API_TOKEN) request.setHeader("authorization", `Bearer ${VIEWER_API_TOKEN}`);
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3030,
    strictPort: true,
    proxy: {
      "/api": {
        ...viewerApiProxy(),
      },
      "/loopback-api": {
        target: LOOPBACK_API,
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 3030,
    strictPort: true,
    proxy: { "/api": viewerApiProxy() },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // Exclude playwright E2E specs from vitest runs
    exclude: ["**/node_modules/**", "**/e2e/**", "**/*.spec.ts"],
    // Use node environment for provenance-correctness (non-browser, file I/O)
    environmentMatchGlobs: [
      ["src/test/provenance-correctness.test.ts", "node"],
    ],
  },
});
