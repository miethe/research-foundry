"""Claude Agent SDK adapter — orchestration (spec §13.3).

Real mode (when ``claude_agent_sdk`` is importable and configured) would run a
Claude subagent to produce a structured artifact + session trace. The default
environment has no SDK installed and no API keys, so this adapter degrades to a
deterministic stub that echoes the request intent. The stub is never treated as
authoritative — downstream stages still route its output through the claim
ledger and verifier.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, BaseAdapter, register


class ClaudeAgentSDKAdapter(BaseAdapter):
    """Wraps the Claude Agent SDK for structured orchestration."""

    id = "claude_agent_sdk"
    requires = ("claude_agent_sdk",)

    def run(self, request: dict[str, Any]) -> AdapterResult:
        if not self.available():
            return self._degraded(request)
        # Real mode is intentionally not implemented in the MVP service layer.
        # It would require live SDK + credentials; we degrade to keep the
        # deterministic default path honest.
        return self._degraded(request, note="SDK present but real mode is opt-in")

    def _degraded(self, request: dict[str, Any], *, note: str | None = None) -> AdapterResult:
        prompt = str(request.get("prompt") or request.get("intent") or "").strip()
        model_profile = str(request.get("model_profile") or "rf_synthesize_deep")
        allowed_tools = list(request.get("allowed_tools") or [])
        stub = {
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
            artifacts={"orchestration_stub": dumps(stub)},
            notes=notes,
        )


def dumps(obj: dict[str, Any]) -> str:
    """Stable YAML rendering of a stub payload (kept local to avoid imports)."""

    from ..yamlio import dumps_yaml

    return dumps_yaml(obj)


register(ClaudeAgentSDKAdapter())

__all__ = ["ClaudeAgentSDKAdapter"]
