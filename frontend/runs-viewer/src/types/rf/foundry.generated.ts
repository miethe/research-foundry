/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * Top-level foundry.yaml manifest for a Research Foundry workspace. Wraps the workspace identity under a `foundry:` object alongside a `schema_version`.
 */
export interface FoundryWorkspaceManifest {
  schema_version?: number | string;
  foundry: {
    id: string;
    name: string;
    owner: string;
    default_profile?: "personal" | "work_approved" | "client_approved" | "offline_only";
    storage_mode?: string;
    timezone?: string;
    systems?: {
      [k: string]: any;
    };
    defaults?: {
      [k: string]: any;
    };
    adapters?: {
      [k: string]: any;
    };
    [k: string]: any;
  };
  [k: string]: any;
}
