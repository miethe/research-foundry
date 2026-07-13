"""Deterministic identity rules for immutable source assertions.

The JSON Schema describes the fields and their individual shapes.  This module
binds the identity fields to their canonical payload, which JSON Schema alone
cannot express (hash calculation and cross-field equality).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

SOURCE_ASSERTION_IDENTITY_ALGORITHM = "sha256-canonical-json-v1"
SOURCE_ASSERTION_MATERIAL_FIELDS = (
    "source_edition_id",
    "passage_id",
    "assertion_text_sha256",
    "qualifiers",
    "qualifier_extensions",
)


def canonical_source_assertion_payload(assertion: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact payload from which an assertion identity is derived."""

    return {
        field: assertion.get(field)
        for field in SOURCE_ASSERTION_MATERIAL_FIELDS
    }


def canonical_source_assertion_json(assertion: Mapping[str, Any]) -> str:
    """Serialize the identity payload with the stable v1 canonical JSON form."""

    return json.dumps(
        canonical_source_assertion_payload(assertion),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def source_assertion_fingerprint(assertion: Mapping[str, Any]) -> str:
    """Calculate the SHA-256 fingerprint for a source assertion payload."""

    return sha256(canonical_source_assertion_json(assertion).encode("utf-8")).hexdigest()


def source_assertion_id(assertion: Mapping[str, Any]) -> str:
    """Calculate the public immutable source-assertion identifier."""

    return f"ast_{source_assertion_fingerprint(assertion)}"


def validate_source_assertion_identity(instance: Mapping[str, Any]) -> list[str]:
    """Return deterministic identity binding errors for a source assertion."""

    errors: list[str] = []
    text = instance.get("assertion_text")
    text_digest = instance.get("assertion_text_sha256")
    if isinstance(text, str) and isinstance(text_digest, str):
        expected_text_digest = sha256(text.encode("utf-8")).hexdigest()
        if text_digest != expected_text_digest:
            errors.append(
                "assertion_text_sha256: must equal the SHA-256 digest of assertion_text"
            )

    identity = instance.get("identity")
    if not isinstance(identity, Mapping):
        return errors

    if identity.get("algorithm") != SOURCE_ASSERTION_IDENTITY_ALGORITHM:
        errors.append("identity/algorithm: must use sha256-canonical-json-v1")
    if identity.get("material_fields") != list(SOURCE_ASSERTION_MATERIAL_FIELDS):
        errors.append(
            "identity/material_fields: must list the v1 material fields in canonical order"
        )

    fingerprint = source_assertion_fingerprint(instance)
    if identity.get("fingerprint") != fingerprint:
        errors.append(
            "identity/fingerprint: must equal the SHA-256 digest of the canonical identity payload"
        )
    if instance.get("assertion_id") != f"ast_{fingerprint}":
        errors.append("assertion_id: must equal ast_ plus the canonical identity fingerprint")
    return errors


__all__ = [
    "SOURCE_ASSERTION_IDENTITY_ALGORITHM",
    "SOURCE_ASSERTION_MATERIAL_FIELDS",
    "canonical_source_assertion_json",
    "canonical_source_assertion_payload",
    "source_assertion_fingerprint",
    "source_assertion_id",
    "validate_source_assertion_identity",
]
