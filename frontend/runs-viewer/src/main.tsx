import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";

// Design system: IntentTree plain-CSS tokens + components + runs-viewer styles.
// No Tailwind, no @miethe/ui.
import "./styles/index.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error('Root element "#root" not found');
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
