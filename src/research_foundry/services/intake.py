"""IntentTree → RF inbound intake service (spec §3.3).

``intake_from_intenttree`` pulls a dispatched research task from IntentTree
(online) or from a local YAML file (offline fallback), runs it through
capture → triage → optional plan, and closes the loop with Phase 1 by
setting the resulting intent's ``intenttree_node_ref`` to the SOURCE node_id
rather than minting a new local node.

Design decisions
----------------
* The intent's ``intenttree_node_ref`` is set to the *source* node_id (the
  IntentTree node that dispatched the task). This means Phase 1 writeback
  (``writeback.writeback(..., targets=("intenttree",))``) will update the
  originating node rather than a locally-minted placeholder.
* triage normally creates a local ``intenttree_node`` YAML. We suppress that
  (``create_tree_node=False``) and instead back-patch ``intenttree_node_ref``
  on the resulting intent to the source node_id. This avoids a confusing
  second node record for the same task.
* Attachments are built from the node's ``links`` and ``artifacts`` lists.
  MeatyWiki refs (``type == "meatywiki_note"`` or URL containing ``meatywiki``)
  are preserved as attachments with ``source`` set to
  ``"intenttree:<node_id>"``.
* Sensitivity flows from the caller's ``sensitivity`` arg; the service never
  auto-escalates.
* Offline-only mode works via ``--from-file`` / ``from_file`` kwarg: no live
  HTTP is attempted when that path is given OR when
  ``IntentTreeClient.available()`` returns False and ``from_file`` is absent
  (raises ``RFError`` in that case — callers must supply a file for offline
  use).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import NotFoundError, RFError
from ..paths import FoundryPaths
from ..yamlio import load_yaml
from .capture import capture_idea, triage_idea


@dataclass(frozen=True)
class IntakeResult:
    """Outcome of :func:`intake_from_intenttree`."""

    node_id: str
    raw_idea_id: str
    intent_id: str | None
    run_id: str | None
    raw_idea_path: Path | None
    intent_path: Path | None
    run_dir: Path | None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_node_from_file(from_file: Path) -> dict[str, Any]:
    """Load a node from a local YAML file (offline fallback).

    Raises :class:`NotFoundError` when the file does not exist or cannot be
    parsed as a mapping.
    """

    if not from_file.exists():
        raise NotFoundError(f"offline node file not found: {from_file}")
    data = load_yaml(from_file)
    if not isinstance(data, dict):
        raise RFError(f"node file is not a YAML mapping: {from_file}")
    return data


def _fetch_node_online(node_id: str) -> dict[str, Any] | None:
    """Attempt a live GET from IntentTree; return None when unreachable."""

    try:
        from ..integrations.intenttree import IntentTreeClient

        client = IntentTreeClient.from_config()
        if not client.available():
            return None
        return client.get_node(node_id, include="artifacts,edges")
    except Exception:  # noqa: BLE001 — fail-soft; caller decides
        return None


def _build_body(node: dict[str, Any]) -> str:
    """Construct the raw-idea body text from the node record.

    Combines the node's ``body`` / ``objective`` / ``description`` with a
    ``## Links`` section listing all links and artifacts.
    """

    parts: list[str] = []

    # Body / objective
    for key in ("body", "objective", "description"):
        val = node.get(key)
        if val and isinstance(val, str) and val.strip():
            parts.append(val.strip())
            break

    # Fallback: use title as body if nothing else is available
    if not parts:
        title = str(node.get("title") or node.get("node_id") or "")
        parts.append(title)

    # Links section
    links: list[str] = []
    for link in node.get("links") or []:
        if isinstance(link, dict):
            uri = link.get("url") or link.get("uri") or link.get("href") or ""
            label = link.get("label") or link.get("title") or link.get("type") or ""
            if uri:
                links.append(f"- [{label}]({uri})" if label else f"- {uri}")
        elif isinstance(link, str) and link.strip():
            links.append(f"- {link.strip()}")
    for art in node.get("artifacts") or []:
        if isinstance(art, dict):
            uri = art.get("url") or art.get("path") or ""
            label = art.get("type") or art.get("label") or ""
            if uri:
                links.append(f"- [{label}]({uri})" if label else f"- {uri}")

    if links:
        parts.append("\n## Links\n\n" + "\n".join(links))

    return "\n\n".join(parts)


def _build_attachments(
    node: dict[str, Any],
    node_id: str,
) -> list[dict[str, Any]]:
    """Build the ``attachments`` list for ``capture_idea`` from the node's
    links and artifacts.

    Each attachment has:
    - ``path_or_uri``: the URL or path from the node
    - ``type``: inferred from the link/artifact type field, or "url" / "other"
    - ``source``: ``"intenttree:<node_id>"`` for traceability
    """

    source_tag = f"intenttree:{node_id}"
    attachments: list[dict[str, Any]] = []

    def _attachment_type(item: dict[str, Any], uri: str) -> str:
        raw_type = (item.get("type") or "").lower()
        if raw_type in ("url", "pdf", "markdown", "image", "audio", "other"):
            return raw_type
        if "meatywiki" in uri.lower():
            return "url"
        if uri.endswith(".pdf"):
            return "pdf"
        if uri.endswith(".md"):
            return "markdown"
        if uri.startswith("http"):
            return "url"
        return "other"

    for link in node.get("links") or []:
        if isinstance(link, dict):
            uri = str(link.get("url") or link.get("uri") or link.get("href") or "").strip()
            if not uri:
                continue
            attachments.append({
                "path_or_uri": uri,
                "type": _attachment_type(link, uri),
                "source": source_tag,
                "label": link.get("label") or link.get("title") or "",
            })
        elif isinstance(link, str) and link.strip():
            attachments.append({
                "path_or_uri": link.strip(),
                "type": "url",
                "source": source_tag,
            })

    for art in node.get("artifacts") or []:
        if isinstance(art, dict):
            uri = str(art.get("url") or art.get("path") or "").strip()
            if not uri:
                continue
            attachments.append({
                "path_or_uri": uri,
                "type": _attachment_type(art, uri),
                "source": source_tag,
                "label": art.get("type") or art.get("label") or "",
            })

    return attachments


def _patch_intent_node_ref(intent_path: Path, source_node_id: str) -> None:
    """Back-patch ``intenttree_node_ref`` on the written intent file.

    triage_idea with ``create_tree_node=False`` leaves ``intenttree_node_ref``
    absent (no local node was minted). We set it to the *source* node_id so
    Phase 1 writeback updates the originating IntentTree node.
    """

    from ..yamlio import dump_yaml, load_yaml

    data = load_yaml(intent_path)
    if not isinstance(data, dict):
        return
    data["intenttree_node_ref"] = source_node_id
    dump_yaml(data, intent_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def intake_from_intenttree(
    node_id: str,
    *,
    from_file: Path | None = None,
    do_plan: bool = False,
    sensitivity: str = "personal",
    profile: str | None = None,
    paths: FoundryPaths | None = None,
) -> IntakeResult:
    """Pull a dispatched research task from IntentTree and run capture→triage.

    Parameters
    ----------
    node_id:
        The IntentTree node id being pulled (e.g. ``"node_abc_123"``).
    from_file:
        When given, load the node from this local YAML file instead of hitting
        the live server. Useful for offline / replay scenarios.
    do_plan:
        If True, also run ``plan_run(intent_id)`` after triage and include the
        run_id in the result.
    sensitivity:
        Governance sensitivity; flows into the intent's ``governance.sensitivity``
        block. Never auto-escalated by this function.
    profile:
        Runtime key profile passed to ``plan_run`` when ``do_plan=True``.
    paths:
        FoundryPaths override (defaults to ``FoundryPaths.discover()``).

    Returns
    -------
    IntakeResult
        Contains node_id, raw_idea_id, intent_id, optional run_id, and paths.

    Raises
    ------
    RFError
        When neither the live server yields the node nor a ``from_file`` was
        supplied (or the file does not exist / is not a mapping).
    NotFoundError
        When ``from_file`` is given but the file does not exist.
    """

    paths = paths or FoundryPaths.discover()

    # --- Source the node -----------------------------------------------------
    node: dict[str, Any] | None = None

    if from_file is not None:
        # Offline / explicit file override — never hit the server
        node = _load_node_from_file(from_file)
    else:
        # Try live; fall through to error if unreachable
        node = _fetch_node_online(node_id)

    if node is None:
        raise RFError(
            f"IntentTree node {node_id!r} could not be sourced: "
            "server is unreachable and no --from-file was given. "
            "Provide a local YAML snapshot with --from-file for offline use."
        )

    # --- Map node → capture_idea ---------------------------------------------
    title = str(node.get("title") or node.get("node_id") or node_id)
    body_text = _build_body(node)
    attachments = _build_attachments(node, node_id)

    cap = capture_idea(
        body_text,
        title=title,
        captured_from="intenttree",
        sensitivity=sensitivity,
        attachments=attachments,
        paths=paths,
    )

    # --- Triage (suppress local tree node — we'll link to source instead) ----
    tri = triage_idea(
        cap.raw_idea_id,
        create_tree_node=False,  # do not mint a local node; use source node_id
        paths=paths,
    )

    # Back-patch intenttree_node_ref on the intent so Phase 1 writeback
    # updates the originating node (the one that dispatched this task).
    intent_path: Path | None = tri.intent_path
    if intent_path is not None and intent_path.exists() and tri.intent_id:
        _patch_intent_node_ref(intent_path, node_id)

    # --- Optional planning pass ----------------------------------------------
    run_id: str | None = None
    run_dir: Path | None = None

    if do_plan and tri.intent_id:
        from .planning import plan_run

        plan = plan_run(tri.intent_id, profile=profile, paths=paths)
        run_id = plan.run_id
        run_dir = plan.run_dir

    return IntakeResult(
        node_id=node_id,
        raw_idea_id=cap.raw_idea_id,
        intent_id=tri.intent_id,
        run_id=run_id,
        raw_idea_path=cap.path,
        intent_path=intent_path,
        run_dir=run_dir,
    )


@dataclass(frozen=True)
class NLMIntakeResult:
    """Outcome of :func:`intake_from_notebooklm`."""

    notebook_id: str
    raw_idea_id: str
    intent_id: str | None
    raw_idea_path: Path | None
    intent_path: Path | None
    offline: bool


def intake_from_notebooklm(
    notebook_id: str,
    *,
    project: str | None = None,
    paths: FoundryPaths | None = None,
) -> NLMIntakeResult:
    """Pull a NotebookLM notebook identity into RF as a new captured idea.

    Registers the notebook as a research interest without executing any run.
    A back-link (``notebooklm_notebook_ref``) is written on the resulting
    intent so that downstream writebacks and the correlation layer can locate
    the originating notebook.

    Design decisions
    ----------------
    * Fail-soft on client unavailability — when the ``notebooklm`` CLI is
      absent or the client returns ``None`` for the notebook record the intake
      still completes: a minimal raw idea is captured with the ``notebook_id``
      as context, and ``offline=True`` is set on the result.
    * The back-link ``notebooklm_notebook_ref`` is back-patched onto the
      written intent file (same pattern as :func:`intake_from_intenttree` and
      its ``intenttree_node_ref``).
    * ``suggested_project`` is threaded through to ``capture_idea`` so the
      triage / planning layers can pick it up via the intent's
      ``project``/``suggested_project`` field.
    * No network I/O is attempted beyond the best-effort ``get_notebook``
      call. The pipeline never blocks on a missing NotebookLM endpoint.

    Parameters
    ----------
    notebook_id:
        The NotebookLM notebook identifier (e.g. ``"nb_abc123"``).
    project:
        Optional project slug to associate with this intake. Stored as
        ``suggested_project`` on the raw idea and forwarded to correlation.
    paths:
        FoundryPaths override (defaults to ``FoundryPaths.discover()``).

    Returns
    -------
    NLMIntakeResult
        Contains the notebook_id, raw_idea_id, intent_id, and file paths.
        ``offline=True`` when the live notebook record could not be retrieved.
    """

    paths = paths or FoundryPaths.discover()

    # --- Attempt live notebook lookup (fail-soft) ----------------------------
    notebook_record: dict[str, Any] | None = None
    offline = False

    try:
        from ..integrations.notebooklm import get_notebooklm_client

        client = get_notebooklm_client()
        if client.available():
            notebook_record = client.get_notebook(notebook_id)
    except Exception:  # noqa: BLE001 — fail-soft; never raise
        pass

    if notebook_record is None:
        offline = True

    # --- Build body text from notebook record --------------------------------
    title: str
    body_parts: list[str] = []

    if notebook_record and isinstance(notebook_record, dict):
        title = str(notebook_record.get("title") or notebook_id)
        if notebook_record.get("description"):
            body_parts.append(str(notebook_record["description"]).strip())
    else:
        title = f"NotebookLM notebook {notebook_id}"

    if not body_parts:
        body_parts.append(
            f"Notebook captured from NotebookLM (id: {notebook_id})."
        )

    body_parts.append(f"\n## Source\n\n- notebooklm:{notebook_id}")
    if project:
        body_parts.append(f"- project: {project}")

    body_text = "\n\n".join(body_parts)

    # --- capture_idea --------------------------------------------------------
    cap = capture_idea(
        body_text,
        title=title,
        captured_from="notebooklm",
        sensitivity="personal",
        suggested_project=project or "Research Foundry",
        paths=paths,
    )

    # --- triage (no local tree node; NLM is the source) ---------------------
    tri = triage_idea(
        cap.raw_idea_id,
        create_tree_node=False,
        paths=paths,
    )

    # Back-patch notebooklm_notebook_ref on the intent file so the correlation
    # layer and writeback service can find the originating notebook.
    intent_path: Path | None = tri.intent_path
    if intent_path is not None and intent_path.exists():
        _patch_notebooklm_ref(intent_path, notebook_id, project=project)

    return NLMIntakeResult(
        notebook_id=notebook_id,
        raw_idea_id=cap.raw_idea_id,
        intent_id=tri.intent_id,
        raw_idea_path=cap.path,
        intent_path=intent_path,
        offline=offline,
    )


# ---------------------------------------------------------------------------
# Internal helper — NLM back-patch
# ---------------------------------------------------------------------------


def _patch_notebooklm_ref(
    intent_path: Path,
    notebook_id: str,
    *,
    project: str | None = None,
) -> None:
    """Back-patch ``notebooklm_notebook_ref`` (and optionally ``project``) on
    the written intent file.

    Mirrors :func:`_patch_intent_node_ref` for the NLM integration path.
    """
    from ..yamlio import dump_yaml, load_yaml

    try:
        data = load_yaml(intent_path)
        if not isinstance(data, dict):
            return
        data["notebooklm_notebook_ref"] = notebook_id
        if project and not data.get("project"):
            data["project"] = project
        dump_yaml(data, intent_path)
    except Exception:  # noqa: BLE001 — fail-soft; never raise
        pass


__all__ = ["IntakeResult", "NLMIntakeResult", "intake_from_intenttree", "intake_from_notebooklm"]
