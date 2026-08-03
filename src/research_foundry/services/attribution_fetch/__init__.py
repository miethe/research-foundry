"""Attribution-fetch seam — INERT scaffolding for the deferred DEF-1 mechanism.

This package is the deferred "Phase C" fetch path named by
``docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md``
(the "source-metadata-propagation-v1" PRD, §7 deferrals table). It exists
**only** as typed scaffolding — a shape for what a live third-party
attribution fetch would eventually look like — and issues **no network
call under any input combination**, including with any provider or the
umbrella flag enabled. See ``FoundryConfig.attribution_fetch_controls()``
(``src/research_foundry/config.py``) for the (also hard-off-by-default)
config flag that gates *visibility* of this package's intent, not its
network reachability — reachability is unconditionally off, by
construction, regardless of that flag's value.

Two gates keep this off. Neither is closed by this scaffolding, by any
other code in this package, by any doc this package touches, or by any
tracker entry this package touches:

DEF-1
    Per-provider license terms verified for bundle redistribution — NOT
    yet true. PRD §7: "``defer-until: per-provider license terms verified
    for bundle redistribution.`` Propagation architecture is proven
    independent of what feeds it; ingestion itself is the licensing-gated
    piece." Until each provider's terms are independently verified for RF's
    specific redistribution model, no adapter in this package may fetch,
    cache, or redistribute a live third-party value.

DEF-6
    Live ToS re-verification for Semantic Scholar / NCBI — NOT yet done.
    PRD §7: "Licensing table in risk-findings.md is stated from general
    domain knowledge of these programs' public policies, not re-verified
    against live current ToS pages." This is explicitly **not legal
    advice**, and nothing in this package should be read as a licensing or
    legal determination for any provider.

This module asserts **no license posture** for OpenAlex, Crossref, or
Semantic Scholar — favorable, unfavorable, or otherwise. Do not cite this
package, its tests, or its presence in the tree as evidence that DEF-1 or
DEF-6 is closed in any plan, PRD, progress tracker, or IntentTree node.
(Two specific IntentTree nodes carry a ``status: completed`` value from an
unrelated bulk sweep and must NOT be read as clearing either gate here —
both DEF-1 and DEF-6 remain OPEN regardless of what any tracker's status
field currently shows.)

Non-laundering guarantee
-------------------------
Every provider adapter's public entrypoint (``fetch()``) returns a
:class:`ProviderFetchResult` — a value-free, disabled/no-op result carrying
only ``provider``, ``status`` (always ``"disabled"`` today), and a human
``reason``. ``ProviderFetchResult`` has **no** ``value``, ``asserter_type``,
or ``license_basis`` attribute of any kind, so there is structurally
nothing on it a caller could write into ``source_attribution.value`` or any
``trust.*`` field. A caller wanting to author a real
``source_attribution`` record (e.g. from a human-entered value) still has
to independently construct a full record satisfying
``schemas/source_attribution.schema.yaml`` — including its
``if asserter_type startsWith "third_party_" then retrieval_evidence_ref
required`` gate — exactly as before this package existed. This package
adds no shortcut around that schema gate, and no adapter return type is
capable of being mistaken for, or substituted for, a validated
``source_attribution`` record.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The only status value any adapter in this package can currently produce.
#: Reserved for future non-disabled statuses once DEF-1/DEF-6 close and a
#: real implementation lands — neither exists yet.
DISABLED_STATUS = "disabled"


@dataclass(frozen=True)
class ProviderFetchResult:
    """Value-free result returned by every provider adapter's ``fetch()``.

    Deliberately carries no ``value``, ``asserter_type``, or
    ``license_basis`` field — see the module docstring's "Non-laundering
    guarantee". A caller cannot extract a third-party value from this type
    because it never carries one; there is nothing here to write into a
    governed field.
    """

    provider: str
    status: str
    reason: str


def disabled_result(provider: str, reason: str) -> ProviderFetchResult:
    """Build the standard disabled result shared by every adapter.

    Always returns ``status=DISABLED_STATUS`` — this package has exactly
    one status today. No socket, HTTP client, or DNS lookup is touched to
    produce this value.
    """

    return ProviderFetchResult(provider=provider, status=DISABLED_STATUS, reason=reason)


__all__ = ["DISABLED_STATUS", "ProviderFetchResult", "disabled_result"]
