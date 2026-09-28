"""Single-run administrative repair verbs (``rf run set-visibility`` / ``set-workspace``).

itt0926-rfws (node ``node_01M1HV11263E3VNB2ZC0A0K1KZ``): before this module,
``run.yaml``'s DF-004 ``workspace_id``/``visibility`` fields had no supported
repair path once a run was planned — a run that ended up with a bad or
mismatched ``workspace_id`` (e.g. ``rf plan``'s pre-fix ``workspace_id: null``
bug, see ``services/planning.py:plan_run``) could only be fixed by hand-editing
``run.yaml`` on disk, as the node's own symptom description records.

These are narrow, single-record mutations — deliberately NOT a bulk migration
(that is ``workspace_migration_service.backfill_runs``, which only ever
touches records where ``workspace_id`` is currently falsy). Both functions
here operate unconditionally on the one named run, atomically rewrite
``run.yaml``, and return the updated record.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from ..errors import ExitCode, RFError
from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, loads_yaml

#: DF-004 visibility vocabulary (mirrors ``services/planning.py:plan_run``'s
#: ``visibility`` docstring: any other value falls back to ``"workspace"`` at
#: plan time, but a repair verb should refuse an unrecognised value outright
#: rather than silently coercing it).
ALLOWED_VISIBILITY = ("workspace", "public")


class RunAdminError(RFError):
    """A single-run administrative mutation could not be applied."""

    exit_code = ExitCode.USAGE

    def __init__(self, message: str, *, run_id: str | None = None) -> None:
        super().__init__(message, exit_code=ExitCode.USAGE)
        self.run_id = run_id


def _run_yaml_path(paths: FoundryPaths, run_id: str) -> Path:
    """Resolve ``runs/<run_id>/run.yaml``, raising :class:`RunAdminError` if absent.

    Deliberately does NOT use ``export_service.resolve_run_paths``'s
    recursive-discovery fallback: a repair verb should target the exact
    ``run_id`` the caller named, not silently match a differently-nested
    directory sharing a leaf name.
    """

    run_yaml = paths.run_dir(run_id) / "run.yaml"
    if not run_yaml.is_file():
        raise RunAdminError(f"run not found: {run_id}", run_id=run_id)
    return run_yaml


def _load_run_yaml(run_yaml: Path, *, run_id: str) -> dict[str, Any]:
    try:
        data = loads_yaml(run_yaml.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RunAdminError(f"could not read {run_yaml}: {exc}", run_id=run_id) from exc
    if not isinstance(data, dict):
        raise RunAdminError(f"malformed run.yaml (not a mapping): {run_yaml}", run_id=run_id)
    return data


def _atomic_write_yaml(obj: dict[str, Any], path: Path) -> None:
    """Write YAML atomically: temp file in the same directory, then ``os.replace``.

    Mirrors ``workspace_migration_service._atomic_write_yaml`` /
    ``builder_service``'s identical pattern — a crash mid-write never leaves
    a torn ``run.yaml``.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(dumps_yaml(obj))
        os.replace(tmp_name, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(tmp_name)
        raise


def set_run_visibility(paths: FoundryPaths, run_id: str, value: str) -> dict[str, Any]:
    """Set ``run.yaml.visibility`` for *run_id* to *value*.

    Parameters
    ----------
    value:
        Must be one of :data:`ALLOWED_VISIBILITY` (``"workspace"`` |
        ``"public"``). Unlike ``plan_run``'s plan-time default-on-typo
        behavior, an unrecognised value here is refused outright
        (:class:`RunAdminError`) — a repair verb should never silently
        coerce an operator's explicit typo.

    Returns
    -------
    dict
        The full updated ``run.yaml`` record.

    Raises
    ------
    RunAdminError
        *run_id* does not exist, its ``run.yaml`` is unreadable/malformed,
        or *value* is not a recognised visibility.
    """

    if value not in ALLOWED_VISIBILITY:
        raise RunAdminError(
            f"invalid visibility {value!r}; must be one of {ALLOWED_VISIBILITY}",
            run_id=run_id,
        )
    run_yaml = _run_yaml_path(paths, run_id)
    data = _load_run_yaml(run_yaml, run_id=run_id)
    data["visibility"] = value
    _atomic_write_yaml(data, run_yaml)
    return data


def set_run_workspace(paths: FoundryPaths, run_id: str, workspace_id: str) -> dict[str, Any]:
    """Set ``run.yaml.workspace_id`` for *run_id* to *workspace_id* (repair path).

    Unconditional (unlike ``workspace_migration_service.backfill_runs``,
    which only ever touches runs whose ``workspace_id`` is currently falsy):
    this is the targeted single-run repair verb for a run that was planned
    with a wrong or missing ``workspace_id`` (e.g. the pre-fix ``rf plan``
    ``workspace_id: null`` bug this node's symptom describes) and needs its
    ownership corrected after the fact.

    Raises
    ------
    RunAdminError
        *run_id* does not exist, its ``run.yaml`` is unreadable/malformed,
        or *workspace_id* is empty.
    """

    if not workspace_id or not workspace_id.strip():
        raise RunAdminError("workspace_id must be a non-empty string", run_id=run_id)
    run_yaml = _run_yaml_path(paths, run_id)
    data = _load_run_yaml(run_yaml, run_id=run_id)
    data["workspace_id"] = workspace_id
    _atomic_write_yaml(data, run_yaml)
    return data


__all__ = [
    "ALLOWED_VISIBILITY",
    "RunAdminError",
    "set_run_visibility",
    "set_run_workspace",
]
