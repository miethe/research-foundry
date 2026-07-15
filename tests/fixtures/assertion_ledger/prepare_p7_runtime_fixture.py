#!/usr/bin/env python3
"""Create a local-only P7 browser-smoke workspace from production services.

The resulting data are synthetic and remain under the caller-provided root.
They exercise the running API/viewer contract but are not private-provider or
owner authorization evidence.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def _write_run(paths: FoundryPaths, run_id: str, workspace_id: str, content: str) -> str:
    run = paths.run_paths(run_id).ensure_scaffold()
    dump_yaml(
        {
            "schema_version": "1.5",
            "run_id": run_id,
            "created_at": "2026-07-14T00:00:00Z",
            "status": "claim_mapped",
            "sensitivity": "personal",
            "tags": ["p7-runtime", workspace_id],
        },
        run.run_yaml,
    )
    ingest_source(
        f"{run_id}.txt",
        run_id=run_id,
        title=f"P7 synthetic {run_id}",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id=workspace_id,
        paths=paths,
    )
    extraction.extract_run(run_id, paths=paths)
    claim_mapping.build_claim_ledger(run_id, paths=paths)
    result = AssertionMaterializer(workspace_id=workspace_id, paths=paths).materialize_run(run_id)
    if result.status != "materialized":
        raise RuntimeError(f"{run_id}: materialization did not complete: {result}")
    ledger = load_yaml(run.claim_ledger)
    assert isinstance(ledger, dict)
    claim = ledger["claims"][0]
    run.report_draft.write_text(
        f"## P7 runtime evidence\n\n{claim['text']} [claim:{claim['claim_id']}]\n",
        encoding="utf-8",
    )
    return result.assertion_ids[0]


def _assertion_path(paths: FoundryPaths, workspace_id: str, assertion_id: str) -> Path:
    materializer = AssertionMaterializer(workspace_id=workspace_id, paths=paths)
    return materializer.root / "assertions" / f"{assertion_id}.yaml"


def _deny_workspace(paths: FoundryPaths, workspace_id: str) -> None:
    materializer = AssertionMaterializer(workspace_id=workspace_id, paths=paths)
    edition = next(materializer.root.glob("sources/*/editions/*.yaml"))
    payload = load_yaml(edition)
    assert isinstance(payload, dict)
    metadata = dict(payload.get("metadata_extensions") or {})
    metadata["allowed_use"] = {"allowed_for_work_output": False}
    payload["metadata_extensions"] = metadata
    dump_yaml(payload, edition)


def prepare(root: Path) -> dict[str, str]:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    dist = distribution_root()
    for directory in ("schemas", "config", "templates"):
        shutil.copytree(dist / directory, root / directory)
    foundry = load_yaml(dist / "foundry.yaml")
    assert isinstance(foundry, dict)
    configuration = foundry.setdefault("foundry", {})
    assert isinstance(configuration, dict)
    configuration["viewer"] = {"sensitivity_threshold": "personal", "bind_host": "127.0.0.1"}
    configuration["assertion_ledger"] = {"ledger_write_enabled": True}
    configuration["auth"] = {
        "provider": "local_static",
        "local_static": {
            "tokens": [
                {"token_env": "P7_TOKEN_ALICE", "user_id": "alice", "workspace_id": "workspace-a", "roles": ["owner"]},
                {"token_env": "P7_TOKEN_MALLORY", "user_id": "mallory", "workspace_id": "workspace-b", "roles": ["viewer"]},
            ]
        },
    }
    dump_yaml(foundry, root / "foundry.yaml")
    paths = FoundryPaths(root=root)

    full = _write_run(paths, "rf_run_p7_full", "workspace-a", "Full packet runtime evidence preserves exact provenance.")
    legacy = _write_run(paths, "rf_run_p7_legacy", "workspace-a", "Legacy packet runtime evidence omits optional qualifier extensions.")
    stale = _write_run(paths, "rf_run_p7_stale", "workspace-a", "Stale packet runtime evidence stays historically readable.")
    denied = _write_run(paths, "rf_run_p7_denied", "workspace-b", "Denied workspace evidence must not become discoverable.")

    legacy_payload = load_yaml(_assertion_path(paths, "workspace-a", legacy))
    assert isinstance(legacy_payload, dict)
    legacy_payload.pop("qualifier_extensions", None)
    dump_yaml(legacy_payload, _assertion_path(paths, "workspace-a", legacy))

    stale_payload = load_yaml(_assertion_path(paths, "workspace-a", stale))
    assert isinstance(stale_payload, dict)
    stale_payload["lifecycle_state"] = "stale"
    dump_yaml(stale_payload, _assertion_path(paths, "workspace-a", stale))
    _deny_workspace(paths, "workspace-b")

    manifest = {
        "full_run": "rf_run_p7_full",
        "full_assertion": full,
        "legacy_run": "rf_run_p7_legacy",
        "legacy_assertion": legacy,
        "stale_run": "rf_run_p7_stale",
        "stale_assertion": stale,
        "denied_run": "rf_run_p7_denied",
        "denied_assertion": denied,
    }
    (root / "p7-runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.root), sort_keys=True))


if __name__ == "__main__":
    main()
