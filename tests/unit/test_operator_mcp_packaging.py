"""Packaging/entrypoint contract tests for `rf-operator-mcp` (M2 Leg C,
OPM-5.5).

Mirrors `test_operator_mcp_serve_extra_boundary.py`'s own child-interpreter
technique: every check that must observe state that a WARM pytest process
cannot reliably provide (the `mcp` SDK genuinely unimportable, thread/socket
side effects at import time) runs in a fresh subprocess via
`sys.executable -c <script>`, with `mcp` blocked by a `sys.meta_path` finder
-- never `builtins.__import__` patching in-process, which cannot un-import
an `mcp` module this repo's own `importorskip("mcp")`-gated integration
tests have already imported elsewhere in the same pytest run (confirmed:
this venv DOES have the `mcp` SDK installed).

Distinct from `tests/test_operator_mcp_offline_import.py` (Leg B): that file
proves the SAME contract in-process via a `builtins.__import__` monkeypatch;
this file proves it via the strongest available technique (a genuinely
fresh interpreter) and adds the packaging-specific surface Leg B does not
cover -- `pyproject.toml`'s `[project.scripts]`/`[project.optional-
dependencies]` declarations, no-auto-start-on-import, and the packaged
`rf` CLI binary itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


def _mcp_blocker_preamble() -> str:
    return textwrap.dedent(
        """
        import sys

        class _McpBlocker:
            def find_spec(self, name, path=None, target=None):
                if name == "mcp" or name.startswith("mcp."):
                    raise ImportError(f"BLOCKED (packaging test boundary): {name}")
                return None

        sys.meta_path.insert(0, _McpBlocker())
        """
    )


def _run_child(script: str) -> subprocess.CompletedProcess[str]:
    """Run an already-dedented `script` in a fresh interpreter with the
    `mcp` SDK unimportable regardless of whether it is actually installed."""

    full_script = _mcp_blocker_preamble() + "\n" + script
    return subprocess.run(
        [sys.executable, "-c", full_script],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(_SRC_ROOT)},
    )


def _load_pyproject() -> dict:
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - matches this repo's documented
        import tomli as tomllib  # type: ignore[no-redef]  # < 3.11 fallback convention

    with (_REPO_ROOT / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def test_process_entrypoint_resolves_without_mcp_sdk() -> None:
    """`from research_foundry.operator_mcp.process import main` must succeed
    in a fresh interpreter with the `mcp` SDK unimportable, and the imported
    `main` must be callable -- proving the packaged entrypoint
    (`research_foundry.operator_mcp.process:main`, D2) resolves cleanly
    without the optional `mcp` extra installed."""

    result = _run_child(
        textwrap.dedent(
            """
            from research_foundry.operator_mcp.process import main

            assert callable(main), "main is not callable"
            print("ENTRYPOINT_OK")
            """
        )
    )
    assert result.returncode == 0, (
        f"entrypoint import raised with mcp blocked.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "ENTRYPOINT_OK" in result.stdout


def test_pyproject_declares_operator_mcp_script_and_mcp_extra_pin() -> None:
    """`[project.scripts]` must map `rf-operator-mcp` to the packaged
    entrypoint (D2), and the SHARED `mcp` extra (no new extra, per D2) must
    stay pinned to the 1.x line `_MISSING_SDK_MSG` promises via
    `uv sync --extra mcp`."""

    data = _load_pyproject()

    scripts = data["project"]["scripts"]
    assert scripts.get("rf-operator-mcp") == "research_foundry.operator_mcp.process:main", scripts

    mcp_extra = data["project"]["optional-dependencies"]["mcp"]
    assert mcp_extra == ["mcp>=1.0,<2"], mcp_extra


def test_import_performs_no_auto_start_side_effects() -> None:
    """Importing `research_foundry.operator_mcp` (and its `.process`/
    `.server` submodules) must never spawn a thread, construct a socket, or
    emit any MCP stdio handshake -- `server.run()` (reached only via
    `process.main()`) is the ONE blessed way to start the process (D1), and
    neither is invoked at import time."""

    result = _run_child(
        textwrap.dedent(
            """
            import ast
            import inspect
            import socket
            import threading

            _start_threads = threading.active_count()

            class _NoSocket(socket.socket):
                def __init__(self, *a, **kw):
                    raise AssertionError(
                        "socket.socket() constructed during import "
                        "(no-autostart contract)"
                    )

            socket.socket = _NoSocket

            import importlib

            pkg = importlib.import_module("research_foundry.operator_mcp")
            process = importlib.import_module("research_foundry.operator_mcp.process")
            server = importlib.import_module("research_foundry.operator_mcp.server")

            _end_threads = threading.active_count()
            assert _end_threads == _start_threads, (
                f"thread count changed on import: {_start_threads} -> {_end_threads}"
            )

            for module in (pkg, process, server):
                tree = ast.parse(inspect.getsource(module))
                for node in ast.walk(tree):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names = [node.module]
                    for name in names:
                        assert name.split(".")[0] != "socket", (
                            f"{module.__name__} imports 'socket' at module "
                            f"level: {name}"
                        )

            print("NO_AUTOSTART_OK")
            """
        )
    )
    assert result.returncode == 0, (
        f"import performed a disallowed side effect.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "NO_AUTOSTART_OK" in result.stdout
    for handshake_marker in ("jsonrpc", "Content-Length", "initialize"):
        assert handshake_marker not in result.stdout, (
            f"unexpected MCP handshake-shaped output at import time: {result.stdout!r}"
        )


def test_build_server_raises_single_hint_runtime_error_without_sdk() -> None:
    """`build_server()` must raise a `RuntimeError` whose message contains
    the `uv sync --extra mcp` and `research-foundry[mcp]` install hints
    EXACTLY ONCE each, matching `_MISSING_SDK_MSG`'s single-hint contract
    (D1), when the `mcp` SDK is unimportable."""

    result = _run_child(
        textwrap.dedent(
            """
            import importlib

            server = importlib.import_module("research_foundry.operator_mcp.server")
            try:
                server.build_server()
            except RuntimeError as exc:
                print("RUNTIME_ERROR_START")
                print(str(exc))
                print("RUNTIME_ERROR_END")
            else:
                raise AssertionError("build_server() did not raise RuntimeError")
            """
        )
    )
    assert result.returncode == 0, (
        f"build_server() did not fail as expected with mcp blocked.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    stdout = result.stdout
    start = stdout.index("RUNTIME_ERROR_START") + len("RUNTIME_ERROR_START")
    end = stdout.index("RUNTIME_ERROR_END")
    message = stdout[start:end]

    assert message.count("uv sync --extra mcp") == 1, message
    assert message.count("research-foundry[mcp]") == 1, message


def test_base_package_imports_without_mcp_sdk() -> None:
    """`import research_foundry` must stay clean with the `mcp` SDK
    unimportable -- the mere existence of `operator_mcp` on disk, and its
    new `[project.scripts]` entry, must not regress the base package
    import."""

    result = _run_child(
        textwrap.dedent(
            """
            import research_foundry  # noqa: F401

            print("BASE_IMPORT_OK")
            """
        )
    )
    assert result.returncode == 0, (
        f"base package import raised with mcp blocked.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "BASE_IMPORT_OK" in result.stdout


def test_rf_cli_help_exits_zero() -> None:
    """`./.venv/bin/rf --help` must exit 0 -- the packaged base CLI must not
    regress merely because `operator_mcp` (and its new `[project.scripts]`
    entry) now exists alongside it."""

    rf_bin = _REPO_ROOT / ".venv" / "bin" / "rf"
    assert rf_bin.exists(), f"expected venv rf script at {rf_bin}"

    result = subprocess.run(
        [str(rf_bin), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"rf --help exited {result.returncode}.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
