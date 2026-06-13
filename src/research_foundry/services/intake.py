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


__all__ = ["IntakeResult", "intake_from_intenttree"]
