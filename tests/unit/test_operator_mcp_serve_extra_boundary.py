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

import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _serve_extra_package_names() -> set[str]:
    """NB-6 (round 5, fixed): derive the serve-extra blocklist from
    `pyproject.toml`'s own `[project.optional-dependencies].serve` list
    rather than a hard-coded, driftable duplicate -- if a package is ever
    added to (or removed from) that extra, this test boundary now follows
    it automatically instead of silently going stale.

    `starlette` is added explicitly, unconditionally: it is fastapi's
    TRANSITIVE dependency, never `research-foundry`'s own declared `serve`
    extra, so it cannot be derived from `pyproject.toml` at all -- this
    comment is the record of why it stays hard-coded."""

    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - matches this repo's documented
        import tomli as tomllib  # type: ignore[no-redef]  # < 3.11 fallback convention

    with (_REPO_ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    serve_deps = data["project"]["optional-dependencies"]["serve"]
    names = {re.split(r"[\[<>=!~; ]", dep, maxsplit=1)[0].strip() for dep in serve_deps}
    return names | {"starlette"}


_BLOCKED: set[str] = _serve_extra_package_names()


def _blocker_preamble(blocked: set[str]) -> str:
    return textwrap.dedent(
        f"""
        import sys

        _BLOCKED = {blocked!r}

        class _Blocker:
            def find_spec(self, name, path=None, target=None):
                if name.split(".")[0] in _BLOCKED:
                    raise ImportError(f"BLOCKED (test boundary): {{name}}")
                return None

        sys.meta_path.insert(0, _Blocker())
        """
    )


def _run_blocked(script: str, blocked: set[str] = _BLOCKED) -> subprocess.CompletedProcess[str]:
    """Run `script` in a fresh subprocess with the serve-extra packages blocked."""

    src_root = str(_REPO_ROOT / "src")
    full_script = _blocker_preamble(blocked) + "\n" + script
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


def test_evaluate_policy_and_mint_confirmation_run_without_serve_extra() -> None:
    """NB-6 (round 5, fixed): tests (a)/(b) above only exercise IMPORT and
    identity CONSTRUCTION -- neither runs an actual POLICY STAGE under the
    blocker. `evaluate_policy` (capability -> rbac -> audit_health -> guard
    -> preflight) additionally touches `governance.guard_check` and
    `audit_service.health_check`, and `mint_confirmation` re-derives
    identity a second time and computes a canonical digest -- if either
    accidentally imported something serve-gated on this path, tests (a)/(b)
    alone would not catch it. Builds the same substrate
    `tests/conftest.py::tmp_foundry` builds (schemas/config/templates copied
    from the distribution root), since this runs in a bare subprocess with
    no access to that fixture."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "fdry"
        script = textwrap.dedent(
            f"""
            import shutil
            from pathlib import Path

            from research_foundry.paths import FoundryPaths, distribution_root
            from research_foundry.yamlio import dump_yaml, load_yaml
            from research_foundry.services import operator_mcp_policy as policy

            root = Path({str(root)!r})
            root.mkdir(parents=True)
            dist = distribution_root()
            for sub in ("schemas", "config", "templates"):
                src = dist / sub
                if src.exists():
                    shutil.copytree(src, root / sub)
            shutil.copyfile(dist / "foundry.yaml", root / "foundry.yaml")
            for d in ("inbox/raw_ideas", "runs", "registries"):
                (root / d).mkdir(parents=True, exist_ok=True)

            data = load_yaml(root / "foundry.yaml") or {{}}
            data.setdefault("foundry", {{}})
            data["foundry"]["operator_mcp"] = {{
                "identity": {{"user_id": "alice", "workspace_id": "ws-mine", "roles": ["owner"]}}
            }}
            dump_yaml(data, root / "foundry.yaml")

            paths = FoundryPaths(root=root)
            ctx = policy.PolicyContext.for_configured_operator(
                operation_kind="run.plan",
                idempotency_key="idem-1",
                effective_sensitivity="public",
                sensitivity_ceiling="client_sensitive",
                paths=paths,
            )
            assert ctx.identity is not None, "expected a populated identity, got None"

            decision = policy.evaluate_policy(ctx, paths=paths)
            assert decision.allowed, decision

            issued = policy.mint_confirmation(ctx, paths=paths)
            assert issued.record["status"] == "issued"
            print("POLICY_OK")
            """
        )
        result = _run_blocked(script)
        assert result.returncode == 0, (
            f"a policy stage raised under the serve-extra blocker.\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )
        assert "POLICY_OK" in result.stdout


def test_planning_module_imports_without_serve_extra() -> None:
    """P3-F2 -- `research_foundry.services.planning` must import cleanly
    without the serve extra (P3 implementer contract). The FULL import
    closure required THREE fixes, not one -- "fix the layer below"
    (P1 defect-class checklist item 2), discovered iteratively:

    1. `assertion_catalog.py:45` -- the ORIGINALLY-traced blocker
       (`planning.py:47 -> assertion_catalog.py:45 -> api/__init__.py:21`,
       "fastapi and uvicorn are required").
    2. `catalog_retrieval.py:24` -- a SECOND, independent module-level
       `from ..api.auth.provider import AuthIdentity`, imported by BOTH
       `planning.py:49` directly and by (3) below. Invisible in the
       original trace because Python's import system stops at the FIRST
       failing import -- this one was masked by (1) until (1) was fixed.
    3. `research_evidence_planning.py:122` -- a THIRD, independent
       module-level `from ..api.auth.provider import AuthIdentity`,
       imported by `planning.py:50`. Also masked by (1)/(2) until both
       were fixed.

    All three now import `AuthIdentity` from `..auth_identity` (the
    deliberately import-clean canonical module `api/auth/provider.py`
    itself re-exports the SAME class object from -- never a
    `TYPE_CHECKING`-only guard, so each still works at RUNTIME, not merely
    at import time). Verified by walking the closure to a fixed point: after
    fixing all three, `governance.py`/`backlog_metadata.py`/
    `assertion_reuse.py`/`sensitivity.py` (the remaining modules `planning`,
    `catalog_retrieval`, and `research_evidence_planning` import at module
    level) carry NO `..api.auth.*` reference of their own -- there is no
    fourth link.

    Five FURTHER module-level `..api.auth.*` imports exist elsewhere in
    `services/` (`assertion_impact.py`, `builder_service.py`,
    `catalog_service.py`, `knowledge_access.py`, `verification.py`) -- NOT
    in `planning`'s import closure (confirmed by this test actually
    importing `planning` successfully without touching any of them), out
    of scope, not touched. `builder_service.py`/`catalog_service.py`/
    `knowledge_access.py` also import `..api.auth.scope` helpers
    (`require_workspace_scope`/`resolve_workspace_isolation_active`) at
    module level, which have no import-clean twin -- correctly left alone.

    Carries its own CONTROL ASSERTION (P3 implementer contract requirement):
    a `sys.meta_path` blocker built on the deprecated `find_module` API is
    silently inert on Python 3.12 (the import protocol dropped
    `find_module`) and would make this whole test a meaningless pass. The
    script below asserts `import fastapi` itself raises INSIDE the harness
    BEFORE asserting the real import under test succeeds -- proving the
    `find_spec`-based `_Blocker` this file already uses (see
    `_blocker_preamble` above) actually bites.
    """

    result = _run_blocked(
        textwrap.dedent(
            """
            import importlib

            # Control assertion: the blocker must actually block, or this
            # whole test is a meaningless pass (see docstring).
            try:
                import fastapi  # noqa: F401
            except ImportError:
                pass
            else:
                raise AssertionError("control failed: fastapi import was NOT blocked")

            importlib.import_module("research_foundry.services.planning")
            print("PLANNING_IMPORT_OK")
            """
        )
    )
    assert result.returncode == 0, (
        f"research_foundry.services.planning import raised under the serve-extra "
        f"blocker.\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "PLANNING_IMPORT_OK" in result.stdout


def test_operator_mcp_adapters_job_lifecycle_imports_without_serve_extra() -> None:
    """The new `job.status`/`job.cancel`/`job.resume` adapter module
    (OPM-3.4) must also import cleanly without the serve extra -- every
    module it imports (`operator_attempt_adapter`, `operator_cancel_resume_
    service`, `operator_operation_service`, `operator_receipt_service`,
    `operator_mcp_policy`) already satisfies that boundary; this proves the
    NEW module adds no regression."""

    result = _run_blocked(
        textwrap.dedent(
            """
            import importlib

            importlib.import_module(
                "research_foundry.services.operator_mcp_adapters.job_lifecycle"
            )
            print("JOB_LIFECYCLE_IMPORT_OK")
            """
        )
    )
    assert result.returncode == 0, (
        f"job_lifecycle import raised under the serve-extra blocker.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "JOB_LIFECYCLE_IMPORT_OK" in result.stdout
