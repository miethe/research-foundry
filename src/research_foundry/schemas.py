"""Schema registry + validation.

Schemas live as JSON Schema (Draft 2020-12) authored in YAML under
``schemas/*.schema.yaml`` — the literal source of truth for every artifact's
shape. This module loads them and validates instance documents, returning a
list of human-readable error strings (empty == valid).

The registry resolves the ``schemas/`` directory from the active workspace,
falling back to the distribution root so it works both inside a foundry and
from a fresh checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from .paths import FoundryPaths, distribution_root
from .yamlio import load_yaml

SCHEMA_SUFFIX = ".schema.yaml"


def _schemas_dir(start: str | Path | None = None) -> Path:
    paths = FoundryPaths.discover(start)
    if paths.schemas.exists():
        return paths.schemas
    dist = distribution_root() / "schemas"
    return dist if dist.exists() else paths.schemas


@dataclass
class ValidationResult:
    """Outcome of validating one instance against one schema."""

    schema: str
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:  # truthy == valid
        return self.ok


class SchemaRegistry:
    """Loads and caches JSON Schemas from a ``schemas/`` directory."""

    def __init__(self, schemas_dir: str | Path | None = None) -> None:
        self.dir = Path(schemas_dir) if schemas_dir else _schemas_dir()

    @cache  # noqa: B019  (registry instances are long-lived)
    def _load(self, name: str) -> dict[str, Any]:
        path = self.dir / f"{name}{SCHEMA_SUFFIX}"
        if not path.exists():
            raise FileNotFoundError(f"Schema not found: {path}")
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise ValueError(f"Schema {path} is not a mapping")
        return data

    def names(self) -> list[str]:
        if not self.dir.exists():
            return []
        return sorted(
            p.name[: -len(SCHEMA_SUFFIX)]
            for p in self.dir.glob(f"*{SCHEMA_SUFFIX}")
        )

    def has(self, name: str) -> bool:
        return (self.dir / f"{name}{SCHEMA_SUFFIX}").exists()

    def get(self, name: str) -> dict[str, Any]:
        return self._load(name)

    def validate(self, instance: Any, schema_name: str) -> ValidationResult:
        """Validate ``instance`` against the named schema.

        Returns a :class:`ValidationResult`; ``.errors`` is a list of
        ``path: message`` strings (sorted, deterministic). A missing schema is
        reported as a single error rather than raising, so the CLI can surface
        it uniformly.
        """

        try:
            schema = self.get(schema_name)
        except (FileNotFoundError, ValueError) as exc:
            return ValidationResult(schema=schema_name, errors=[str(exc)])

        # Imported lazily so the package imports even if jsonschema is absent
        # in some minimal environment; validation then reports the missing dep.
        try:
            from jsonschema import Draft202012Validator
        except ImportError as exc:  # pragma: no cover - dep declared in pyproject
            return ValidationResult(schema=schema_name, errors=[f"jsonschema unavailable: {exc}"])

        validator = Draft202012Validator(schema)
        errors = []
        for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{loc}: {err.message}")
        return ValidationResult(schema=schema_name, errors=errors)


@lru_cache(maxsize=1)
def default_registry() -> SchemaRegistry:
    """Process-wide default registry resolved from the active workspace."""

    return SchemaRegistry()


def validate(instance: Any, schema_name: str) -> ValidationResult:
    """Convenience: validate against the default registry."""

    return default_registry().validate(instance, schema_name)


__all__ = [
    "SchemaRegistry",
    "ValidationResult",
    "default_registry",
    "validate",
    "SCHEMA_SUFFIX",
]
