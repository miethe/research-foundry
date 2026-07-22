"""Filesystem layout resolution for a Research Foundry workspace.

``FoundryPaths`` is the single source of truth for *where things live* so no
service hard-codes directory names. It locates the workspace root by walking up
from a starting directory until it finds ``foundry.yaml`` (falling back to a
``.skillmeat`` or ``.git`` marker, then the start dir itself).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_ROOT_MARKERS = ("foundry.yaml",)
_FALLBACK_MARKERS = (".skillmeat", ".git")


def find_workspace_root(start: str | Path | None = None) -> Path:
    """Walk up from ``start`` (default cwd) to find the foundry workspace root."""

    cur = Path(start or Path.cwd()).resolve()
    candidates = [cur, *cur.parents]
    for marker in (_ROOT_MARKERS, _FALLBACK_MARKERS):
        for d in candidates:
            if any((d / m).exists() for m in marker):
                return d
    return cur


def distribution_root() -> Path:
    """Root of the installed distribution (for ``rf init`` to copy templates).

    In an editable/dev checkout this resolves to the repo root (``src``'s
    parent's parent). It is where the canonical ``schemas/``, ``config/``, and
    ``templates/`` directories live.
    """

    # src/research_foundry/paths.py -> parents[0]=research_foundry, [1]=src, [2]=repo root
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class FoundryPaths:
    """Resolved paths for a foundry workspace rooted at :attr:`root`."""

    root: Path

    @classmethod
    def discover(cls, start: str | Path | None = None) -> FoundryPaths:
        return cls(root=find_workspace_root(start))

    # --- top-level directories (spec §5) ---
    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def schemas(self) -> Path:
        return self.root / "schemas"

    @property
    def templates(self) -> Path:
        return self.root / "templates"

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    @property
    def raw_ideas(self) -> Path:
        return self.inbox / "raw_ideas"

    @property
    def intents(self) -> Path:
        return self.root / "intents"

    @property
    def intents_active(self) -> Path:
        return self.intents / "active"

    @property
    def iboms(self) -> Path:
        return self.root / "iboms"

    @property
    def iboms_active(self) -> Path:
        return self.iboms / "active"

    @property
    def intenttree(self) -> Path:
        return self.root / "intenttree"

    @property
    def intenttree_nodes(self) -> Path:
        return self.intenttree / "nodes"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    @property
    def registries(self) -> Path:
        return self.root / "registries"

    @property
    def meatywiki(self) -> Path:
        return self.root / "meatywiki"

    @property
    def skillmeat(self) -> Path:
        return self.root / "skillmeat"

    @property
    def ccdash(self) -> Path:
        return self.root / "ccdash"

    @property
    def foundry_yaml(self) -> Path:
        return self.root / "foundry.yaml"

    # --- report builder (public-multiuser-release Phase 3, plan D10) ---
    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def report_drafts(self) -> Path:
        """Durable, file-canonical Report Builder draft store (plan D10).

        Draft truth (``draft.yaml`` + revision snapshots) lives here, never in
        the rebuildable ``catalog.db`` cache — see ``builder_service``.
        """
        return self.reports / "drafts"

    def report_draft_dir(self, report_draft_id: str) -> Path:
        return self.report_drafts / report_draft_id

    # --- agent jobs (public-multiuser-release Phase 4, plan OQ-B) ---
    @property
    def agent_jobs(self) -> Path:
        """Durable agent-job store (plan OQ-B). Lives under workspace root, not .rf_cache/."""
        return self.root / "agent_jobs"

    def agent_job_dir(self, agent_job_id: str) -> Path:
        return self.agent_jobs / agent_job_id

    # --- derived/local caches (gitignored; never canonical) ---
    @property
    def rf_cache(self) -> Path:
        return self.root / ".rf_cache"

    @property
    def catalog_db(self) -> Path:
        """Path to the derived, rebuildable shared-evidence-catalog sqlite3 DB.

        Public-multiuser-release Phase 1 (catalog_service). Lives under
        ``.rf_cache/`` (gitignored) — files stay canonical, this DB is a
        rebuildable read model (AOS constraint 2).
        """
        return self.rf_cache / "catalog.db"

    # --- durable auth/RBAC state (public-multiuser-release Phase 5, plan AUTH-103) ---
    @property
    def rf_state(self) -> Path:
        """Durable authentication and RBAC state store.

        Sibling to ``.rf_cache/`` at workspace root but intentionally NOT
        placed under ``.rf_cache/`` — this directory contains long-lived data
        (``rbac.db``) that must survive catalog.db rebuilds.  Unlike
        ``.rf_cache/``, it is NOT gitignored by default because some
        deployments may want to commit auth state (single-user, embedded).

        See ``services/rbac_store.py`` and P5 auth provider plan.
        """
        return self.root / ".rf_state"

    @property
    def rbac_db(self) -> Path:
        """Path to the durable RBAC sqlite3 database.

        Public-multiuser-release Phase 5 (rbac_store). Lives under
        ``.rf_state/`` — NOT under ``.rf_cache/`` — because RBAC membership
        data must survive catalog.db rebuilds (AOS durability constraint).
        """
        return self.rf_state / "rbac.db"

    # --- run sub-tree (spec §5 runs/rf_run_*/...) ---
    def run_dir(self, run_id: str) -> Path:
        return self.runs / run_id

    def run_paths(self, run_id: str) -> RunPaths:
        return RunPaths(run=self.run_dir(run_id))


@dataclass(frozen=True)
class RunPaths:
    """Resolved paths within a single ``runs/<run_id>/`` directory (spec §5)."""

    run: Path

    @property
    def run_yaml(self) -> Path:
        return self.run / "run.yaml"

    @property
    def routing_decision(self) -> Path:
        return self.run / "routing_decision.yaml"

    @property
    def research_brief(self) -> Path:
        return self.run / "research_brief.md"

    @property
    def swarm_plan(self) -> Path:
        return self.run / "swarm_plan.yaml"

    @property
    def source_candidates(self) -> Path:
        return self.run / "source_candidates.yaml"

    @property
    def sources(self) -> Path:
        return self.run / "sources"

    @property
    def extractions(self) -> Path:
        return self.run / "extractions"

    @property
    def claims(self) -> Path:
        return self.run / "claims"

    @property
    def claim_ledger(self) -> Path:
        return self.claims / "claim_ledger.yaml"

    @property
    def contradiction_log(self) -> Path:
        return self.claims / "contradiction_log.yaml"

    @property
    def inference_log(self) -> Path:
        return self.claims / "inference_log.yaml"

    @property
    def reports(self) -> Path:
        return self.run / "reports"

    @property
    def report_draft(self) -> Path:
        return self.reports / "report_draft.md"

    @property
    def report_final(self) -> Path:
        return self.reports / "report_final.md"

    @property
    def reviews(self) -> Path:
        return self.run / "reviews"

    @property
    def critic_review(self) -> Path:
        return self.reviews / "critic_review.yaml"

    @property
    def council_review(self) -> Path:
        return self.reviews / "council_review.yaml"

    @property
    def governance_review(self) -> Path:
        return self.reviews / "governance_review.yaml"

    @property
    def verification(self) -> Path:
        return self.reviews / "verification.yaml"

    @property
    def evidence_bundle(self) -> Path:
        return self.run / "evidence_bundle.yaml"

    @property
    def lineage(self) -> Path:
        """Append-only seal/lineage record for tamper-evidence (TASK-4.2/4.3).

        Written by the seal trigger (``rf run export --seal``) and read by
        verification tooling to confirm a run's evidence has not been altered
        since sealing. TASK-4.3 owns the actual digest-computation and
        append-only write logic; this property only resolves the on-disk
        location.
        """
        return self.run / "lineage.yaml"

    @property
    def rights(self) -> Path:
        """Run-local rights-substrate artifacts (rights-entity-model-v1, P4-2+).

        Deliberately NOT part of :meth:`ensure_scaffold` -- unlike the
        always-present pipeline dirs, this subtree is created lazily by the
        first caller that needs it (e.g. ``services.terms_snapshot``), and it
        is never read by ``services/export_service.py`` (FR-19: excluded from
        exported/shipped bundles by construction -- the export path only ever
        reads a fixed, explicitly-named artifact set, never a glob of
        ``self.run``).
        """
        return self.run / "rights"

    @property
    def rights_terms_snapshots(self) -> Path:
        """Content-addressed terms-of-service/license snapshot store (P4-2)."""
        return self.rights / "terms_snapshots"

    @property
    def writebacks(self) -> Path:
        return self.run / "writebacks"

    @property
    def meatywiki_writeback(self) -> Path:
        return self.writebacks / "meatywiki_writeback.md"

    @property
    def skillbom_candidate(self) -> Path:
        return self.writebacks / "skillbom_candidate.md"

    @property
    def ccdash_event(self) -> Path:
        return self.writebacks / "ccdash_event.yaml"

    @property
    def intenttree_update(self) -> Path:
        return self.writebacks / "intenttree_update.yaml"

    @property
    def arc_review_request(self) -> Path:
        return self.writebacks / "arc_review_request.yaml"

    @property
    def notebooklm_update(self) -> Path:
        return self.writebacks / "notebooklm_update.yaml"

    @property
    def decision_record_writeback(self) -> Path:
        return self.writebacks / "decision_record_writeback.md"

    @property
    def telemetry(self) -> Path:
        return self.run / "telemetry"

    @property
    def token_costs(self) -> Path:
        return self.telemetry / "token_costs.yaml"

    @property
    def tool_calls(self) -> Path:
        return self.telemetry / "tool_calls.yaml"

    @property
    def run_trace(self) -> Path:
        return self.telemetry / "run_trace.jsonl"

    def ensure_scaffold(self) -> RunPaths:
        """Create the standard run sub-directories (idempotent)."""

        for d in (self.sources, self.extractions, self.claims, self.reports,
                  self.reviews, self.writebacks, self.telemetry):
            d.mkdir(parents=True, exist_ok=True)
        return self


__all__ = ["find_workspace_root", "distribution_root", "FoundryPaths", "RunPaths"]
