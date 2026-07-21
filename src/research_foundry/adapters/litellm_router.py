"""LiteLLM router adapter — model-profile routing (spec §13, §8.2).

Exposes :meth:`route` which maps a model-profile name (e.g. ``rf_extract_cheap``)
to a concrete ``{provider, model, ...}`` decision by reading
``config/model_profiles.yaml`` and the environment. In the default environment
``litellm`` is not installed and no provider keys are present, so:

* :meth:`available` is False, and
* :meth:`route` deterministically returns the profile's first ``preferred``
  entry (degraded, no live completion).

Real mode (when ``litellm`` is importable) would additionally honour env-based
key availability to pick the first reachable provider; we keep the default
deterministic so routing never depends on network or secrets.
"""

from __future__ import annotations

import os
from typing import Any

from ..config import FoundryConfig
from ..paths import FoundryPaths
from ..services.governance import GuardContext, guard_check
from .base import AdapterResult, BaseAdapter, register

# Mapping from a profile's preferred ``provider`` to the env var that would make
# it live. Used only to *prefer* a reachable provider when keys exist; absence
# never fails routing (we fall back to the first preferred entry).
#
# ``ica`` is the IBM ICA gateway (OpenAI-compatible chat-completions), the default
# agentic-node model lane. It carries a dedicated ``RF_LLM_API_KEY`` (never the
# real-vendor ``ANTHROPIC_API_KEY``/``OPENAI_API_KEY`` — those are forbidden under
# Mode-D Gate #2) and a per-entry ``api_base``. Mapping it here (rather than
# leaving it unmapped) is a correctness requirement: an unmapped provider is
# treated as key-free (like ``ollama``) and would be considered reachable without
# any credential.
_PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ica": "RF_LLM_API_KEY",  # IBM ICA gateway (OpenAI-compatible); api_base per entry
    "ollama": None,  # local; no key required
}


class LiteLLMRouterAdapter(BaseAdapter):
    """Routes model profiles to concrete (provider, model) decisions."""

    id = "litellm_router"
    requires = ("litellm",)

    def route(
        self,
        model_profile: str,
        *,
        paths: FoundryPaths | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Resolve ``model_profile`` to a concrete routing decision.

        Reads ``config/model_profiles.yaml`` for the profile's ``preferred``
        list and returns the first entry whose provider key is present in the
        environment; if none are reachable (the default offline case), returns
        the first preferred entry with ``degraded=True``.
        """

        paths = paths or FoundryPaths.discover()
        env = env if env is not None else dict(os.environ)
        cfg = FoundryConfig(paths=paths)
        profiles = cfg.model_profiles.get("model_profiles", {})
        profile = profiles.get(model_profile) if isinstance(profiles, dict) else None

        if not isinstance(profile, dict):
            return {
                "model_profile": model_profile,
                "provider": None,
                "model": None,
                "degraded": True,
                "reason": "unknown_profile",
            }

        preferred = [p for p in (profile.get("preferred") or []) if isinstance(p, dict)]
        if not preferred:
            return {
                "model_profile": model_profile,
                "provider": None,
                "model": None,
                "degraded": True,
                "reason": "no_preferred_entries",
            }

        chosen = preferred[0]
        reachable = None
        if self.available():
            for entry in preferred:
                provider = str(entry.get("provider") or "")
                key_var = _PROVIDER_KEYS.get(provider)
                if key_var is None or env.get(key_var):  # local provider or key present
                    reachable = entry
                    break

        live = reachable is not None
        selected = reachable or chosen
        return {
            "model_profile": model_profile,
            "provider": selected.get("provider"),
            "model": selected.get("model"),
            # ``api_base`` (e.g. the ICA gateway) propagates to the consumer so a
            # downstream completion — or the out-of-band swarm reading the routing
            # decision — targets the right OpenAI-compatible endpoint. None for
            # direct-vendor providers that use the SDK default base.
            "api_base": selected.get("api_base"),
            "tier": profile.get("tier"),
            "temperature": profile.get("temperature"),
            "max_tokens": profile.get("max_tokens"),
            "preferred": preferred,
            "degraded": not live,
            "reason": "reachable_provider" if live else "preferred_fallback",
        }

    def complete(
        self,
        prompt: str,
        *,
        model_profile: str = "rf_extract_cheap",
        messages: list[dict[str, Any]] | None = None,
        paths: FoundryPaths | None = None,
        env: dict[str, str] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        sensitivity: str | None = None,
        profile: str = "personal",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Run a raw LLM completion for ``model_profile`` — **DARK by default**.

        LLM-001 / OQ-3 / D8 decision — *new method, not a ``run(complete=True)``
        request-mode branch*
        ------------------------------------------------------------------------
        ``run()`` is frozen to return :class:`AdapterResult`, which is
        ``source_candidates``-shaped (a discovery result: candidate sources +
        artifacts + notes). A raw completion is a *text payload* (+ finish
        reason + token/cost accounting) with **no** source candidates; forcing
        it through ``AdapterResult`` would either abuse ``artifacts``/``notes``
        to smuggle the completion text or emit a semantically-empty
        ``source_candidates=[]`` result. A ``run(complete=True)`` branch inherits
        that same return-type mismatch. So ``complete()`` is a **dedicated method
        returning a plain ``dict``**, exactly parallel to :meth:`route` (which
        also returns a plain decision dict, not an ``AdapterResult``). This keeps
        the completion payload honest and leaves the frozen ``AdapterResult``
        contract — and the swarm/source-discovery path that depends on it —
        untouched. Rationale mirrored in the E2-P1 running-log note.

        Dark / degraded gate (D3, FR-13, R2/R3/R6)
        ------------------------------------------
        The live wire call fires **only** when *all three* hold:

        1. the routing decision selects ``provider == "ica"`` (the only
           OpenAI-compatible lane wired for a raw completion here);
        2. :meth:`available` is True (``litellm`` importable in this env); and
        3. the ICA key — resolved **exclusively** via ``_PROVIDER_KEYS["ica"]``
           (``RF_LLM_API_KEY``), *never* ``ANTHROPIC_API_KEY``/``OPENAI_API_KEY``
           — is present in ``env``.

        In every other environment (and in the entire offline test suite, where
        ``litellm`` is absent) this returns ``degraded=True`` with ``text=None``
        and performs **zero** live calls. Activation of the live path is gated
        behind Mode-D Gate #2 + an operator-supplied ``RF_LLM_API_KEY``; the
        first live nonce probe is E2-P4, deferred to the operator — this method
        merges dark (D3).

        Wire contract (R2/R3)
        ---------------------
        The live call is ``litellm.completion(model="openai/<plain-id>",
        api_base=<from route()>, api_key=<RF_LLM_API_KEY via _PROVIDER_KEYS>)``:

        * the wire model id is the **plain** ``<model>`` from the profile — the
          ``openai/`` prefix only forces litellm's OpenAI-compatible chat client
          against ``api_base``; a ``[1m]`` suffix is **never** appended (it 401s
          a raw caller);
        * no ``anthropic``/``openai`` litellm provider entry is created for ICA
          (that would read the real-vendor keys — a Gate #2 violation).

        Structured output — forced tool-call, never ``response_format`` (OQ-4, R5/R6)
        ----------------------------------------------------------------------------
        **OQ-4 resolution — which ``model_profile`` roles need schema-constrained
        (forced tool-call) output vs free prose** (``config/model_profiles.yaml``
        ``allowed_for`` roles, grouped by tier):

        * **Schema-constrained → forced tool-call** (the record must conform to a
          typed artifact schema): every role of the *extract* and *verify* tiers —
          ``rf_extract_free`` (``source_carding``, ``simple_extraction``,
          ``tagging``, ``dedupe``), ``rf_extract_cheap`` (``source_carding``,
          ``extraction_cards``, ``initial_claim_mapping``), and
          ``rf_verify_balanced`` (``claim_audit``, ``contradiction_review``,
          ``council_review``). These emit source cards / extraction cards / claim
          maps / verdicts / tag sets that are deserialised into typed records, so
          they require a strict JSON shape.
        * **Free prose → no schema**: the *synthesize* tier —
          ``rf_synthesize_deep`` (``final_report``, ``executive_synthesis``,
          ``deep_literature_synthesis``). These produce natural-language report
          text; forcing a tool-call would be counter-productive.

        For the schema-constrained roles the structured shape is obtained by
        passing ``tools`` + ``tool_choice`` (OpenAI-compatible forced function
        call) straight through to ``litellm.completion``. This method **never**
        sets ``response_format`` and there is **no** ``output_config`` /
        ``output_config.format`` key on the wire: ICA's OpenAI-compatible chat
        endpoint honours forced tool-calls but not JSON-mode ``response_format``
        (R5/R6), and ``output_config.format`` is an ICA-native field that is
        dropped on the OpenAI-compatible path. Callers that need a schema pass
        ``tools``/``tool_choice``; this adapter forwards them verbatim and adds
        no alternate structured-output channel.

        Governance gate (LLM-004/LLM-005, OQ-2 resolution)
        ----------------------------------------------------
        **OQ-2 resolution**: neither existing ``guard_check()`` call-site guards
        this method. ``api/routers/agent_jobs.py::launch_job`` gates *subprocess*
        agent-job spawns (GPT Researcher/PaperQA2/etc.) and
        ``services/writeback.py``'s governed writeback gates *outbound* writes
        (MeatyWiki/IntentTree/ARC) — both are a disjoint surface from a raw
        in-process model completion, and neither call-site knows this method
        exists. So the guard is added **inside** ``complete()`` itself, run
        *before* the dark/live gate above — a completion cannot reach the
        ``can_fire`` check, let alone fire live, without first passing
        :func:`~research_foundry.services.governance.guard_check`.

        The check builds a :class:`~research_foundry.services.governance.GuardContext`
        from the caller-supplied ``sensitivity``/``profile``/``run_id`` and the
        *routed* ``provider`` (not a hardcoded ``"ica"``), so a future non-ICA
        routing decision is evaluated honestly too. Rule
        ``no_work_sensitive_to_unapproved_provider`` (severity ``block``,
        governance.py ~L283-297) fires whenever ``sensitivity`` is
        ``work_sensitive``/``client_sensitive`` and the routed provider is not
        in ``approved_work_providers`` — which **defaults to ``[]``** (D7) and
        is *not* relaxed by this change. Personal/public sensitivities are
        never matched by that rule, so they are **not** gated by this check
        (they may still degrade/fire per the dark gate above, on their own
        merits). A blocked guard returns ``degraded=True,
        reason="governance_blocked"`` with the fired rule ids — never a live
        call, regardless of key/availability state.
        """

        env = env if env is not None else dict(os.environ)
        decision = self.route(model_profile, paths=paths, env=env)
        provider = decision.get("provider")
        model = decision.get("model")
        api_base = decision.get("api_base")

        # ICA key comes ONLY from RF_LLM_API_KEY, resolved via the provider→key
        # map — the completion path never names ANTHROPIC_API_KEY/OPENAI_API_KEY.
        ica_key_var = _PROVIDER_KEYS["ica"]
        ica_key = env.get(ica_key_var) if ica_key_var else None

        base = {
            "model_profile": model_profile,
            "provider": provider,
            "model": model,
            "api_base": api_base,
            "text": None,
            "finish_reason": None,
            "cost_usd": 0.0,
            "tokens": 0,
        }

        # --- Governance gate (LLM-004/LLM-005) — strictly upstream of the dark/
        # live gate below. See the "Governance gate" docstring section above for
        # the OQ-2 resolution. Evaluated unconditionally, regardless of
        # available()/key state, so a work-sensitive completion is blocked even
        # if litellm were installed and a key present.
        guard_result = guard_check(
            GuardContext(
                profile=profile,
                run_id=run_id,
                sensitivity=sensitivity,
                model_provider=provider,
            ),
            paths=paths,
        )
        if not guard_result.passed:
            return {
                **base,
                "degraded": True,
                "reason": "governance_blocked",
                "violations": [v.rule_id for v in guard_result.violations],
            }

        can_fire = provider == "ica" and self.available() and bool(ica_key)
        if not can_fire:
            if provider != "ica":
                reason = "non_ica_provider_completion_unsupported"
            elif not self.available():
                reason = "litellm_unavailable"
            else:
                reason = "no_ica_key"
            return {**base, "degraded": True, "reason": reason}

        # --- Live path (dark until Gate #2 + key; never reached offline) -------
        try:
            import litellm  # noqa: PLC0415 — optional dep, only importable in real mode

            wire_model = f"openai/{model}"
            call_kwargs: dict[str, Any] = {
                "model": wire_model,
                "api_base": api_base,
                "api_key": ica_key,
                "messages": messages or [{"role": "user", "content": prompt}],
            }
            if temperature is None:
                temperature = decision.get("temperature")
            if max_tokens is None:
                max_tokens = decision.get("max_tokens")
            if temperature is not None:
                call_kwargs["temperature"] = temperature
            if max_tokens is not None:
                call_kwargs["max_tokens"] = max_tokens
            # Schema-constrained roles (OQ-4) force structured output via an
            # OpenAI-compatible tool-call — NEVER ``response_format`` /
            # ``output_config`` (R5/R6). We forward the caller's tools verbatim
            # and add no alternate structured-output channel here.
            if tools is not None:
                call_kwargs["tools"] = tools
            if tool_choice is not None:
                call_kwargs["tool_choice"] = tool_choice

            response = litellm.completion(**call_kwargs)
            choice = response.choices[0]
            text = getattr(choice.message, "content", None)
            usage = getattr(response, "usage", None)
            tokens = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
            cost = float(
                getattr(response, "_hidden_params", {}).get("response_cost", 0.0) or 0.0
            )
            return {
                **base,
                "text": text,
                "finish_reason": getattr(choice, "finish_reason", None),
                "tokens": tokens,
                "cost_usd": cost,
                "degraded": False,
                "reason": "live_completion",
            }
        except Exception as exc:  # noqa: BLE001 — degrade, never crash the pipeline
            from research_foundry.services.governance import redact_payload  # noqa: PLC0415

            safe = redact_payload(str(exc))
            return {
                **base,
                "degraded": True,
                "reason": "live_completion_failed",
                "error": safe,
            }

    def run(self, request: dict[str, Any]) -> AdapterResult:
        model_profile = str(request.get("model_profile") or "rf_extract_cheap")
        paths = request.get("paths")
        decision = self.route(
            model_profile,
            paths=paths if isinstance(paths, FoundryPaths) else None,
        )
        degraded = bool(decision.get("degraded", True))
        notes = [
            f"routed {model_profile} -> {decision.get('provider')}:{decision.get('model')}"
        ]
        if degraded:
            notes.append("litellm unavailable or no provider key: returned preferred fallback")
        return AdapterResult(
            adapter=self.id,
            degraded=degraded,
            artifacts={"routing_decision": _yaml(decision)},
            notes=notes,
        )


def _yaml(obj: dict[str, Any]) -> str:
    from ..yamlio import dumps_yaml

    return dumps_yaml(obj)


register(LiteLLMRouterAdapter())

__all__ = ["LiteLLMRouterAdapter"]
