/// <reference types="node" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

const LOOPBACK_API = process.env.RUNS_LOOPBACK_API_URL ?? "http://127.0.0.1:8765";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5175,
    proxy: {
      "/api": {
        target: LOOPBACK_API,
        changeOrigin: true,
      },
    },
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
