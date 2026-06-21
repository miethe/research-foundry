/**
 * LedgerFacets — facet filter panel for ClaimLedgerTable.
 *
 * Facets:
 *   - status (supported/inference/speculation/…)
 *   - materiality (core/background/style/material)
 *   - claim_type (factual/inference/speculation)
 *   - confidence (low/medium/high)
 *
 * Multi-facet selection is AND logic: a claim must match ALL active facet
 * selections to be visible. Selecting no facets in a dimension shows all.
 *
 * Emits the filtered claim array via onFiltered(claims).
 */

import { useState, useEffect, useCallback } from "react";
import type { RFClaim, RFClaimStatus, RFClaimConfidence, RFMateriality, RFClaimType } from "@/types/rf";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface LedgerFacetState {
  status:      Set<string>;
  materiality: Set<string>;
  claim_type:  Set<string>;
  confidence:  Set<string>;
}

export interface LedgerFacetsProps {
  claims:        RFClaim[];
  onFiltered:    (filtered: RFClaim[]) => void;
  onFacetChange?: (facets: LedgerFacetState) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_OPTIONS: { value: RFClaimStatus; label: string; chip: string }[] = [
  { value: "supported",    label: "Supported",    chip: "green"  },
  { value: "inference",    label: "Inference",    chip: "blue"   },
  { value: "speculation",  label: "Speculation",  chip: "orange" },
  { value: "mixed",        label: "Mixed",        chip: "gold"   },
  { value: "contradicted", label: "Contradicted", chip: "red"    },
  { value: "unsupported",  label: "Unsupported",  chip: "red"    },
];

const MATERIALITY_OPTIONS: { value: RFMateriality; label: string }[] = [
  { value: "core",       label: "Core"       },
  { value: "material",   label: "Material"   },
  { value: "background", label: "Background" },
  { value: "style",      label: "Style"      },
];

const CLAIM_TYPE_OPTIONS: { value: RFClaimType; label: string }[] = [
  { value: "factual",     label: "Factual"     },
  { value: "inference",   label: "Inference"   },
  { value: "speculation", label: "Speculation" },
];

const CONFIDENCE_OPTIONS: { value: RFClaimConfidence; label: string; chip: string }[] = [
  { value: "high",   label: "High",   chip: "green"  },
  { value: "medium", label: "Medium", chip: "gold"   },
  { value: "low",    label: "Low",    chip: "orange" },
];

function emptyFacets(): LedgerFacetState {
  return {
    status:      new Set(),
    materiality: new Set(),
    claim_type:  new Set(),
    confidence:  new Set(),
  };
}

function applyFacets(claims: RFClaim[], facets: LedgerFacetState): RFClaim[] {
  return claims.filter((c) => {
    if (facets.status.size      > 0 && !facets.status.has(c.status ?? ""))           return false;
    if (facets.materiality.size > 0 && !facets.materiality.has(c.materiality ?? "")) return false;
    if (facets.claim_type.size  > 0 && !facets.claim_type.has(c.claim_type ?? ""))   return false;
    if (facets.confidence.size  > 0 && !facets.confidence.has(c.confidence ?? ""))   return false;
    return true;
  });
}

function toggle(set: Set<string>, value: string): Set<string> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

// ── FacetGroup sub-component ──────────────────────────────────────────────────

interface FacetGroupProps {
  label:   string;
  testId:  string;
  options: { value: string; label: string; chip?: string }[];
  active:  Set<string>;
  counts:  Map<string, number>;
  onToggle: (value: string) => void;
}

function FacetGroup({ label, testId, options, active, counts, onToggle }: FacetGroupProps) {
  // Only show options that have at least one claim (or are currently active)
  const visible = options.filter((o) => (counts.get(o.value) ?? 0) > 0 || active.has(o.value));
  if (visible.length === 0) return null;

  return (
    <div className="rv-facet-group" data-testid={`facet-group-${testId}`}>
      <span className="rv-facet-group__label">{label}</span>
      <div className="rv-facet-group__pills">
        {visible.map((opt) => {
          const isActive = active.has(opt.value);
          const count = counts.get(opt.value) ?? 0;
          return (
            <button
              key={opt.value}
              type="button"
              className={`rv-facet-pill${isActive ? " rv-facet-pill--active" : ""} ${opt.chip ?? ""}`}
              data-testid={`facet-pill-${testId}-${opt.value}`}
              data-active={isActive ? "true" : "false"}
              onClick={() => onToggle(opt.value)}
              aria-pressed={isActive}
            >
              {opt.label}
              <span className="rv-facet-pill__count">{count}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LedgerFacets({ claims, onFiltered, onFacetChange }: LedgerFacetsProps) {
  const [facets, setFacets] = useState<LedgerFacetState>(emptyFacets);

  // Recompute counts from the FULL claims set (not filtered)
  const statusCounts      = new Map<string, number>();
  const materialityCounts = new Map<string, number>();
  const claimTypeCounts   = new Map<string, number>();
  const confidenceCounts  = new Map<string, number>();

  for (const c of claims) {
    if (c.status)      statusCounts.set(c.status,           (statusCounts.get(c.status)            ?? 0) + 1);
    if (c.materiality) materialityCounts.set(c.materiality, (materialityCounts.get(c.materiality)  ?? 0) + 1);
    if (c.claim_type)  claimTypeCounts.set(c.claim_type,    (claimTypeCounts.get(c.claim_type)     ?? 0) + 1);
    if (c.confidence)  confidenceCounts.set(c.confidence,   (confidenceCounts.get(c.confidence)    ?? 0) + 1);
  }

  // Notify parent whenever facets change
  useEffect(() => {
    onFiltered(applyFacets(claims, facets));
    onFacetChange?.(facets);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facets, claims]);

  const handleToggle = useCallback((dim: keyof LedgerFacetState, value: string) => {
    setFacets((prev) => ({
      ...prev,
      [dim]: toggle(prev[dim], value),
    }));
  }, []);

  const hasActive = (
    facets.status.size > 0 ||
    facets.materiality.size > 0 ||
    facets.claim_type.size > 0 ||
    facets.confidence.size > 0
  );

  return (
    <div className="rv-facets" data-testid="ledger-facets">
      <div className="rv-facets__header">
        <span className="rv-facets__title">Filter</span>
        {hasActive && (
          <button
            type="button"
            className="it-btn ghost xs rv-facets__clear"
            data-testid="facet-clear"
            onClick={() => setFacets(emptyFacets())}
          >
            Clear all
          </button>
        )}
      </div>

      <div className="rv-facets__groups">
        <FacetGroup
          label="Status"
          testId="status"
          options={STATUS_OPTIONS}
          active={facets.status}
          counts={statusCounts}
          onToggle={(v) => handleToggle("status", v)}
        />
        <FacetGroup
          label="Materiality"
          testId="materiality"
          options={MATERIALITY_OPTIONS}
          active={facets.materiality}
          counts={materialityCounts}
          onToggle={(v) => handleToggle("materiality", v)}
        />
        <FacetGroup
          label="Claim Type"
          testId="claim_type"
          options={CLAIM_TYPE_OPTIONS}
          active={facets.claim_type}
          counts={claimTypeCounts}
          onToggle={(v) => handleToggle("claim_type", v)}
        />
        <FacetGroup
          label="Confidence"
          testId="confidence"
          options={CONFIDENCE_OPTIONS}
          active={facets.confidence}
          counts={confidenceCounts}
          onToggle={(v) => handleToggle("confidence", v)}
        />
      </div>
    </div>
  );
}

export default LedgerFacets;
