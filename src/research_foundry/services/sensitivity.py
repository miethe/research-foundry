"""Shared sensitivity ordinal ranking across two parallel vocabularies.

Promoted out of ``rf agent-job``'s CLI filters (``cli/commands/agent_job.py``,
``list``/``stream`` subcommands each carried their own copy) so every caller
comparing a sensitivity label against a threshold shares one ordering.
:func:`~research_foundry.services.catalog_retrieval._project_reuse_input`
also imports this to rank ``source_edition.access_scope`` against a
caller-supplied threshold (CARP-2.G finding). A second, independently
maintained copy of a governance ordering is itself a governance defect --
this module exists so there is exactly one.

This map actually ranks **two distinct vocabularies** that happen to share
their lower tiers:

* ``source_edition.access_scope`` (``assertion_catalog.py``'s
  ``_rights_decision`` known-set): ``public``, ``personal``,
  ``work_sensitive``, ``client_sensitive``, ``private`` -- ``private`` is
  this vocabulary's most-sensitive member. It has no ``top_secret`` value.
* Run/agent-job ``sensitivity`` thresholds (``cli/commands/agent_job.py``):
  ``public``, ``personal``, ``work_sensitive``, ``client_sensitive``,
  ``top_secret`` -- ``top_secret`` is this vocabulary's most-sensitive
  member. It has no ``private`` value.

``private`` and ``top_secret`` are each vocabulary's own "most sensitive"
label, never used by the other caller, so they are ranked co-top (same
ordinal) rather than as two separate tiers -- a caller comparing across
vocabularies (e.g. an access-scope value against a run-sensitivity
threshold) still gets a coherent ordering instead of an arbitrary one.

Distinct from :data:`research_foundry.services.export_service.SENSITIVITY_ORDER`,
which ranks a different vocabulary (run/report ``sensitivity``, four levels,
no ``top_secret``) for the export/redaction pipeline. Do not merge the two:
they rank different fields for different consumers.
"""

from __future__ import annotations

SENSITIVITY_RANK: dict[str, int] = {
    "public": 0,
    "personal": 1,
    "work_sensitive": 2,
    "client_sensitive": 3,
    "private": 4,
    "top_secret": 4,
}

__all__ = ["SENSITIVITY_RANK"]
