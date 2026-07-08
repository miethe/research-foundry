/**
 * LocalLoginForm.tsx — login form for provider=local_static (P5.8 FEAUTH-001).
 *
 * Rendered by AuthProvider when provider=local_static and identity is null.
 * Accepts an onSubmit callback that exchanges credentials via the backend
 * POST /api/auth/login endpoint (mediated by AuthProvider/AuthContext).
 *
 * WCAG 2.1 AA compliance:
 *   - Explicit <label htmlFor> for each input field (not placeholder as label)
 *   - Visible focus ring on all interactive elements (:focus-visible)
 *   - Keyboard-navigable: Tab cycles through username → password → submit
 *   - Error surfaced in role="alert" live region for screen readers
 *   - Submit button disabled during loading to prevent double-submit
 *   - aria-busy on submit communicates loading state to assistive technology
 *   - aria-required on required fields
 *
 * CSS: follows house rv-* / it-* convention (src/styles/auth.css).
 * No Tailwind. No inline styles.
 */

import React, { useState } from "react";
import "@/styles/auth.css";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface LocalLoginFormProps {
  /** Called on form submit with username and password. May reject on error. */
  onSubmit: (username: string, password: string) => Promise<void>;
  /** When true, the form is in a submitting state: inputs and button are disabled. */
  isLoading?: boolean;
  /** When set, an error message is displayed in a visible alert region. */
  error?: string | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * LocalLoginForm — full-page login form for local_static auth provider.
 *
 * Renders over the app via position:fixed overlay (rv-auth-overlay) so it
 * blocks all other UI until authenticated — matching the Clerk SignIn behavior.
 */
export function LocalLoginForm({
  onSubmit,
  isLoading = false,
  error = null,
}: LocalLoginFormProps): React.JSX.Element {
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (!isLoading && username.trim()) {
      void onSubmit(username.trim(), password);
    }
  };

  const isSubmitDisabled = isLoading || !username.trim();

  return (
    <div className="rv-auth-overlay">
      <div
        className="rv-auth-card"
        role="main"
        aria-label="Research Foundry login"
      >
        {/* ── Brand header ──────────────────────────────────────────────── */}
        <header className="rv-auth-header">
          <div className="rv-auth-brand" aria-hidden="true">
            <span className="rv-auth-brand__mark">RF</span>
          </div>
          <h1 className="rv-auth-title">Research Foundry</h1>
          <p className="rv-auth-subtitle">Sign in to continue</p>
        </header>

        {/* ── Sign-in form ───────────────────────────────────────────────── */}
        <form
          className="rv-auth-form"
          onSubmit={handleSubmit}
          aria-label="Sign in"
          noValidate
        >
          {/* Username */}
          <div className="rv-auth-field">
            <label htmlFor="rv-login-username" className="rv-auth-label">
              Username
            </label>
            <input
              id="rv-login-username"
              type="text"
              className="rv-auth-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              required
              disabled={isLoading}
              aria-required="true"
              aria-disabled={isLoading ? "true" : undefined}
            />
          </div>

          {/* Password */}
          <div className="rv-auth-field">
            <label htmlFor="rv-login-password" className="rv-auth-label">
              Password
            </label>
            <input
              id="rv-login-password"
              type="password"
              className="rv-auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={isLoading}
              aria-required="true"
              aria-disabled={isLoading ? "true" : undefined}
            />
          </div>

          {/* Error — rendered in role="alert" so screen readers announce it */}
          {error && (
            <div
              className="rv-auth-error"
              role="alert"
              aria-live="assertive"
              aria-atomic="true"
            >
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            className="rv-auth-submit"
            disabled={isSubmitDisabled}
            aria-busy={isLoading ? "true" : undefined}
            aria-label={isLoading ? "Signing in, please wait" : "Sign in"}
          >
            {isLoading ? (
              <>
                <span
                  className="rv-auth-submit__spinner"
                  aria-hidden="true"
                />
                <span>Signing in…</span>
              </>
            ) : (
              "Sign in"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default LocalLoginForm;
