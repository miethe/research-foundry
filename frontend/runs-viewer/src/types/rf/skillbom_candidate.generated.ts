/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A candidate reusable skill stack proposed for promotion into SkillMeat/SAM.
 */
export interface SkillBOMCandidate {
  id: string;
  name: string;
  proposed_skillbom_id?: string;
  evidence_bundle_id?: string;
  status?: "candidate" | "needs_review" | "promoted" | "rejected";
  purpose?: string;
  agent_postures?: string[];
  tools_used?: string[];
  prompts?: {
    system?: string;
    task?: string;
    [k: string]: any;
  };
  context_packs?: string[];
  output_schemas?: string[];
  validation?: string[];
  known_failure_modes?: string[];
  performance_evidence?: {
    ccdash_event_id?: string;
    quality_score?: string | number;
    rework_count?: number;
    estimated_cost_usd?: number;
    [k: string]: any;
  };
  [k: string]: any;
}
