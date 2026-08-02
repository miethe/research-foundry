"""Backfill operations for the reusable assertion ledger.

Each submodule here targets one named backfill (e.g. the ERI legacy
``extraction_status`` backfill). A submodule's write path (its ``apply_*``
function) is gated on an explicit ``apply=True``/``--apply`` flag and on the
Mode-D human approval named in its own plan (see ``docs/project_plans/
implementation_plans/enhancements/eri-legacy-extraction-status-backfill-v1.md``
for the ERI legacy backfill specifically) -- the default for every submodule
is always a zero-write preview.
"""

from __future__ import annotations
