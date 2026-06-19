/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A council review packet capturing voting policy, members, decision, and concerns.
 */
export interface ReviewPacket {
  id: string;
  evidence_bundle_id?: string;
  voting?: {
    allowed_votes?: string[];
    [k: string]: any;
  };
  members?: {
    role?: string;
    posture?: string;
    [k: string]: any;
  }[];
  output?: {
    decision?: "approve" | "revise" | "required_block";
    concerns?: {
      concern_id?: string;
      severity?: "low" | "medium" | "high" | "blocker";
      text?: string;
      required_fix?: string;
      [k: string]: any;
    }[];
    [k: string]: any;
  };
  reviewer_notes?: string;
  [k: string]: any;
}
