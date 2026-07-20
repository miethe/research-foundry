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

import time
from typing import Any
from urllib.parse import urlparse

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.extractors.pdf_extractor import extract_pdf
from research_foundry.yamlio import dump_yaml

from .budgets import Budget, BudgetTracker
from .dedupe import dedupe_hits
from .modes import MODES
from .policy import build_routing_decision, resolve_chain, select_mode
from .providers.base import SearchHit, SearchProvider, all_providers
from .ranking import rank_hits

_EXTRACTION_PROVIDER_PREFERENCE = ("jina", "firecrawl")

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
) -> dict[str, Any]:
    """Execute a full search run and return the ``search_run`` record."""

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
    for pid in chain:
        provider = providers_map.get(pid)
        if provider is None or "discovery" not in provider.roles:
            continue
        if not tracker.can_query():
            break
        try:
            res = provider.search(query, max_results=max_search, constraints=constraints)
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
    routing = build_routing_decision(run_id, request, mode, chain)
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
