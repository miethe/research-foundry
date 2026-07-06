/**
 * BuilderDraftCard — the "Draft Report" card (P3 Wave F, F2 polish-pass fix).
 *
 * The original layout rendered BuilderOutline and BuilderBlockEditor as two
 * separate `it-card`s side by side inside the center grid column — the
 * mockup has ONE "Draft Report" card with a shared header, a full-width
 * Title field, and the outline as a ~210-230px left sub-column INSIDE that
 * card (not its own card). This component is that single card: header +
 * title + a two-column body (BuilderOutline | BuilderBlockEditor).
 *
 * F8: Title is rendered as a real input (still visual-only — there is no
 * draft-metadata PATCH endpoint in the Wave E contract to persist it against,
 * so it's `readOnly` with a tooltip explaining why, rather than silently
 * discarding edits). Schema version is formatted via
 * lib/builderCoverage.ts::formatSchemaVersion (draft schema_version is a
 * plain integer; the mockup's "Schema: 1.2" dotted format is approximated as
 * "1.0" rather than fabricating a false minor version).
 */
import { formatSchemaVersion } from "@/lib/builderCoverage";
import type { BuilderOutlineSection, ParagraphAuditSummary } from "@/lib/builderCoverage";
import { BuilderOutline } from "./BuilderOutline";
import { BuilderBlockEditor } from "./BuilderBlockEditor";
import type { ReportBlock, ReportBlockType, ReportClaimLink } from "@/types/rf/report_draft";

export interface BuilderDraftCardProps {
  title: string;
  schemaVersion: number;
  sensitivity: string;
  outlineSections: BuilderOutlineSection[];
  activeHeadingBlockId: string | null;
  onSelectSection: (headingBlockId: string) => void;
  onAddSection: () => void;
  section: BuilderOutlineSection | null;
  blocksById: Map<string, ReportBlock>;
  claimLinks: ReportClaimLink[];
  selectedBlockId: string | null;
  sectionCoverage: ParagraphAuditSummary;
  showClaimChips: boolean;
  disabled: boolean;
  onSelectBlock: (blockId: string) => void;
  onCommitBlockMarkdown: (blockId: string, markdown: string) => void;
  onRemoveClaimLink: (claimLinkId: string) => void;
  onInsertBlock: (blockType: ReportBlockType) => void;
  onToggleShowClaimChips: () => void;
}

export function BuilderDraftCard({
  title,
  schemaVersion,
  sensitivity,
  outlineSections,
  activeHeadingBlockId,
  onSelectSection,
  onAddSection,
  section,
  blocksById,
  claimLinks,
  selectedBlockId,
  sectionCoverage,
  showClaimChips,
  disabled,
  onSelectBlock,
  onCommitBlockMarkdown,
  onRemoveClaimLink,
  onInsertBlock,
  onToggleShowClaimChips,
}: BuilderDraftCardProps) {
  return (
    <section className="rv-builder-draftcard it-card" aria-label="Draft report" data-testid="builder-draftcard">
      <header className="rv-builder-draftcard__header">
        <h3>Draft Report</h3>
        <span className="rv-builder-draftcard__meta">
          Schema: {formatSchemaVersion(schemaVersion)} · Threshold: {sensitivity}
        </span>
        <button type="button" className="rv-builder-toolbar-btn rv-builder-draftcard__expand" aria-label="Expand draft report" title="Expand">
          ⤢
        </button>
      </header>

      <div className="rv-builder-draftcard__title-row">
        <label htmlFor="builder-title-input" className="rv-builder-draftcard__title-label">Title</label>
        <input
          id="builder-title-input"
          className="rv-builder-title-input"
          type="text"
          defaultValue={title}
          readOnly
          title="Title editing isn't wired to a persistence endpoint yet — Wave E's contract has no draft-metadata PATCH route."
          data-testid="builder-title-input"
        />
      </div>

      <div className="rv-builder-draftcard__body">
        <BuilderOutline
          sections={outlineSections}
          activeHeadingBlockId={activeHeadingBlockId}
          onSelectSection={onSelectSection}
          onAddSection={onAddSection}
          disabled={disabled}
        />
        <BuilderBlockEditor
          section={section}
          blocksById={blocksById}
          claimLinks={claimLinks}
          selectedBlockId={selectedBlockId}
          sectionCoverage={sectionCoverage}
          showClaimChips={showClaimChips}
          disabled={disabled}
          onSelectBlock={onSelectBlock}
          onCommitBlockMarkdown={onCommitBlockMarkdown}
          onRemoveClaimLink={onRemoveClaimLink}
          onInsertBlock={onInsertBlock}
          onToggleShowClaimChips={onToggleShowClaimChips}
        />
      </div>
    </section>
  );
}

export default BuilderDraftCard;
