"""Error types and process exit codes for Research Foundry.

The exit codes are a stable contract (spec §10.10) used by ``rf verify`` and
other commands so that CI and the execution loop can branch on outcomes.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Stable CLI exit codes (spec §10.10).

    These map deterministically to failure classes so automation can react
    without parsing text output.
    """

    OK = 0
    USAGE = 1
    SCHEMA = 2          # Schema validation failed
    GOVERNANCE = 3      # Governance policy blocked
    UNSUPPORTED = 4     # Unsupported material claim
    BUDGET = 5          # Budget exceeded
    ADAPTER = 6         # Adapter / tool failure
    HUMAN_REVIEW = 7    # Human review required


class RFError(Exception):
    """Base class for all Research Foundry errors.

    Carries an :class:`ExitCode` so the CLI can translate any raised error into
    the correct process exit status.
    """

    exit_code: ExitCode = ExitCode.USAGE

    def __init__(self, message: str, *, exit_code: ExitCode | None = None) -> None:
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class SchemaError(RFError):
    exit_code = ExitCode.SCHEMA


class GovernanceError(RFError):
    """Raised when a governance policy rule with severity ``block`` fires."""

    exit_code = ExitCode.GOVERNANCE

    def __init__(self, message: str, *, violations: list[str] | None = None) -> None:
        super().__init__(message)
        self.violations = violations or []


class UnsupportedClaimError(RFError):
    exit_code = ExitCode.UNSUPPORTED


class BudgetError(RFError):
    exit_code = ExitCode.BUDGET


class AdapterError(RFError):
    exit_code = ExitCode.ADAPTER


class HumanReviewRequired(RFError):
    exit_code = ExitCode.HUMAN_REVIEW


class NotFoundError(RFError):
    """A referenced artifact (run, intent, source card, ...) does not exist."""

    exit_code = ExitCode.USAGE


__all__ = [
    "ExitCode",
    "RFError",
    "SchemaError",
    "GovernanceError",
    "UnsupportedClaimError",
    "BudgetError",
    "AdapterError",
    "HumanReviewRequired",
    "NotFoundError",
]
