"""Notebook correlation layer — maps research runs to NotebookLM notebooks.

Three modes (configurable per project in ``foundry.yaml``):

* ``project`` (default) — all runs sharing a project slug share one notebook.
* ``run`` — each run gets its own dedicated notebook.
* ``explicit`` — the caller supplies a ``notebook_id`` directly; no notebook
  is created.  Use when the notebook was provisioned outside the foundry.

The correlation registry lives at ``registries/notebooklm/notebooks.yaml`` and
has a two-section layout so both lookup directions are O(1)::

    projects:
      my-project:
        notebook_id: nb_abc123
        notebook_title: "RF — my-project"
        runs:
          - rf_run_20260613_my_project_first
          - rf_run_20260613_my_project_second
    runs:
      rf_run_20260613_my_project_first:
        notebook_id: nb_abc123
        notebook_title: "RF — my-project"
        project: my-project
        created_at: 2026-06-13T12:00:00-04:00

All network operations are fail-soft: ``None`` is returned rather than raising
when the client is offline or returns an error. The pipeline is never blocked by
an unavailable NotebookLM endpoint.

Determinism: all reads/writes use ``yamlio.load_yaml`` / ``yamlio.dump_yaml``
(insertion-order preserved, no random dict ordering).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import dump_yaml, load_yaml

if TYPE_CHECKING:
    # Avoid a circular import at runtime — the client module imports integrations
    # which may transitively import services. The type-check-only guard lets
    # mypy see the type without executing the import.
    from ..integrations.notebooklm import NotebookLMClient

# Registry filename (relative to FoundryPaths.registries).
_REGISTRY_FILE = "notebooklm/notebooks.yaml"

# Regex to extract a run_id from an arbitrary filesystem path segment.
# Matches paths like "runs/<run_id>/sources/..." or just "<run_id>".
_RUN_ID_RE = re.compile(r"(?:runs[/\\])?([^/\\]+)")

_DEFAULT_CORRELATION_MODE = "project"
_DEFAULT_TITLE_TEMPLATE = "RF — {project}"


# ---------------------------------------------------------------------------
# Internal registry helpers
# ---------------------------------------------------------------------------


def _registry_path(paths: FoundryPaths | None = None) -> Path:
    """Return the absolute path to the notebooklm notebooks registry file."""
    fp = paths or FoundryPaths.discover()
    return fp.registries / _REGISTRY_FILE


def _read_registry(paths: FoundryPaths | None = None) -> dict[str, Any]:
    """Load the registry YAML, returning an empty skeleton on any error or absence."""
    p = _registry_path(paths)
    if not p.exists():
        return {"projects": {}, "runs": {}}
    try:
        data = load_yaml(p)
        if not isinstance(data, dict):
            return {"projects": {}, "runs": {}}
        data.setdefault("projects", {})
        data.setdefault("runs", {})
        return data
    except Exception:  # noqa: BLE001
        return {"projects": {}, "runs": {}}


def _write_registry(data: dict[str, Any], paths: FoundryPaths | None = None) -> None:
    """Persist registry YAML atomically (via dump_yaml's parent-mkdir guarantee)."""
    p = _registry_path(paths)
    dump_yaml(data, p)


def _notebooklm_config(paths: FoundryPaths | None = None) -> dict[str, Any]:
    """Return the ``integrations.notebooklm`` block from foundry.yaml (fail-soft)."""
    try:
        from ..config import FoundryConfig

        cfg = FoundryConfig.load(paths.root if paths else None)
        foundry = cfg.foundry or {}
        integrations = foundry.get("integrations") or {}
        nlm = integrations.get("notebooklm") or {}
        return nlm if isinstance(nlm, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _notebook_title(project: str, *, paths: FoundryPaths | None = None) -> str:
    """Render the notebook title from the configured template."""
    cfg = _notebooklm_config(paths)
    template = str(cfg.get("notebook_title_template") or _DEFAULT_TITLE_TEMPLATE)
    try:
        return template.format(project=project)
    except (KeyError, ValueError):
        return f"RF — {project}"


def _parse_run_id_from_path(file_path: str | Path) -> str | None:
    """Extract a run_id from a path containing ``runs/<run_id>/...``.

    Returns ``None`` when the path does not match the expected pattern.
    """
    parts = Path(file_path).parts
    for i, part in enumerate(parts):
        if part == "runs" and i + 1 < len(parts):
            candidate = parts[i + 1]
            if candidate:
                return candidate
    return None


def _link_run_to_project(
    data: dict[str, Any],
    run_id: str,
    project: str,
    notebook_id: str,
    notebook_title: str,
) -> dict[str, Any]:
    """Mutate ``data`` to associate ``run_id`` with the project entry.

    Idempotent — repeated calls with the same arguments produce the same result.
    Returns the mutated data dict.
    """
    # Ensure project entry exists.
    if project not in data["projects"]:
        data["projects"][project] = {
            "notebook_id": notebook_id,
            "notebook_title": notebook_title,
            "runs": [],
        }
    else:
        # Keep notebook_id/title up-to-date.
        data["projects"][project]["notebook_id"] = notebook_id
        data["projects"][project]["notebook_title"] = notebook_title

    proj_runs: list[str] = data["projects"][project].setdefault("runs", [])
    if run_id not in proj_runs:
        proj_runs.append(run_id)

    # Ensure run entry exists.
    if run_id not in data["runs"]:
        data["runs"][run_id] = {
            "notebook_id": notebook_id,
            "notebook_title": notebook_title,
            "project": project,
            "created_at": now_iso(),
        }
    else:
        # Keep fields current.
        data["runs"][run_id]["notebook_id"] = notebook_id
        data["runs"][run_id]["notebook_title"] = notebook_title
        data["runs"][run_id].setdefault("project", project)

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def correlation_mode(*, paths: FoundryPaths | None = None) -> str:
    """Return the configured correlation mode from foundry.yaml.

    Reads ``integrations.notebooklm.correlation_mode``.  Defaults to
    ``'project'`` when the key is absent or the config is unreadable.

    Parameters
    ----------
    paths:
        Optional ``FoundryPaths`` override (workspace discovery used when
        ``None``).

    Returns
    -------
    str
        One of ``'project'``, ``'run'``, or ``'explicit'``.
    """
    cfg = _notebooklm_config(paths)
    mode = cfg.get("correlation_mode") or _DEFAULT_CORRELATION_MODE
    return str(mode)


def resolve_notebook(
    run_id: str,
    *,
    project: str | None = None,
    mode: str | None = None,
    create: bool = False,
    client: NotebookLMClient | None = None,
    paths: FoundryPaths | None = None,
) -> dict[str, Any] | None:
    """Resolve (and optionally create) the notebook for a research run.

    Mode precedence: explicit ``mode`` arg > ``foundry.yaml`` setting >
    ``'project'`` default.

    **project mode** — all runs sharing ``project`` map to one notebook.
    If the project has no notebook yet and ``create=True`` and ``client``
    is provided, a new notebook is created and the registry is updated.

    **run mode** — each ``run_id`` gets its own notebook.  Creation
    behaviour is identical to project mode but keyed by run_id.

    **explicit mode** — ``project`` is re-interpreted as a raw
    ``notebook_id``.  The mapping is recorded (without creating anything)
    and returned.  Returns ``None`` when no notebook_id is passed.

    All network operations are fail-soft: if ``client`` is ``None``, offline,
    or returns an error the function returns the recorded mapping (if any) or
    ``None`` without raising.

    Parameters
    ----------
    run_id:
        The RF run identifier (e.g. ``rf_run_20260613_my_topic``).
    project:
        Project slug for project/run modes; raw notebook_id for explicit mode.
    mode:
        Correlation mode override.  When ``None`` the foundry.yaml value is
        used.
    create:
        When ``True`` and the notebook is not yet recorded, attempt to create
        it via ``client``.  No-op when ``client`` is ``None`` or offline.
    client:
        Optional :class:`~research_foundry.integrations.notebooklm.NotebookLMClient`
        instance.  Lazy-imported default singleton is NOT used here to avoid
        circular imports — callers must supply it when network access is needed.
    paths:
        Optional ``FoundryPaths`` override.

    Returns
    -------
    dict or None
        ``{notebook_id, notebook_title, project, run_id, mode}`` on success;
        ``None`` when no mapping can be resolved.
    """
    effective_mode = mode or correlation_mode(paths=paths)
    data = _read_registry(paths)

    # ------------------------------------------------------------------ #
    # explicit mode
    # ------------------------------------------------------------------ #
    if effective_mode == "explicit":
        # ``project`` carries the literal notebook_id in explicit mode.
        notebook_id = project
        if not notebook_id:
            return None
        # Record the association (idempotent).
        notebook_title = _notebook_title(notebook_id, paths=paths)
        data = _link_run_to_project(data, run_id, notebook_id, notebook_id, notebook_title)
        _write_registry(data, paths)
        return {
            "notebook_id": notebook_id,
            "notebook_title": notebook_title,
            "project": notebook_id,
            "run_id": run_id,
            "mode": effective_mode,
        }

    # ------------------------------------------------------------------ #
    # project mode
    # ------------------------------------------------------------------ #
    if effective_mode == "project":
        if not project:
            # Fall back to run lookup before giving up.
            run_entry = data["runs"].get(run_id)
            if run_entry and run_entry.get("notebook_id"):
                return {
                    "notebook_id": run_entry["notebook_id"],
                    "notebook_title": run_entry.get("notebook_title", ""),
                    "project": run_entry.get("project", ""),
                    "run_id": run_id,
                    "mode": effective_mode,
                }
            return None

        proj_entry = data["projects"].get(project)
        if proj_entry and proj_entry.get("notebook_id"):
            # Project already has a notebook — associate this run.
            notebook_id = proj_entry["notebook_id"]
            notebook_title = proj_entry.get("notebook_title") or _notebook_title(project, paths=paths)
            data = _link_run_to_project(data, run_id, project, notebook_id, notebook_title)
            _write_registry(data, paths)
            return {
                "notebook_id": notebook_id,
                "notebook_title": notebook_title,
                "project": project,
                "run_id": run_id,
                "mode": effective_mode,
            }

        # No existing notebook for this project.
        if create and client is not None:
            try:
                if client.available():
                    title = _notebook_title(project, paths=paths)
                    result = client.create_notebook(title)
                    if result and result.get("notebook_id"):
                        notebook_id = str(result["notebook_id"])
                        notebook_title = str(result.get("notebook_title") or title)
                        data = _link_run_to_project(data, run_id, project, notebook_id, notebook_title)
                        _write_registry(data, paths)
                        return {
                            "notebook_id": notebook_id,
                            "notebook_title": notebook_title,
                            "project": project,
                            "run_id": run_id,
                            "mode": effective_mode,
                        }
            except Exception:  # noqa: BLE001 — fail-soft
                pass

        return None

    # ------------------------------------------------------------------ #
    # run mode
    # ------------------------------------------------------------------ #
    if effective_mode == "run":
        run_entry = data["runs"].get(run_id)
        if run_entry and run_entry.get("notebook_id"):
            return {
                "notebook_id": run_entry["notebook_id"],
                "notebook_title": run_entry.get("notebook_title", ""),
                "project": run_entry.get("project", project or ""),
                "run_id": run_id,
                "mode": effective_mode,
            }

        if create and client is not None:
            try:
                if client.available():
                    label = project or run_id
                    title = _notebook_title(label, paths=paths)
                    result = client.create_notebook(title)
                    if result and result.get("notebook_id"):
                        notebook_id = str(result["notebook_id"])
                        notebook_title = str(result.get("notebook_title") or title)
                        record_run_notebook(
                            run_id,
                            notebook_id,
                            project=project,
                            notebook_title=notebook_title,
                            paths=paths,
                        )
                        return {
                            "notebook_id": notebook_id,
                            "notebook_title": notebook_title,
                            "project": project or "",
                            "run_id": run_id,
                            "mode": effective_mode,
                        }
            except Exception:  # noqa: BLE001 — fail-soft
                pass

        return None

    # Unknown mode — degrade gracefully.
    return None


def record_run_notebook(
    run_id: str,
    notebook_id: str,
    *,
    project: str | None = None,
    notebook_title: str | None = None,
    paths: FoundryPaths | None = None,
) -> None:
    """Idempotently record a run → notebook association in the registry.

    Writes to ``registries/notebooklm/notebooks.yaml``.  If ``project`` is
    provided the run is also linked under the project key.  Safe to call
    multiple times with the same arguments.

    Parameters
    ----------
    run_id:
        RF run identifier.
    notebook_id:
        NotebookLM notebook identifier.
    project:
        Optional project slug.  When supplied the project section is also
        updated.
    notebook_title:
        Human-readable notebook title.  Stored as-is (no template expansion).
    paths:
        Optional ``FoundryPaths`` override.
    """
    data = _read_registry(paths)
    resolved_title = notebook_title or ""

    if project:
        data = _link_run_to_project(data, run_id, project, notebook_id, resolved_title)
    else:
        # Record in runs section only.
        if run_id not in data["runs"]:
            data["runs"][run_id] = {
                "notebook_id": notebook_id,
                "notebook_title": resolved_title,
                "project": project or "",
                "created_at": now_iso(),
            }
        else:
            data["runs"][run_id]["notebook_id"] = notebook_id
            if resolved_title:
                data["runs"][run_id]["notebook_title"] = resolved_title

    _write_registry(data, paths)


def notebook_for_run(run_id: str, *, paths: FoundryPaths | None = None) -> str | None:
    """Return the notebook_id recorded for ``run_id``, or ``None``.

    Checks the correlation registry first; falls back to ``run.yaml`` when the
    registry has no entry.

    Parameters
    ----------
    run_id:
        RF run identifier.
    paths:
        Optional ``FoundryPaths`` override.

    Returns
    -------
    str or None
        The ``notebook_id`` string, or ``None`` when none is recorded.
    """
    data = _read_registry(paths)
    run_entry = data["runs"].get(run_id)
    if run_entry and run_entry.get("notebook_id"):
        return str(run_entry["notebook_id"])

    # Fallback: check run.yaml for a notebook_id field.
    try:
        fp = paths or FoundryPaths.discover()
        run_yaml_path = fp.run_paths(run_id).run_yaml
        if run_yaml_path.exists():
            run_doc = load_yaml(run_yaml_path)
            if isinstance(run_doc, dict) and run_doc.get("notebook_id"):
                return str(run_doc["notebook_id"])
    except Exception:  # noqa: BLE001 — fail-soft
        pass

    return None


def notebook_for_path(
    file_path: str | Path,
    *,
    paths: FoundryPaths | None = None,
) -> str | None:
    """Return the notebook_id for the run that owns ``file_path``.

    Parses the ``run_id`` from a path of the form
    ``runs/<run_id>/...`` and delegates to :func:`notebook_for_run`.  Returns
    ``None`` when the path is not under a known run directory.

    Parameters
    ----------
    file_path:
        Any filesystem path that falls under ``runs/<run_id>/``.
    paths:
        Optional ``FoundryPaths`` override.

    Returns
    -------
    str or None
        The ``notebook_id``, or ``None`` when the path cannot be resolved.
    """
    run_id = _parse_run_id_from_path(file_path)
    if not run_id:
        return None
    return notebook_for_run(run_id, paths=paths)


__all__ = [
    "correlation_mode",
    "resolve_notebook",
    "record_run_notebook",
    "notebook_for_run",
    "notebook_for_path",
]
