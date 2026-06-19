/* AUTO-GENERATED — do not edit by hand. Run `pnpm codegen` to regenerate. */

/**
 * A captured raw idea prior to triage into a research intent.
 */
export interface RawIdea {
  id: string;
  created_at?: string;
  captured_from?: "chat" | "voice" | "note" | "clip" | "email" | "meeting" | "manual" | "intenttree";
  title: string;
  body: string;
  tags?: string[];
  sensitivity?: "public" | "personal" | "work_sensitive" | "client_sensitive";
  urgency?: "low" | "medium" | "high";
  research_potential?: "unknown" | "low" | "medium" | "high";
  suggested_project?: "Research Foundry" | "Agentic OS" | "unassigned";
  initial_questions?: string[];
  attachments?: {
    path_or_uri?: string;
    type?: "url" | "pdf" | "markdown" | "image" | "audio" | "other";
    [k: string]: any;
  }[];
  triage?: {
    status?: "untriaged" | "converted_to_intent" | "archived" | "duplicate";
    intent_id?: string | null;
    [k: string]: any;
  };
  [k: string]: any;
}
