"""Real jsonschema validation of the authored §17.1 SkillMeat tool profiles.

These 5 files (``skillmeat/tool_profiles/*.yaml``) are durable, versioned
catalog data — not per-run output — and back
``search_router.router._TOOL_PROFILE_BY_PROVIDER``. This module loads each
file from disk and validates it against ``schemas/tool_profile.schema.yaml``
via the project's :class:`SchemaRegistry` (a thin wrapper over
``jsonschema.Draft202012Validator``), so a future edit that re-wraps the
top-level keys (e.g. under a ``tool_profile:`` key) or drops a required field
fails CI instead of silently shipping an invalid profile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.paths import distribution_root
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.search_router.router import _TOOL_PROFILE_BY_PROVIDER
from research_foundry.yamlio import load_yaml

_TOOL_PROFILE_IDS = sorted(_TOOL_PROFILE_BY_PROVIDER.values())


def _tool_profiles_dir() -> Path:
    return distribution_root() / "skillmeat" / "tool_profiles"


@pytest.mark.parametrize("profile_id", _TOOL_PROFILE_IDS)
def test_authored_tool_profile_validates_against_schema(profile_id: str) -> None:
    """Each authored profile YAML is a flat, schema-valid ``tool_profile`` instance."""

    path = _tool_profiles_dir() / f"{profile_id}.yaml"
    assert path.exists(), f"missing tool-profile file: {path}"

    instance = load_yaml(path)
    assert isinstance(instance, dict), f"{path} did not load as a mapping"

    # The classic regression this test guards against: an authored profile
    # nested under a ``tool_profile:`` wrapper key instead of top-level
    # ``id``/``provider`` fields, which fails schema validation with
    # "'id' is a required property".
    assert "id" in instance, f"{path} is missing top-level 'id' (wrapped under a key?)"
    assert "provider" in instance, f"{path} is missing top-level 'provider'"

    registry = SchemaRegistry(schemas_dir=distribution_root() / "schemas")
    result = registry.validate(instance, "tool_profile")
    assert result.ok, f"{path} failed tool_profile schema validation: {result.errors}"
    assert instance["id"] == profile_id


def test_tool_profile_ids_match_router_provider_mapping() -> None:
    """Every id referenced by router._TOOL_PROFILE_BY_PROVIDER resolves to a real,
    schema-valid file whose ``id``/``provider`` fields match the router's mapping.
    """

    for router_provider_id, profile_id in _TOOL_PROFILE_BY_PROVIDER.items():
        path = _tool_profiles_dir() / f"{profile_id}.yaml"
        instance = load_yaml(path)
        assert instance["id"] == profile_id
        assert instance["provider"] == router_provider_id


def test_no_stray_tool_profile_wrapper_key() -> None:
    """No authored profile should re-introduce the invalid ``tool_profile:`` wrapper."""

    for path in sorted(_tool_profiles_dir().glob("*.yaml")):
        instance = load_yaml(path)
        assert isinstance(instance, dict)
        assert "tool_profile" not in instance, (
            f"{path} still wraps its fields under a 'tool_profile:' key — "
            "flatten so id/provider/etc. are top-level"
        )
