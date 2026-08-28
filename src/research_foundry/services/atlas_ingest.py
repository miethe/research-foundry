"""Best-effort Atlas ingest hook for the rf run-export close point.

WHY THIS EXISTS (node_01M14VK4ZNCXB5B8CPZR2W33TA leg): `artifact_atlas` ships an
ingest surface (`POST /api/projects/{projectId}/inbox/{import,upload}`), but
nothing in research-foundry ever called it when a run finalizes — the
"built lane, no writers" failure mode (`.claude/rules/built-lane-no-writers.md`
in agentic_meta_dev): a reader/ingest path existing proves nothing about
whether it is fed.

RUN-CLOSE POINT: `rf run export` (``cli_commands.py`` ``run_export``, backed by
``export_service.export_to_file``/``export_run``) is the one CLI-hookable point
that finalizes a run's artifacts into ``run.json`` — this repo has no separate
"close"/"finalize" verb; ``export_service.derive_status`` computes the
planned->...->published status lattice used elsewhere (catalog_service,
knowledge_access, the runs API) directly from artifact presence, and export is
the point that snapshots it. ``swarm drive`` (the discovery loop) never calls
export itself; export is the deliberate hand-off/finalization step. See the PR
body / IntentTree finding this leg filed for the residual gap this creates
(export is opt-in per run, not auto-fired at drive-completion — a real
"run closed but never exported" run stays unfed forever).

WHY UPLOAD, NOT `atlas import <path>` OR `file://` INBOX IMPORT: the CLI
(`python3 -m app.cli.atlas import <path>`) calls straight into
`ImportService.import_local_path` against a *local* `ATLAS_REGISTRY_DIR` --
there is no `atlas` binary on PATH here, and no shared filesystem between this
repo's checkout and the artifact-atlas container (verified 2026-08-28: the
node's artifact-atlas stack is a podman-compose deployment with
`workspace_root == /app` inside the container and no bind mount of any sibling
repo's checkout -- `POST .../inbox/import` with a `file://` URI would 400 on
the container's own allowlist). The multipart `POST
/api/projects/{projectId}/inbox/upload` endpoint transmits bytes over HTTP and
has no filesystem-coupling requirement, so it is the only ingest surface this
repo can call from an arbitrary host. Live-verified against
http://10.42.10.76:8042 on 2026-08-28: uploading a real run's
``reports/report_draft.md`` registered ``asset_7e542cf86890485b`` under
``proj_research_foundry`` (confirmed via a follow-up ``GET
/api/assets/{id}``).

CONTRACT (mirrors agentic_meta_dev's ``sdlc-sync.sh`` / dev-execution hooks):
  * default ON; only an explicit falsy ``AOS_ATLAS_INGEST`` (0/false/no/off)
    disables it -- per Nick's standing ruling, EVERYTHING ingests, fully open
    on LAN; the disable knob exists for OTHER environments only.
  * true no-op when the run has nothing ingestible (no report file at all).
  * NEVER raises past the caller -- every failure (atlas unreachable, bad
    response, network timeout) is caught, logged as a warning, and swallowed.
    The caller (``run_export``) treats this as fire-and-forget.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FALSY = {"0", "false", "no", "off"}

_DEFAULT_ATLAS_URL = "http://10.42.10.76:8042"
_DEFAULT_PROJECT_SLUG = "research-foundry"
_DEFAULT_TIMEOUT_S = 10.0

# Candidate report files to ingest, in preference order. The first one that
# exists on disk is uploaded; none existing is a true no-op (nothing to
# ingest yet -- e.g. a run exported before synthesis).
_CANDIDATE_RELATIVE_PATHS: tuple[str, ...] = (
    "reports/report_final.md",
    "reports/report_draft.md",
    "reports/report_deterministic.md",
    "research_brief.md",
)


def _is_falsy(value: str | None) -> bool:
    return (value or "").strip().lower() in _FALSY


def _find_ingest_candidate(run_dir: Path) -> Path | None:
    for rel in _CANDIDATE_RELATIVE_PATHS:
        candidate = run_dir / rel
        if candidate.is_file():
            return candidate
    return None


def _resolve_project_id(atlas_url: str, slug: str, *, timeout: float) -> str | None:
    """Resolve a project slug to its atlas project id via GET /api/projects.

    Returns None (never raises) when atlas is unreachable, the response is
    malformed, or no project matches the slug.
    """

    import urllib.request
    import json as _json

    req = urllib.request.Request(f"{atlas_url}/api/projects")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = _json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - non-fatal by contract
        logger.warning("[atlas-ingest] could not list atlas projects: %s", exc)
        return None

    for item in payload.get("items", []) if isinstance(payload, dict) else []:
        if isinstance(item, dict) and item.get("slug") == slug:
            return item.get("id")
    logger.warning("[atlas-ingest] no atlas project with slug=%r", slug)
    return None


def _upload_file(
    atlas_url: str,
    project_id: str,
    path: Path,
    *,
    sensitivity: str,
    agent_access: str,
    timeout: float,
) -> dict[str, Any] | None:
    """POST the file to the project's inbox/upload endpoint. Never raises."""

    import urllib.request
    import json as _json
    import mimetypes
    import uuid

    boundary = uuid.uuid4().hex
    body_lines: list[bytes] = []

    def _field(name: str, value: str) -> None:
        body_lines.append(f"--{boundary}".encode())
        body_lines.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        body_lines.append(b"")
        body_lines.append(value.encode("utf-8"))

    _field("sensitivity", sensitivity)
    _field("agent_access", agent_access)

    file_bytes = path.read_bytes()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body_lines.append(f"--{boundary}".encode())
    body_lines.append(
        f'Content-Disposition: form-data; name="files"; filename="{path.name}"'.encode()
    )
    body_lines.append(f"Content-Type: {content_type}".encode())
    body_lines.append(b"")
    body_lines.append(file_bytes)
    body_lines.append(f"--{boundary}--".encode())
    body_lines.append(b"")

    body = b"\r\n".join(body_lines)

    req = urllib.request.Request(
        f"{atlas_url}/api/projects/{project_id}/inbox/upload",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return _json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - non-fatal by contract
        logger.warning("[atlas-ingest] upload to atlas failed: %s", exc)
        return None


def maybe_ingest_run(run_id: str, run_dir: Path) -> dict[str, Any] | None:
    """Best-effort: upload the run's report to Atlas after `rf run export`.

    Returns the atlas response dict on success (``{"imported_count": ...,
    "asset_ids": [...]}``), or None on any no-op / failure. NEVER raises.
    """

    if _is_falsy(os.environ.get("AOS_ATLAS_INGEST")):
        return None

    candidate = _find_ingest_candidate(run_dir)
    if candidate is None:
        # True no-op: nothing ingestible yet for this run.
        return None

    atlas_url = (os.environ.get("AOS_ATLAS_URL") or _DEFAULT_ATLAS_URL).rstrip("/")
    project_slug = os.environ.get("AOS_ATLAS_PROJECT") or _DEFAULT_PROJECT_SLUG
    sensitivity = os.environ.get("AOS_ATLAS_SENSITIVITY") or "personal"
    agent_access = os.environ.get("AOS_ATLAS_AGENT_ACCESS") or "read_allowed"
    try:
        timeout = float(os.environ.get("AOS_ATLAS_TIMEOUT_S") or _DEFAULT_TIMEOUT_S)
    except ValueError:
        timeout = _DEFAULT_TIMEOUT_S

    try:
        project_id = _resolve_project_id(atlas_url, project_slug, timeout=timeout)
        if project_id is None:
            return None
        result = _upload_file(
            atlas_url,
            project_id,
            candidate,
            sensitivity=sensitivity,
            agent_access=agent_access,
            timeout=timeout,
        )
        if result:
            logger.info(
                "[atlas-ingest] run %s -> atlas project %s: %s",
                run_id,
                project_slug,
                result,
            )
        return result
    except Exception as exc:  # noqa: BLE001 - contract: never raise past caller
        logger.warning("[atlas-ingest] unexpected failure ingesting run %s: %s", run_id, exc)
        return None
