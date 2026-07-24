"""Search run orchestrator for the Research Foundry Search Router (Wave 3).

:func:`run_search` ties the Wave-1 routing primitives (modes, budgets, dedupe,
ranking) and the Wave-2 provider adapters into a single, file-backed search run.
It is offline-first and degrade-safe: a missing provider, a network failure, or
a schema mismatch never raises — issues are recorded in the returned record's
``schema_errors`` and the run still produces a ``search_run.yaml`` on disk.

:func:`extract_urls` is the standalone known-URL extraction path used by
``rf fetch``.
"""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.assertion_catalog import AssertionCatalog
from research_foundry.services.catalog_retrieval import (
    RetrievalConstraints,
    RetrievalLimits,
)
from research_foundry.services.extractors.pdf_extractor import extract_pdf
from research_foundry.services.research_evidence_planning import (
    EvidencePlanLimits,
    EvidencePlanQuestion,
    EvidencePlanRequest,
    build_evidence_plan,
    write_evidence_plan,
)
from research_foundry.yamlio import dump_yaml

from .budgets import Budget, BudgetTracker
from .dedupe import dedupe_hits
from .modes import MODES
from .policy import build_routing_decision, resolve_chain, select_mode
from .providers.base import SearchHit, SearchProvider, all_providers
from .ranking import rank_hits

# NOTE (offline-safety convention -- same rationale as ``planning.py`` /
# ``run_launch.py``): ``api.auth.provider`` module-imports ``starlette``.
# ``run_search`` only ever forwards ``identity`` into the CARP catalog helpers
# below (never inspects it directly), so it needs the name only for
# annotations -- imported under TYPE_CHECKING only. (``catalog_retrieval.py``/
# ``research_evidence_planning.py`` already import it unconditionally
# themselves, so this module's own transitive dependency on ``starlette`` is
# unchanged by this branch either way -- this is purely about not adding a
# *second*, direct, unconditional import here.)
if TYPE_CHECKING:
    from research_foundry.api.auth.provider import AuthIdentity

_EXTRACTION_PROVIDER_PREFERENCE = ("jina", "firecrawl")

#: CARP-4.1/4.3. A retrieval policy other than these two is treated as
#: "disabled" -- the v1 default and every legacy caller's behavior
#: (carp-contract-freeze.md §1).
_ACTIVE_RETRIEVAL_POLICIES = frozenset({"catalog_only", "catalog_then_discovery"})

#: Same conservative lexical-terms rule as ``planning.py``'s own
#: ``_lexical_terms`` -- duplicated rather than imported (the two call sites
#: turn different free-text into terms: a brief question here vs. a raw
#: search query there; sharing one three-line regex helper across an
#: unrelated import boundary is not worth the coupling).
_WORD_RE = re.compile(r"[A-Za-z0-9]+")

#: Same conservative English closed-class stopword set as ``planning.py``'s
#: own ``_STOPWORDS`` -- see that module's comment for the full rationale
#: (articles/auxiliaries/prepositions/pronouns/conjunctions/wh-words carry no
#: discriminating power against ``search_text`` and each still spends one of
#: the shared ``max_pages_per_question`` sub-query slots in
#: ``catalog_retrieval._collect_candidates``, crowding out real topical
#: terms). Kept as a literal duplicate, not shared, for the same reason
#: ``_WORD_RE`` above is duplicated.
_STOPWORDS: frozenset[str] = frozenset(
    {
        # Articles
        "a",
        "an",
        "the",
        # Auxiliary / modal verbs
        "am",
        "are",
        "be",
        "been",
        "being",
        "can",
        "could",
        "did",
        "do",
        "does",
        "had",
        "has",
        "have",
        "is",
        "may",
        "might",
        "must",
        "said",
        "say",
        "says",
        "shall",
        "should",
        "was",
        "were",
        "will",
        "would",
        # Prepositions
        "about",
        "above",
        "across",
        "after",
        "against",
        "along",
        "among",
        "around",
        "at",
        "before",
        "behind",
        "below",
        "between",
        "beyond",
        "by",
        "down",
        "during",
        "for",
        "from",
        "in",
        "into",
        "near",
        "of",
        "off",
        "on",
        "onto",
        "out",
        "over",
        "through",
        "to",
        "toward",
        "under",
        "until",
        "up",
        "upon",
        "with",
        "within",
        "without",
        # Pronouns
        "he",
        "her",
        "hers",
        "him",
        "his",
        "i",
        "it",
        "its",
        "me",
        "mine",
        "my",
        "our",
        "ours",
        "she",
        "that",
        "their",
        "theirs",
        "them",
        "these",
        "they",
        "this",
        "those",
        "us",
        "we",
        "you",
        "your",
        "yours",
        # Conjunctions
        "although",
        "and",
        "because",
        "but",
        "nor",
        "or",
        "so",
        "than",
        "though",
        "unless",
        "while",
        "yet",
        # Wh-words
        "how",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "whose",
        "why",
        # planning.py's default-fallback-question template's one content
        # word -- kept for parity with that copy, not a function word here.
        "evidence",
    }
)


def _lexical_terms(text: str) -> tuple[str, ...]:
    """Derive ``required_terms`` from free text: case-folded, 3+ chars,
    stopword-filtered, deduped, first-occurrence order, uncapped.

    LIMITATION: see ``planning.py``'s own ``_lexical_terms`` docstring --
    ``catalog_retrieval._collect_candidates`` spends ``max_pages_per_question``
    (frozen ceiling: 5) as ONE budget shared across every required-term
    sub-query, never per term. A question whose distinct content-term count
    exceeds that shared budget resolves ``residual``/``pagination_limit``
    even when catalog evidence may exist, rather than falsely resolving
    ``covered`` (the previous per-question term cap this function used to
    apply). This is a documented v1 fail-closed limitation, not an optimal
    outcome.

    P6 CARP-6.9 F1 fix -- same fail-closed guard as ``planning.py``'s own
    ``_lexical_terms``: ``catalog_retrieval.retrieve()``'s coverage condition
    1 is vacuous whenever ``required_terms`` is empty (every authorized
    candidate reports lexically matched). A raw search query that is entirely
    stopwords/short tokens (e.g. a query typed as "how do they do it") would
    otherwise collapse to ``()`` and silently trip that vacuous rule. When
    stopword filtering would empty an otherwise non-empty length-filtered
    token stream, this function falls back to the unfiltered (stopwords
    included) token set instead.
    """

    seen: set[str] = set()
    ordered: list[str] = []
    fallback_seen: set[str] = set()
    fallback_ordered: list[str] = []
    for match in _WORD_RE.finditer(text.casefold()):
        term = match.group(0)
        if len(term) < 3:
            continue
        if term not in fallback_seen:
            fallback_seen.add(term)
            fallback_ordered.append(term)
        if term in seen or term in _STOPWORDS:
            continue
        seen.add(term)
        ordered.append(term)
    if not ordered and fallback_ordered:
        return tuple(fallback_ordered)
    return tuple(ordered)


def _evidence_plan_question(question_id: str, question_text: str) -> EvidencePlanQuestion:
    """Build one CARP question, guarding the P6 CARP-6.9 F4 boundary.

    Duplicated copy of ``planning.py``'s own helper of the same name -- see
    that module's docstring for the full rationale. ``_lexical_terms`` above
    still correctly derives ``()`` for a genuinely contentless query (no
    token clears the 3-char floor, e.g. "is it up?"), or an empty/whitespace
    query outright; passing that straight through as ``required_terms``
    would trip ``catalog_retrieval.retrieve()``'s frozen condition-1
    vacuous-match rule and let an arbitrary catalog assertion resolve
    ``covered`` for a query that said nothing derivable. ``required_terms``
    at this boundary is always derived from ``query``, never a caller
    declaration, so an empty derived term set is always a derivation
    outcome -- it is unconditionally marked
    ``forced_residual_reason="evaluation_error"`` instead of ever calling
    ``retrieve()`` for it.
    """

    terms = _lexical_terms(question_text)
    if not terms:
        return EvidencePlanQuestion(
            question_id=question_id,
            question_text=question_text,
            required_terms=(),
            forced_residual_reason="evaluation_error",
        )
    return EvidencePlanQuestion(question_id=question_id, question_text=question_text, required_terms=terms)


def _evidence_plan_limits(retrieval_limits: Mapping[str, Any] | None) -> EvidencePlanLimits:
    """Map ``search_request.schema.yaml``'s ``retrieval.limits`` shape onto
    :class:`EvidencePlanLimits`; absent/partial input falls back to the
    dataclass's own defaults field-by-field."""

    defaults = EvidencePlanLimits()
    if not retrieval_limits:
        return defaults
    return EvidencePlanLimits(
        max_questions=int(retrieval_limits.get("max_questions", defaults.max_questions)),
        retrieval=RetrievalLimits(
            max_candidates_per_question=int(
                retrieval_limits.get(
                    "max_candidates_per_question", defaults.retrieval.max_candidates_per_question
                )
            ),
            max_pages_per_question=int(
                retrieval_limits.get("max_pages_per_question", defaults.retrieval.max_pages_per_question)
            ),
            page_size=int(retrieval_limits.get("page_size", defaults.retrieval.page_size)),
        ),
    )


def _build_ad_hoc_evidence_plan(
    query: str,
    *,
    run_id: str,
    catalog: AssertionCatalog,
    identity: AuthIdentity | None,
    retrieval_policy: str,
    sensitivity_threshold: str | None,
    retrieval_limits: Mapping[str, Any] | None,
    generated_at: str,
    paths: FoundryPaths,
) -> dict[str, Any]:
    """CARP-4.1: treat this search request's own ``query`` as ONE evidence-
    plan question and evaluate it through the P2 adapter + P3 planner
    (:func:`build_evidence_plan`) -- never the ledger, never a provider.

    ``sensitivity_threshold`` is threaded through verbatim, never defaulted:
    an omitted threshold makes every candidate deny with
    ``sensitivity_denied`` (fail-closed by the adapter's own design, not a
    bug this function papers over -- see
    ``catalog_retrieval.RetrievalConstraints``).

    ``automated_reuse_allowed`` is resolved from the SAME source
    ``run_launch.py:195`` uses -- ``FoundryConfig(paths).assertion_ledger_capabilities()``.
    Never hardcoded to ``True``; a deployment with automated reuse disabled
    resolves every otherwise-eligible candidate to ``residual``/``reuse_denied``,
    the same fail-closed outcome the ledger seam already produces.
    """

    from research_foundry.config import FoundryConfig  # local: avoid top-level cycle risk

    capabilities = FoundryConfig(paths=paths).assertion_ledger_capabilities()

    question = _evidence_plan_question(run_id, query)
    request = EvidencePlanRequest(
        evidence_plan_id=f"evp_{run_id}",
        workspace_id=identity.workspace_id if identity is not None else "",
        retrieval_policy=retrieval_policy,
        questions=(question,),
        schema_version="1",
        brief_id=None,
        run_id=run_id,
        generated_at=generated_at,
        decided_at=generated_at,
        constraints=RetrievalConstraints(
            sensitivity_threshold=sensitivity_threshold,
            automated_reuse_allowed=capabilities.automated_reuse_allowed,
        ),
        limits=_evidence_plan_limits(retrieval_limits),
    )
    return build_evidence_plan(catalog, identity=identity, request=request)

# Router provider id -> SkillMeat tool-profile id (skillmeat/tool_profiles/*.yaml,
# §17.1). Providers without an authored profile (e.g. the keyless aos-web/searxng
# free-discovery lane) are simply absent here and contribute no candidate id.
_TOOL_PROFILE_BY_PROVIDER: dict[str, str] = {
    "brave": "brave_search_v1",
    "exa": "exa_search_v1",
    "jina": "jina_reader_v1",
    "firecrawl": "firecrawl_v1",
    "github": "github_discovery_v1",
}

# The durable SkillBOM (skillmeat/skillboms/skill_source_discovery_v1.md) backing
# this router's discovery+extraction provider chain — distinct from the generic
# per-run ``skill_research_swarm_v0`` candidate emitted by services.writeback.
_SOURCE_DISCOVERY_SKILLBOM_ID = "skill_source_discovery_v1"


def _skillmeat_candidate_ids(provider_chain_log: list[dict[str, Any]]) -> list[str]:
    """Tool-profile + SkillBOM ids referenced by this run's provider chain.

    Reuses the static, authored §17.1 tool-profile ids (no new id-minting
    subsystem) — a provider is credited once it appears in the chain log
    (i.e. it was actually invoked this run), regardless of success/failure
    status, since the profile documents its *known* failure modes too.
    """

    profile_ids: list[str] = []
    for entry in provider_chain_log:
        pid = entry.get("provider")
        profile_id = _TOOL_PROFILE_BY_PROVIDER.get(str(pid))
        if profile_id and profile_id not in profile_ids:
            profile_ids.append(profile_id)
    if profile_ids:
        return [_SOURCE_DISCOVERY_SKILLBOM_ID, *profile_ids]
    return []


# ---------------------------------------------------------------------------
# Schema helpers (best-effort; never raise)
# ---------------------------------------------------------------------------


def _registry(paths: FoundryPaths) -> SchemaRegistry | None:
    if paths.schemas.exists():
        return SchemaRegistry(schemas_dir=paths.schemas)
    from research_foundry.paths import distribution_root

    dist = distribution_root() / "schemas"
    return SchemaRegistry(schemas_dir=dist) if dist.exists() else None


def _validate(obj: Any, name: str, paths: FoundryPaths) -> list[str]:
    """Validate ``obj`` against schema ``name``; return error strings (never raise)."""

    registry = _registry(paths)
    if registry is None or not registry.has(name):
        return []
    try:
        result = registry.validate(obj, name)
    except Exception as exc:  # noqa: BLE001 - validation is best-effort
        return [f"{name}: validation error: {exc}"]
    return [f"{name}: {e}" for e in result.errors]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _apply_constraints(hits: list[SearchHit], constraints: dict[str, Any]) -> list[SearchHit]:
    blocked = {d.lower() for d in (constraints.get("blocked_domains") or [])}
    allowed = {d.lower() for d in (constraints.get("allowed_domains") or [])}
    required = set(constraints.get("required_source_types") or [])
    out: list[SearchHit] = []
    for hit in hits:
        host = _host(hit.url)
        if blocked and any(host == b or host.endswith("." + b) for b in blocked):
            continue
        if allowed and not any(host == a or host.endswith("." + a) for a in allowed):
            continue
        # Lenient required-source-type filter: keep undetermined-type hits
        # (source_type is None) and hits whose type is explicitly required.
        if required and hit.source_type is not None and hit.source_type not in required:
            continue
        out.append(hit)
    return out


def _is_pdf_url(url: str) -> bool:
    """Detect a PDF locator by URL path suffix only (no content-type sniffing)."""

    try:
        path = urlparse(url).path
    except ValueError:
        return False
    return path.lower().endswith(".pdf")


def _download_pdf_bytes(url: str) -> bytes | None:
    """Best-effort raw-bytes download for PDF extraction; never raises."""

    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310
            return resp.read()
    except Exception:  # noqa: BLE001  (offline / unreachable -> None, never raise)
        return None


def _first_extraction_provider(
    candidate_ids: list[str],
    providers: dict[str, SearchProvider],
) -> tuple[str | None, SearchProvider | None]:
    """Return the first available extraction provider among ``candidate_ids``."""

    for pid in candidate_ids:
        provider = providers.get(pid)
        if provider is None:
            continue
        try:
            if "extraction" in provider.roles and provider.available():
                return pid, provider
        except Exception:  # noqa: BLE001
            continue
    return None, None


# ---------------------------------------------------------------------------
# run_search
# ---------------------------------------------------------------------------


def run_search(
    request: dict[str, Any],
    *,
    paths: FoundryPaths | None = None,
    providers: dict[str, SearchProvider] | None = None,
    identity: AuthIdentity | None = None,
    catalog: AssertionCatalog | None = None,
    sensitivity_threshold: str | None = None,
    evidence_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a full search run and return the ``search_run`` record.

    CARP-4.1/4.3 (catalog-assisted-research-planning) additions, all
    keyword-only with safe defaults that reproduce the pre-CARP behavior
    exactly: ``identity``, ``catalog``, ``sensitivity_threshold``, and
    ``evidence_plan``. They activate ONLY when ``request["retrieval"]
    ["policy"]`` is ``"catalog_only"`` or ``"catalog_then_discovery"`` --
    every legacy request (the field absent, or ``"disabled"``, the v1
    default) runs the exact same discovery/extraction/metrics flow as
    before this phase, byte-identical (carp-contract-freeze.md §1).

    When active:

    * ``evidence_plan`` (a pre-built ``research_evidence_plan`` dict -- e.g.
      one :mod:`planning` already built and persisted over a brief's
      questions) is consumed AS-IS: no retrieval happens inside this call.
    * Otherwise, this request's own ``query`` is treated as ONE evidence-plan
      question and evaluated live through the P2 adapter + P3 planner
      (:func:`_build_ad_hoc_evidence_plan`) -- never the ledger, never a
      provider.

    Either way, the plan's covered/residual partition then governs
    discovery: under ``catalog_only`` no provider is ever called (an empty
    or denied catalog result is terminal); under ``catalog_then_discovery``
    only the plan's residual question IDs generate a provider request --
    covered questions are never re-queried and their selection is never
    mutated by the discovery merge.
    """

    paths = paths or FoundryPaths.discover()
    started = time.monotonic()
    created_at = ids.now_iso()
    schema_errors: list[str] = _validate(request, "search_request", paths)

    query = str(request.get("query", ""))
    mode = select_mode(request)
    budget = Budget.from_request_dict(request).merge_mode_defaults(MODES[mode].budget)
    tracker = BudgetTracker(budget)

    # Mint a collision-free run id rooted at the query.
    base_id = ids.run_id(query or "search")
    run_id = ids.disambiguate_id(
        base_id,
        seed=query or base_id,
        exists=lambda c: paths.run_dir(c).exists(),
    )
    rp = paths.run_paths(run_id)
    rp.run.mkdir(parents=True, exist_ok=True)

    providers_map = providers if providers is not None else all_providers()
    chain = resolve_chain(mode, providers=providers_map)
    constraints: dict[str, Any] = request.get("constraints", {}) or {}

    # --- CARP-4.1/4.3: catalog retrieval phase ----------------------------
    # Gated entirely on retrieval_policy != "disabled". A legacy request
    # (the common case) never enters this block: plan_dict stays None,
    # residual_question_ids stays empty, catalog_terminal stays False, and
    # discovery_queries below collapses to today's exact single-query loop.
    retrieval_block: dict[str, Any] = request.get("retrieval") or {}
    retrieval_policy = str(retrieval_block.get("policy") or "disabled")
    if retrieval_policy not in _ACTIVE_RETRIEVAL_POLICIES:
        retrieval_policy = "disabled"

    plan_dict: dict[str, Any] | None = None
    residual_questions: list[dict[str, Any]] = []
    residual_question_ids: list[str] = []
    catalog_terminal = False

    if evidence_plan is not None:
        plan_dict = dict(evidence_plan)
        # An explicitly-supplied plan is authoritative over its own policy;
        # a mismatched/absent retrieval.policy on the raw request is not
        # trusted to override it.
        plan_policy = str(plan_dict.get("retrieval_policy") or retrieval_policy)
        retrieval_policy = plan_policy if plan_policy in _ACTIVE_RETRIEVAL_POLICIES else "disabled"
    elif retrieval_policy != "disabled":
        plan_dict = _build_ad_hoc_evidence_plan(
            query,
            run_id=run_id,
            catalog=catalog if catalog is not None else AssertionCatalog(paths),
            identity=identity,
            retrieval_policy=retrieval_policy,
            sensitivity_threshold=sensitivity_threshold,
            retrieval_limits=retrieval_block.get("limits"),
            generated_at=created_at,
            paths=paths,
        )
        schema_errors.extend(_validate(plan_dict, "research_evidence_plan", paths))
        write_evidence_plan(plan_dict, rp.run / "research_evidence_plan.yaml")

    if plan_dict is not None and retrieval_policy != "disabled":
        residual_questions = [q for q in plan_dict.get("questions", []) if q.get("coverage_state") == "residual"]
        if retrieval_policy == "catalog_only":
            # catalog_only NEVER routes to discovery (carp-contract-freeze.md
            # §1) -- terminal regardless of any question's own coverage_state.
            residual_question_ids = []
            catalog_terminal = True
        else:  # catalog_then_discovery
            residual_question_ids = [q["question_id"] for q in residual_questions]
            catalog_terminal = not residual_question_ids

    # --- discovery -------------------------------------------------------
    provider_chain_log: list[dict[str, Any]] = []
    all_hits: list[SearchHit] = []
    # Per-provider scorecard inputs (spec §17 rollup) — aggregated below into
    # metrics["providers"] and, via search_metrics, into the ccdash event so
    # telemetry.provider_scorecard() can roll cost/duplicate/failure rates up
    # across runs without re-deriving them from raw hit lists.
    provider_stats: dict[str, dict[str, Any]] = {}

    def _touch_provider(pid: str, role: str) -> dict[str, Any]:
        entry = provider_stats.setdefault(pid, {"provider": pid, "roles": []})
        if role not in entry["roles"]:
            entry["roles"].append(role)
        return entry

    max_search = (
        min(budget.max_urls_to_extract, 25)
        if budget.max_urls_to_extract and budget.max_urls_to_extract > 0
        else 10
    )

    # CARP-4.1/4.3: which (question_id, query_text) pairs actually reach a
    # provider. Legacy/disabled reduces to exactly one iteration with this
    # request's own ``query`` -- identical to the pre-CARP single loop below.
    # catalog_only (or a fully-covered catalog_then_discovery plan) is
    # terminal: zero iterations, so the loop body never runs and no provider
    # is ever touched, regardless of what ``chain`` contains.
    if retrieval_policy == "disabled":
        discovery_queries: list[tuple[str | None, str]] = [(None, query)]
    elif catalog_terminal:
        discovery_queries = []
    else:
        discovery_queries = [(q["question_id"], q.get("question_text") or query) for q in residual_questions]

    for _question_id, q_query in discovery_queries:
        for pid in chain:
            provider = providers_map.get(pid)
            if provider is None or "discovery" not in provider.roles:
                continue
            if not tracker.can_query():
                break
            try:
                res = provider.search(q_query, max_results=max_search, constraints=constraints)
            except Exception as exc:  # noqa: BLE001 - providers must never break the run
                provider_chain_log.append({"provider": pid, "role": "discovery", "status": "failed"})
                schema_errors.append(f"provider {pid}: {exc}")
                continue
            provider_chain_log.append(
                {"provider": pid, "role": "discovery", "status": res.status}
            )
            tracker.add_query()
            tracker.add_cost(res.estimated_cost_usd)
            all_hits.extend(res.hits)
            stat = _touch_provider(pid, "discovery")
            stat["queries_executed"] = stat.get("queries_executed", 0) + 1
            stat["estimated_cost_usd"] = round(
                stat.get("estimated_cost_usd", 0.0) + res.estimated_cost_usd, 6
            )
            stat["raw_hits"] = stat.get("raw_hits", 0) + len(res.hits)
            if tracker.exceeded():
                break
        if tracker.exceeded():
            break

    raw_count = len(all_hits)
    deduped = dedupe_hits(all_hits)
    ranked = rank_hits(deduped)
    hits = _apply_constraints(ranked, constraints)

    surviving_by_provider: dict[str, int] = {}
    for hit in hits:
        if hit.provider:
            surviving_by_provider[hit.provider] = surviving_by_provider.get(hit.provider, 0) + 1
    for pid, stat in provider_stats.items():
        raw_hits = stat.get("raw_hits", 0)
        if raw_hits:
            surviving = surviving_by_provider.get(pid, 0)
            stat["duplicate_rate"] = round((raw_hits - surviving) / raw_hits, 4)
        elif "discovery" in stat.get("roles", []):
            stat["duplicate_rate"] = 0.0

    dump_yaml([h.to_dict() for h in hits], rp.source_candidates)

    # --- source cards (+ optional extraction) ---------------------------
    output_reqs: dict[str, Any] = request.get("output_requirements", {}) or {}
    want_cards = output_reqs.get("source_cards", True) is not False
    extractor_id, extractor = _first_extraction_provider(chain, providers_map)

    from research_foundry.services.source_cards import create_source_card

    source_card_ids: list[str] = []
    extract_attempts = 0
    extract_failures = 0
    if want_cards:
        for hit in hits[: budget.max_urls_to_extract]:
            if not tracker.can_extract():
                break
            markdown: str | None = None
            risk_flags: list[str] = []
            if extractor is not None:
                extract_attempts += 1
                try:
                    res = extractor.extract([hit.url])
                    doc = res.docs[0] if res.docs else None
                    markdown = doc.markdown if doc is not None else None
                    risk_flags = list(doc.risk_flags) if doc is not None else []
                except Exception:  # noqa: BLE001
                    markdown = None
                if not markdown:
                    extract_failures += 1
            try:
                ingest = create_source_card(
                    locator=hit.url,
                    run_id=run_id,
                    source_type=hit.source_type or "other",
                    title=hit.title or None,
                    created_by_agent=f"rf_search_router:{extractor_id or 'discovery'}",
                    content=markdown,
                    extra_limitations=risk_flags or None,
                    fetch=False,
                    paths=paths,
                )
            except Exception as exc:  # noqa: BLE001 - card creation is best-effort
                schema_errors.append(f"source_card {hit.url}: {exc}")
                continue
            source_card_ids.append(ingest.source_card_id)
            tracker.add_extract(1)

    if extractor_id and extract_attempts:
        extract_stat = _touch_provider(extractor_id, "extraction")
        extract_stat["extraction_attempts"] = extract_attempts
        extract_stat["extraction_failure_rate"] = round(extract_failures / extract_attempts, 4)

    # --- metrics ---------------------------------------------------------
    latency_ms = int((time.monotonic() - started) * 1000)
    duplicate_rate = round((raw_count - len(deduped)) / raw_count, 4) if raw_count else 0.0
    extraction_failure_rate = (
        round(extract_failures / extract_attempts, 4) if extract_attempts else 0.0
    )
    # useful_source_count: hits that actually produced a source card (the
    # useful subset of the discovery pipeline's output).
    useful_source_count = len(source_card_ids)
    # citation_coverage: source-carded hits ÷ hits surviving constraints —
    # i.e. useful_source_count / len(hits), where `hits` is the post-dedupe,
    # post-ranking, post-constraint candidate set this run considered for
    # extraction. 0.0 when there were no surviving hits (avoids div-by-zero).
    citation_coverage = round(useful_source_count / len(hits), 4) if hits else 0.0
    metrics: dict[str, Any] = {
        "queries_executed": tracker.queries,
        "urls_extracted": tracker.urls,
        "pages_crawled": 0,
        "useful_source_count": useful_source_count,
        "duplicate_rate": duplicate_rate,
        "extraction_failure_rate": extraction_failure_rate,
        "citation_coverage": citation_coverage,
        "estimated_cost_usd": round(tracker.cost, 6),
        "latency_ms": latency_ms,
        # Per-provider scorecard rollup input (spec §17) — merged into the
        # ccdash event's metrics via search_metrics below; consumed by
        # telemetry.provider_scorecard(). Additive/optional; empty when the
        # run had no discovery/extraction provider activity.
        "providers": dict(sorted(provider_stats.items())),
    }

    search_run: dict[str, Any] = {
        "run_id": run_id,
        "created_at": created_at,
        "completed_at": ids.now_iso(),
        "request": request,
        "provider_chain": provider_chain_log,
        "normalized_results": [h.to_dict() for h in hits],
        "source_cards": [{"source_id": cid} for cid in source_card_ids],
        "metrics": metrics,
        "writebacks": {
            "ccdash_event_id": None,
            "meatywiki_page_ids": [],
            "skillmeat_candidate_ids": _skillmeat_candidate_ids(provider_chain_log),
        },
    }

    # CARP-4.1/4.3: mirror the evidence plan's selections/metrics into this
    # search run (search_run.schema.yaml's `retrieval` block --
    # non-authoritative persisted mirror; the plan file itself, written
    # above, stays the sole authoritative source -- carp-contract-freeze.md
    # §4.1). Omitted entirely under disabled, exactly like every legacy run.
    if plan_dict is not None and retrieval_policy != "disabled":
        search_run["retrieval"] = {
            "policy": retrieval_policy,
            "evidence_plan_ref": plan_dict.get("evidence_plan_id"),
            "mirror_is_authoritative": False,
            "selections": [
                {
                    "question_id": q["question_id"],
                    "assertion_id": (q.get("selected_assertion_ref") or {}).get("assertion_id"),
                    "assertion_version": (q.get("selected_assertion_ref") or {}).get("assertion_version"),
                    "retrieval_receipt": q.get("retrieval_receipt"),
                }
                for q in plan_dict.get("questions", [])
            ],
            "metrics": plan_dict.get("summary", {}),
        }

    # CCDash telemetry — best-effort; never breaks the run. Runs before the
    # search_run.yaml dump below so the persisted artifact (not just the
    # in-memory return value) reflects the minted ccdash_event_id.
    try:
        from research_foundry.services.telemetry import emit_ccdash_event

        event_id = emit_ccdash_event(run_id, paths=paths, search_metrics=metrics)
        search_run["writebacks"]["ccdash_event_id"] = event_id
    except Exception:  # noqa: BLE001 - telemetry is best-effort
        pass

    schema_errors.extend(_validate(search_run, "search_run", paths))
    dump_yaml(search_run, rp.run / "search_run.yaml")

    # Routing decision — only persist when it is schema-valid.
    routing = build_routing_decision(
        run_id,
        request,
        mode,
        chain,
        retrieval_policy=retrieval_policy,
        residual_question_ids=residual_question_ids,
    )
    if not _validate(routing, "routing_decision", paths):
        dump_yaml(routing, rp.run / "routing_decision.yaml")

    if schema_errors:
        search_run["schema_errors"] = schema_errors
    return search_run


# ---------------------------------------------------------------------------
# extract_urls
# ---------------------------------------------------------------------------


def extract_urls(
    urls: list[str],
    *,
    run_id: str | None = None,
    paths: FoundryPaths | None = None,
    providers: dict[str, SearchProvider] | None = None,
) -> dict[str, Any]:
    """Extract markdown from ``urls`` into source cards under a run directory."""

    paths = paths or FoundryPaths.discover()
    providers_map = providers if providers is not None else all_providers()

    if run_id is None:
        base = ids.run_id("extract " + (urls[0] if urls else "urls"))
        run_id = ids.disambiguate_id(
            base,
            seed=",".join(urls) or base,
            exists=lambda c: paths.run_dir(c).exists(),
        )
    rp = paths.run_paths(run_id)
    rp.run.mkdir(parents=True, exist_ok=True)

    extractor_id, extractor = _first_extraction_provider(
        list(_EXTRACTION_PROVIDER_PREFERENCE), providers_map
    )

    from research_foundry.services.source_cards import create_source_card

    card_ids: list[str] = []
    degraded_any = False
    for url in urls:
        markdown: str | None = None
        risk_flags: list[str] = []
        pdf_extraction_status: str | None = None
        if _is_pdf_url(url):
            # PDF-aware path: download raw bytes ourselves and run the local
            # pypdf-backed extractor instead of the jina/firecrawl chain,
            # which isn't PDF-aware. Every failure mode here (no download,
            # missing pdf extra, corrupted PDF, no text layer) degrades to
            # markdown=None, which falls into the existing locator_only path
            # below -- never an unhandled exception. The tri-state
            # ``PdfExtractionResult.status`` (full_text/partial/locator_only)
            # is threaded through to ``create_source_card`` below so a
            # truncated (>100KB) PDF is recorded as "partial" rather than
            # being mislabeled "full_text" by the content-derived default.
            try:
                data = _download_pdf_bytes(url)
                if data:
                    pdf_result = extract_pdf(data)
                    markdown = pdf_result.text
                    pdf_extraction_status = pdf_result.status
            except Exception:  # noqa: BLE001
                markdown = None
                pdf_extraction_status = None
        elif extractor is not None:
            try:
                res = extractor.extract([url])
                doc = res.docs[0] if res.docs else None
                markdown = doc.markdown if doc is not None else None
                risk_flags = list(doc.risk_flags) if doc is not None else []
            except Exception:  # noqa: BLE001
                markdown = None
        try:
            ingest = create_source_card(
                locator=url,
                run_id=run_id,
                source_type="other",
                created_by_agent=f"rf_search_router:{extractor_id or 'none'}",
                content=markdown,
                extra_limitations=risk_flags or None,
                fetch=False,
                paths=paths,
                extraction_status=pdf_extraction_status,
            )
        except Exception:  # noqa: BLE001
            degraded_any = True
            continue
        card_ids.append(ingest.source_card_id)
        if ingest.degraded:
            degraded_any = True

    return {"run_id": run_id, "source_cards": card_ids, "degraded": degraded_any}


__all__ = ["run_search", "extract_urls"]
