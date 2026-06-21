/**
 * HelpScreen — static reference screen (G6).
 *
 * Accessible at /help. Renders four sections:
 *   1. About          — brief description of Research Foundry and this viewer.
 *   2. Keyboard Shortcuts — table of viewer-wide keyboard shortcuts.
 *   3. Glossary       — alphabetical definitions of core RF terms.
 *   4. Links          — external documentation references.
 *
 * Fully static: no API calls, no loading state, no data dependency.
 * All preferences and state remain unchanged by this screen.
 */

import "@/styles/help.css";

// ── Keyboard shortcuts ──────────────────────────────────────────────────────
// Discovered from onKeyDown handlers in:
//   RunDetailModal.tsx       — Escape closes run detail modal
//   ProvenanceModal.tsx      — Escape closes provenance modal
//   DetailModal.tsx          — Escape closes detail modal
//   RunCard.tsx              — Enter / Space activates a run card
//   LineageFlow.tsx          — Enter / Space activates a lineage node
//   ClaimLedgerTable.tsx     — Enter / Space activates a claim row
//   LineageList.tsx          — Enter / Space activates a lineage list row;
//                              ArrowRight / ArrowLeft expands/collapses nodes

interface Shortcut {
  keys: string[];
  action: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: ["Escape"], action: "Close overlay, detail pane, or modal" },
  { keys: ["Enter", "Space"], action: "Activate focused run card, claim row, or lineage node" },
  { keys: ["ArrowRight"], action: "Expand a lineage tree node (Lineage list view)" },
  { keys: ["ArrowLeft"], action: "Collapse a lineage tree node (Lineage list view)" },
];

// ── Glossary ────────────────────────────────────────────────────────────────
// Terms in alphabetical order (AC G6-04).

interface GlossaryEntry {
  term: string;
  definition: string;
}

const GLOSSARY: GlossaryEntry[] = [
  {
    term: "Claim",
    definition:
      "An atomic, evidence-linked assertion extracted from a source. Each claim carries a verification status (supported, contradicted, unsupported, or unverified) and maps to one or more source cards.",
  },
  {
    term: "Governance",
    definition:
      "The policy layer controlling sensitivity classification, redaction thresholds, and writeback approval. Governance rules are evaluated before any run export or external integration proceeds.",
  },
  {
    term: "Lineage",
    definition:
      "The provenance chain from a raw source through extraction, claim formation, and final report output. The Lineage tab visualises this graph so you can trace any claim back to its origin.",
  },
  {
    term: "Run",
    definition:
      "A single end-to-end research execution: plan → swarm → extract → verify → report. Each run produces a self-contained run.json artifact that the viewer reads.",
  },
  {
    term: "Sensitivity",
    definition:
      "The confidentiality tier assigned to a source or run. Tiers in ascending order: public, personal, work_sensitive, client_sensitive. The viewer redacts content above the export threshold unless the Show All setting is enabled.",
  },
  {
    term: "Source",
    definition:
      "A document or URL from which claims are extracted. Sources carry provenance metadata, access status, and a sensitivity classification recorded in source_card.md files.",
  },
  {
    term: "Verification",
    definition:
      "The automated claim-checking pass that compares each claim against its cited sources and assigns a status: supported, contradicted, unsupported, or unverified.",
  },
  {
    term: "Writeback",
    definition:
      "A governed export of a report or claim set to an external destination (MeatyWiki, NotebookLM, IntentTree, etc.). Writebacks must pass governance checks before execution.",
  },
];

// ── External links ──────────────────────────────────────────────────────────
// Stub links are used where no stable public URL exists yet (noted below).

interface DocLink {
  label: string;
  href: string;
  stub?: boolean; // true → href="#" placeholder; no stable URL yet
}

const DOC_LINKS: DocLink[] = [
  {
    label: "Research Foundry — Project Overview",
    href: "#",
    stub: true,
  },
  {
    label: "RF CLI Reference",
    href: "#",
    stub: true,
  },
  {
    label: "Viewer Unredaction Guide",
    href: "#",
    stub: true,
  },
  {
    label: "Writeback Integration Guide",
    href: "#",
    stub: true,
  },
];

// ── Component ───────────────────────────────────────────────────────────────

export function HelpScreen() {
  return (
    <div className="rv-help" data-testid="help-screen">
      <h1 className="rv-help__title">Help</h1>

      {/* ── About ── */}
      <section
        className="rv-help__section"
        aria-labelledby="help-about-title"
        data-testid="help-section-about"
      >
        <h2 id="help-about-title" className="rv-help__section-title">
          About
        </h2>
        <p className="rv-help__about-text">
          <strong>Research Foundry</strong> is a Markdown/YAML-first, evidence-first research
          control plane that turns raw ideas into governed research swarms, evidence bundles, and
          claim-verified reports. This viewer is a read-only SPA that displays the output of
          completed research runs — browsing claims, sources, lineage graphs, verification results,
          and writeback status without requiring any backend connection. All data is loaded from
          static <code>run.json</code> export files served from the configured data path.
        </p>
      </section>

      {/* ── Keyboard Shortcuts ── */}
      <section
        className="rv-help__section"
        aria-labelledby="help-shortcuts-title"
        data-testid="help-section-shortcuts"
      >
        <h2 id="help-shortcuts-title" className="rv-help__section-title">
          Keyboard Shortcuts
        </h2>
        <table className="rv-help__table" aria-label="Keyboard shortcuts reference">
          <thead>
            <tr>
              <th scope="col">Key / Combo</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {SHORTCUTS.map((s) => (
              <tr key={s.keys.join("+")}>
                <td>
                  {s.keys.map((k, i) => (
                    <span key={k}>
                      <kbd className="rv-help__kbd">{k}</kbd>
                      {i < s.keys.length - 1 && (
                        <span aria-label="or"> / </span>
                      )}
                    </span>
                  ))}
                </td>
                <td>{s.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* ── Glossary ── */}
      <section
        className="rv-help__section"
        aria-labelledby="help-glossary-title"
        data-testid="help-section-glossary"
      >
        <h2 id="help-glossary-title" className="rv-help__section-title">
          Glossary
        </h2>
        <ul className="rv-help__glossary" aria-label="RF term definitions">
          {GLOSSARY.map((entry) => (
            <li key={entry.term} className="rv-help__glossary-item">
              <span className="rv-help__term">{entry.term}</span>
              <p className="rv-help__definition">{entry.definition}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ── Links ── */}
      <section
        className="rv-help__section"
        aria-labelledby="help-links-title"
        data-testid="help-section-links"
      >
        <h2 id="help-links-title" className="rv-help__section-title">
          Links
        </h2>
        <ul className="rv-help__links-list" aria-label="External documentation links">
          {DOC_LINKS.map((link) => (
            <li key={link.label}>
              <a
                href={link.href}
                className="rv-help__link"
                target="_blank"
                rel="noopener noreferrer"
              >
                {link.label}
              </a>
              {link.stub && (
                <span className="rv-help__link-note" aria-label="placeholder link">
                  (link pending — docs not yet publicly hosted)
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default HelpScreen;
