/**
 * LineageList.tsx — Compact, keyboard-accessible tree view for the lineage list mode.
 *
 * Design: file-tree guide lines, per-kind accent rail, compact single-line rows.
 * All inline <dl> details have been removed — they now live in LineageDetailPanel.
 */

import type { CSSProperties, KeyboardEvent } from "react";
import type { LineageNode } from "./lineageTree";
import { LINEAGE_KIND_META } from "./lineageTree";
import { KindIcon, ChevronDown, ChevronRight } from "./kindIcons";

// ── Shared view contract (sprint 2 graph view uses the same props) ─────────────

export interface LineageViewProps {
  roots: LineageNode[];
  expanded: Set<string>;
  onToggle: (id: string) => void;
  selectedNodeId: string | null;
  onSelectNode: (id: string) => void;
  /** Called when the user double-clicks a row; opens DetailModal with the node payload. */
  onExpandNode?: (node: LineageNode) => void;
}

// ── LineageList ────────────────────────────────────────────────────────────────

export function LineageList({ roots, expanded, onToggle, selectedNodeId, onSelectNode, onExpandNode }: LineageViewProps) {
  return (
    <div
      className="rv-lineage-tree rv-lineage-list"
      role="tree"
      aria-label="Run lineage explorer"
    >
      {roots.map((node, idx) => (
        <LineageListRow
          key={node.id}
          node={node}
          depth={0}
          expanded={expanded}
          selectedNodeId={selectedNodeId}
          onToggle={onToggle}
          onSelectNode={onSelectNode}
          onExpandNode={onExpandNode}
          isLast={idx === roots.length - 1}
          ancestorLines={[]}
        />
      ))}
    </div>
  );
}

// ── LineageListRow ─────────────────────────────────────────────────────────────

interface LineageListRowProps {
  node: LineageNode;
  depth: number;
  expanded: Set<string>;
  selectedNodeId: string | null;
  onToggle: (id: string) => void;
  onSelectNode: (id: string) => void;
  onExpandNode?: (node: LineageNode) => void;
  isLast: boolean;
  /** For each ancestor depth, whether that ancestor's guide line should continue. */
  ancestorLines: boolean[];
}

function LineageListRow({
  node,
  depth,
  expanded,
  selectedNodeId,
  onToggle,
  onSelectNode,
  onExpandNode,
  isLast,
  ancestorLines,
}: LineageListRowProps) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(node.id);
  const isSelected = selectedNodeId === node.id;
  const meta = LINEAGE_KIND_META[node.kind];

  // testId follows original convention: claim nodes use claimId if available
  const testId =
    node.kind === "claim" && node.claimId
      ? `lineage-node-${node.claimId}`
      : `lineage-node-${node.id}`;

  function handleRowClick() {
    onSelectNode(node.id);
  }

  function handleRowKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelectNode(node.id);
    } else if (e.key === "ArrowRight") {
      // Expand a collapsed node (treeitem keyboard pattern). The toggle button is
      // not in the Tab order, so arrows are the keyboard path to expand/collapse.
      if (hasChildren && !isExpanded) {
        e.preventDefault();
        onToggle(node.id);
      }
    } else if (e.key === "ArrowLeft") {
      if (hasChildren && isExpanded) {
        e.preventDefault();
        onToggle(node.id);
      }
    }
  }

  function handleToggleClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (hasChildren) onToggle(node.id);
  }

  function handleToggleKey(e: KeyboardEvent<HTMLButtonElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      e.stopPropagation();
      if (hasChildren) onToggle(node.id);
    }
  }

  const indent = depth * 20; // 20px per depth level

  return (
    <>
      <div
        className={[
          "rv-ll-row",
          `rv-ll-row--${node.kind}`,
          isSelected ? "rv-ll-row--selected" : "",
        ].filter(Boolean).join(" ")}
        role="treeitem"
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-selected={isSelected || undefined}
        data-testid={testId}
        data-kind={node.kind}
        tabIndex={0}
        onClick={handleRowClick}
        onDoubleClick={() => onExpandNode?.(node)}
        onKeyDown={handleRowKey}
        style={{ "--ll-depth": depth, "--ll-indent": `${indent}px` } as CSSProperties & Record<string, unknown>}
      >
        {/* Guide lines: ancestor connectors + elbow for current row */}
        <span className="rv-ll-guides" aria-hidden="true" style={{ width: `${indent + (depth > 0 ? 20 : 0)}px` }}>
          {ancestorLines.map((continues, i) => (
            <span
              key={i}
              className={`rv-ll-guide-line${continues ? " rv-ll-guide-line--continues" : ""}`}
              style={{ left: `${i * 20 + 10}px` }}
            />
          ))}
          {depth > 0 && (
            <span
              className={`rv-ll-guide-elbow${isLast ? " rv-ll-guide-elbow--last" : ""}`}
              style={{ left: `${(depth - 1) * 20 + 10}px` }}
            />
          )}
        </span>

        {/* Left accent rail */}
        <span
          className="rv-ll-rail"
          style={{ background: meta.accent }}
          aria-hidden="true"
        />

        {/* Kind icon */}
        <span
          className="rv-ll-icon"
          style={{ color: meta.accent }}
          aria-hidden="true"
        >
          <KindIcon kind={node.kind} size={14} />
        </span>

        {/* Chevron toggle */}
        <button
          type="button"
          className="rv-ll-toggle"
          aria-label={
            hasChildren
              ? `${isExpanded ? "Collapse" : "Expand"} ${node.title}`
              : undefined
          }
          aria-expanded={hasChildren ? isExpanded : undefined}
          disabled={!hasChildren}
          onClick={handleToggleClick}
          onKeyDown={handleToggleKey}
          tabIndex={-1}
        >
          {hasChildren ? (
            isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
          ) : null}
        </button>

        {/* Title + subtitle */}
        <div className="rv-ll-title-group">
          <strong className="rv-ll-title">{node.title}</strong>
          {node.subtitle && <code className="rv-ll-subtitle">{node.subtitle}</code>}
        </div>

        {/* Chips (right-aligned) */}
        {node.chips && node.chips.length > 0 && (
          <div className="rv-ll-chips" aria-hidden="true">
            {node.chips.map((chip) => (
              <span key={chip} className="it-chip rv-ll-chip">{chip}</span>
            ))}
          </div>
        )}
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <div role="group">
          {node.children.map((child, idx) => {
            const childIsLast = idx === node.children.length - 1;
            // Ancestor lines: pass-through parent's ancestorLines + whether this depth continues
            const childAncestorLines = [...ancestorLines, !isLast];
            return (
              <LineageListRow
                key={child.id}
                node={child}
                depth={depth + 1}
                expanded={expanded}
                selectedNodeId={selectedNodeId}
                onToggle={onToggle}
                onSelectNode={onSelectNode}
                onExpandNode={onExpandNode}
                isLast={childIsLast}
                ancestorLines={childAncestorLines}
              />
            );
          })}
        </div>
      )}
    </>
  );
}

export default LineageList;
