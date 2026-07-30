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
import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import pytest

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_operation_service import (
    AuthorizationProof,
    OperationOutcome,
    OperatorOperationService,
    authorize_for_consumption,
)

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
    the confirmations table must show no partial mutation."""

    service = OperatorOperationService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(service, ctx)
    authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=record, presented_token=token
    )

    conn = _raw_connect(tmp_foundry)
    try:
        conn.execute(
            "UPDATE confirmations SET status = 'desynced' WHERE confirmation_id = ?",
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
    assert _confirmation_status(tmp_foundry, confirmation_id) == "desynced"
