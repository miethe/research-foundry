"""Regression test for finding node_01M38EDYFJYJFCTYXTETD60V2M:
``swarm_drive._CLAIM_SCHEMA`` (the leg-bundle hint shown to Hermes) advertised
enums that ``schemas/claim_ledger.schema.yaml`` actually rejects. Assert the
enums advertised in ``_CLAIM_SCHEMA`` equal the schema file's own enum sets so
this cannot drift again.
"""

from __future__ import annotations

from research_foundry.paths import distribution_root
from research_foundry.services.swarm_drive import _CLAIM_SCHEMA
from research_foundry.yamlio import load_yaml


def _schema_enums() -> dict[str, list[str]]:
    raw = load_yaml(distribution_root() / "schemas" / "claim_ledger.schema.yaml")
    item_props = raw["properties"]["claims"]["items"]["properties"]
    source_props = item_props["sources"]["items"]["properties"]
    return {
        "claim_type": list(item_props["claim_type"]["enum"]),
        "materiality": list(item_props["materiality"]["enum"]),
        "status": list(item_props["status"]["enum"]),
        "relation": list(source_props["relation"]["enum"]),
    }


def test_claim_schema_enums_match_ledger_schema():
    schema_enums = _schema_enums()

    assert set(_CLAIM_SCHEMA["claim_type"].split("|")) == set(schema_enums["claim_type"])
    assert set(_CLAIM_SCHEMA["materiality"].split("|")) == set(schema_enums["materiality"])
    assert set(_CLAIM_SCHEMA["status"].split("|")) == set(schema_enums["status"])

    source_hint = _CLAIM_SCHEMA["sources"][0]["relation"]
    assert set(source_hint.split("|")) == set(schema_enums["relation"])
