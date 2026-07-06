/**
 * ClaimBasket — bottom bar of the Report Builder (P3 Wave F).
 *
 * Staging area for catalog items picked in BuilderCatalogPane before they're
 * inserted into a specific block. "Insert" calls addClaimLink/addSourceLink
 * against whichever block is currently selected in the center editor; the
 * basket keeps the item afterward (matches the mockup: the basket count
 * doesn't drop after a claim already appears in the draft) — only the ×
 * button removes it from the basket.
 */
import type { CatalogItemSummary } from "@/types/rf/catalog";

export interface ClaimBasketProps {
  items: CatalogItemSummary[];
  collapsed: boolean;
  onToggleCollapse: () => void;
  onRemove: (catalogItemId: string) => void;
  onInsert: (item: CatalogItemSummary) => void;
  canInsert: boolean;
  disabled: boolean;
}

const STATUS_CHIP: Record<string, string> = {
  supported: "green",
  mixed: "orange",
  contradicted: "red",
  unsupported: "red",
  inference: "blue",
  speculation: "orange",
};

export function ClaimBasket({ items, collapsed, onToggleCollapse, onRemove, onInsert, canInsert, disabled }: ClaimBasketProps) {
  return (
    <section className="rv-builder-basket" aria-label="Claim basket" data-testid="claim-basket">
      <header className="rv-builder-basket__header">
        <div>
          <h3>Claim Basket</h3>
          <span className="rv-builder-basket__count" data-testid="claim-basket-count">
            {items.length} item{items.length === 1 ? "" : "s"} selected
          </span>
        </div>
        <span className="rv-builder-basket__hint">Check a catalog row, then click a chip to insert it into the selected block.</span>
        <button
          type="button"
          className="it-btn ghost xs"
          onClick={onToggleCollapse}
          aria-expanded={!collapsed}
          data-testid="claim-basket-toggle"
        >
          {collapsed ? "Expand ▾" : "Collapse ▴"}
        </button>
      </header>

      {!collapsed && (
        <div className="rv-builder-basket__list" data-testid="claim-basket-list">
          {items.length === 0 && <p className="rv-muted">Drag a claim from the catalog or check a row to add it here.</p>}
          {items.map((item) => (
            <div key={item.catalog_item_id} className="rv-builder-basket__chip" data-testid={`claim-basket-chip-${item.local_ref}`}>
              <div className="rv-builder-basket__chip-head">
                <code>{item.local_ref}</code>
                {item.status && <span className={`it-chip ${STATUS_CHIP[item.status] ?? ""}`}>{item.status}</span>}
                <button type="button" aria-label={`Remove ${item.local_ref} from basket`} onClick={() => onRemove(item.catalog_item_id)}>
                  ×
                </button>
              </div>
              <p className="rv-builder-basket__chip-text" title={item.title}>{item.title}</p>
              <button
                type="button"
                className="it-btn ghost xs"
                disabled={disabled || !canInsert}
                title={!canInsert ? "Select a block in the draft first" : disabled ? "Read-only in static mode" : "Insert into selected block"}
                onClick={() => onInsert(item)}
                data-testid={`claim-basket-insert-${item.local_ref}`}
              >
                Insert →
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default ClaimBasket;
