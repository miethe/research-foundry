"""OpenAI Agents SDK adapter — orchestration (spec §13.3).

Promoted from a stub to a real-mode implementation in P4.6.

The real-mode path is reachable when:

* the ``openai_agents`` third-party library is importable
  (``self.available()`` returns ``True``), **or**
* a mock client is injected at construction time via the ``sdk_client``
  constructor kwarg.

Mode-D Gate #2 (real API keys / live provider network calls) is NOT yet
approved.  The real-mode path therefore requires an injected client for any
meaningful test.  The degraded path is preserved intact so the pipeline always
completes deterministically when neither condition is met.

**Key constraint (Mode-D Gate #2)**: This module MUST NOT read any environment
variable named ``OPENAI_API_KEY`` or any other real credential.  All test
doubles MUST use stub bytes / mock clients with no live network access.

**Tool-call redaction requirement**: Any tool_call result dict returned by the
SDK through the ``run_agent`` call MUST be passed through
:func:`~research_foundry.services.governance.redact_payload` before any
persistence or return.  This guards against prompt-injection exfiltration
(SPIKE finding G3).
"""

from __future__ import annotations

from typing import Any

from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths

from .base import AdapterResult, BaseAdapter, register

# ---------------------------------------------------------------------------
# Optional real SDK import — guarded so the module loads without it.
# ---------------------------------------------------------------------------

try:
    import openai_agents as _real_sdk  # type: ignore[import]
    _SDK_MODULE_AVAILABLE = True
except ImportError:
    _real_sdk = None  # type: ignore[assignment]
    _SDK_MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class OpenAIAgentsAdapter(BaseAdapter):
    """Wraps the OpenAI Agents SDK for structured orchestration.

    Parameters
    ----------
    sdk_client:
        An optional pre-built (or mock) SDK client instance.  When supplied,
        real mode is available regardless of whether the third-party
        ``openai_agents`` package is installed.

        In tests pass an instance of :class:`MockOpenAIAgentsClient` (or any
        duck-typed object with a ``run_agent(job_brief: dict) -> dict`` method):

        .. code-block:: python

            adapter = OpenAIAgentsAdapter(sdk_client=MockOpenAIAgentsClient())
            result = adapter.run({"intent": "summarise X"})
            assert not result.degraded

        **Constraint**: MUST NOT be a live client holding real API credentials
        until Mode-D Gate #2 is approved.
    """

    id = "openai_agents"
    requires: tuple[str, ...] = ("openai_agents",)

    def __init__(
        self,
        *,
        sdk_client: Any | None = None,
        config: FoundryConfig | None = None,
    ) -> None:
        self._sdk_client = sdk_client
        # Cached config — populated lazily if not injected at construction time.
        self._config: FoundryConfig | None = config

    # ------------------------------------------------------------------
    # Protocol impl
    # ------------------------------------------------------------------

    def _ensure_config(self) -> FoundryConfig:
        """Return cached :class:`FoundryConfig`, loading it lazily on first call.

        Loads once and caches on ``self._config`` so governance.yaml patterns
        are resolved before any redact_payload call without per-call I/O.
        """
        if self._config is None:
            self._config = FoundryConfig(paths=FoundryPaths.discover())
        return self._config

    def available(self) -> bool:
        """True when the real SDK is importable OR a mock client is injected."""
        return self._sdk_client is not None or super().available()

    def run(self, request: dict[str, Any]) -> AdapterResult:
        """Dispatch the request in real mode if available, else degrade."""
        if not self.available():
            return self._degraded(request)
        client = self._sdk_client or self._make_sdk_client()
        return self._run_real(request, client)

    # ------------------------------------------------------------------
    # Real-mode path
    # ------------------------------------------------------------------

    def _run_real(self, request: dict[str, Any], client: Any) -> AdapterResult:
        """Invoke *client*.run_agent (or run_agent_with_guardrails), redact, normalise.

        When the client exposes a ``run_agent_with_guardrails`` method **and** the
        request carries a ``policy_snapshot`` with non-empty ``allowed_tools``, the
        guardrails path is taken.  Any ``blocked_events`` in the result are included
        in the redacted payload so they are visible in the adapter result without
        leaking secrets (SPIKE finding G3).
        """
        from research_foundry.services.governance import redact_payload  # noqa: PLC0415

        policy_snapshot: dict[str, Any] = dict(request.get("policy_snapshot") or {})
        job_brief: dict[str, Any] = {
            "job_id": str(request.get("job_id") or ""),
            "model_profile": str(request.get("model_profile") or "rf_synthesize_deep"),
            "allowed_tools": list(request.get("allowed_tools") or []),
            "intent": str(request.get("intent") or request.get("prompt") or ""),
            "policy_snapshot": policy_snapshot,
        }

        # Prefer the guardrails path when available and policy_snapshot names tools.
        use_guardrails = (
            hasattr(client, "run_agent_with_guardrails")
            and bool(policy_snapshot.get("allowed_tools"))
        )

        try:
            if use_guardrails:
                sdk_result: dict[str, Any] = client.run_agent_with_guardrails(
                    job_brief,
                    allowed_tools=list(policy_snapshot.get("allowed_tools") or []),
                    data_scopes=list(policy_snapshot.get("data_scopes") or []),
                )
            else:
                sdk_result = client.run_agent(job_brief)
        except Exception as exc:  # noqa: BLE001
            method = "run_agent_with_guardrails" if use_guardrails else "run_agent"
            # Redact the exception text before it enters AdapterResult.notes —
            # SDK exceptions can embed the API key in their message (e.g.
            # "Invalid API key: sk-...").  Mirror the run_job_tool pattern.
            safe_exc = redact_payload(str(exc), config=self._ensure_config())
            return self._degraded(request, note=f"sdk_client.{method} raised: {safe_exc}")

        # Redact tool-call payloads (and any blocked_events) before persistence
        # (SPIKE finding G3). Pass resolved config so custom secret_patterns apply.
        sdk_result = redact_payload(sdk_result, config=self._ensure_config())
        return AdapterResult(
            adapter=self.id,
            degraded=False,
            artifacts={"sdk_result": _dumps(sdk_result)},
            notes=["openai_agents real-mode execution"],
        )

    def _make_sdk_client(self) -> Any:
        """Instantiate the real SDK client when the module is importable.

        Concrete construction (auth, base URL, etc.) requires Mode-D Gate #2
        approval.  Tests should always inject ``sdk_client`` instead of
        exercising this path.

        Raises
        ------
        RuntimeError
            If the SDK module failed to import (should not happen when
            ``self.available()`` is True via the module path).
        """
        if _real_sdk is None:
            raise RuntimeError(
                "openai_agents not installed — cannot build real client; "
                "inject an sdk_client or install the SDK package."
            )
        # NOTE: Until Gate #2 is approved, no credentials are configured here.
        # The returned client will fail at the run_agent call without real
        # configuration; tests must inject MockOpenAIAgentsClient instead.
        return _real_sdk.Client()

    # ------------------------------------------------------------------
    # Degraded path — preserved intact from MVP (do NOT remove)
    # ------------------------------------------------------------------

    def _degraded(
        self, request: dict[str, Any], *, note: str | None = None
    ) -> AdapterResult:
        """Return a deterministic, clearly-labelled stub result (degraded mode)."""
        prompt = str(request.get("prompt") or request.get("intent") or "").strip()
        model_profile = str(request.get("model_profile") or "rf_synthesize_deep")
        allowed_tools = list(request.get("allowed_tools") or [])
        stub: dict[str, Any] = {
            "echo_intent": prompt[:280],
            "model_profile": model_profile,
            "allowed_tools": allowed_tools,
            "structured_artifact": None,
            "session_trace": [],
        }
        notes = ["openai_agents unavailable: returning deterministic orchestration stub"]
        if note:
            notes.append(note)
        return AdapterResult(
            adapter=self.id,
            degraded=True,
            artifacts={"orchestration_stub": _dumps(stub)},
            notes=notes,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dumps(obj: dict[str, Any]) -> str:
    """Stable YAML rendering of a payload (kept local to avoid top-level imports)."""
    from ..yamlio import dumps_yaml  # noqa: PLC0415

    return dumps_yaml(obj)


# ---------------------------------------------------------------------------
# Test double — self-contained, no network, no real keys
# ---------------------------------------------------------------------------


class MockOpenAIAgentsClient:
    """Drop-in test double for the real ``openai_agents.Client``.

    Has no external dependencies, makes no network calls, and holds no real
    credentials.  Use in tests:

    .. code-block:: python

        adapter = OpenAIAgentsAdapter(sdk_client=MockOpenAIAgentsClient())
        result = adapter.run({"intent": "summarise X"})
        assert not result.degraded

    The returned payload mirrors the shape ``_run_real`` expects so integration
    tests can exercise the full real-mode code path offline.

    The ``check_tool_call`` method provides a guardrail/HITL stub: it returns
    ``True`` for tools in ``allowed_tools`` and ``False`` otherwise, giving
    ADP-6.2 tests a concrete hook to exercise.
    """

    def __init__(
        self,
        *,
        allowed_tools: list[str] | None = None,
    ) -> None:
        self._allowed_tools: list[str] = list(allowed_tools or [])

    def run_agent(self, job_brief: dict[str, Any]) -> dict[str, Any]:
        """Echo the job brief back as a completed mock result."""
        return {
            "status": "completed",
            "job_id": job_brief.get("job_id", ""),
            "output": f"mock-result: {str(job_brief.get('intent', ''))[:120]}",
            "tool_calls": [],
            "cost_usd": 0.0,
            "tokens": 0,
        }

    def check_tool_call(self, tool_name: str, payload: dict[str, Any]) -> bool:
        """Guardrail/HITL stub: allow tool calls only for declared allowed tools.

        Parameters
        ----------
        tool_name:
            The name of the tool being invoked.
        payload:
            The tool-call payload dict (must have already been redacted before
            reaching this guard).

        Returns
        -------
        bool
            ``True`` if *tool_name* is in the ``allowed_tools`` list supplied
            at construction time, ``False`` otherwise.
        """
        return tool_name in self._allowed_tools

    def run_agent_with_guardrails(
        self,
        job_brief: dict[str, Any],
        allowed_tools: list[str],
        data_scopes: list[str],
    ) -> dict[str, Any]:
        """Run agent with SDK-native guardrails/HITL stub.

        Simulates a set of tool calls (taken from *job_brief* if it names tools,
        otherwise from a fixed representative probe list).  Each tool is passed
        through :meth:`check_tool_call`; any call that returns ``False`` is
        recorded as a ``tool_blocked`` event.

        Parameters
        ----------
        job_brief:
            The job brief dict forwarded from :class:`OpenAIAgentsAdapter`.
            ``job_brief["allowed_tools"]`` is used as the probe list when present
            and non-empty; otherwise the fixed probe list
            ``["search", "fetch", "blocked_tool"]`` is used.
        allowed_tools:
            The policy-level allowed tool list (from ``policy_snapshot``).
            Not used directly here — guardrail decisions are made against
            ``self._allowed_tools`` as set at construction time.
        data_scopes:
            Declared data scopes from the policy snapshot (reserved for future
            scope-based guardrail logic; currently unused in the stub).

        Returns
        -------
        dict
            A result dict with keys:

            * ``"result"`` — ``"mock-guardrails-result"``
            * ``"job_id"`` — echoed from *job_brief*
            * ``"blocked_events"`` — list of ``{"type": "tool_blocked",
              "tool": <name>, "reason": "not in allowed_tools"}`` dicts, one
              per blocked tool (empty list when no tools were blocked).
        """
        # Build the probe list: prefer tools named in the brief, fall back to
        # a fixed representative set that includes a guaranteed-blocked entry.
        probe_tools: list[str] = list(job_brief.get("allowed_tools") or []) or [
            "search",
            "fetch",
            "blocked_tool",
        ]

        blocked_events: list[dict[str, Any]] = []
        for tool_name in probe_tools:
            # Payload is empty here — real payloads must be pre-redacted before
            # reaching the guardrail (SPIKE finding G3).
            if not self.check_tool_call(tool_name, {}):
                blocked_events.append(
                    {
                        "type": "tool_blocked",
                        "tool": tool_name,
                        "reason": "not in allowed_tools",
                    }
                )

        return {
            "result": "mock-guardrails-result",
            "job_id": str(job_brief.get("job_id") or ""),
            "blocked_events": blocked_events,
        }


# ---------------------------------------------------------------------------
# Module-level registration
# ---------------------------------------------------------------------------

register(OpenAIAgentsAdapter())

__all__ = ["OpenAIAgentsAdapter", "MockOpenAIAgentsClient"]
