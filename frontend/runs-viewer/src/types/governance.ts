/**
 * GovernanceConfig — shape of public/data/governance.json written by
 * prebuild-static-data.mjs from config/governance.yaml.
 *
 * This is a static snapshot baked at build time; it is not updated at runtime.
 * All fields are optional because governance.yaml structure may vary across
 * deployments, and the file may be absent (resulting in an empty object {}).
 */

export interface GovernancePolicyRule {
  id: string;
  severity: string;
  description?: string;
}

/**
 * The minimal viewer-relevant shape of the governance config snapshot.
 * key_profiles may have arbitrary nested structure (profile-name → settings),
 * so we type it as Record<string, unknown> to allow safe display via JSON.stringify.
 */
export interface GovernanceConfig {
  key_profiles?: Record<string, unknown> | null;
  policy_rules?: GovernancePolicyRule[] | null;
}
