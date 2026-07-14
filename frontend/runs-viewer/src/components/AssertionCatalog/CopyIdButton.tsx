/**
 * CopyIdButton — small copy-to-clipboard affordance for opaque object IDs
 * and locators in the assertion catalog / provenance surfaces.
 *
 * Accessible names follow spec §10: "Copy controls have object-specific
 * names such as `Copy source assertion ID`." Callers pass the exact label.
 */
import { useState } from "react";

export interface CopyIdButtonProps {
  value: string;
  /** Exact accessible name, e.g. "Copy source assertion ID" or "Copy locator". */
  label: string;
}

export function CopyIdButton({ value, label }: CopyIdButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can be denied by the browser sandbox; no-op is safe.
    }
  }

  return (
    <button
      type="button"
      className="it-btn ghost xs rv-assertion-copy-btn"
      onClick={handleCopy}
      aria-label={label}
      data-testid="assertion-copy-button"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default CopyIdButton;
