/**
 * BuilderOutline — left sub-column of the Draft Report card (P3 Wave F,
 * folded into BuilderDraftCard per the F2 visual-fidelity fix — this is no
 * longer its own top-level `it-card`, just a bare nav inside the shared
 * card's body grid). Numbered h2/h3 outline derived from draft blocks via
 * lib/builderCoverage.ts::buildOutline — same "click heading to navigate"
 * idea as ReportOverlay/ReportOutline.tsx, but sourced from Builder blocks
 * (draft.blocks) rather than a rendered markdown DOM, since sections here
 * are directly selectable/editable units, not just scroll targets.
 *
 * F8 fix: dropped the per-section "has issues" red dot — the mockup has no
 * such indicator, and it fired on ordinary "needs_review" paragraphs (e.g.
 * an inference awaiting citation), reading as a false-alarm "stray red dot"
 * rather than a real contradiction. Issue severity now surfaces only in the
 * Audit Inspector, where it can carry real semantics (BuilderIssue.severity).
 */
import type { BuilderOutlineSection } from "@/lib/builderCoverage";

export interface BuilderOutlineProps {
  sections: BuilderOutlineSection[];
  activeHeadingBlockId: string | null;
  onSelectSection: (headingBlockId: string) => void;
  onAddSection: () => void;
  disabled?: boolean;
}

export function BuilderOutline({ sections, activeHeadingBlockId, onSelectSection, onAddSection, disabled = false }: BuilderOutlineProps) {
  return (
    <nav className="rv-builder-outline" aria-label="Report outline" data-testid="builder-outline">
      <h4 className="rv-builder-outline__title">Outline</h4>
      <ol className="rv-builder-outline__list">
        {sections.map((section) => {
          const isActive = section.headingBlockId === activeHeadingBlockId;
          return (
            <li key={section.headingBlockId} className={`rv-builder-outline__item rv-builder-outline__item--h${section.level}`}>
              <button
                type="button"
                className={`rv-builder-outline__link${isActive ? " rv-builder-outline__link--active" : ""}`}
                onClick={() => onSelectSection(section.headingBlockId)}
                data-testid={`builder-outline-item-${section.headingBlockId}`}
                aria-current={isActive ? "true" : undefined}
              >
                <span className="rv-builder-outline__handle" aria-hidden="true">⠿</span>
                <span className="rv-builder-outline__number">{section.numberLabel}</span>
                <span className="rv-builder-outline__text">{section.text}</span>
              </button>
            </li>
          );
        })}
      </ol>
      <button
        type="button"
        className="it-btn ghost sm rv-builder-outline__add"
        onClick={onAddSection}
        disabled={disabled}
        title={disabled ? "Read-only in static mode" : "Add section"}
        data-testid="builder-outline-add-section"
      >
        + Add section
      </button>
    </nav>
  );
}

export default BuilderOutline;
