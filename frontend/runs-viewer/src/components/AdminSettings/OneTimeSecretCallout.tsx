/**
 * OneTimeSecretCallout — shared shown-once plaintext token display.
 *
 * Used by ServiceAccountsPanel and PersonalAccessTokensPanel (ACT-501/ACT-502,
 * AC-1) immediately after a `POST .../tokens` / `POST /admin/pats` call.
 *
 * Security invariant (AC-1): *plaintext* is held only in the parent's local
 * component state — this component never fetches it, never re-requests it,
 * and never writes it to localStorage/sessionStorage/URL. Dismissing (or the
 * parent unmounting/navigating away) clears the only reference to it, since
 * the plaintext lives in React state that disappears with the component.
 *
 * CSS: rv-one-time-secret (rv-* / it-* convention). No CSS file changes are
 * required to render correctly — mirrors the existing AdminSettings panels,
 * which reference `rv-admin-*` classes without dedicated stylesheet rules.
 *
 * Focus/live-region contract (a11y-sheriff P5 review — WCAG 2.4.3 / 4.1.2 /
 * 4.1.3 fix):
 *   - This is an INLINE, non-trapping callout, not a modal dialog — it uses
 *     `role="region"` with an accessible name (`aria-label`), NOT
 *     `role="alertdialog"`. `alertdialog` promises a focus-management
 *     contract (focus moves in on open, is trapped, and is restored on
 *     close) that this component never implemented; misusing it is a WCAG
 *     2.4.3/4.1.2 violation on its own. A non-modal live region carries no
 *     such promise, so it is the correct — and simpler — fix.
 *   - `role="alert"` stays on the warning line only, so its appearance is
 *     announced without requiring focus to move anywhere.
 *   - Focus RESTORATION on dismiss (to the button that triggered the
 *     issue/rotate action) is this component's caller's responsibility —
 *     `onDismiss` is called first; the parent (ServiceAccountsPanel /
 *     PersonalAccessTokensPanel) moves focus back to its trigger button via
 *     a ref. This component does not know which button triggered it, so it
 *     cannot own that step itself.
 *   - The Copy button's success state is echoed in a `role="status"`
 *     `aria-live="polite"` region (visually hidden) so screen-reader users
 *     get programmatic confirmation, not just a visual label swap
 *     (WCAG 4.1.3).
 */

import { useState } from "react";

export interface OneTimeSecretCalloutProps {
  /** Heading text, e.g. "Service account token issued" */
  title: string;
  /** The one-time plaintext secret. Never re-fetchable after this render. */
  plaintext: string;
  /** Short, non-secret prefix for display context after dismissal. */
  tokenPrefix: string;
  /** ISO-8601 expiry, if any. */
  expiresAt?: string | null;
  /** Called when the user dismisses the callout — parent MUST clear plaintext state. */
  onDismiss: () => void;
  /** Prefix for data-testid attributes, e.g. "svc-token" | "pat-token". */
  testIdPrefix: string;
}

export function OneTimeSecretCallout({
  title,
  plaintext,
  tokenPrefix,
  expiresAt,
  onDismiss,
  testIdPrefix,
}: OneTimeSecretCalloutProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy(): Promise<void> {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(plaintext);
        setCopied(true);
      }
    } catch {
      // Clipboard API unavailable/denied — the plaintext is still selectable
      // in the <code> block below; never treat this as an error state.
      setCopied(false);
    }
  }

  return (
    <div
      className="rv-one-time-secret"
      role="region"
      aria-label={title}
      data-testid={`${testIdPrefix}-callout`}
    >
      <p className="rv-one-time-secret__title" id={`${testIdPrefix}-title`}>
        {title}
      </p>
      <p className="rv-one-time-secret__warning" role="alert">
        This secret is shown once and cannot be retrieved again. Copy it now.
      </p>
      <code
        className="rv-one-time-secret__value"
        data-testid={`${testIdPrefix}-plaintext`}
      >
        {plaintext}
      </code>
      <dl className="rv-one-time-secret__meta">
        <div>
          <dt>Prefix</dt>
          <dd data-testid={`${testIdPrefix}-prefix`}>{tokenPrefix}</dd>
        </div>
        {expiresAt ? (
          <div>
            <dt>Expires</dt>
            <dd data-testid={`${testIdPrefix}-expires`}>{expiresAt}</dd>
          </div>
        ) : null}
      </dl>
      <div className="rv-one-time-secret__actions">
        <button
          type="button"
          className="it-btn sm"
          onClick={() => void handleCopy()}
          data-testid={`${testIdPrefix}-copy-btn`}
          aria-label={`Copy ${title.toLowerCase()} to clipboard`}
        >
          {copied ? "Copied" : "Copy"}
        </button>
        {/* WCAG 4.1.3: programmatic copy confirmation for screen-reader users —
            the button label swap above is visual-only and not reliably
            announced on its own. Visually hidden; announced via aria-live. */}
        <span
          role="status"
          aria-live="polite"
          className="rv-visually-hidden"
          data-testid={`${testIdPrefix}-copy-status`}
        >
          {copied ? "Copied to clipboard" : ""}
        </span>
        <button
          type="button"
          className="it-btn sm it-btn--ghost"
          onClick={onDismiss}
          data-testid={`${testIdPrefix}-dismiss-btn`}
          aria-label={`Dismiss ${title.toLowerCase()} — this secret cannot be shown again`}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

export default OneTimeSecretCallout;
