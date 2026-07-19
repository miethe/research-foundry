"""Research Foundry — a Markdown/YAML-first research control plane.

Turns raw ideas into governed research swarms, evidence bundles, verifiable
reports, MeatyWiki writebacks, SkillBOM candidates, and CCDash telemetry.

The differentiated value is *claim traceability*: every material claim in a
research output maps to a source card or is explicitly labeled inference or
speculation. See ``services/verification.py`` and ``services/governance.py``.
"""

__version__ = "0.1.0"
SCHEMA_VERSION = "0.1"

#: Canonical semver contract-version stamped as the top-level ``rf_schema_version``
#: field on every machine-readable ``rf`` surface (CLI ``--json`` output, verify
#: YAML/JSON, and the LAN API payloads). This is distinct from ``SCHEMA_VERSION``
#: above (an unused legacy package-level constant) and from ``EXPORT_SCHEMA_VERSION``
#: in ``services/export_service.py`` (the runs-viewer run-export document schema,
#: currently "1.5") — those version independent, narrower contracts. Bump this only
#: when a stamped surface's shape changes; see
#: ``docs/dev/architecture/machine-surface-inventory.md`` for the full surface list
#: and per-surface stamping status.
RF_SCHEMA_VERSION = "1.0.0"

__all__ = ["__version__", "SCHEMA_VERSION", "RF_SCHEMA_VERSION"]
