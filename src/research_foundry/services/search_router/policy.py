"""Routing policy for the Research Foundry Search Router (Wave 3).

Pure, side-effect-free helpers that decide *which* mode a request runs in and
*which* provider chain is viable given the currently registered + available
providers.

Usage::

    from research_foundry.services.search_router.policy import (
        select_mode, resolve_chain, build_routing_decision,
    )

    mode = select_mode(request)
    chain = resolve_chain(mode)
"""

from __future__ import annotations

from typing import Any

from .modes import MODES
from .providers.base import SearchProvider, all_providers

_DEFAULT_MODE = "source_discovery"


def select_mode(request: dict[str, Any]) -> str:
    """Return the request's ``mode`` when present and valid, else the default."""

    mode = request.get("mode")
    if isinstance(mode, str) and mode in MODES:
        return mode
    return _DEFAULT_MODE


def resolve_chain(
    mode: str,
    *,
    providers: dict[str, SearchProvider] | None = None,
) -> list[str]:
    """Return the mode's provider chain filtered to registered + available ids.

    ``providers`` defaults to the global registry (:func:`all_providers`). A
    provider id from the chain is kept only when it is present in the map AND
    its ``available()`` check passes.
    """

    registry = providers if providers is not None else all_providers()
    chain: list[str] = []
    for pid in MODES[mode].provider_chain:
        provider = registry.get(pid)
        if provider is None:
            continue
        try:
            if provider.available():
                chain.append(pid)
        except Exception:  # noqa: BLE001 - availability checks never break routing
            continue
    return chain


def build_routing_decision(
    run_id: str,
    request: dict[str, Any],
    mode: str,
    chain: list[str],
    *,
    retrieval_policy: str | None = None,
    residual_question_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a schema-valid ``routing_decision`` record for the run.

    Populates every required field (``id``/``intent_id``/``active_node_id``)
    plus sensible search-router defaults so the record validates and can be
    persisted alongside the run.

    ``retrieval_policy``/``residual_question_ids`` are CARP-4.3 additions:
    when ``retrieval_policy`` is ``None`` or ``"disabled"`` (the default, and
    every legacy call site), neither key is added to the returned mapping --
    byte-identical to the pre-CARP shape. Otherwise both are set verbatim, so
    the caller (``run_search``) is the sole source of truth for what counts
    as "residual" here; this function performs no coverage evaluation itself.
    """

    approval = request.get("approval", {}) or {}
    decision: dict[str, Any] = {
        "id": f"routing_{run_id}",
        "intent_id": request.get("intent_id") or f"intent_search_{run_id}",
        "active_node_id": request.get("task_node_id") or run_id,
        "selected_posture_chain": ["researcher"],
        "selected_tools": list(chain),
        "human_required": bool(approval.get("requires_human_approval")),
        "rationale": f"search mode={mode}",
        # Search-router context (schema allows additionalProperties).
        "mode": mode,
        "provider_chain": list(chain),
        "query": request.get("query", ""),
    }
    if retrieval_policy is not None and retrieval_policy != "disabled":
        decision["retrieval_policy"] = retrieval_policy
        decision["residual_question_ids"] = list(residual_question_ids or [])
    return decision


__all__ = ["select_mode", "resolve_chain", "build_routing_decision"]
