"""TASK-1.6a (ENTRY-BLOCKING GUARD TEST): `_term_index` must never affect
source-assertion identity (D2/D8, decisions-block.md). Fails loudly if a
future PR ever adds `_term_index` (or any other derived field) to
`SOURCE_ASSERTION_MATERIAL_FIELDS`.
"""

from __future__ import annotations

import copy

from research_foundry.assertion_identity import (
    SOURCE_ASSERTION_MATERIAL_FIELDS,
    source_assertion_fingerprint,
    source_assertion_id,
)

_ASSERTION = {
    "source_edition_id": "ed_20260724_aaaaaaaa",
    "passage_id": "pas_0001",
    "assertion_text": "Hemoglobin below 11.0 g/dL indicates anemia in this population.",
    "assertion_text_sha256": "de" * 32,
    "qualifiers": ["threshold"],
    "qualifier_extensions": {"note": "pediatric"},
}


def test_term_index_key_does_not_change_fingerprint_or_id():
    baseline_fingerprint = source_assertion_fingerprint(_ASSERTION)
    baseline_id = source_assertion_id(_ASSERTION)

    with_term_index = copy.deepcopy(_ASSERTION)
    with_term_index["_term_index"] = {
        "terms": ["hemoglobin", "anemia"],
        "usage_roles": {"hemoglobin": "threshold", "anemia": "background"},
        "vocabulary_version": "pediatric-terms-v1",
    }

    assert source_assertion_fingerprint(with_term_index) == baseline_fingerprint
    assert source_assertion_id(with_term_index) == baseline_id


def test_term_index_is_never_added_to_the_material_fields_tuple():
    """The guard this test exists for: fails loudly the moment a future PR
    adds `_term_index` (or a bare `usage_role`) to the identity-hash's fixed
    5-tuple, which would make the assertion id depend on derived,
    non-authoritative data."""

    assert "_term_index" not in SOURCE_ASSERTION_MATERIAL_FIELDS
    assert "usage_role" not in SOURCE_ASSERTION_MATERIAL_FIELDS
    assert SOURCE_ASSERTION_MATERIAL_FIELDS == (
        "source_edition_id",
        "passage_id",
        "assertion_text_sha256",
        "qualifiers",
        "qualifier_extensions",
    )
