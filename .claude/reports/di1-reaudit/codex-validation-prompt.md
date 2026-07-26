ROLE: Independent adversarial cross-validator for a DI-1 multi-tenant isolation re-audit of the Research Foundry codebase (Python `rf`). You are the SECOND model; four Claude probes already ran. Your job is NOT to agree — it is to try to REFUTE their two load-bearing structural claims and to find any isolation surface they missed. Read-only: do not modify files.

REPO ROOT: current -C directory. HEAD should be d71a261 (git rev-parse to confirm).

CONTEXT: A prior DI-1 audit accepted only a "trusted-cohort multi_user" posture and explicitly did NOT certify adversarial multi-tenant isolation for runs/claims/evidence. Commit 08559a0 (DF-004) later added workspace_id isolation to runs/claims/evidence. Four commits landed on top (CARP C3 catalog-assisted planning 95e8419/d824290; claim-term-index feab7de/d71a261). This re-audit asks whether current HEAD is adversarially multi-tenant safe.

The four Claude probe reports are on disk — READ them first, they contain the exact claims and file:line evidence you must challenge:
- .claude/reports/di1-reaudit/probe-1-runs-writeback.md
- .claude/reports/di1-reaudit/probe-2-enforcement-default.md
- .claude/reports/di1-reaudit/probe-3-jobs-termindex.md
- .claude/reports/di1-reaudit/probe-4-catalog-share.md

YOUR TASKS:

CLAIM 1 (from probe-2) — "Isolation is fail-closed on any public bind." The argument: `_validate_nonloopback_bind` in src/research_foundry/cli_commands.py (~lines 161-205, 3093-3110) hard-blocks binding a non-loopback host without auth (raises ValueError), and `config.py::resolve_workspace_isolation_enforced` (~787-861) AUTO-enforces the moment auth.provider != "none"; isolation cannot be explicitly disabled on a non-loopback bind (config.py:843-851 raises).
  ATTACK IT: Is `rf serve`'s CLI gate the ONLY way the ASGI app can be bound to a public interface? Trace src/research_foundry/api/app.py::create_app and any other entrypoint. Can an operator bypass the CLI guard by running uvicorn/gunicorn/hypercorn directly against the app factory, a docker/systemd CMD, or a programmatic serve — binding 0.0.0.0 with auth.provider="none" so identity is always None and require_workspace_scope short-circuits to allow? Does create_app re-validate the bind, or does it trust the CLI (app.py comment ~250-253)? Is there any config combination (workspace_isolation_enforcement / deployment_mode / viewer.* / env vars) that yields a non-loopback bind with advisory-only or identity-None behavior? Verdict: CONFIRMED / REFUTED / PARTIAL, with file:line.

CLAIM 2 (from probe-4) — "The CARP-5.2 MCP transport trusts an unverified client-supplied identity + sensitivity_threshold, wired into the real workspace-partitioned AssertionCatalog." Files: src/research_foundry/services/search_router/mcp_server.py (_identity_from_mapping ~80-104, the 7 tool registrations) and services/search_router/router.py (run_search ~500-608, _build_ad_hoc_evidence_plan ~308-358).
  VERIFY + EXTEND: Confirm the identity really is unauthenticated end-to-end (no server-side auth in front). Then determine the MISSING deployment fact the probe flagged: HOW is this MCP server actually launched? Is it stdio-only (per-process, per-user) or can it be bound to a network port / run as a shared service (grep for how mcp_server is invoked — CLI command, systemd unit, --transport/--host/--port, FastMCP/stdio)? That determines whether this is a full cross-tenant break or a local-operator non-issue. Report what you find; do not certify safety.

TASK 3 — MISSED-SURFACE HUNT. The four probes covered: runs, writeback, scope/config, agent_jobs, term_index, catalog_retrieval, research_evidence_planning, catalog_service, assertions router, share_store, public-visibility. Independently hunt for isolation-relevant surfaces they did NOT cover. Specifically check: src/research_foundry/api/routers/audit.py, admin.py (delta endpoints since acceptance), reports.py (beyond share-links), export_service.py (full read surface), auth_identity.py, any other MCP server (services/search_router/mcp_server.py vs any catalog/assertion MCP), and any CLI/network entrypoint that reads cross-workspace data without identity. For each: is a cross-workspace read/write reachable by an authenticated ws_b caller against ws_a data? file:line + severity.

OUTPUT FORMAT (concise, this is your final message — no file writes):
## CLAIM 1 verdict: <CONFIRMED|REFUTED|PARTIAL> — <2-4 sentences + file:line>
## CLAIM 2 verdict: <CONFIRMED|REFUTED|PARTIAL> + MCP launch topology finding — <file:line>
## MISSED SURFACES: <bullet list, each: surface, file:line, severity {high|med|low|none-found}>
## NET ASSESSMENT: one paragraph — is HEAD adversarially multi-tenant safe? What must a human weigh? (You may NOT certify safety from code reading; state the residual uncertainty.)

HARD RULE: distinguish "code enforces X under config Y" from "adversarially safe by default." Never certify adversarial multi-tenant safety from a static code read — that is a human Mode-D decision.