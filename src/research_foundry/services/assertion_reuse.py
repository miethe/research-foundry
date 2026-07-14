"""Fail-closed reuse eligibility for the reusable assertion ledger.

The ledger remains the authority.  This module only evaluates the supplied
authoritative record and never enables retrieval or mutates feature flags.
Lifecycle invalidation is deliberately evaluated before any impact traversal.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

DecisionAction = str
_EDITION_ID_RE = re.compile(r"^sed_[a-f0-9]{64}$")
_CONTRACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class ReuseDecision:
    """A deterministic reuse decision that is safe to persist in a receipt."""

    action: DecisionAction
    reason_code: str
    assertion_id: str | None = None

    @property
    def allowed(self) -> bool:
        return self.action == "allow"


_INVALID_LIFECYCLE_STATES = frozenset({"blocked", "invalid", "retracted", "deleted", "superseded"})
_KNOWN_LIFECYCLE_STATES = frozenset({"eligible", "stale", *_INVALID_LIFECYCLE_STATES})


def evaluate_reuse(
    assertion: Mapping[str, Any] | None,
    *,
    workspace_id: str | None,
    required_edition_id: str | None = None,
    required_extraction_contract: str | None = None,
) -> ReuseDecision:
    """Return ``allow``, ``deny``, or ``refresh`` without inferred defaults.

    Every policy input is authoritative data.  Missing, malformed, unknown,
    or interrupted state therefore denies reuse rather than exposing a partial
    result.  ``stale`` is the one recoverable state and requests a refresh.
    """

    if not isinstance(assertion, Mapping):
        return ReuseDecision("deny", "assertion_missing")
    assertion_id = assertion.get("assertion_id")
    safe_id = assertion_id if isinstance(assertion_id, str) and assertion_id else None
    if safe_id is None:
        return ReuseDecision("deny", "assertion_id_missing")
    if not workspace_id:
        return ReuseDecision("deny", "workspace_context_missing", safe_id)
    if assertion.get("workspace_id") != workspace_id:
        return ReuseDecision("deny", "workspace_mismatch", safe_id)
    state = assertion.get("lifecycle_state")
    if not isinstance(state, str) or state not in _KNOWN_LIFECYCLE_STATES:
        return ReuseDecision("deny", "lifecycle_unknown", safe_id)
    if state in _INVALID_LIFECYCLE_STATES:
        return ReuseDecision("deny", "lifecycle_blocked", safe_id)
    if state == "stale":
        return ReuseDecision("refresh", "freshness_refresh_required", safe_id)
    if assertion.get("freshness_current") is False:
        return ReuseDecision("refresh", "freshness_refresh_required", safe_id)
    if assertion.get("freshness_current") is not True:
        return ReuseDecision("deny", "freshness_context_missing", safe_id)
    if assertion.get("rights_allowed") is not True:
        return ReuseDecision("deny", "rights_denied", safe_id)
    if assertion.get("sensitivity_allowed") is not True:
        return ReuseDecision("deny", "sensitivity_denied", safe_id)
    if assertion.get("evaluation_passed") is not True:
        return ReuseDecision("deny", "evaluation_missing_or_failed", safe_id)
    if assertion.get("invalidation_state") != "active":
        return ReuseDecision("deny", "invalidation_unknown", safe_id)
    edition_id = assertion.get("source_edition_id")
    contract = assertion.get("extraction_contract")
    if not isinstance(edition_id, str) or not _EDITION_ID_RE.fullmatch(edition_id):
        return ReuseDecision("deny", "edition_context_invalid", safe_id)
    if not isinstance(contract, str) or not _CONTRACT_ID_RE.fullmatch(contract):
        return ReuseDecision("deny", "extraction_contract_invalid", safe_id)
    if required_edition_id is not None and not _EDITION_ID_RE.fullmatch(required_edition_id):
        return ReuseDecision("deny", "required_edition_invalid", safe_id)
    if required_extraction_contract is not None and not _CONTRACT_ID_RE.fullmatch(required_extraction_contract):
        return ReuseDecision("deny", "required_extraction_contract_invalid", safe_id)
    if required_edition_id and edition_id != required_edition_id:
        return ReuseDecision("refresh", "edition_refresh_required", safe_id)
    if required_extraction_contract and contract != required_extraction_contract:
        return ReuseDecision("refresh", "extraction_refresh_required", safe_id)
    return ReuseDecision("allow", "eligible", safe_id)


def block_authoritative_reuse(assertion: Mapping[str, Any], *, event_id: str) -> dict[str, Any]:
    """Return the monotonic authoritative invalidation update for an assertion.

    The caller persists this update before invoking impact reconciliation.  A
    repeated event is byte-for-byte idempotent; a different or absent event is
    rejected as an out-of-order lifecycle operation.
    """

    existing = assertion.get("invalidation_event_id")
    invalidation_state = assertion.get("invalidation_state")
    lifecycle_state = assertion.get("lifecycle_state")
    if invalidation_state == "blocked":
        if existing == event_id:
            if lifecycle_state != "blocked":
                raise ValueError("lifecycle_invalidation_inconsistent")
            return dict(assertion)
        if existing is not None:
            raise ValueError("out_of_order_lifecycle_event")
        raise ValueError("invalidation_state_unknown")
    if invalidation_state != "active":
        raise ValueError("invalidation_state_unknown")
    if existing is not None:
        raise ValueError("out_of_order_lifecycle_event")
    if lifecycle_state not in {"eligible", "stale"}:
        raise ValueError("lifecycle_state_unknown")
    updated = dict(assertion)
    updated["lifecycle_state"] = "blocked"
    updated["invalidation_state"] = "blocked"
    updated["invalidation_event_id"] = event_id
    return updated


__all__ = ["ReuseDecision", "block_authoritative_reuse", "evaluate_reuse"]
