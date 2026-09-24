#!/usr/bin/env python3
"""Thin CLI: fulfil an emitted ``leg_requests.yaml`` via ``ica-claude.sh``.

Not imported by the ``research_foundry`` package (rf's own package stays
zero-model) -- this is the out-of-band caller that injects the real model
call into ``research_foundry.services.leg_fulfilment.fulfil_run``.

Usage::

    python scripts/rf_fulfil_ica_legs.py <run_id> \\
        [--ica-bin ~/ica-claude.sh]

Models are the ones each leg in ``leg_requests.yaml`` advertises (carding:
``claude-haiku-4-5[1m]``, claim map: ``claude-sonnet-5[1m]``); every call,
including a crash or timeout, is journaled to the run's ``leg_calls.jsonl``
and counted in ``leg_receipts.yaml``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def build_call_leg(ica_bin: str):
    """Build a ``call_leg(prompt, model, max_turns)`` bound to ``ica_bin``."""

    def call_leg(prompt: str, model: str | None, max_turns: int | None) -> dict[str, Any]:
        cmd = [ica_bin, "-p", prompt]
        if model:
            cmd += ["--model", str(model)]
        cmd += ["--output-format", "json"]
        if max_turns:
            cmd += ["--max-turns", str(max_turns)]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=900, check=False
            )
        except (subprocess.TimeoutExpired, OSError):
            return {"result": None, "num_turns": None, "is_error": True}

        last_json: dict[str, Any] | None = None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(obj, dict):
                last_json = obj

        if last_json is None:
            return {"result": None, "num_turns": None, "is_error": True}

        return {
            "result": last_json.get("result"),
            "num_turns": last_json.get("num_turns"),
            "is_error": bool(last_json.get("is_error")) or proc.returncode != 0,
        }

    return call_leg


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--ica-bin", default=str(Path.home() / "ica-claude.sh"))
    args = parser.parse_args()

    from research_foundry.paths import FoundryPaths
    from research_foundry.services.leg_fulfilment import fulfil_run

    call_leg = build_call_leg(args.ica_bin)
    summary = fulfil_run(args.run_id, call_leg=call_leg, paths=FoundryPaths.discover())
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
