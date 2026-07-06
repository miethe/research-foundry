/**
 * BuilderBlockEditor — the editor BODY of the Draft Report card (P3 Wave F).
 *
 * Mounted inside BuilderDraftCard.tsx alongside BuilderOutline (F2 fix: the
 * two used to render as separate `it-card`s side by side; the outline, the
 * shared "Draft Report" header, and the Title field now live in
 * BuilderDraftCard — this component owns only the active section's toolbar
 * + blocks + footer).
 *
 * Renders the SELECTED outline section as its constituent blocks (a heading
 * block + its body blocks), each independently editable and each carrying
 * its own evidence-chip row sourced from `draft.claim_links` — this is the
 * "structured blocks + evidence chips, not a blank editor" requirement from
 * the handoff brief. Deviation from the mockup (documented in the Wave F
 * completion report): the mockup shows claim citations as an inline
 * superscript marker inside flowing rendered prose; this implementation
 * edits each block's raw markdown in a textarea (so it stays a real editor)
 * and shows linked claims as a compact chip row BELOW the block instead of
 * re-rendering markdown inline with injected chips. Coverage/materiality/
 * risk semantics are unaffected — only the inline-citation-marker visual
 * treatment is simplified.
 *
 * F1 fix: textareas auto-grow to fit content (no clipped text, no resize
 * grip, transparent at rest, bordered + ringed only on hover/focus) via
 * `field-sizing: content` (builder.css) backed by a JS autosize effect for
 * engines that don't support it yet.
 *
 * Formatting toolbar targets whichever block is currently selected
 * (`selectedBlockId`, shared with the Audit Inspector so "click a paragraph"
 * means the same thing everywhere in the workspace).
 */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { BuilderOutlineSection, ParagraphAuditSummary } from "@/lib/builderCoverage";
import { resolveBuilderClaimPreview } from "@/lib/builderMocks";
import type { ReportBlock, ReportBlockType, ReportClaimLink } from "@/types/rf/report_draft";

// ── Markdown wrap helpers (operate on a textarea's current selection) ────────

function wrapSelection(el: HTMLTextAreaElement, before: string, after: string = before): string {
  const { selectionStart, selectionEnd, value } = el;
  return value.slice(0, selectionStart) + before + value.slice(selectionStart, selectionEnd) + after + value.slice(selectionEnd);
}

function prefixLines(value: string, prefix: (i: number) => string): string {
  return value
    .split("\n")
    .map((line, i) => (line.trim() ? `${prefix(i)}${line}` : line))
    .join("\n");
}

/** Grows a textarea to fit its content. Belt-and-suspenders alongside the CSS `field-sizing: content` declaration for engines that don't support it yet. */
function useAutosizeTextarea(ref: HTMLTextAreaElement | null, value: string) {
  useLayoutEffect(() => {
    if (!ref) return;
    ref.style.height = "auto";
    ref.style.height = `${ref.scrollHeight}px`;
  }, [ref, value]);
}

// ── Toggle switch (F8: teal toggle, not a native checkbox) ────────────────────

function ToggleSwitch({ checked, onChange, disabled, label, testId }: { checked: boolean; onChange: () => void; disabled?: boolean; label: string; testId: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className="rv-builder-toggle"
      data-checked={checked ? "true" : "false"}
      onClick={onChange}
      data-testid={testId}
    >
      <span className="rv-builder-toggle__knob" aria-hidden="true" />
    </button>
  );
}

// ── Toolbar ───────────────────────────────────────────────────────────────────

interface ToolbarProps {
  disabled: boolean;
  onFormat: (kind: "bold" | "italic" | "h2" | "h3" | "bullet" | "numbered" | "link") => void;
  onInsert: (blockType: ReportBlockType) => void;
}

function BlockToolbar({ disabled, onFormat, onInsert }: ToolbarProps) {
  const [insertOpen, setInsertOpen] = useState(false);
  return (
    <div className="rv-builder-toolbar" role="toolbar" aria-label="Block formatting" data-testid="builder-toolbar">
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("bold")} aria-label="Bold"><strong>B</strong></button>
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("italic")} aria-label="Italic"><em>I</em></button>
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("h2")} aria-label="Heading 2">H2</button>
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("h3")} aria-label="Heading 3">H3</button>
      <span className="rv-builder-toolbar__divider" aria-hidden="true" />
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("bullet")} aria-label="Bulleted list">•</button>
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("numbered")} aria-label="Numbered list">1.</button>
      <button type="button" className="rv-builder-toolbar-btn" disabled={disabled} onClick={() => onFormat("link")} aria-label="Insert link">🔗</button>
      <div className="rv-builder-toolbar__insert">
        <button
          type="button"
          className="rv-builder-toolbar-btn rv-builder-toolbar-btn--wide"
          disabled={disabled}
          onClick={() => setInsertOpen((o) => !o)}
          aria-haspopup="menu"
          aria-expanded={insertOpen}
          data-testid="builder-toolbar-insert"
        >
          Insert ▾
        </button>
        {insertOpen && (
          <div className="rv-builder-toolbar__menu" role="menu">
            {(["paragraph", "quote", "callout", "table", "evidence_summary"] as ReportBlockType[]).map((bt) => (
              <button
                key={bt}
                type="button"
                role="menuitem"
                onClick={() => {
                  onInsert(bt);
                  setInsertOpen(false);
                }}
                data-testid={`builder-toolbar-insert-${bt}`}
              >
                {bt.replace("_", " ")}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Claim chip status dot (F6: status folded into the chip, not a separate pill) ─

/** relation/link_status -> dot color, matching the audit inspector's stat tick colors (green supports / blue infers / red contradicts-or-broken / amber needs review). */
function chipDotTone(link: ReportClaimLink): "green" | "blue" | "red" | "amber" {
  if (link.relation === "contradicts") return "red";
  if (link.link_status === "missing_claim" || link.link_status === "missing_source") return "red";
  if (link.link_status === "needs_review" || link.link_status === "stale") return "amber";
  if (link.relation === "inferred_from") return "blue";
  return "green";
}

// ── Per-block field ───────────────────────────────────────────────────────────

interface BlockFieldProps {
  block: ReportBlock;
  claimLinks: ReportClaimLink[];
  isSelected: boolean;
  showClaimChips: boolean;
  disabled: boolean;
  registerTextarea: (blockId: string, el: HTMLTextAreaElement | null) => void;
  onSelect: () => void;
  onCommitMarkdown: (markdown: string) => void;
  onRemoveClaimLink: (claimLinkId: string) => void;
}

function BlockField({
  block,
  claimLinks,
  isSelected,
  showClaimChips,
  disabled,
  registerTextarea,
  onSelect,
  onCommitMarkdown,
  onRemoveClaimLink,
}: BlockFieldProps) {
  const [text, setText] = useState(block.markdown);
  const [el, setEl] = useState<HTMLTextAreaElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useAutosizeTextarea(el, text);

  // Reflect external updates (e.g. after a claim-link insert appended a [claim:] tag)
  // without clobbering in-flight typing: only resync when not actively focused.
  const focusedRef = useRef(false);
  useEffect(() => {
    if (!focusedRef.current) setText(block.markdown);
  }, [block.markdown]);

  function scheduleCommit(next: string) {
    setText(next);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onCommitMarkdown(next), 700);
  }

  const blockLinks = claimLinks.filter((cl) => cl.block_id === block.block_id);

  return (
    <div
      className={`rv-builder-block${isSelected ? " rv-builder-block--selected" : ""} rv-builder-block--${block.block_type}`}
      data-testid={`builder-block-${block.block_id}`}
      data-coverage={block.coverage_status}
      onClick={onSelect}
    >
      <textarea
        ref={(node) => {
          registerTextarea(block.block_id, node);
          setEl(node);
        }}
        className="rv-builder-block__textarea"
        value={text}
        disabled={disabled}
        rows={1}
        onFocus={() => {
          focusedRef.current = true;
          onSelect();
        }}
        onBlur={() => {
          focusedRef.current = false;
          if (timerRef.current) clearTimeout(timerRef.current);
          if (text !== block.markdown) onCommitMarkdown(text);
        }}
        onChange={(e) => scheduleCommit(e.target.value)}
        data-testid={`builder-block-textarea-${block.block_id}`}
        aria-label={`${block.block_type} block`}
      />
      {showClaimChips && blockLinks.length > 0 && (
        <div className="rv-builder-block__chips" data-testid={`builder-block-chips-${block.block_id}`}>
          {blockLinks.map((link) => {
            const preview = resolveBuilderClaimPreview(link.claim_id);
            return (
              <span
                key={link.claim_link_id}
                className="rv-builder-claim-chip"
                data-testid={`builder-claim-chip-${link.claim_id}`}
                title={preview?.text ?? "Claim text unavailable"}
              >
                <span className={`rv-builder-claim-chip__dot rv-builder-claim-chip__dot--${chipDotTone(link)}`} aria-hidden="true" />
                <code>{link.claim_id}</code>
                <span className="rv-builder-claim-chip__text">{preview?.text ?? "Claim text unavailable"}</span>
                <button
                  type="button"
                  aria-label={`Unlink ${link.claim_id}`}
                  disabled={disabled}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveClaimLink(link.claim_link_id);
                  }}
                >
                  ×
                </button>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export interface BuilderBlockEditorProps {
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

export function BuilderBlockEditor({
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
}: BuilderBlockEditorProps) {
  const textareaRefs = useRef<Map<string, HTMLTextAreaElement>>(new Map());

  function registerTextarea(blockId: string, el: HTMLTextAreaElement | null) {
    if (el) textareaRefs.current.set(blockId, el);
    else textareaRefs.current.delete(blockId);
  }

  function activeTextarea(): { blockId: string; el: HTMLTextAreaElement } | null {
    const blockId = selectedBlockId ?? section?.bodyBlockIds[0] ?? null;
    if (!blockId) return null;
    const el = textareaRefs.current.get(blockId);
    return el ? { blockId, el } : null;
  }

  function handleFormat(kind: "bold" | "italic" | "h2" | "h3" | "bullet" | "numbered" | "link") {
    const target = activeTextarea();
    if (!target) return;
    const { blockId, el } = target;
    let next = el.value;
    if (kind === "bold") next = wrapSelection(el, "**");
    else if (kind === "italic") next = wrapSelection(el, "*");
    else if (kind === "link") next = wrapSelection(el, "[", "](https://)");
    else if (kind === "bullet") next = prefixLines(el.value, () => "- ");
    else if (kind === "numbered") next = prefixLines(el.value, (i) => `${i + 1}. `);
    else if (kind === "h2" || kind === "h3") {
      const hashes = kind === "h2" ? "## " : "### ";
      next = el.value.replace(/^(#{2,3}\s+)?/, hashes);
    }
    onCommitBlockMarkdown(blockId, next);
  }

  if (!section) {
    return (
      <div className="rv-builder-editor" data-testid="builder-block-editor">
        <p className="rv-muted">Select a section from the outline to begin editing.</p>
      </div>
    );
  }

  const bodyBlocks = section.bodyBlockIds.map((id) => blocksById.get(id)).filter((b): b is ReportBlock => Boolean(b));
  const wordCount = bodyBlocks.reduce((n, b) => n + b.markdown.split(/\s+/).filter(Boolean).length, 0);
  const claimCount = new Set(bodyBlocks.flatMap((b) => b.linked_claim_ids)).size;
  const citationCount = bodyBlocks.reduce((n, b) => n + claimLinks.filter((cl) => cl.block_id === b.block_id).length, 0);

  return (
    <div className="rv-builder-editor" data-testid="builder-block-editor">
      <div className="rv-builder-editor__section-head">
        <h4>
          {section.numberLabel} {section.text}
        </h4>
        <div className="rv-builder-editor__coverage">
          <span>Section coverage</span>
          <span className="rv-builder-editor__coverage-bar">
            <span className="rv-builder-editor__coverage-fill" style={{ width: `${sectionCoverage.isApplicable ? sectionCoverage.coveragePct : 0}%` }} />
          </span>
          <span>{sectionCoverage.isApplicable ? `${sectionCoverage.coveragePct}%` : "—"}</span>
        </div>
      </div>

      <BlockToolbar disabled={disabled} onFormat={handleFormat} onInsert={onInsertBlock} />

      <div className="rv-builder-editor__blocks" data-testid="builder-editor-blocks">
        {bodyBlocks.length === 0 && <p className="rv-muted">No content blocks in this section yet.</p>}
        {bodyBlocks.map((block) => (
          <BlockField
            key={block.block_id}
            block={block}
            claimLinks={claimLinks}
            isSelected={block.block_id === selectedBlockId}
            showClaimChips={showClaimChips}
            disabled={disabled}
            registerTextarea={registerTextarea}
            onSelect={() => onSelectBlock(block.block_id)}
            onCommitMarkdown={(md) => onCommitBlockMarkdown(block.block_id, md)}
            onRemoveClaimLink={onRemoveClaimLink}
          />
        ))}
      </div>

      <footer className="rv-builder-editor__footer">
        <span>
          Markdown · {wordCount} words · {claimCount} claims · {citationCount} citations
        </span>
        <label className="rv-builder-editor__toggle">
          <span>Show claim chips</span>
          <ToggleSwitch checked={showClaimChips} onChange={onToggleShowClaimChips} label="Show claim chips" testId="builder-toggle-chips" />
        </label>
      </footer>
    </div>
  );
}

export default BuilderBlockEditor;
