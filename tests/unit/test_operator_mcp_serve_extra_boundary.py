"""Regression test for NEW-23 (Operator MCP serve-extra import boundary).

`research_foundry.services.operator_mcp_policy` declares a "local-stdio"
topology that must import -- and actually resolve an identity -- in a BASE
install (``pip install research-foundry``, WITHOUT the optional ``[serve]``
extra, i.e. no fastapi / uvicorn / starlette).

Two failure modes are covered here:

1. **Import-time**: the module-level import chain
   (``operator_mcp_policy`` -> ``services.audit_service``/``governance`` ->
   ``api.auth.provider``/``api.auth.scope`` -> the ``api`` package's
   ``__init__.py``) used to require fastapi/uvicorn eagerly, and
   ``api.auth.provider`` itself imported ``starlette.requests.Request`` at
   module level.

2. **Runtime (the layer *below* the import fix)**:
   ``resolve_operator_identity()`` lazily imports ``AuthIdentity`` and
   *constructs* it at call time. A fix that only defers the import (e.g.
   ``TYPE_CHECKING``) would let the module import cleanly but still crash
   the first time an identity is actually resolved. This test exercises
   that construction path, not just the import.

Both checks run in a **subprocess** with fastapi/uvicorn/starlette blocked
via a ``sys.meta_path`` finder, so already-imported modules in the pytest
process (which does import fastapi elsewhere in the suite) cannot mask a
regression.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

_BLOCKER_PREAMBLE = textwrap.dedent(
    """
    import sys

    _BLOCKED = {"fastapi", "uvicorn", "starlette"}

    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in _BLOCKED:
                raise ImportError(f"BLOCKED (test boundary): {name}")
            return None

    sys.meta_path.insert(0, _Blocker())
    """
)


def _run_blocked(script: str) -> subprocess.CompletedProcess[str]:
    """Run `script` in a fresh subprocess with fastapi/uvicorn/starlette blocked."""

    src_root = str(Path(__file__).resolve().parents[2] / "src")
    full_script = _BLOCKER_PREAMBLE + "\n" + script
    return subprocess.run(
        [sys.executable, "-c", full_script],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": src_root},
    )


def test_operator_mcp_policy_imports_without_serve_extra() -> None:
    """(a) Module-level import chain must not require fastapi/uvicorn/starlette."""

    result = _run_blocked(
        textwrap.dedent(
            """
            import importlib

            importlib.import_module("research_foundry.services.operator_mcp_policy")
            print("IMPORT_OK")
            """
        )
    )
    assert result.returncode == 0, (
        f"import raised under the serve-extra blocker.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "IMPORT_OK" in result.stdout


def test_resolve_operator_identity_constructs_authidentity_without_serve_extra() -> None:
    """(b) Runtime AuthIdentity construction must not require the serve extra.

    This is the layer *below* the import fix: `resolve_operator_identity`
    lazily imports and constructs `AuthIdentity` at call time. A fix that
    only makes the import lazy (e.g. TYPE_CHECKING) would pass test (a)
    above but still raise ImportError here.
    """

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "fdry"
        root.mkdir(parents=True)
        (root / "foundry.yaml").write_text(
            textwrap.dedent(
                """
                foundry:
                  operator_mcp:
                    identity:
                      user_id: alice
                      workspace_id: ws-mine
                      roles:
                        - owner
                """
            ),
            encoding="utf-8",
        )

        script = textwrap.dedent(
            f"""
            from pathlib import Path
            from research_foundry.paths import FoundryPaths
            from research_foundry.services import operator_mcp_policy as policy

            paths = FoundryPaths(root=Path({str(root)!r}))
            identity = policy.resolve_operator_identity(paths)
            assert identity is not None, "expected a populated AuthIdentity, got None"
            assert identity.user_id == "alice", identity
            assert identity.workspace_id == "ws-mine", identity
            assert identity.roles == ("owner",), identity
            print("IDENTITY_OK")
            """
        )
        result = _run_blocked(script)
        assert result.returncode == 0, (
            f"resolve_operator_identity() raised under the serve-extra blocker.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
        assert "IDENTITY_OK" in result.stdout
