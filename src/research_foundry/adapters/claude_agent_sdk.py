"""Claude Agent SDK adapter — orchestration (spec §13.3).

Promoted from the MVP echo-stub to a real-mode implementation in P4.3.

The real-mode path is reachable when:

* the ``claude_agent_sdk`` third-party library is importable
  (``self.available()`` returns ``True``), **or**
* a mock client is injected at construction time via the ``sdk_client``
  constructor kwarg.

Mode-D Gate #2 (real API keys / live provider network calls) is NOT yet
approved.  The real-mode path therefore requires an injected client for any
meaningful test.  The degraded path is preserved intact so the pipeline always
completes deterministically when neither condition is met.

**Key constraint (Mode-D Gate #2)**: This module MUST NOT read any environment
variable named ``ANTHROPIC_API_KEY`` or any other real credential.  All test
doubles MUST use stub bytes / mock clients with no live network access.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, BaseAdapter, register

# ---------------------------------------------------------------------------
# Optional real SDK import — guarded so the module loads without it.
# ---------------------------------------------------------------------------

try:
    import claude_agent_sdk as _real_sdk  # type: ignore[import]
    _SDK_MODULE_AVAILABLE = True
except ImportError:
    _real_sdk = None  # type: ignore[assignment]
    _SDK_MODULE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class ClaudeAgentSDKAdapter(BaseAdapter):
    """Wraps the Claude Agent SDK for structured orchestration.

    Parameters
    ----------
    sdk_client:
        An optional pre-built (or mock) SDK client instance.  When supplied,
        real mode is available regardless of whether the third-party
        ``claude_agent_sdk`` package is installed.

        In tests pass an instance of :class:`MockSDKClient` (or any duck-typed
        object with a ``run_agent(job_brief: dict) -> dict`` method):

        .. code-block:: python

            adapter = ClaudeAgentSDKAdapter(sdk_client=MockSDKClient())
            result = adapter.run({"intent": "summarise X"})
            assert not result.degraded

        **Constraint**: MUST NOT be a live client holding real API credentials
        until Mode-D Gate #2 is approved.
    """

    id = "claude_agent_sdk"
    requires: tuple[str, ...] = ("claude_agent_sdk",)

    def __init__(self, *, sdk_client: Any | None = None) -> None:
        self._sdk_client = sdk_client

    # ------------------------------------------------------------------
    # Protocol impl
    # ------------------------------------------------------------------

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
        """Invoke *client*.run_agent and normalise the response into an AdapterResult."""
        job_brief: dict[str, Any] = {
            "job_id": str(request.get("job_id") or ""),
            "model_profile": str(request.get("model_profile") or "rf_synthesize_deep"),
            "allowed_tools": list(request.get("allowed_tools") or []),
            "intent": str(request.get("intent") or request.get("prompt") or ""),
            "policy_snapshot": dict(request.get("policy_snapshot") or {}),
        }
        try:
            sdk_result: dict[str, Any] = client.run_agent(job_brief)
        except Exception as exc:  # noqa: BLE001
            return self._degraded(request, note=f"sdk_client.run_agent raised: {exc}")
        return AdapterResult(
            adapter=self.id,
            degraded=False,
            artifacts={"sdk_result": _dumps(sdk_result)},
            notes=["claude_agent_sdk real-mode execution"],
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
                "claude_agent_sdk not installed — cannot build real client; "
                "inject an sdk_client or install the SDK package."
            )
        # NOTE: Until Gate #2 is approved, no credentials are configured here.
        # The returned client will fail at the run_agent call without real
        # configuration; tests must inject MockSDKClient instead.
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
        notes = ["claude_agent_sdk unavailable: returning deterministic orchestration stub"]
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


class MockSDKClient:
    """Drop-in test double for the real ``claude_agent_sdk.Client``.

    Has no external dependencies, makes no network calls, and holds no real
    credentials.  Use in tests:

    .. code-block:: python

        adapter = ClaudeAgentSDKAdapter(sdk_client=MockSDKClient())
        result = adapter.run({"intent": "summarise X"})
        assert not result.degraded

    The returned payload mirrors the shape ``_run_real`` expects so integration
    tests can exercise the full real-mode code path offline.
    """

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


# ---------------------------------------------------------------------------
# Module-level registration
# ---------------------------------------------------------------------------

register(ClaudeAgentSDKAdapter())

__all__ = ["ClaudeAgentSDKAdapter", "MockSDKClient"]
