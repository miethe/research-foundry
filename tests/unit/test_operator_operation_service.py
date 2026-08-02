"""Unit tests for `operator_operation_service` (research-foundry-operator-mcp-v1
P2, OPM-2.1 -- DUR-1: durable, atomic confirmation-consumption + operation-
manifest persistence).

Reuses `test_operator_mcp_policy`'s `tmp_foundry`-threading conventions and
its `_write_operator_identity` / `_default_operator_identity` / `_basic_ctx`
helpers rather than reinventing identity-resolution fixtures -- see that
module's own docstring for why `PolicyContext.identity` has no public
constructor field and must be driven through
`policy.resolve_operator_identity` (monkeypatched by the imported
`_default_operator_identity` autouse fixture).

Covers (OPM-2.1 acceptance criteria):

* exact manifest replay resolves the SAME operation -- both via the SAME
  confirmation presented twice (P1's own `exact_replay` outcome) and via a
  FRESH confirmation under the same `(workspace_id, idempotency_key)` with
  an identical canonical digest;
* a changed manifest under the same idempotency_key is an
  `idempotency_conflict` -- zero manifest, zero effect, confirmation left
  unconsumed;
* every non-`issued` confirmation status (consumed-with-mismatch, expired,
  revoked) routes to a denial with zero manifest;
* a binding mismatch (any bound field differs from what was minted) denies;
* the clamped TTL expiry denies;
* a wrong-workspace `load_operation` lookup is indistinguishable from a
  genuinely missing one;
* real concurrency: two threads racing to consume the SAME confirmation
  yield exactly one `"created"`, one `"exact_replay"`, and exactly one
  persisted manifest row -- this is the DUR-1 property a read-then-write
  implementation cannot provide.

Also covers four defects found on re-review of the above (see each
section's own docstring for detail):

* F1 -- `consume_and_create_operation` now requires an `AuthorizationProof`
  (obtained ONLY via `authorize_for_consumption`) as a DATA dependency, not
  a docstring instruction; absent/`None`/wrong-ctx/pre-confirmation-stage-
  denied proofs all deny before any persistence is touched;
* F2 -- the public `now` seam is gone from `consume_and_create_operation`;
  the CAS moment is always `research_foundry.ids.now()`;
* F3 -- `record_confirmation` no longer defaults a missing `status` to
  `"issued"` or a missing `issued_at` to now; both are required, and the
  denormalized `status` COLUMN can never diverge from the `record_json`
  blob's own `status` field;
* F4 -- the DUR-1 CAS-invariant violation (`rowcount != 1`) never crosses
  `consume_and_create_operation`'s boundary as a raw exception; it comes
  back as a bounded `OperationOutcome("denied", "internal_error", None)`.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import multiprocessing
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import operator_operation_service as service_module
from research_foundry.services.operator_attempt_adapter import OperatorAttemptAdapter
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import (
    AuthorizationProof,
    ConfirmationPersistenceError,
    OperationOutcome,
    OperatorOperationService,
    authorize_for_consumption,
)
from research_foundry.services.operator_receipt_service import OperatorReceiptService

# Reuse, never reinvent (per this task's instructions): the policy test
# module's identity fixtures/helpers. `_default_operator_identity` is an
# autouse fixture; importing the decorated function object into this
# module's namespace registers it as an autouse fixture HERE too.
from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _IDENTITY,
    _IDENTITY_OTHER_WORKSPACE,
    _VIEWER_IDENTITY,
    _basic_ctx,
    _default_operator_identity,
    _run_targets,
    _write_operator_identity,
)

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


def _mint_and_record(
    service: OperatorOperationService,
    ctx: policy.PolicyContext,
    *,
    now: datetime | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """Mint a confirmation for `ctx` and durably persist it. Returns
    `(confirmation_id, presented_token, record)` -- `record` is the
    freshly-minted, still-`"issued"` schema-shaped confirmation record
    (P1's `mint_confirmation(...).record`), for callers that need to build
    an `AuthorizationProof` (F1) against it.

    Defaults `now` to `ids.now()` (the repo-wide injectable clock, pinned
    by the autouse `_fixed_clock` fixture) rather than leaving it `None` --
    `policy.mint_confirmation`'s OWN `now` default is REAL wall-clock time
    (that module is frozen, unrelated to `ids`), so leaving it unset here
    would mint an `issued_at` using the real clock while F2 makes this
    service's own consumption `moment` always `ids.now()` (the pinned
    sentinel). Since the pinned sentinel is chronologically BEFORE real
    wall-clock time, that mismatch makes every confirmation look "issued in
    the future" relative to consumption -- `_record_expiry`'s NEW-7 guard
    (`issued_at > moment -> always expired`) then denies it. Aligning both
    on the SAME `ids.now()` by default avoids that entirely; a test that
    wants to exercise real expiry passes an explicit `now=` here AND to
    `_authorize`/monkeypatches `ids.now` for the consume-time moment (see
    `test_expired_confirmation_denies_with_zero_manifest`)."""

    moment = now if now is not None else ids.now()
    issued = policy.mint_confirmation(ctx, now=moment)
    service.record_confirmation(issued.record)
    return issued.record["confirmation_id"], issued.token, dict(issued.record)


def _authorize(
    paths: FoundryPaths,
    ctx: policy.PolicyContext,
    *,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    now: datetime | None = None,
) -> AuthorizationProof:
    """Thin test-local wrapper around `authorize_for_consumption` -- the
    ONE sanctioned way (F1) to obtain the `AuthorizationProof`
    `consume_and_create_operation` now requires.

    Defaults `now` to `ids.now()` for the same reason `_mint_and_record`
    does -- `policy.authorize_operation`'s own `now` default is real
    wall-clock time, and this module's `moment` is always `ids.now()`."""

    moment = now if now is not None else ids.now()
    return authorize_for_consumption(
        ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        paths=paths,
        now=moment,
    )


def _raw_connect(paths: FoundryPaths) -> sqlite3.Connection:
    conn = sqlite3.connect(str(paths.operator_operations_db))
    conn.row_factory = sqlite3.Row
    return conn


def _count_operations(paths: FoundryPaths) -> int:
    conn = _raw_connect(paths)
    try:
        return conn.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
    finally:
        conn.close()


def _confirmation_status(paths: FoundryPaths, confirmation_id: str) -> str:
    conn = _raw_connect(paths)
    try:
        row = conn.execute(
            "SELECT status FROM confirmations WHERE confirmation_id = ?",
            (confirmation_id,),
        ).fetchone()
        assert row is not None
        return row["status"]
    finally:
        conn.close()


def _load_confirmation_record(paths: FoundryPaths, confirmation_id: str) -> dict[str, Any]:
    """Read back the CURRENT `record_json` blob for a confirmation --
    mirrors what a real caller would have to do to build a second,
    up-to-date `AuthorizationProof` after the row has changed underneath
    the first one (e.g. re-presenting an already-consumed confirmation)."""

    conn = _raw_connect(paths)
    try:
        row = conn.execute(
            "SELECT record_json FROM confirmations WHERE confirmation_id = ?",
            (confirmation_id,),
        ).fetchone()
        assert row is not None
        return json.loads(row["record_json"])
    finally:
        conn.close()


def _force_confirmation_status(paths: FoundryPaths, confirmation_id: str, status: str) -> None:
    """Force a confirmation to a non-`issued` status for test setup.

    Updates BOTH the denormalized `status` column (the CAS predicate's own
    gate) AND the `record_json` blob's internal `status` field (what
    `verify_confirmation`/`consume_confirmation` actually read) -- these two
    must always agree; `_consume_locked` itself only ever writes them
    together, and `record_confirmation` (post-F3) only ever writes a
    validated `status="issued"` for both. A test that mutated only the
    column would desynchronize them and exercise a state this store's own
    write path can never produce -- see
    `test_dur1_cas_invariant_violation_returns_governed_denial_not_raw_exception`
    (F4) for a test that deliberately DOES desync them, directly via raw
    SQL, to exercise that unreachable-via-this-module's-own-writes branch.
    """

    conn = _raw_connect(paths)
    try:
        row = conn.execute(
            "SELECT record_json FROM confirmations WHERE confirmation_id = ?",
            (confirmation_id,),
        ).fetchone()
        assert row is not None
        record = json.loads(row["record_json"])
        record["status"] = status
        conn.execute(
            "UPDATE confirmations SET status = ?, record_json = ? WHERE confirmation_id = ?",
            (status, json.dumps(record), confirmation_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Happy path: create + persist + load, schema-shape-valid
# ---------------------------------------------------------------------------


def test_consume_creates_operation_and_consumes_confirmation(
    tmp_foundry: FoundryPaths,
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )

    assert outcome.outcome == "created"
    assert outcome.reason_code is None
    assert outcome.operation is not None
    assert outcome.operation.operation_id.startswith("opm_")
    assert outcome.operation.workspace_id == _IDENTITY.workspace_id
    assert outcome.operation.manifest["confirmation_proof"]["confirmation_id"] == confirmation_id
    assert _confirmation_status(tmp_foundry, confirmation_id) == "consumed"
    assert _count_operations(tmp_foundry) == 1

    # Schema-shape valid: the nested operation envelope round-trips through
    # the real operator_mcp_operation schema, not merely "no exception was
    # raised during creation".
    registry = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    result = registry.validate(outcome.operation.manifest["operation"], "operator_mcp_operation")
    assert result.ok, result.errors

    loaded = service.load_operation(outcome.operation.operation_id)
    assert loaded.operation_id == outcome.operation.operation_id
    assert loaded.manifest == outcome.operation.manifest


# ---------------------------------------------------------------------------
# K3-NB-5: authoritative, persisted action_index -> action_id binding
# ---------------------------------------------------------------------------


def test_declared_action_ids_bind_action_index_to_action_id_for_every_contiguous_index(
    tmp_foundry: FoundryPaths,
) -> None:
    """(a) a created operation exposes the expected `action_id` for each
    contiguous `action_index` 0..N-1, read back via the PERSISTED manifest
    (`get_expected_action_id`), not any in-memory state from this test."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="idem-k3nb5-a")
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    declared_action_ids = ["fetch_source", "extract_claims", "write_bundle"]
    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
        declared_action_ids=declared_action_ids,
    )
    assert outcome.outcome == "created"
    assert outcome.operation is not None
    operation_id = outcome.operation.operation_id

    for index, action_id in enumerate(declared_action_ids):
        assert service.get_expected_action_id(operation_id, index) == action_id

    # The binding is persisted inside the open `action_manifest` map region,
    # never a new top-level manifest field.
    persisted = service.load_operation(operation_id).manifest["action_manifest"]
    assert persisted["_action_index_binding"] == {"0": "fetch_source", "1": "extract_claims", "2": "write_bundle"}


def test_get_expected_action_id_returns_none_for_unknown_or_out_of_range_index(
    tmp_foundry: FoundryPaths,
) -> None:
    """(b) an index the operation never declared -- past the end of the
    sequence, or negative -- returns `None`, never a raised exception or a
    fabricated action_id."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="idem-k3nb5-b")
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
        declared_action_ids=["only_action"],
    )
    assert outcome.outcome == "created"
    assert outcome.operation is not None
    operation_id = outcome.operation.operation_id

    assert service.get_expected_action_id(operation_id, 0) == "only_action"
    assert service.get_expected_action_id(operation_id, 1) is None
    assert service.get_expected_action_id(operation_id, 999) is None
    assert service.get_expected_action_id(operation_id, -1) is None

    # A wholly unknown operation_id is likewise `None`, never an exception.
    assert service.get_expected_action_id("opm_does_not_exist", 0) is None


def test_operation_with_no_declared_actions_has_empty_binding_and_none_accessor(
    tmp_foundry: FoundryPaths,
) -> None:
    """(c) an operation created with no action list at all (`declared_action_ids`
    omitted) persists an empty binding, not a missing/None `action_manifest`
    field, and the accessor returns `None` for any index without error."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="idem-k3nb5-c")
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "created"
    assert outcome.operation is not None
    operation_id = outcome.operation.operation_id

    persisted = service.load_operation(operation_id).manifest["action_manifest"]
    assert persisted["_action_index_binding"] == {}

    assert service.get_expected_action_id(operation_id, 0) is None
    assert service.get_expected_action_id(operation_id, 1) is None


# ---------------------------------------------------------------------------
# Exact manifest replay resolves the SAME operation
# ---------------------------------------------------------------------------


def test_same_confirmation_presented_twice_is_exact_replay_of_same_operation(
    tmp_foundry: FoundryPaths,
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    first_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    first = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=first_authorization,
    )
    assert first.outcome == "created"
    assert first.operation is not None

    # A real caller re-presenting the SAME confirmation must re-fetch its
    # NOW-consumed record to build a fresh proof -- `authorize_operation`
    # itself denies an exact-replay presentation (`confirmation_replayed`,
    # C1/NEW-1), but at `stage="confirmation"` (the five gate stages already
    # passed), which is exactly what lets `consume_and_create_operation`'s
    # gate admit it through to `_consume_locked`'s own replay resolution.
    consumed_record = _load_confirmation_record(tmp_foundry, confirmation_id)
    second_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=consumed_record, presented_token=token
    )
    assert second_authorization.decision.denied
    assert second_authorization.decision.stage == "confirmation"
    assert second_authorization.decision.reason_code == "confirmation_replayed"

    second = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=second_authorization,
    )
    assert second.outcome == "exact_replay"
    assert second.reason_code is None
    assert second.operation is not None
    assert second.operation.operation_id == first.operation.operation_id
    assert _count_operations(tmp_foundry) == 1


def test_fresh_confirmation_same_idempotency_key_and_digest_is_exact_replay(
    tmp_foundry: FoundryPaths,
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="idem-fixed")

    confirmation_id_1, token_1, record_1 = _mint_and_record(service, ctx)
    first_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record_1, presented_token=token_1
    )
    first = service.consume_and_create_operation(
        confirmation_id=confirmation_id_1,
        presented_token=token_1,
        ctx=ctx,
        authorization=first_authorization,
    )
    assert first.outcome == "created"
    assert first.operation is not None

    # A SEPARATE mint (fresh confirmation_id/token) for the SAME logical
    # request (identical canonical fields -> identical digest). This
    # confirmation is itself fresh/`"issued"` -- authorize_operation
    # ACCEPTS it (not a replay at the confirmation-binding level); the
    # idempotency-key collision is resolved by `_consume_locked` itself.
    confirmation_id_2, token_2, record_2 = _mint_and_record(service, ctx)
    assert confirmation_id_2 != confirmation_id_1
    second_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record_2, presented_token=token_2
    )
    assert second_authorization.decision.allowed

    second = service.consume_and_create_operation(
        confirmation_id=confirmation_id_2,
        presented_token=token_2,
        ctx=ctx,
        authorization=second_authorization,
    )
    assert second.outcome == "exact_replay"
    assert second.operation is not None
    assert second.operation.operation_id == first.operation.operation_id
    # The SECOND confirmation is still consumed (a legitimately bound
    # confirmation for the same retried request), pointing at the
    # pre-existing operation -- but no duplicate manifest was created.
    assert _confirmation_status(tmp_foundry, confirmation_id_2) == "consumed"
    assert _count_operations(tmp_foundry) == 1


# ---------------------------------------------------------------------------
# Changed manifest, same idempotency_key -> conflict, zero effect
# ---------------------------------------------------------------------------


def test_changed_manifest_same_idempotency_key_is_idempotency_conflict(
    tmp_foundry: FoundryPaths,
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx1 = _basic_ctx(targets=_run_targets(), idempotency_key="idem-shared")
    confirmation_id_1, token_1, record_1 = _mint_and_record(service, ctx1)
    authorization_1 = _authorize(
        tmp_foundry, ctx1, confirmation_record=record_1, presented_token=token_1
    )
    first = service.consume_and_create_operation(
        confirmation_id=confirmation_id_1,
        presented_token=token_1,
        ctx=ctx1,
        authorization=authorization_1,
    )
    assert first.outcome == "created"

    # Same idempotency_key, DIFFERENT operation_kind -> different canonical
    # digest -- a genuine idempotency-key collision, not a retry.
    ctx2 = _basic_ctx(
        targets=_run_targets(),
        idempotency_key="idem-shared",
        operation_kind="run.extract",
    )
    confirmation_id_2, token_2, record_2 = _mint_and_record(service, ctx2)
    authorization_2 = _authorize(
        tmp_foundry, ctx2, confirmation_record=record_2, presented_token=token_2
    )

    second = service.consume_and_create_operation(
        confirmation_id=confirmation_id_2,
        presented_token=token_2,
        ctx=ctx2,
        authorization=authorization_2,
    )
    assert second.outcome == "idempotency_conflict"
    assert second.reason_code == "idempotency_conflict"
    assert second.operation is None
    # Zero effect: no new manifest, AND the second confirmation was never
    # consumed for a request the server refused to execute.
    assert _count_operations(tmp_foundry) == 1
    assert _confirmation_status(tmp_foundry, confirmation_id_2) == "issued"


# ---------------------------------------------------------------------------
# Non-`issued` status routes to conflict/denial with zero manifest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bad_status", "expected_reason_code"),
    [("expired", "confirmation_expired"), ("revoked", "confirmation_mismatch")],
)
def test_non_issued_confirmation_status_denies_with_zero_manifest(
    tmp_foundry: FoundryPaths, bad_status: str, expected_reason_code: str
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, _record = _mint_and_record(service, ctx)
    _force_confirmation_status(tmp_foundry, confirmation_id, bad_status)
    forced_record = _load_confirmation_record(tmp_foundry, confirmation_id)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=forced_record, presented_token=token
    )
    assert authorization.decision.stage == "confirmation"
    assert authorization.decision.reason_code == expected_reason_code

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    # The PRECISE reason code matters, not merely "denied" -- a fallback
    # guard elsewhere in the CAS (`consume_confirmation`'s own status check)
    # would also produce a "denied" outcome here but with the wrong,
    # less-specific `idempotency_conflict` reason if the dedicated
    # verify_confirmation pre-check were ever removed.
    assert outcome.reason_code == expected_reason_code
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0


def test_consumed_confirmation_with_mismatched_bindings_denies_as_conflict(
    tmp_foundry: FoundryPaths,
) -> None:
    """A `status: consumed` record whose bindings no longer match the
    presented ctx (distinct from the SAME-ctx exact-replay case above) is
    `idempotency_conflict`, per `verify_confirmation`'s own contract."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )
    first = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert first.outcome == "created"

    changed_ctx = dataclasses.replace(ctx, idempotency_key="a-different-key")
    consumed_record = _load_confirmation_record(tmp_foundry, confirmation_id)
    changed_authorization = _authorize(
        tmp_foundry, changed_ctx, confirmation_record=consumed_record, presented_token=token
    )
    assert changed_authorization.decision.stage == "confirmation"
    assert changed_authorization.decision.reason_code == "idempotency_conflict"

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=changed_ctx,
        authorization=changed_authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "idempotency_conflict"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 1  # only the first, unchanged


# ---------------------------------------------------------------------------
# Binding mismatch on a still-`issued` confirmation denies
# ---------------------------------------------------------------------------


def test_binding_mismatch_on_issued_confirmation_denies(tmp_foundry: FoundryPaths) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)

    changed_ctx = dataclasses.replace(ctx, effective_sensitivity="work_sensitive")
    authorization = _authorize(
        tmp_foundry, changed_ctx, confirmation_record=record, presented_token=token
    )
    assert authorization.decision.stage == "confirmation"
    assert authorization.decision.reason_code == "confirmation_mismatch"

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=changed_ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "confirmation_mismatch"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # The confirmation itself is untouched -- still issued, available for a
    # correctly-bound retry within its TTL.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


# ---------------------------------------------------------------------------
# Clamped TTL expiry denies
# ---------------------------------------------------------------------------


def test_expired_confirmation_denies_with_zero_manifest(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    confirmation_id, token, record = _mint_and_record(service, ctx, now=minted_at)

    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token, now=later
    )
    assert authorization.decision.stage == "confirmation"
    assert authorization.decision.reason_code == "confirmation_expired"

    # F2: `consume_and_create_operation` no longer accepts a public `now` --
    # the CAS moment is always `ids.now()`. Move the injectable clock
    # forward for the duration of this call (mirrors how every other
    # service in this codebase tests time-dependent behaviour).
    monkeypatch.setattr(ids, "now", lambda: later)
    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "confirmation_expired"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


# ---------------------------------------------------------------------------
# Missing confirmation
# ---------------------------------------------------------------------------


def test_missing_confirmation_id_denies(tmp_foundry: FoundryPaths) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=None, presented_token="whatever-token"
    )
    assert authorization.decision.stage == "confirmation"
    assert authorization.decision.reason_code == "confirmation_missing"

    outcome = service.consume_and_create_operation(
        confirmation_id="opc_" + "0" * 64,
        presented_token="whatever-token",
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "confirmation_missing"
    assert outcome.operation is None


# ---------------------------------------------------------------------------
# Wrong-workspace lookup is indistinguishable from missing
# ---------------------------------------------------------------------------


def test_wrong_workspace_operation_lookup_indistinguishable_from_missing(
    tmp_foundry: FoundryPaths,
) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )
    created = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert created.outcome == "created"
    assert created.operation is not None
    operation_id = created.operation.operation_id
    fake_id = "opm_" + "f" * 64

    with pytest.raises(KeyError) as genuinely_missing:
        service.load_operation(fake_id)
    assert str(genuinely_missing.value) == repr(f"operation not found: {fake_id}")

    with pytest.raises(KeyError) as scope_denied:
        service.load_operation(operation_id, identity=_IDENTITY_OTHER_WORKSPACE)
    assert str(scope_denied.value) == repr(f"operation not found: {operation_id}")

    # Same TEMPLATE for both -- a wrong-workspace denial's message carries
    # no distinguishing "wrong workspace"/"scope" text, only the identical
    # "operation not found: <id>" shape a genuinely missing id produces
    # (the ids necessarily differ -- they're two different lookups -- but
    # the exception type and message FORMAT are indistinguishable).
    _prefix = "operation not found: "
    assert _prefix in str(genuinely_missing.value)
    assert _prefix in str(scope_denied.value)
    assert type(genuinely_missing.value) is type(scope_denied.value) is KeyError

    # Same-workspace lookup succeeds.
    same_workspace = service.load_operation(operation_id, identity=_IDENTITY)
    assert same_workspace.operation_id == operation_id


# ---------------------------------------------------------------------------
# Real concurrency: DUR-1's actual point
# ---------------------------------------------------------------------------


def test_concurrent_consumers_of_one_confirmation_yield_one_success_one_conflict(
    tmp_foundry: FoundryPaths,
) -> None:
    """The property a read-then-write implementation cannot provide: two
    threads racing to consume the SAME confirmation must yield exactly one
    `"created"`, one `"exact_replay"`, and exactly one persisted manifest
    row -- never two manifests, never two "created" outcomes.

    Both threads share the SAME `AuthorizationProof`, computed ONCE before
    either thread starts (mirrors NB-9: `authorize_for_consumption` is
    always called OUTSIDE the `BEGIN IMMEDIATE` lock, and a real caller
    would authorize once per incoming request before racing on the shared
    confirmation) -- DUR-1's atomicity guarantee is entirely
    `_consume_locked`'s, unaffected by F1's outer gate.
    """

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    results: list[OperationOutcome] = [None, None]  # type: ignore[list-item]
    barrier = threading.Barrier(2)

    def _worker(index: int) -> None:
        barrier.wait()
        results[index] = service.consume_and_create_operation(
            confirmation_id=confirmation_id,
            presented_token=token,
            ctx=ctx,
            authorization=authorization,
        )

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    outcomes = sorted(r.outcome for r in results)
    assert outcomes == ["created", "exact_replay"]

    operation_ids = {r.operation.operation_id for r in results if r.operation is not None}
    assert len(operation_ids) == 1
    assert _count_operations(tmp_foundry) == 1


def test_consume_locked_is_only_ever_invoked_with_an_already_open_transaction(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P2S-BLOCK-1, mechanism half: a direct, white-box assertion that
    `_consume_locked` is invoked with `conn.in_transaction is True` (i.e.
    `BEGIN IMMEDIATE` has already executed) and that the SAME transaction
    is STILL open when it returns (`COMMIT` happens in the CALLER,
    `consume_and_create_operation`, never inside `_consume_locked`
    itself) -- proving DUR-1's "verify, CAS, and manifest-write all happen
    in ONE transaction" contract by inspecting the real `sqlite3.Connection`
    object, not by inferring it from an outcome.

    This is the discriminating half of the reviewer's own recommended fix
    for P2S-BLOCK-1 (this module's docstring, and the P2 security gate's
    `FIND-P2-SECURITY-GATE` finding): it fails immediately, deterministically,
    and without any multiprocessing/timing dependency against the EXACT
    mutation the gate applied (moving `conn.execute("COMMIT")` ahead of the
    `_consume_locked` call) -- see
    `test_two_real_os_processes_genuinely_block_on_begin_immediate_not_merely_interleave`
    below for the companion multi-process wall-clock proof.
    """

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(tmp_foundry, ctx, confirmation_record=record, presented_token=token)

    observed: dict[str, bool] = {}
    original = OperatorOperationService._consume_locked

    def _wrapped(self: OperatorOperationService, conn: sqlite3.Connection, **kwargs: Any) -> Any:
        observed["in_transaction_on_entry"] = conn.in_transaction
        result = original(self, conn, **kwargs)
        observed["in_transaction_on_exit"] = conn.in_transaction
        return result

    monkeypatch.setattr(OperatorOperationService, "_consume_locked", _wrapped)

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "created"
    assert observed["in_transaction_on_entry"] is True, (
        "_consume_locked was entered WITHOUT an open transaction -- the "
        "read-then-write mutation this test detects moves COMMIT (or "
        "never opens BEGIN IMMEDIATE) before the critical section runs"
    )
    assert observed["in_transaction_on_exit"] is True, (
        "the transaction was closed INSIDE _consume_locked -- COMMIT must "
        "happen in the caller, after this method returns, so the CAS and "
        "the manifest INSERT stay in the SAME transaction as the caller's "
        "own COMMIT"
    )
    assert _count_operations(tmp_foundry) == 1


# U10/REGATE-NB-1: both real-OS-process tests below were observed to flake
# under FULL-SUITE load (a 60s `result_queue.get`/`p.join` timeout, once in
# two runs at this exact tree) -- root-caused to `spawn`'s own overhead
# under a loaded machine PLUS (before U6) a child dying outright on a raw
# `sqlite3.OperationalError` escaping the CAS `UPDATE` rather than returning
# normally. U6 removes the second cause entirely (that exception is now a
# governed, queue-reported denial, never a process death); this constant
# gives the FIRST cause (pure scheduling/spawn overhead under load) more
# headroom WITHOUT touching either test's own discriminating assertion --
# widening a wall-clock budget is not the same as weakening what the
# assertion proves, and per this task's own instruction a flaky-but-
# discriminating test must stay discriminating, never be made unfalsifiable
# to buy stability.
_MP_RESULT_TIMEOUT_SECONDS = 120

# ---------------------------------------------------------------------------
# G5: the SAME guarantee, across REAL OS processes (not threads)
# ---------------------------------------------------------------------------
#
# The threaded test immediately above shares ONE interpreter and ONE GIL --
# it cannot exercise DUR-1's actual claim, which is durability under an
# exclusive FILE lock across INDEPENDENT connections/processes. This
# top-level (module-scope, so it is importable/picklable under
# `multiprocessing`'s `spawn` start method) worker function runs
# `consume_and_create_operation` in a genuinely separate OS process, with
# its own interpreter, its own sqlite3 connection, and its own
# `research_foundry.ids` clock state -- pytest's `_fixed_clock` autouse
# fixture and this module's `_default_operator_identity` monkeypatch do NOT
# cross a process boundary, so the clock is re-pinned explicitly to the
# SAME `fixed_now` the confirmation was minted against in the parent
# (identity does not need re-deriving in the child: `ctx`/`authorization`
# were already fully resolved in the parent and are passed through by
# value -- `_consume_locked`'s own logic never re-derives identity from
# config, only `authorize_for_consumption`/`mint_confirmation` do, and both
# already ran in the parent).


def _g5_consume_worker(
    root: str,
    confirmation_id: str,
    presented_token: str,
    ctx: policy.PolicyContext,
    authorization: AuthorizationProof,
    fixed_now: datetime,
    barrier: Any,
    result_queue: Any,
) -> None:
    from research_foundry import ids as _ids
    from research_foundry.paths import FoundryPaths as _FoundryPaths
    from research_foundry.services.operator_operation_service import (
        OperatorOperationService as _OperatorOperationService,
    )

    _ids.set_clock(lambda: fixed_now)
    service = _OperatorOperationService(_FoundryPaths(root=Path(root)))
    barrier.wait()
    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=presented_token,
        ctx=ctx,
        authorization=authorization,
    )
    operation_id = outcome.operation.operation_id if outcome.operation is not None else None
    result_queue.put((outcome.outcome, outcome.reason_code, operation_id))


def test_two_real_os_processes_racing_the_same_confirmation_yield_one_success_one_conflict(
    tmp_foundry: FoundryPaths,
) -> None:
    """G5 (coverage gap, cross-model concurrency review): races two REAL,
    separately-`spawn`ed OS processes against the SAME confirmation row in
    the SAME sqlite file, and asserts the identical DUR-1 property the
    threaded test above asserts: exactly one `"created"`, exactly one
    `"exact_replay"`, and exactly one persisted `operations` row -- never
    two manifests, never two `"created"` outcomes. A `multiprocessing.Barrier`
    holds both children at the same starting line so they genuinely race on
    `BEGIN IMMEDIATE`, not merely execute sequentially."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    fixed_now = ids.now()
    confirmation_id, token, record = _mint_and_record(service, ctx, now=fixed_now)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token, now=fixed_now
    )
    assert authorization.decision.allowed

    mp_ctx = multiprocessing.get_context("spawn")
    result_queue = mp_ctx.Queue()
    barrier = mp_ctx.Barrier(2)
    processes = [
        mp_ctx.Process(
            target=_g5_consume_worker,
            args=(
                str(tmp_foundry.root),
                confirmation_id,
                token,
                ctx,
                authorization,
                fixed_now,
                barrier,
                result_queue,
            ),
        )
        for _ in range(2)
    ]
    for p in processes:
        p.start()

    results = [result_queue.get(timeout=_MP_RESULT_TIMEOUT_SECONDS) for _ in processes]
    for p in processes:
        p.join(timeout=_MP_RESULT_TIMEOUT_SECONDS)
        assert p.exitcode == 0, f"worker process failed (exitcode={p.exitcode})"

    outcomes = sorted(r[0] for r in results)
    assert outcomes == ["created", "exact_replay"]

    operation_ids = {r[2] for r in results if r[2] is not None}
    assert len(operation_ids) == 1
    assert _count_operations(tmp_foundry) == 1


# ---------------------------------------------------------------------------
# P2S-BLOCK-1: the SAME two-process race, but discriminating by WALL CLOCK,
# not by outcome distribution.
# ---------------------------------------------------------------------------
#
# The G5 test immediately above proves the OBSERVABLE outcome contract
# (one "created", one "exact_replay", one row) -- but the P2 security gate
# demonstrated that outcome contract ALONE survives a read-then-write
# mutation unchanged: `UNIQUE (workspace_id, idempotency_key)` on
# `operations` produces the identical one-created/one-exact_replay split
# even with NO exclusive lock at all, because the second process's
# unlocked read simply observes the first process's already-committed row.
# A test that cannot fail when the lock is deleted is not evidence for the
# lock (this module's own DUR-1 docstring, and the gate's exact words).
#
# This test instead proves the LOCK ITSELF, by wall-clock evidence. ONLY
# the "holder" child's `policy.consume_confirmation` is monkeypatched
# (in-process, spawn-child-local) to (1) set a `ready_event` the INSTANT it
# is entered -- which is only ever true AFTER `BEGIN IMMEDIATE` has already
# been executed by the SAME child's `consume_and_create_operation` call
# (`_consume_locked` calls `consume_confirmation` from inside the locked
# section, strictly between the caller's `BEGIN IMMEDIATE` and `COMMIT` --
# see `operator_operation_service.py`'s own module docstring), then (2)
# sleep `_SLEEP_SECONDS` before returning. The "waiter" child is
# UNPATCHED -- it blocks on `ready_event` before calling
# `consume_and_create_operation` AT ALL (so it cannot even attempt `BEGIN
# IMMEDIATE` before the holder is PROVABLY already inside its lock), then
# runs the real, fast, un-slowed method.
#
# Under the REAL implementation, the waiter's OWN `BEGIN IMMEDIATE` must
# block until the holder's transaction commits -- which cannot happen
# before the holder's `_SLEEP_SECONDS` sleep finishes, because the sleep is
# INSIDE that transaction. So the waiter's measured wall-clock duration is
# bounded below by (approximately) `_SLEEP_SECONDS`, even though the waiter
# itself never sleeps.
#
# Under the reviewer's EXACT read-then-write mutation (`COMMIT` moved
# ahead of the `_consume_locked` call, CAS predicate removed), the
# holder's `COMMIT` fires BEFORE `_consume_locked` -- and therefore before
# `ready_event` is even set -- releasing any lock immediately. By the time
# the waiter (signaled by the event, which now fires on an already-
# unlocked database) opens its own `BEGIN IMMEDIATE`, there is nothing to
# wait for: it succeeds instantly, and the waiter -- unpatched, un-slowed
# -- completes in a small fraction of `_SLEEP_SECONDS`. `_MIN_WAITER_SECONDS`
# (a majority fraction of `_SLEEP_SECONDS`, comfortably above realistic
# spawn/IPC/scheduling overhead alone) is the threshold that discriminates
# the two: only the locked implementation can push the waiter above it.

_SLEEP_SECONDS = 0.35
_MIN_WAITER_SECONDS = 0.20  # comfortably < _SLEEP_SECONDS, comfortably > pure IPC/spawn overhead


def _g5_blocking_probe_worker(
    root: str,
    confirmation_id: str,
    presented_token: str,
    ctx: policy.PolicyContext,
    authorization: AuthorizationProof,
    fixed_now: datetime,
    role: str,
    ready_event: Any,
    result_queue: Any,
) -> None:
    import time as _time

    from research_foundry import ids as _ids
    from research_foundry.paths import FoundryPaths as _FoundryPaths
    from research_foundry.services import operator_mcp_policy as _policy
    from research_foundry.services.operator_operation_service import (
        OperatorOperationService as _OperatorOperationService,
    )

    _ids.set_clock(lambda: fixed_now)

    if role == "holder":
        _original_consume_confirmation = _policy.consume_confirmation

        def _slow_consume_confirmation(*args: Any, **kwargs: Any) -> Any:
            # Signal readiness ONLY from inside the real critical section --
            # see this section's module-level comment for why this proves
            # the waiter cannot start racing for the lock any earlier than
            # the moment it is genuinely held.
            ready_event.set()
            _time.sleep(_SLEEP_SECONDS)
            return _original_consume_confirmation(*args, **kwargs)

        _policy.consume_confirmation = _slow_consume_confirmation
    else:
        # "waiter": do not even attempt `consume_and_create_operation`
        # until the holder is provably inside its locked section. Runs the
        # REAL, UNPATCHED `consume_confirmation` -- this child never sleeps
        # on its own account, so any measured delay is entirely lock
        # contention, not an injected sleep of its own.
        assert ready_event.wait(timeout=30), "holder never signaled readiness"

    service = _OperatorOperationService(_FoundryPaths(root=Path(root)))
    started = _time.monotonic()
    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=presented_token,
        ctx=ctx,
        authorization=authorization,
    )
    elapsed = _time.monotonic() - started
    operation_id = outcome.operation.operation_id if outcome.operation is not None else None
    result_queue.put((role, outcome.outcome, outcome.reason_code, operation_id, elapsed))


def test_two_real_os_processes_genuinely_block_on_begin_immediate_not_merely_interleave(
    tmp_foundry: FoundryPaths,
) -> None:
    """P2S-BLOCK-1: the discriminating durability test the security gate's
    finding demanded -- see this section's module-level comment above for
    the full mechanism and why the existing G5 test cannot detect the
    read-then-write mutation on its own.

    Proof of discrimination performed manually for this task (not
    encoded here, since the mutation is applied to SOURCE, not to this
    test): copying `operator_operation_service.py` aside, moving
    `conn.execute("COMMIT")` ahead of the `_consume_locked` call and
    deleting the `AND status = 'issued'` CAS predicate (the reviewer's
    EXACT described mutation), running this test alone, observing it FAIL
    on the `waiter_elapsed >= _MIN_WAITER_SECONDS` assertion, then
    restoring the original file and `diff`-verifying byte-identical
    restoration. See this task's final report for the pasted transcript.
    """

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    fixed_now = ids.now()
    confirmation_id, token, record = _mint_and_record(service, ctx, now=fixed_now)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token, now=fixed_now
    )
    assert authorization.decision.allowed

    mp_ctx = multiprocessing.get_context("spawn")
    result_queue = mp_ctx.Queue()
    ready_event = mp_ctx.Event()
    processes = [
        mp_ctx.Process(
            target=_g5_blocking_probe_worker,
            args=(
                str(tmp_foundry.root),
                confirmation_id,
                token,
                ctx,
                authorization,
                fixed_now,
                role,
                ready_event,
                result_queue,
            ),
        )
        for role in ("holder", "waiter")
    ]
    for p in processes:
        p.start()

    results = [result_queue.get(timeout=_MP_RESULT_TIMEOUT_SECONDS) for _ in processes]
    for p in processes:
        p.join(timeout=_MP_RESULT_TIMEOUT_SECONDS)
        assert p.exitcode == 0, f"worker process failed (exitcode={p.exitcode})"

    by_role = {r[0]: r for r in results}
    holder_outcome, waiter_outcome = by_role["holder"], by_role["waiter"]

    # The existing G5 outcome-distribution contract still holds (it is a
    # real, valid property -- just not, on its own, a discriminating one).
    outcomes = sorted([holder_outcome[1], waiter_outcome[1]])
    assert outcomes == ["created", "exact_replay"]
    operation_ids = {r[3] for r in results if r[3] is not None}
    assert len(operation_ids) == 1
    assert _count_operations(tmp_foundry) == 1

    # The discriminating assertion: the UNPATCHED, never-sleeping waiter's
    # own measured wall-clock duration is bounded below by the (patched,
    # sleeping) holder's lock-held time -- proof the waiter genuinely
    # blocked on `BEGIN IMMEDIATE` rather than interleaving past it.
    waiter_elapsed = waiter_outcome[4]
    assert waiter_elapsed >= _MIN_WAITER_SECONDS, (
        f"waiter (never sleeps on its own account) completed in "
        f"{waiter_elapsed:.3f}s (< {_MIN_WAITER_SECONDS}s) -- it did not "
        "genuinely block on BEGIN IMMEDIATE while the holder's transaction "
        "was open; this is exactly what the read-then-write mutation "
        "produces (the holder's own sleep runs OUTSIDE any real lock, so "
        "the waiter never waits for it)"
    )


# ---------------------------------------------------------------------------
# F1: authorization is a DATA dependency, not a docstring instruction
# ---------------------------------------------------------------------------
#
# `consume_and_create_operation`'s only prior guard was its own docstring
# ("Callers MUST have already obtained an allowed decision..."). Each test
# below is a revert-detection pair for one of the three checks in
# `consume_and_create_operation`'s new gate (see that method's docstring
# and `AuthorizationProof`'s module-level comment in
# `operator_operation_service.py`):
#
#   guard removed                         -> test that FAILS
#   ------------------------------------  -> --------------------------------
#   `if authorization is None: deny`      -> test_missing_authorization_...
#   `if decision.stage != "confirmation"` -> test_authorization_denied_at_rbac_...
#   `if ctx_digest != ctx.canonical_...`  -> test_authorization_bound_to_a_...


def test_missing_authorization_denies_without_touching_storage(
    tmp_foundry: FoundryPaths,
) -> None:
    """Omitting `authorization` (the default) must deny -- never proceed to
    open a database connection at all. Real persistence check: the
    confirmation minted for this ctx is left completely untouched (still
    `"issued"`), proving the CAS was never reached."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, _record = _mint_and_record(service, ctx)

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        # authorization intentionally omitted
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


def test_authorization_denied_at_rbac_cannot_be_bypassed_by_a_valid_confirmation(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual F1 attack: an actor denied at RBAC (never reaches the
    confirmation stage) but holding an otherwise legitimately-minted,
    correctly-bound, unexpired confirmation token must still be denied.
    `_consume_locked`'s own confirmation-binding re-check has NO visibility
    into RBAC -- it would happily accept this token if this gate did not
    stop it first (this is the P1-round-2-shaped hole F1 closes)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)

    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )
    assert authorization.decision.denied
    assert authorization.decision.stage == "rbac"
    assert authorization.decision.reason_code == "rbac_denied"

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "rbac_denied"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # Never even reached the CAS -- the confirmation is untouched.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


def test_authorization_bound_to_a_different_ctx_denies(tmp_foundry: FoundryPaths) -> None:
    """F1(c): a proof minted for one `PolicyContext` must never authorize
    consumption against a DIFFERENT one, even though the proof itself is
    genuinely `allowed` for the ctx it was actually computed against."""

    service = OperatorOperationService(tmp_foundry)
    ctx_a = _basic_ctx(targets=_run_targets(), idempotency_key="idem-a")
    ctx_b = _basic_ctx(targets=_run_targets(), idempotency_key="idem-b")
    confirmation_id, token, record = _mint_and_record(service, ctx_a)

    authorization_for_a = _authorize(
        tmp_foundry, ctx_a, confirmation_record=record, presented_token=token
    )
    assert authorization_for_a.decision.allowed
    assert authorization_for_a.ctx_digest == ctx_a.canonical_digest()
    assert authorization_for_a.ctx_digest != ctx_b.canonical_digest()

    # Present the confirmation minted for ctx_a, but the proof-and-ctx pair
    # passed to consume_and_create_operation is (proof-for-ctx_a, ctx_b).
    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx_b,
        authorization=authorization_for_a,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


# ---------------------------------------------------------------------------
# F4 sibling (P2S-NB-4): manifest schema-validation failure must be a
# governed denial, never a raw exception crossing this module's boundary.
# ---------------------------------------------------------------------------


def test_manifest_schema_validation_failure_is_governed_not_raw(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_consume_locked`'s manifest validation is believed unreachable in
    normal operation (the manifest is built entirely from an
    already-validated `ctx`) -- forced here via monkeypatch to prove the
    CATCH, not the (untestable-by-construction) real trigger. Before this
    fix, this raised a bare `RuntimeError` that the generic
    `except Exception: ROLLBACK; raise` in `consume_and_create_operation`
    re-raised RAW past the method boundary."""

    from research_foundry.schemas import ValidationResult

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(tmp_foundry, ctx, confirmation_record=record, presented_token=token)

    monkeypatch.setattr(
        service._schemas,
        "validate",
        lambda payload, kind: ValidationResult(schema=kind, errors=["forced failure"]),
    )

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # The confirmation was NOT consumed -- the whole transaction rolled
    # back, including the CAS that would otherwise have already succeeded.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


# ---------------------------------------------------------------------------
# F3: no fail-open defaults in record_confirmation; column/json status
# can never diverge through this module's own write path.
# ---------------------------------------------------------------------------


def test_record_confirmation_rejects_missing_status(tmp_foundry: FoundryPaths) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    bad_record = dict(issued.record)
    del bad_record["status"]

    with pytest.raises(ValueError):
        service.record_confirmation(bad_record)
    # Zero persistence: the DB is never even created for a rejected record.
    assert not tmp_foundry.operator_operations_db.exists()


def test_record_confirmation_rejects_non_issued_status(tmp_foundry: FoundryPaths) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    bad_record = dict(issued.record)
    bad_record["status"] = "consumed"

    with pytest.raises(ValueError):
        service.record_confirmation(bad_record)
    assert not tmp_foundry.operator_operations_db.exists()


def test_record_confirmation_rejects_missing_issued_at(tmp_foundry: FoundryPaths) -> None:
    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    bad_record = dict(issued.record)
    del bad_record["issued_at"]

    with pytest.raises(ValueError):
        service.record_confirmation(bad_record)
    assert not tmp_foundry.operator_operations_db.exists()


def test_record_confirmation_column_and_json_status_never_diverge(
    tmp_foundry: FoundryPaths,
) -> None:
    """A well-formed `record_confirmation` call always writes the
    denormalized `status` column and the `record_json` blob's own `status`
    field from the SAME validated value -- they cannot diverge (F3)."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    service.record_confirmation(issued.record)

    conn = _raw_connect(tmp_foundry)
    try:
        row = conn.execute(
            "SELECT status, record_json FROM confirmations WHERE confirmation_id = ?",
            (issued.record["confirmation_id"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    json_status = json.loads(row["record_json"])["status"]
    assert row["status"] == json_status == "issued"


# ---------------------------------------------------------------------------
# F4: the DUR-1 CAS-invariant violation never crosses the boundary raw
# ---------------------------------------------------------------------------


def test_dur1_cas_invariant_violation_returns_governed_denial_not_raw_exception(
    tmp_foundry: FoundryPaths,
) -> None:
    """Simulates the `rowcount != 1` defensive branch with a REAL,
    directly-written sqlite row (not a fake/mock): desync ONLY the
    denormalized `status` COLUMN via a raw connection (something F3's fix
    makes unreachable via `record_confirmation` itself, but not something
    the CAS's own defensive check can assume can never happen some other
    way). The JSON blob still says `"issued"`, so `verify_confirmation`/
    `consume_confirmation` judge the record consumable, but the CAS's
    `WHERE status = 'issued'` on the (desynced) column cannot match --
    `cur.rowcount` comes back 0, not 1, exercising the exact branch F4
    guards. The resulting `OperationOutcome` must be bounded/governed, and
    the confirmations table must show no partial mutation.

    Uses `"expired"` (a real member of the schema's closed `status`
    vocabulary) rather than an arbitrary string like the original
    `"desynced"` -- G4's new `trg_confirmations_status_valid_update`
    trigger now rejects any raw UPDATE that sets `status` OUTSIDE
    `issued`/`consumed`/`expired`/`revoked` at the DB level (see
    `operator_operation_service._DDL`), so an out-of-vocabulary literal
    here would raise `sqlite3.IntegrityError` from this setup step itself
    rather than reaching the CAS branch this test exists to exercise. Any
    valid-but-not-`"issued"` value reproduces the identical
    column/JSON-blob desync."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    conn = _raw_connect(tmp_foundry)
    try:
        conn.execute(
            "UPDATE confirmations SET status = 'expired' WHERE confirmation_id = ?",
            (confirmation_id,),
        )
        conn.commit()
    finally:
        conn.close()

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # The desynced status is left exactly as it was -- the failed UPDATE
    # (rowcount 0) never partially applied, and the surrounding transaction
    # was rolled back.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "expired"


# ---------------------------------------------------------------------------
# G1: expiry must be checked AFTER the exclusive lock is acquired, not
# before the (potentially long) wait for it -- time-of-check/time-of-use
# across `BEGIN IMMEDIATE`.
# ---------------------------------------------------------------------------


class _BeginImmediateInterceptingConn:
    """Thin proxy around a real sqlite3 connection that fires a callback
    the FIRST time `execute("BEGIN IMMEDIATE")` is called, before letting
    it proceed -- delegates everything else (including every other
    `execute` call) straight to the real connection unchanged. Used by the
    G1 test below to deterministically simulate "the clock advanced past
    expiry while this call was blocked waiting for the writer lock",
    without any real-time sleep/race."""

    def __init__(self, conn: sqlite3.Connection, on_begin_immediate: Any) -> None:
        self._conn = conn
        self._on_begin_immediate = on_begin_immediate
        self._fired = False

    def execute(self, sql: str, *args: Any, **kwargs: Any) -> sqlite3.Cursor:
        if not self._fired and sql.strip() == "BEGIN IMMEDIATE":
            self._fired = True
            self._on_begin_immediate()
        return self._conn.execute(sql, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def test_expiry_checked_after_lock_acquired_not_before_the_wait_for_it(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G1 (HIGH, cross-model concurrency review): `consume_and_create_operation`
    captured `moment = ids.now()` BEFORE `_ensure_schema()`/`BEGIN IMMEDIATE`
    -- but `BEGIN IMMEDIATE` can block for up to `_BUSY_TIMEOUT_MS` (15s)
    waiting for a concurrent writer's exclusive lock. A confirmation that
    expires WHILE this call is blocked would still be judged not-yet-expired
    once the lock is finally acquired, using the STALE pre-wait `moment` --
    committing a manifest and consuming a token strictly AFTER the
    confirmation's own clamped expiry.

    Simulated deterministically (no real thread/sleep race, so this is not
    flaky): `_BeginImmediateInterceptingConn` wraps the real connection and
    intercepts the FIRST `BEGIN IMMEDIATE` call. Before letting it proceed,
    the interceptor (a) advances the injectable `ids` clock past the
    confirmation's clamped expiry, then (b) commits a competing writer
    (`blocker_conn`) that was already holding the exclusive lock --
    reproducing exactly the interleaving a real caller blocked on a busy
    lock would observe: the wait for the lock ends AFTER expiry has passed.

    MUST FAIL on the pre-fix code (which reads `ids.now()` before the wait,
    observing the PRE-advance, not-yet-expired time, and returns
    `"created"`) and PASS after the fix (which reads `ids.now()` only once
    the lock is actually held, observing the POST-advance, expired time)."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    confirmation_id, token, record = _mint_and_record(service, ctx, now=minted_at)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token, now=minted_at
    )
    assert authorization.decision.allowed

    expired_at = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    clock_holder = {"now": minted_at}
    monkeypatch.setattr(ids, "now", lambda: clock_holder["now"])

    # A competing writer already holding the exclusive lock at the exact
    # moment `consume_and_create_operation` tries to acquire it below.
    blocker_conn = sqlite3.connect(str(tmp_foundry.operator_operations_db), isolation_level=None)
    blocker_conn.execute("PRAGMA busy_timeout = 15000")
    blocker_conn.execute("BEGIN IMMEDIATE")

    def _simulate_expiry_during_the_wait() -> None:
        # "The wait for the lock took long enough that the token expired
        # mid-wait" -- advance the clock, THEN release the competing
        # holder so the real `BEGIN IMMEDIATE` this wraps can finally
        # proceed, observing a database that is no longer locked.
        clock_holder["now"] = expired_at
        blocker_conn.execute("COMMIT")

    real_connect = service_module._connect

    def _patched_connect(paths: FoundryPaths) -> _BeginImmediateInterceptingConn:
        return _BeginImmediateInterceptingConn(real_connect(paths), _simulate_expiry_during_the_wait)

    monkeypatch.setattr(service_module, "_connect", _patched_connect)
    try:
        outcome = service.consume_and_create_operation(
            confirmation_id=confirmation_id,
            presented_token=token,
            ctx=ctx,
            authorization=authorization,
        )
    finally:
        blocker_conn.close()

    assert outcome.outcome == "denied"
    assert outcome.reason_code == "confirmation_expired"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # Zero effect: the confirmation is left `issued` (its own TTL already
    # governs any future retry) -- never consumed for a request whose
    # expiry had already passed by the time the lock was actually held.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


# ---------------------------------------------------------------------------
# G2: a lock-acquisition timeout must return a governed denial, not a raw
# sqlite3.OperationalError -- the sibling of F4's already-closed
# lock-invariant-violation path, at the ACQUISITION site instead.
# ---------------------------------------------------------------------------


def test_lock_acquisition_timeout_returns_governed_denial_not_raw_exception(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G2 (MEDIUM, cross-model concurrency review): `_ensure_schema()` and
    `BEGIN IMMEDIATE` sat OUTSIDE any exception handler -- when the busy
    timeout is exhausted acquiring the exclusive writer lock, `BEGIN
    IMMEDIATE` raises `sqlite3.OperationalError` ("database is locked") and
    it used to propagate straight out of `consume_and_create_operation`
    instead of returning a governed `OperationOutcome`.

    Holds a REAL competing writer lock (`blocker_conn`, `BEGIN IMMEDIATE`,
    never released until after the call under test returns) and shrinks
    `_BUSY_TIMEOUT_MS` to 50ms so the test exercises a REAL timeout without
    waiting the real 15s window.

    MUST FAIL on the pre-fix code (an uncaught `sqlite3.OperationalError`
    propagates out of the test as an error, not a returned `OperationOutcome`)
    and PASS after the fix (`OperationOutcome("denied", "internal_error", None)`
    is returned; no transaction was ever opened, so the confirmation is
    completely untouched)."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    # Small busy_timeout so this test does not actually wait the real 15s
    # window -- exercises the SAME exhausted-timeout path, just faster.
    monkeypatch.setattr(service_module, "_BUSY_TIMEOUT_MS", 50)

    blocker_conn = sqlite3.connect(str(tmp_foundry.operator_operations_db), isolation_level=None)
    blocker_conn.execute("BEGIN IMMEDIATE")
    try:
        outcome = service.consume_and_create_operation(
            confirmation_id=confirmation_id,
            presented_token=token,
            ctx=ctx,
            authorization=authorization,
        )
    finally:
        blocker_conn.execute("ROLLBACK")
        blocker_conn.close()

    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # No transaction was ever opened on this path -- the confirmation is
    # completely untouched, still available (within its own TTL) for a
    # retry once the competing writer releases the lock.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


def test_operational_error_inside_locked_transaction_returns_governed_denial_not_raw_exception(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """U6/REGATE-NB-2: G2's original fix wrapped only `_ensure_schema`/`BEGIN
    IMMEDIATE` -- a `sqlite3.OperationalError` raised INSIDE the locked
    section (e.g. the CAS `UPDATE` promoting to an EXCLUSIVE lock while a
    concurrent reader still holds a shared one) still propagated raw through
    the `except Exception: ROLLBACK; raise` catch-all below it. This is not
    hypothetical: this exact exception, from this exact statement, killed a
    real child process during this tree's own full-suite run (see the
    finding's validation transcript).

    `_consume_locked` is monkeypatched to raise the SAME exception class
    SQLite itself raises on lock contention, from INSIDE the real,
    already-open `BEGIN IMMEDIATE` transaction this call opens (only
    `_consume_locked`'s body is replaced -- the transaction, the connection,
    and the surrounding exception handling are all real). This exercises
    the NEW `except sqlite3.OperationalError` clause around the
    `_consume_locked` call specifically, distinct from the pre-existing G2
    clause around `BEGIN IMMEDIATE` itself covered by
    `test_lock_acquisition_timeout_returns_governed_denial_not_raw_exception`
    above.

    MUST FAIL on the pre-fix code (the `OperationalError` propagates raw
    out of `consume_and_create_operation`, exactly as it did in the real
    full-suite run) and PASS after the fix (a governed
    `OperationOutcome("denied", "internal_error", None)` is returned, the
    transaction is rolled back, and the confirmation is left untouched)."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    def _raise_operational_error(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(service, "_consume_locked", _raise_operational_error)

    outcome = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )

    assert outcome.outcome == "denied"
    assert outcome.reason_code == "internal_error"
    assert outcome.operation is None
    assert _count_operations(tmp_foundry) == 0
    # No COMMIT was ever reached on this path -- the confirmation is left
    # completely untouched, still "issued", available for a retry.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


# ---------------------------------------------------------------------------
# G4: `confirmations.status` and `operations` immutability are now ALSO
# enforced at the DB level (triggers), not merely by this module's Python.
# ---------------------------------------------------------------------------


def test_db_rejects_out_of_vocabulary_confirmation_status_at_insert(
    tmp_foundry: FoundryPaths,
) -> None:
    """G4: `trg_confirmations_status_valid_insert` rejects an INSERT whose
    `status` is outside `issued`/`consumed`/`expired`/`revoked` -- a
    real, DB-level guarantee independent of `record_confirmation`'s own
    (already-tested, F3) Python-level validation."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    # Force the DB file (and its schema, including the new triggers) into
    # existence via the real write path first.
    _mint_and_record(service, ctx)

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO confirmations"
                " (confirmation_id, workspace_id, status, record_json, created_at)"
                " VALUES ('opc_bogus', 'ws-mine', 'not_a_real_status', '{}', 'x')"
            )
    finally:
        conn.close()


def test_db_rejects_out_of_vocabulary_confirmation_status_at_update(
    tmp_foundry: FoundryPaths,
) -> None:
    """G4: `trg_confirmations_status_valid_update` rejects an UPDATE that
    sets `status` outside the closed vocabulary."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, _token, _record = _mint_and_record(service, ctx)

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE confirmations SET status = 'not_a_real_status' WHERE confirmation_id = ?",
                (confirmation_id,),
            )
    finally:
        conn.close()
    # Untouched -- the rejected UPDATE never partially applied.
    assert _confirmation_status(tmp_foundry, confirmation_id) == "issued"


def test_db_rejects_update_of_an_operations_row(tmp_foundry: FoundryPaths) -> None:
    """G4: `trg_operations_immutable_no_update` rejects ANY UPDATE against
    `operations`, independent of which column is targeted -- a real,
    DB-level enforcement of the module docstring's "manifests are
    immutable once written" claim."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )
    created = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert created.outcome == "created"
    assert created.operation is not None

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE operations SET manifest_json = '{}' WHERE operation_id = ?",
                (created.operation.operation_id,),
            )
    finally:
        conn.close()


def test_db_rejects_delete_of_an_operations_row(tmp_foundry: FoundryPaths) -> None:
    """G4: `trg_operations_immutable_no_delete` rejects ANY DELETE against
    `operations`."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )
    created = service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )
    assert created.outcome == "created"
    assert created.operation is not None

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "DELETE FROM operations WHERE operation_id = ?",
                (created.operation.operation_id,),
            )
    finally:
        conn.close()
    assert _count_operations(tmp_foundry) == 1


# ---------------------------------------------------------------------------
# K3-BLOCK-1 (Karen gate, tree `be6ba96`): `record_confirmation`'s OWN lock
# acquisition and in-transaction contention must not escape raw.
# ---------------------------------------------------------------------------
#
# U6 governed `consume_and_create_operation`'s two contention paths, and the
# F4 enumeration comment in `record_confirmation` then claimed -- about the
# module, from inside the method it was WRONG about -- that "EVERY
# reachable-by-contention raw exception in this module (lock acquisition,
# in-lock promotion, ...) is now governed". `record_confirmation`'s own
# `_ensure_schema`/`BEGIN IMMEDIATE` sat outside any handler and its
# `ROLLBACK` lacked U6's best-effort guard, so an ordinary "database is
# locked" -- precisely the contention DUR-1 consumers create on this same
# file for up to `_BUSY_TIMEOUT_MS` -- escaped raw. Two tests, one per half,
# because governing only the acquisition half is the exact
# layer-below/sibling miss the original G2 fix made and U6 had to return for.


def test_record_confirmation_lock_acquisition_timeout_raises_bounded_error_not_raw(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """K3-BLOCK-1, half 1 (the G2 analogue). Holds a REAL competing writer
    lock and shrinks `_BUSY_TIMEOUT_MS` so `BEGIN IMMEDIATE` genuinely times
    out, rather than simulating the exception.

    MUST FAIL pre-fix: a raw `sqlite3.OperationalError` propagates out of
    `record_confirmation`. Passes post-fix: a bounded, module-owned
    `ConfirmationPersistenceError` is raised whose message carries no
    driver text, no SQL and no file path (the
    `operator_mcp_error.schema.yaml` bounded/redacted contract, AC OPM-7).
    """

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    # Materialize the database/schema with an unrelated, successful record
    # first -- the blocker connection below cannot open a file that does
    # not exist yet, and this also proves the failure is contention and not
    # a cold-start artifact.
    _mint_and_record(service, ctx)

    issued = policy.mint_confirmation(_basic_ctx(targets=_run_targets()), now=ids.now())

    monkeypatch.setattr(service_module, "_BUSY_TIMEOUT_MS", 50)

    blocker_conn = sqlite3.connect(str(tmp_foundry.operator_operations_db), isolation_level=None)
    blocker_conn.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(ConfirmationPersistenceError) as excinfo:
            service.record_confirmation(issued.record)
    finally:
        blocker_conn.execute("ROLLBACK")
        blocker_conn.close()

    # Bounded/redacted: no driver detail, no SQL, no path leaks out.
    message = str(excinfo.value)
    assert "database is locked" not in message
    assert "INSERT" not in message
    assert str(tmp_foundry.operator_operations_db) not in message
    # NOT the raw driver type -- the whole point of the finding.
    assert not isinstance(excinfo.value, sqlite3.OperationalError)


def test_record_confirmation_lock_contention_inside_transaction_raises_bounded_error_not_raw(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """K3-BLOCK-1, half 2 (the U6 analogue). `BEGIN IMMEDIATE` takes
    RESERVED immediately but SQLite promotes to EXCLUSIVE lazily, on the
    first real write -- so contention can still fire AFTER a successful
    `BEGIN IMMEDIATE`. Wraps the module's `_connect` in a proxy whose
    `execute` raises the SAME exception class SQLite raises, on the INSERT
    specifically (`sqlite3.Connection` is an immutable C type and cannot be
    patched directly), so the transaction, the connection and the
    surrounding handling are all real and only the failing statement is
    simulated.

    This is NOT redundant with half 1: half 1's guard sits around
    `_ensure_schema`/`BEGIN IMMEDIATE` and cannot fire here, because
    `BEGIN IMMEDIATE` succeeds on this path. Deleting only the in-lock
    clause leaves half 1's test green and fails this one.
    """

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx, now=ids.now())

    rollbacks: list[str] = []

    class _FailingInsertConnection:
        """Real connection, one poisoned statement."""

        def __init__(self, conn: sqlite3.Connection) -> None:
            self._conn = conn

        def execute(self, sql: str, *args: Any, **kwargs: Any) -> Any:
            if sql.lstrip().upper().startswith("INSERT INTO CONFIRMATIONS"):
                raise sqlite3.OperationalError("database is locked")
            if sql.strip().upper() == "ROLLBACK":
                rollbacks.append(sql)
            return self._conn.execute(sql, *args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._conn, name)

    real_connect = service_module._connect
    monkeypatch.setattr(
        service_module, "_connect", lambda paths: _FailingInsertConnection(real_connect(paths))
    )

    with pytest.raises(ConfirmationPersistenceError) as excinfo:
        service.record_confirmation(issued.record)

    assert not isinstance(excinfo.value, sqlite3.OperationalError)
    assert "database is locked" not in str(excinfo.value)
    # The transaction really was rolled back -- not merely abandoned.
    assert rollbacks == ["ROLLBACK"]

    monkeypatch.undo()
    # Nothing was committed: the confirmation row is absent, so a retry once
    # the lock clears is clean rather than colliding with a half-written row.
    # (`_confirmation_status` asserts presence, so query raw here.)
    conn = _raw_connect(tmp_foundry)
    try:
        row = conn.execute(
            "SELECT status FROM confirmations WHERE confirmation_id = ?",
            (issued.record["confirmation_id"],),
        ).fetchone()
    finally:
        conn.close()
    assert row is None


# ---------------------------------------------------------------------------
# OPM-6.1 / OPM-6.4 (AC OPM-3): the H3 ten-scenario lifecycle recovery
# matrix, driven by the public-safe fixture matrix under
# tests/fixtures/operator_mcp/ (D4/D6, m3-implementer-contract.md).
#
# Scenario -> interruption point / property
# -------------------------------------------------------------------------
# H3-01  after the operation manifest is durably written, before
#        run_actions is ever called
# H3-02  mid-attempt -- an attempt is minted but crashes before its action
#        produces any receipt; resume mints a NEW attempt, never reuses it
# H3-03  after an effect_receipt is durably committed, before the
#        following checkpoint write
# H3-04  after every action's receipts + checkpoint are committed, before
#        finalize_terminal_receipt is ever reached
# H3-05  during a cancel -- the cancellation request and one action's
#        receipts are committed, but the CANCELED checkpoint/terminal
#        receipt write is lost
# H3-06  exact-retry idempotency: `run_or_replay(is_replay=True)` against
#        an already-completed operation returns the identical terminal
#        receipt with zero re-execution
# H3-07  cancel semantics: cancellation observed before the first action
#        -> canceled, zero effects (explicit D2 zero-effect assertion)
# H3-08  resume-after-cancel refusal: `resume_operation` against a
#        terminal-canceled operation resolves to `already_terminal`, never
#        re-executing and never minting a new attempt
# H3-09  duplicate suppression: a SECOND, freshly-minted confirmation
#        under the SAME (workspace_id, idempotency_key, digest) resolves
#        to `exact_replay` against the SAME operation -- zero duplicate
#        action/effect receipts, zero duplicate `operations` rows
# H3-10  the full D6 convergence requirement over the largest fixture (5
#        actions): an uninterrupted control run and a run interrupted
#        after action 2's effect_receipt (then resumed on a fresh service
#        instance) converge to SET-EQUAL canonical effects, identical
#        receipt counts, and an identical normalized terminal receipt.
#
# Every H3 test below drives the SAME public entry surface a real caller
# uses (`OperatorOperationService.consume_and_create_operation`,
# `OperatorCancelResumeService.run_actions` / `run_or_replay` /
# `resume_operation`) against REAL sqlite persistence (`tmp_foundry`) --
# process loss is simulated the same way
# `test_operator_cancel_resume_service.py` does: durably write the
# pre-loss receipts via one service instance, then resolve/resume via
# BRAND-NEW service instances backed by the same durable files, never an
# in-process continuation. Convergence is asserted as SET equality on
# canonical (effect_kind, effect_ref) pairs and exact receipt counts
# (D6), not merely matching terminal status.
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "operator_mcp"

_FORBIDDEN_FIXTURE_SUBSTRINGS: tuple[str, ...] = (
    "miethe",
    "10.42.",
    "/users/",
    "/home/",
    "ghp_",
    "sk-ant-",
    "sk-proj-",
    "bearer ",
    "akia",
)

# Any private/LAN-shaped IPv4 literal (10.x, 192.168.x, 172.16-31.x) -- a
# regex sibling to the plain "10.42." substring check above, so a fixture
# using a DIFFERENT private range still fails the grep-clean property.
_PRIVATE_IPV4_RE = re.compile(
    r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
)


def _load_json_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _workspaces_fixture() -> dict[str, Any]:
    return _load_json_fixture("workspaces.json")


def _scenario(scenario_id: str) -> dict[str, Any]:
    scenarios = _load_json_fixture("interrupted_operations.json")["scenarios"]
    for scenario in scenarios:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise KeyError(f"no such fixture scenario: {scenario_id}")


def _fixture_identity(scenario: Mapping[str, Any]) -> AuthIdentity:
    """The `AuthIdentity` a scenario's `workspace_id` resolves to, sourced
    entirely from `workspaces.json` -- makes the fixture matrix
    load-bearing for identity resolution too, not merely for action/effect
    content."""

    workspace_id = scenario["workspace_id"]
    for ws in _workspaces_fixture()["workspaces"]:
        if ws["workspace_id"] == workspace_id:
            return AuthIdentity(ws["user_id"], ws["workspace_id"], tuple(ws["roles"]))
    raise KeyError(f"no such fixture workspace: {workspace_id}")


def _fixture_actions(scenario: Mapping[str, Any], executed: list[str]) -> list[ActionSpec]:
    """Build the `ActionSpec` sequence declared by `scenario["actions"]` --
    each action appends its own `action_id` to `executed` and produces the
    fixture's declared `(effect_kind, effect_ref)` pair. `effect_digest` is
    freshly minted per call (it is a GLOBAL primary key across every
    operation in `effect_receipts` -- see
    `test_operator_cancel_resume_service.py`'s own module docstring for
    why two operations can never share one), never read from the fixture."""

    specs: list[ActionSpec] = []
    for action in scenario["actions"]:
        action_id = action["action_id"]
        effect_kind = action["effect_kind"]
        effect_ref = action["effect_ref"]

        def _run(
            action_id: str = action_id, effect_kind: str = effect_kind, effect_ref: str = effect_ref
        ) -> ActionEffect:
            executed.append(action_id)
            return ActionEffect(
                effect_kind=effect_kind,
                effect_digest=hashlib.sha256(
                    f"{effect_ref}-{ids.now_iso()}-{id(executed)}".encode("utf-8")
                ).hexdigest(),
                effect_ref=effect_ref,
            )

        specs.append(ActionSpec(action_id=action_id, run=_run))
    return specs


def _must_not_run(action_id: str, *, scenario_id: str, reason: str) -> Any:
    """An `ActionSpec.run` callable that fails the test loudly if invoked
    -- the assertion mechanism for "this action must not be (re-)executed"
    used throughout the H3 matrix below."""

    def _run() -> None:  # pragma: no cover - only reached on test failure
        raise AssertionError(f"{scenario_id}: {action_id} must not run -- {reason}")

    return _run


def _canonical_effects(paths: FoundryPaths, operation_id: str) -> set[tuple[str, str]]:
    """The (effect_kind, effect_ref) pairs persisted for `operation_id` --
    the CANONICAL, operation-id-independent content of its effects
    (excludes `effect_digest`, content-addressed against `operation_id`
    and therefore never comparable across two distinct operations)."""

    conn = _raw_connect(paths)
    try:
        rows = conn.execute(
            "SELECT effect_kind, effect_ref FROM effect_receipts WHERE operation_id = ?",
            (operation_id,),
        ).fetchall()
    finally:
        conn.close()
    return {(row["effect_kind"], row["effect_ref"]) for row in rows}


def _action_receipt_count(paths: FoundryPaths, operation_id: str) -> int:
    conn = _raw_connect(paths)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def _effect_receipt_count(paths: FoundryPaths, operation_id: str) -> int:
    conn = _raw_connect(paths)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM effect_receipts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def _normalize_terminal_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Strip the two fields that MUST differ between any two distinct
    operations (`operation_id`, and the content-addressed
    `effect_receipt_refs` digests, which embed `operation_id`) and reduce
    `audit_delivery` to its comparable `status` -- mirrors
    `test_operator_cancel_resume_service.py`'s own `_normalize_terminal`."""

    d = dict(receipt)
    for key in ("operation_id", "effect_receipt_refs"):
        d.pop(key, None)
    audit_delivery = d.get("audit_delivery")
    if isinstance(audit_delivery, Mapping):
        d["audit_delivery"] = {"status": audit_delivery.get("status")}
    return d


def _consume_op(
    paths: FoundryPaths, op_service: OperatorOperationService, ctx: policy.PolicyContext
) -> OperationOutcome:
    """Mint + record + authorize + consume in one call -- the full
    P1/OPM-2.1 entry surface a real caller goes through."""

    confirmation_id, token, record = _mint_and_record(op_service, ctx)
    authorization = _authorize(paths, ctx, confirmation_record=record, presented_token=token)
    return op_service.consume_and_create_operation(
        confirmation_id=confirmation_id, presented_token=token, ctx=ctx, authorization=authorization
    )


def _assert_scenario_convergence(
    paths: FoundryPaths,
    scenario: Mapping[str, Any],
    *,
    control_operation_id: str,
    control_execution: Any,
    subject_operation_id: str,
    subject_execution: Any,
) -> None:
    """D6: assert SET equality on canonical (effect_kind, effect_ref)
    pairs and exact receipt counts between an uninterrupted control run
    and an interrupted-then-resumed subject run, both checked against the
    fixture's own declared oracle -- never merely that both report the
    same terminal status."""

    expected = scenario["expected"]
    expected_pairs = {tuple(pair) for pair in expected["effect_pairs"]}

    assert control_execution.status == expected["terminal_status"]
    assert subject_execution.status == expected["terminal_status"]

    control_effects = _canonical_effects(paths, control_operation_id)
    subject_effects = _canonical_effects(paths, subject_operation_id)
    assert control_effects == expected_pairs
    assert subject_effects == expected_pairs
    assert control_effects == subject_effects  # D6: SET equality, control vs subject

    assert _action_receipt_count(paths, control_operation_id) == expected["action_receipt_count"]
    assert _action_receipt_count(paths, subject_operation_id) == expected["action_receipt_count"]
    assert _effect_receipt_count(paths, control_operation_id) == expected["effect_receipt_count"]
    assert _effect_receipt_count(paths, subject_operation_id) == expected["effect_receipt_count"]

    assert control_execution.terminal_receipt is not None
    assert subject_execution.terminal_receipt is not None
    assert _normalize_terminal_receipt(control_execution.terminal_receipt) == _normalize_terminal_receipt(
        subject_execution.terminal_receipt
    )


def test_operator_mcp_fixtures_are_grep_clean_of_owner_or_private_data() -> None:
    """D4: pins the fixture matrix's public-safety property, rather than
    merely checking it once by inspection at authoring time -- a future
    edit to `tests/fixtures/operator_mcp/` that reintroduces an owner
    string, a real run id shaped like this repo's own, a LAN address, a
    home path, or a token-shaped literal fails THIS test, not a human
    reviewer's memory."""

    fixture_files = sorted(p for p in _FIXTURES_DIR.rglob("*") if p.is_file())
    assert fixture_files, f"no fixture files found under {_FIXTURES_DIR}"
    for path in fixture_files:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for forbidden in _FORBIDDEN_FIXTURE_SUBSTRINGS:
            assert forbidden not in lowered, f"{path}: forbidden pattern {forbidden!r} found"
        assert not _PRIVATE_IPV4_RE.search(text), f"{path}: private/LAN IPv4 address found"


# ---------------------------------------------------------------------------
# H3-01: interrupted after the manifest write, before run_actions ever runs.
# ---------------------------------------------------------------------------


def test_h3_01_interrupted_after_manifest_write_resumes_identically_to_uninterrupted(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-01")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    # Control: a twin operation run straight through, uninterrupted.
    ctx_control = _basic_ctx(targets=_run_targets(), idempotency_key="h3-01-control")
    outcome_control = _consume_op(tmp_foundry, op_service, ctx_control)
    assert outcome_control.outcome == "created"
    executed_control: list[str] = []
    execution_control = svc.run_actions(
        outcome_control.operation.operation_id,
        identity=identity,
        operation_kind=ctx_control.operation_kind,
        actions=_fixture_actions(scenario, executed_control),
        attempt_ref="attempt-control",
    )

    # Subject: the manifest is committed, then the process is lost before
    # run_actions is ever called at all.
    ctx_subject = _basic_ctx(targets=_run_targets(), idempotency_key="h3-01-subject")
    outcome_subject = _consume_op(tmp_foundry, op_service, ctx_subject)
    assert outcome_subject.outcome == "created"
    operation_id = outcome_subject.operation.operation_id

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)
    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 0

    executed_subject: list[str] = []
    execution_subject = fresh_svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx_subject.operation_kind,
        actions=_fixture_actions(scenario, executed_subject),
        attempt_ref="attempt-subject",
        start_index=resume_point.next_action_index,
    )

    _assert_scenario_convergence(
        tmp_foundry,
        scenario,
        control_operation_id=outcome_control.operation.operation_id,
        control_execution=execution_control,
        subject_operation_id=operation_id,
        subject_execution=execution_subject,
    )


# ---------------------------------------------------------------------------
# H3-02: interrupted mid-attempt -- resume mints a NEW attempt, never
# reuses or resurrects the stale one.
# ---------------------------------------------------------------------------


def test_h3_02_interrupted_mid_attempt_mints_a_fresh_attempt_and_resumes_identically(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-02")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    policy_snapshot = {"allowed_tools": ["search"], "data_scopes": []}

    # Control
    ctx_control = _basic_ctx(targets=_run_targets(), idempotency_key="h3-02-control")
    outcome_control = _consume_op(tmp_foundry, op_service, ctx_control)
    executed_control: list[str] = []
    execution_control = svc.run_actions(
        outcome_control.operation.operation_id,
        identity=identity,
        operation_kind=ctx_control.operation_kind,
        actions=_fixture_actions(scenario, executed_control),
        attempt_ref="attempt-control",
    )

    # Subject: an attempt is minted, then the process is lost before that
    # attempt's action produces any action_receipt at all.
    ctx_subject = _basic_ctx(targets=_run_targets(), idempotency_key="h3-02-subject")
    outcome_subject = _consume_op(tmp_foundry, op_service, ctx_subject)
    operation_id = outcome_subject.operation.operation_id
    stale_attempt = attempt_adapter.create_attempt(
        operation_id,
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        dict(policy_snapshot),
        workspace_id=identity.workspace_id,
        identity=identity,
    )
    assert _action_receipt_count(tmp_foundry, operation_id) == 0  # the "loss" gap

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_attempts = OperatorAttemptAdapter(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)
    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 0

    new_attempt = fresh_attempts.create_attempt(
        operation_id,
        "claude_agent_sdk",
        "rf_synthesize_deep",
        "research",
        dict(policy_snapshot),
        workspace_id=identity.workspace_id,
        identity=identity,
    )
    assert new_attempt.attempt_id != stale_attempt.attempt_id

    executed_subject: list[str] = []
    execution_subject = fresh_svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx_subject.operation_kind,
        actions=_fixture_actions(scenario, executed_subject),
        attempt_ref=new_attempt.attempt_id,
        start_index=resume_point.next_action_index,
    )

    _assert_scenario_convergence(
        tmp_foundry,
        scenario,
        control_operation_id=outcome_control.operation.operation_id,
        control_execution=execution_control,
        subject_operation_id=operation_id,
        subject_execution=execution_subject,
    )
    # The stale, never-used attempt is never deleted (immutable ledger) --
    # both attempts remain durably linked to the SAME operation.
    linked = attempt_adapter.list_attempts_for_operation(operation_id, identity=identity)
    assert {a.attempt_id for a in linked} == {stale_attempt.attempt_id, new_attempt.attempt_id}


# ---------------------------------------------------------------------------
# H3-03: interrupted after an effect_receipt, before the following
# checkpoint write -- resume must not replay the already-completed action.
# ---------------------------------------------------------------------------


def test_h3_03_interrupted_after_effect_receipt_resumes_without_replay(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-03")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx_control = _basic_ctx(targets=_run_targets(), idempotency_key="h3-03-control")
    outcome_control = _consume_op(tmp_foundry, op_service, ctx_control)
    executed_control: list[str] = []
    execution_control = svc.run_actions(
        outcome_control.operation.operation_id,
        identity=identity,
        operation_kind=ctx_control.operation_kind,
        actions=_fixture_actions(scenario, executed_control),
        attempt_ref="attempt-control",
    )

    ctx_subject = _basic_ctx(targets=_run_targets(), idempotency_key="h3-03-subject")
    outcome_subject = _consume_op(tmp_foundry, op_service, ctx_subject)
    operation_id = outcome_subject.operation.operation_id

    first = scenario["actions"][0]
    receipt_service.record_action_receipt(
        operation_id,
        identity=identity,
        action_id=first["action_id"],
        action_index=0,
        status="completed",
        attempt_ref="attempt-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_id,
        identity=identity,
        action_id=first["action_id"],
        effect_kind=first["effect_kind"],
        effect_digest=hashlib.sha256(f"{operation_id}-{first['action_id']}".encode("utf-8")).hexdigest(),
        effect_ref=first["effect_ref"],
        generated_at=ids.now_iso(),
    )
    assert receipt_service.load_checkpoint(operation_id) is None  # the "loss" gap

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)
    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 1

    executed_subject: list[str] = [first["action_id"]]  # already ran, pre-loss
    subject_actions = [
        ActionSpec(
            action_id=first["action_id"],
            run=_must_not_run(first["action_id"], scenario_id="H3-03", reason="already committed pre-loss"),
        )
    ]
    subject_actions.extend(
        _fixture_actions({"actions": scenario["actions"][1:]}, executed_subject)
    )

    execution_subject = fresh_svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx_subject.operation_kind,
        actions=subject_actions,
        attempt_ref="attempt-postcrash",
        start_index=resume_point.next_action_index,
    )

    _assert_scenario_convergence(
        tmp_foundry,
        scenario,
        control_operation_id=outcome_control.operation.operation_id,
        control_execution=execution_control,
        subject_operation_id=operation_id,
        subject_execution=execution_subject,
    )


# ---------------------------------------------------------------------------
# H3-04: interrupted before the terminal receipt -- every action's
# receipts and checkpoint are committed, but finalize is never reached.
# ---------------------------------------------------------------------------


def test_h3_04_interrupted_before_terminal_receipt_finalizes_identically(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-04")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx_control = _basic_ctx(targets=_run_targets(), idempotency_key="h3-04-control")
    outcome_control = _consume_op(tmp_foundry, op_service, ctx_control)
    executed_control: list[str] = []
    execution_control = svc.run_actions(
        outcome_control.operation.operation_id,
        identity=identity,
        operation_kind=ctx_control.operation_kind,
        actions=_fixture_actions(scenario, executed_control),
        attempt_ref="attempt-control",
    )

    ctx_subject = _basic_ctx(targets=_run_targets(), idempotency_key="h3-04-subject")
    outcome_subject = _consume_op(tmp_foundry, op_service, ctx_subject)
    operation = outcome_subject.operation
    operation_id = operation.operation_id

    # Every action's action_receipt + effect_receipt + post-action
    # checkpoint is durably committed by hand -- exactly what a real,
    # completed `run_actions` loop would have produced up to, but not
    # including, `finalize_terminal_receipt` -- then the process is lost.
    total = len(scenario["actions"])
    for idx, action in enumerate(scenario["actions"]):
        receipt_service.record_action_receipt(
            operation_id,
            identity=identity,
            action_id=action["action_id"],
            action_index=idx,
            status="completed",
            attempt_ref="attempt-precrash",
            started_at=ids.now_iso(),
            completed_at=ids.now_iso(),
        )
        receipt_service.record_effect_receipt(
            operation_id,
            identity=identity,
            action_id=action["action_id"],
            effect_kind=action["effect_kind"],
            effect_digest=hashlib.sha256(f"{operation_id}-{action['action_id']}".encode("utf-8")).hexdigest(),
            effect_ref=action["effect_ref"],
            generated_at=ids.now_iso(),
        )
    receipt_service.write_checkpoint(
        operation_id,
        identity=identity,
        status="converged",
        next_action_index=None,
        completed_action_count=total,
        total_action_count=total,
        non_cancelable=False,
    )
    assert receipt_service.load_terminal_receipt(operation_id) is None  # the "loss" gap

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)

    subject_actions = [
        ActionSpec(
            action_id=a["action_id"],
            run=_must_not_run(a["action_id"], scenario_id="H3-04", reason="already committed pre-loss"),
        )
        for a in scenario["actions"]
    ]

    execution_subject = fresh_svc.run_or_replay(
        operation,
        is_replay=False,
        identity=identity,
        operation_kind=ctx_subject.operation_kind,
        actions=subject_actions,
        attempt_ref="attempt-postcrash",
    )

    _assert_scenario_convergence(
        tmp_foundry,
        scenario,
        control_operation_id=outcome_control.operation.operation_id,
        control_execution=execution_control,
        subject_operation_id=operation_id,
        subject_execution=execution_subject,
    )


# ---------------------------------------------------------------------------
# H3-05: interrupted during a cancel -- the cancellation request and one
# action's receipts are committed, but the CANCELED checkpoint/terminal
# receipt write is lost.
# ---------------------------------------------------------------------------


def test_h3_05_interrupted_during_cancel_finalizes_canceled_without_replaying_remaining_actions(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-05")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    # Control: cancellation observed inside action 0's own run() callback --
    # one continuous process, the "cancel during a multi-action operation"
    # shape.
    ctx_control = _basic_ctx(targets=_run_targets(), idempotency_key="h3-05-control")
    outcome_control = _consume_op(tmp_foundry, op_service, ctx_control)
    control_operation_id = outcome_control.operation.operation_id
    control_workspace_id = outcome_control.operation.workspace_id
    executed_control: list[str] = []
    control_raw_actions = scenario["actions"]

    def _control_run_first() -> ActionEffect:
        executed_control.append(control_raw_actions[0]["action_id"])
        svc.request_cancellation(control_operation_id, workspace_id=control_workspace_id)
        return ActionEffect(
            effect_kind=control_raw_actions[0]["effect_kind"],
            effect_digest=hashlib.sha256(
                f"{control_operation_id}-{control_raw_actions[0]['action_id']}".encode("utf-8")
            ).hexdigest(),
            effect_ref=control_raw_actions[0]["effect_ref"],
        )

    control_actions = [ActionSpec(control_raw_actions[0]["action_id"], _control_run_first)]
    control_actions.extend(_fixture_actions({"actions": control_raw_actions[1:]}, executed_control))

    execution_control = svc.run_actions(
        control_operation_id,
        identity=identity,
        operation_kind=ctx_control.operation_kind,
        actions=control_actions,
        attempt_ref="attempt-control",
    )

    # Subject: the cancellation request AND action 0's receipts are
    # durably committed, but the process is lost before the CANCELED
    # checkpoint/terminal receipt is written.
    ctx_subject = _basic_ctx(targets=_run_targets(), idempotency_key="h3-05-subject")
    outcome_subject = _consume_op(tmp_foundry, op_service, ctx_subject)
    operation_id = outcome_subject.operation.operation_id
    workspace_id = outcome_subject.operation.workspace_id

    cancel_outcome = svc.request_cancellation(operation_id, workspace_id=workspace_id)
    assert cancel_outcome.outcome == "created"

    first = scenario["actions"][0]
    receipt_service.record_action_receipt(
        operation_id,
        identity=identity,
        action_id=first["action_id"],
        action_index=0,
        status="completed",
        attempt_ref="attempt-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_id,
        identity=identity,
        action_id=first["action_id"],
        effect_kind=first["effect_kind"],
        effect_digest=hashlib.sha256(f"{operation_id}-{first['action_id']}".encode("utf-8")).hexdigest(),
        effect_ref=first["effect_ref"],
        generated_at=ids.now_iso(),
    )
    assert receipt_service.load_checkpoint(operation_id) is None  # the "loss" gap

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)
    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 1

    remaining = scenario["actions"][1:]
    subject_actions = [
        ActionSpec(
            first["action_id"],
            _must_not_run(first["action_id"], scenario_id="H3-05", reason="already committed pre-loss"),
        )
    ]
    subject_actions.extend(
        ActionSpec(
            a["action_id"],
            _must_not_run(a["action_id"], scenario_id="H3-05", reason="cancellation was already observed"),
        )
        for a in remaining
    )

    execution_subject = fresh_svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx_subject.operation_kind,
        actions=subject_actions,
        attempt_ref="attempt-postcrash",
        start_index=resume_point.next_action_index,
    )

    _assert_scenario_convergence(
        tmp_foundry,
        scenario,
        control_operation_id=control_operation_id,
        control_execution=execution_control,
        subject_operation_id=operation_id,
        subject_execution=execution_subject,
    )


# ---------------------------------------------------------------------------
# H3-06: exact-retry idempotency after completion, via run_or_replay.
# ---------------------------------------------------------------------------


def test_h3_06_exact_retry_after_completion_is_idempotent_via_run_or_replay(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-06")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    expected = scenario["expected"]
    expected_pairs = {tuple(p) for p in expected["effect_pairs"]}

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="h3-06")
    outcome = _consume_op(tmp_foundry, op_service, ctx)
    operation = outcome.operation
    operation_id = operation.operation_id
    executed: list[str] = []
    first_execution = svc.run_or_replay(
        operation,
        is_replay=False,
        identity=identity,
        operation_kind=ctx.operation_kind,
        actions=_fixture_actions(scenario, executed),
        attempt_ref="attempt-1",
    )
    assert first_execution.status == expected["terminal_status"]
    assert first_execution.replayed is False
    assert _canonical_effects(tmp_foundry, operation_id) == expected_pairs
    assert _action_receipt_count(tmp_foundry, operation_id) == expected["action_receipt_count"]
    assert _effect_receipt_count(tmp_foundry, operation_id) == expected["effect_receipt_count"]

    # Exact retry: the SAME operation object, as a real caller
    # re-presenting the SAME already-consumed confirmation would resolve
    # to via `consume_and_create_operation`'s own `exact_replay` outcome.
    executed.clear()
    second_execution = svc.run_or_replay(
        operation,
        is_replay=True,
        identity=identity,
        operation_kind=ctx.operation_kind,
        actions=_fixture_actions(scenario, executed),
        attempt_ref="attempt-2",
    )

    assert second_execution.replayed is True
    assert executed == []  # zero re-execution
    assert second_execution.terminal_receipt == first_execution.terminal_receipt
    assert _canonical_effects(tmp_foundry, operation_id) == expected_pairs
    assert _action_receipt_count(tmp_foundry, operation_id) == expected["action_receipt_count"]
    assert _effect_receipt_count(tmp_foundry, operation_id) == expected["effect_receipt_count"]


# ---------------------------------------------------------------------------
# H3-07: cancel semantics -- canceled before the first action, zero
# effects (explicit D2 zero-effect assertion).
# ---------------------------------------------------------------------------


def test_h3_07_cancel_before_first_action_produces_canceled_receipt_with_zero_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-07")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    expected = scenario["expected"]

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="h3-07")
    outcome = _consume_op(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    cancel_outcome = svc.request_cancellation(operation_id, workspace_id=workspace_id)
    assert cancel_outcome.outcome == "created"

    actions = [
        ActionSpec(
            a["action_id"],
            _must_not_run(a["action_id"], scenario_id="H3-07", reason="canceled before the first action"),
        )
        for a in scenario["actions"]
    ]
    execution = svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == expected["terminal_status"] == "canceled"
    assert execution.completed_action_count == 0
    # D2: explicit zero-effect assertion, not merely "the right terminal
    # status" -- zero rows in every receipt table this operation touches.
    assert _canonical_effects(tmp_foundry, operation_id) == set() == {tuple(p) for p in expected["effect_pairs"]}
    assert _action_receipt_count(tmp_foundry, operation_id) == expected["action_receipt_count"] == 0
    assert _effect_receipt_count(tmp_foundry, operation_id) == expected["effect_receipt_count"] == 0


# ---------------------------------------------------------------------------
# H3-08: resume-after-cancel refusal -- resume_operation against a
# terminal-canceled operation resolves to already_terminal, never
# re-executing and never minting a new attempt.
# ---------------------------------------------------------------------------


def test_h3_08_resume_after_terminal_cancel_is_refused_not_re_executed(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-08")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="h3-08")
    outcome = _consume_op(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    svc.request_cancellation(operation_id, workspace_id=workspace_id)
    setup_actions = [
        ActionSpec(
            a["action_id"],
            _must_not_run(a["action_id"], scenario_id="H3-08", reason="canceled before the first action"),
        )
        for a in scenario["actions"]
    ]
    execution = svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx.operation_kind,
        actions=setup_actions,
        attempt_ref="attempt-1",
    )
    assert execution.status == "canceled"
    canceled_receipt = execution.terminal_receipt

    # Attempt to RESUME the canceled operation with a genuinely FRESH,
    # otherwise-valid confirmation -- the resume-authority gate itself
    # would happily accept it (this is not a scenario-9 policy-denial
    # case); the operation's own TERMINAL state is what must refuse it.
    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="h3-08-resume",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(identity.workspace_id,),
    )
    resume_confirmation_id, resume_token, resume_record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=resume_record, presented_token=resume_token
    )
    assert resume_authorization.decision.allowed

    resume_actions = [
        ActionSpec(
            a["action_id"],
            _must_not_run(
                a["action_id"], scenario_id="H3-08", reason="resume-after-terminal-cancel must be refused"
            ),
        )
        for a in scenario["actions"]
    ]
    resume_outcome = svc.resume_operation(
        operation_id,
        identity=identity,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=resume_actions,
        operation_kind=ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot={"allowed_tools": ["search"], "data_scopes": []},
    )

    assert resume_outcome.outcome == "already_terminal"
    assert resume_outcome.new_attempt is None
    assert resume_outcome.execution is None
    assert resume_outcome.terminal_receipt == canceled_receipt
    assert attempt_adapter.list_attempts_for_operation(operation_id, identity=identity) == []
    assert _action_receipt_count(tmp_foundry, operation_id) == 0
    assert _effect_receipt_count(tmp_foundry, operation_id) == 0


# ---------------------------------------------------------------------------
# H3-09: duplicate suppression -- a SECOND, freshly-minted confirmation
# under the SAME (workspace_id, idempotency_key, digest) resolves to
# exact_replay against the SAME operation; zero duplicate receipts, zero
# duplicate `operations` rows.
# ---------------------------------------------------------------------------


def test_h3_09_duplicate_suppression_on_fresh_confirmation_same_idempotency_key(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-09")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    expected = scenario["expected"]
    expected_pairs = {tuple(p) for p in expected["effect_pairs"]}

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="h3-09")
    outcome = _consume_op(tmp_foundry, op_service, ctx)
    operation = outcome.operation
    operation_id = operation.operation_id
    executed: list[str] = []
    first_execution = svc.run_or_replay(
        operation,
        is_replay=False,
        identity=identity,
        operation_kind=ctx.operation_kind,
        actions=_fixture_actions(scenario, executed),
        attempt_ref="attempt-1",
    )
    assert first_execution.status == "completed"
    assert _canonical_effects(tmp_foundry, operation_id) == expected_pairs
    assert _action_receipt_count(tmp_foundry, operation_id) == expected["action_receipt_count"]
    assert _effect_receipt_count(tmp_foundry, operation_id) == expected["effect_receipt_count"]
    assert _count_operations(tmp_foundry) == 1

    # A SECOND, freshly-minted confirmation for the IDENTICAL ctx (same
    # workspace_id, idempotency_key, canonical_input_digest) -- the exact
    # shape of a caller retrying a request whose response it never saw.
    second_confirmation_id, second_token, second_record = _mint_and_record(op_service, ctx)
    second_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=second_record, presented_token=second_token
    )
    retry_outcome = op_service.consume_and_create_operation(
        confirmation_id=second_confirmation_id,
        presented_token=second_token,
        ctx=ctx,
        authorization=second_authorization,
    )
    assert retry_outcome.outcome == "exact_replay"
    assert retry_outcome.operation.operation_id == operation_id
    assert _count_operations(tmp_foundry) == 1  # no second `operations` row

    executed.clear()
    second_execution = svc.run_or_replay(
        retry_outcome.operation,
        is_replay=True,
        identity=identity,
        operation_kind=ctx.operation_kind,
        actions=_fixture_actions(scenario, executed),
        attempt_ref="attempt-2",
    )
    assert second_execution.replayed is True
    assert executed == []  # zero re-execution -- no duplicate card/claim/candidate
    assert second_execution.terminal_receipt == first_execution.terminal_receipt
    assert _canonical_effects(tmp_foundry, operation_id) == expected_pairs
    assert _action_receipt_count(tmp_foundry, operation_id) == expected["action_receipt_count"]
    assert _effect_receipt_count(tmp_foundry, operation_id) == expected["effect_receipt_count"]
    assert _count_operations(tmp_foundry) == 1


# ---------------------------------------------------------------------------
# H3-10: the full D6 convergence requirement over the largest fixture --
# an uninterrupted control run and a run interrupted after action 2's
# effect_receipt, then resumed on a fresh service instance.
# ---------------------------------------------------------------------------


def test_h3_10_full_convergence_uninterrupted_vs_interrupted_after_effect_receipt(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _scenario("H3-10")
    identity = _fixture_identity(scenario)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    # Control
    ctx_control = _basic_ctx(targets=_run_targets(), idempotency_key="h3-10-control")
    outcome_control = _consume_op(tmp_foundry, op_service, ctx_control)
    executed_control: list[str] = []
    execution_control = svc.run_actions(
        outcome_control.operation.operation_id,
        identity=identity,
        operation_kind=ctx_control.operation_kind,
        actions=_fixture_actions(scenario, executed_control),
        attempt_ref="attempt-control",
    )

    # Subject: interrupted after action index 2's effect_receipt -- no
    # checkpoint.
    ctx_subject = _basic_ctx(targets=_run_targets(), idempotency_key="h3-10-subject")
    outcome_subject = _consume_op(tmp_foundry, op_service, ctx_subject)
    operation_id = outcome_subject.operation.operation_id

    for idx in range(3):
        action = scenario["actions"][idx]
        receipt_service.record_action_receipt(
            operation_id,
            identity=identity,
            action_id=action["action_id"],
            action_index=idx,
            status="completed",
            attempt_ref="attempt-precrash",
            started_at=ids.now_iso(),
            completed_at=ids.now_iso(),
        )
        receipt_service.record_effect_receipt(
            operation_id,
            identity=identity,
            action_id=action["action_id"],
            effect_kind=action["effect_kind"],
            effect_digest=hashlib.sha256(f"{operation_id}-{action['action_id']}".encode("utf-8")).hexdigest(),
            effect_ref=action["effect_ref"],
            generated_at=ids.now_iso(),
        )
    assert receipt_service.load_checkpoint(operation_id) is None  # the "loss" gap

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)
    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 3

    executed_subject: list[str] = [a["action_id"] for a in scenario["actions"][:3]]
    subject_actions = [
        ActionSpec(
            a["action_id"],
            _must_not_run(a["action_id"], scenario_id="H3-10", reason="already committed pre-loss"),
        )
        for a in scenario["actions"][:3]
    ]
    subject_actions.extend(_fixture_actions({"actions": scenario["actions"][3:]}, executed_subject))

    execution_subject = fresh_svc.run_actions(
        operation_id,
        identity=identity,
        operation_kind=ctx_subject.operation_kind,
        actions=subject_actions,
        attempt_ref="attempt-postcrash",
        start_index=resume_point.next_action_index,
    )

    _assert_scenario_convergence(
        tmp_foundry,
        scenario,
        control_operation_id=outcome_control.operation.operation_id,
        control_execution=execution_control,
        subject_operation_id=operation_id,
        subject_execution=execution_subject,
    )

    # Explicit, standalone D6 SET-equality re-assertion (redundant with
    # `_assert_scenario_convergence` above, kept literal here since H3-10
    # is this matrix's designated "the hard requirement" scenario).
    control_set = _canonical_effects(tmp_foundry, outcome_control.operation.operation_id)
    subject_set = _canonical_effects(tmp_foundry, operation_id)
    assert control_set == subject_set
    assert len(control_set) == len(subject_set) == 5
