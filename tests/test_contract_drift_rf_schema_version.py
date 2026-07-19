"""Contract-drift tests for ``rf_schema_version`` (PRD FR-4.1 / AC-RFUP4-1, TASK-1.4).

Companion to ``docs/dev/architecture/machine-surface-inventory.md``, which
enumerates the 7 target surfaces. This module has four layers of defense,
from cheapest/most-mechanical to most end-to-end:

1. **Constant + shared-helper unit tests** — ``_stamp()`` (CLI) and ``stamp()``
   (API) always inject the *canonical* ``research_foundry.RF_SCHEMA_VERSION``,
   and a monkeypatch proves the assertion actually catches divergence (rather
   than passing vacuously).
2. **CLI structural scan** (surface #2) — every ``_json.dumps(`` call site in
   ``cli_commands.py`` is mechanically classified as stamped, a documented
   array-root exclusion, or a documented single-field echo. An unclassified
   site (i.e. a new dict-shaped ``--json`` output added without threading
   through ``_stamp()``) fails the test — this is the actual regression gate
   for future CLI additions, since exhaustively invoking all ~20 CLI commands
   here would be redundant with each command's own functional tests.
3. **Live presence/value smoke tests** (surfaces #2, #3, #5, #6, #7) — a
   representative dict-root invocation per surface via ``CliRunner`` /
   ``TestClient`` / direct service call, paired with the documented
   array-root / excluded-field sibling to prove the exclusion is real (key
   absent), not just untested.
4. **Fixture key-diff tests** (all target surfaces) — key-set comparisons
   proving the ``rf_schema_version`` (or ``RF_SCHEMA_VERSION``) contract is
   additive-only and durable:
   - CLI/API: raw service-layer dict (pre-stamp) vs. the actual stamped
     CLI/API output (post-stamp) — exact-equality diff, since both sides are
     produced live in the same test run.
   - ``verification.py`` / ``run-export.ts`` / ``__init__.py``: the current
     source's key/field set is compared against a **pinned pre-Phase-1
     baseline** (frozen constants below, derived once from
     ``git show e0ccd7e~1:<path>`` — the last commit before TASK-1.4/1.5
     stamped these surfaces). This is commit-independent by design: comparing
     against ``git show HEAD:<path>`` only works while a phase's changes are
     uncommitted, and stops working the moment that phase lands. The pinned
     baseline instead asserts the contract intent directly — the stamped key
     is present, no baseline key was ever removed, and new additive keys
     (e.g. Phase 2's ``exact_passage_violations``) are permitted rather than
     asserted away by an exact-equality diff.
   - ``errors.py``: explicitly asserted N/A (no code change; see TASK-1.2).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from research_foundry import RF_SCHEMA_VERSION, cli_commands
from research_foundry.api import response_stamp
from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import _enforce_existence_gate, get_paths
from research_foundry.cli import app as cli_app
from research_foundry.config import FoundryConfig
from research_foundry.errors import ExitCode
from research_foundry.paths import FoundryPaths
from research_foundry.services import builder_service, catalog_service, export_service
from research_foundry.services.verification import VerificationResult, verify_draft, verify_report
from research_foundry.yamlio import dump_yaml, load_yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_COMMANDS_PATH = REPO_ROOT / "src" / "research_foundry" / "cli_commands.py"
VERIFICATION_PATH = REPO_ROOT / "src" / "research_foundry" / "services" / "verification.py"
EXPORT_SERVICE_PATH = REPO_ROOT / "src" / "research_foundry" / "services" / "export_service.py"
INIT_PATH = REPO_ROOT / "src" / "research_foundry" / "__init__.py"
RUN_EXPORT_TS_PATH = REPO_ROOT / "frontend" / "runs-viewer" / "src" / "types" / "rf" / "run-export.ts"

runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Layer-4 pinned pre-Phase-1 baselines
#
# Frozen at git rev e0ccd7e~1 (the last commit before TASK-1.4/1.5 stamped
# `rf_schema_version` onto these surfaces), derived once via:
#   git show e0ccd7e~1:<path>
# and the module's own `_extract_*` helpers. These are commit-independent —
# unlike a live `git show HEAD:<path>` comparison, they don't go stale the
# moment the stamping change is committed to this branch.
# ---------------------------------------------------------------------------

_PRE_PHASE1_VERIFY_REPORT_RECORD_KEYS = frozenset(
    {
        "checks",
        "claim_ledger_path",
        "detail",
        "exit_code",
        "generated_at",
        "human_review_required",
        "id",
        "locations",
        "passed",
        "report_path",
        "run_id",
        "severity",
        "status",
        "unsupported",
    }
)

_PRE_PHASE1_VERIFY_DRAFT_RECORD_KEYS = frozenset(
    {
        "checks",
        "detail",
        "exit_code",
        "generated_at",
        "id",
        "locations",
        "passed",
        "report_draft_id",
        "severity",
        "status",
    }
)

_PRE_PHASE1_EXPORT_RUN_RETURN_KEYS = frozenset(
    {
        "artifact_schema_versions",
        "backlog_idea_id",
        "backlog_idea_ref",
        "category",
        "claim_counts",
        "claims",
        "context",
        "cost_usd",
        "created_at",
        "governance",
        "intent_id",
        "linked_projects",
        "model_profiles",
        "native_aliases",
        "report_anchors",
        "report_draft",
        "run_id",
        "schema_version",
        "sensitivity",
        "sensitivity_threshold",
        "source_count_by_type",
        "status_derived",
        "status_raw",
        "tags",
        "timeline",
        "title",
        "verification",
        "writebacks",
    }
)

_PRE_PHASE1_INIT_DUNDER_ALL = frozenset({"SCHEMA_VERSION", "__version__"})

_PRE_PHASE1_RUN_EXPORT_TS_FIELDS = frozenset(
    {
        "aos_artifact_uuid",
        "aos_feature_uuid",
        "aos_run_uuid",
        "aos_session_uuid",
        "aos_trace_uuid",
        "artifact_schema_versions",
        "backlog_idea_id",
        "backlog_idea_ref",
        "category",
        "claim_counts",
        "claims",
        "context",
        "cost_usd",
        "created_at",
        "extraction_model_profile",
        "freshness_days",
        "governance",
        "intent_id",
        "linked_projects",
        "max_cost_usd",
        "max_runtime_minutes",
        "model_profiles",
        "native_aliases",
        "report_anchors",
        "report_draft",
        "reusable_output_candidates",
        "run_id",
        "schema_version",
        "sensitivity",
        "sensitivity_threshold",
        "source_count_by_type",
        "status_derived",
        "status_raw",
        "synthesis_model_profile",
        "tags",
        "timeline",
        "title",
        "verification",
        "verification_model_profile",
        "writebacks",
    }
)


def _invoke_cli(args: list[str], cwd: Path):
    import os

    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(cli_app, args)
    finally:
        os.chdir(prev)


def _make_client(paths: FoundryPaths):
    from fastapi.testclient import TestClient

    cfg = FoundryConfig(paths=paths)
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: paths
    return TestClient(app, raise_server_exceptions=True)


def _extract_braced_block(source: str, start_marker: str, block_open: str) -> str:
    """Return the ``{...}``-delimited block that begins at the first
    occurrence of *block_open* after *start_marker* in *source* (brace-depth
    matched, so nested dict/object literals are handled correctly)."""

    idx = source.index(start_marker)
    open_idx = source.index(block_open, idx)
    brace_idx = source.index("{", open_idx)
    depth = 0
    i = brace_idx
    while True:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    return source[brace_idx : i + 1]


def _extract_record_keys(source: str, def_marker: str) -> set[str]:
    """Extract the quoted top-level keys of the ``record = {...}`` dict
    literal inside the function beginning at *def_marker* (e.g.
    ``"def verify_report("``)."""

    block = _extract_braced_block(source, def_marker, "record = {")
    return set(re.findall(r'"(\w+)":', block))


def _extract_return_dict_keys(source: str, def_marker: str) -> set[str]:
    """Extract the quoted top-level keys of the ``return {...}`` dict literal
    inside the function beginning at *def_marker* (e.g. ``"def export_run("``)."""

    block = _extract_braced_block(source, def_marker, "return {")
    return set(re.findall(r'"(\w+)":', block))


def _extract_ts_interface_fields(source: str, interface_name: str) -> set[str]:
    """Extract field names from a TypeScript ``export interface <name> {...}``
    block, stripping JSDoc comments first so comment prose never matches."""

    block = _extract_braced_block(source, f"export interface {interface_name} ", "{")
    no_comments = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL)
    no_comments = re.sub(r"//.*", "", no_comments)
    return set(re.findall(r"^\s*(\w+)\??:\s", no_comments, re.MULTILINE))


def _extract_dunder_all(source: str) -> set[str]:
    m = re.search(r"__all__\s*=\s*\[(.*?)\]", source, re.DOTALL)
    assert m, "expected __all__ list in research_foundry/__init__.py"
    return set(re.findall(r'"(\w+)"', m.group(1)))


# ===========================================================================
# 1. Constant + shared-helper unit tests (with drift-detection proof)
# ===========================================================================


def test_rf_schema_version_constant_shape():
    assert RF_SCHEMA_VERSION == "1.0.0"
    assert re.fullmatch(r"\d+\.\d+\.\d+", RF_SCHEMA_VERSION)


def test_cli_stamp_helper_matches_canonical():
    stamped = cli_commands._stamp({"foo": "bar"})
    assert stamped["rf_schema_version"] == RF_SCHEMA_VERSION
    assert stamped["foo"] == "bar"
    # additive-only: original payload untouched (no in-place mutation)
    original: dict[str, Any] = {"foo": "bar"}
    cli_commands._stamp(original)
    assert "rf_schema_version" not in original


def test_cli_stamp_helper_drift_is_actually_caught(monkeypatch):
    """Prove the contract-drift methodology: if the module-local reference to
    RF_SCHEMA_VERSION diverges from the canonical package constant, comparing
    the stamped output against the canonical constant fails — i.e. this test
    suite would catch real drift, not just tautologically re-check itself."""

    monkeypatch.setattr(cli_commands, "RF_SCHEMA_VERSION", "0.9.9-stale")
    drifted = cli_commands._stamp({})["rf_schema_version"]
    assert drifted == "0.9.9-stale"
    assert drifted != RF_SCHEMA_VERSION  # canonical constant is unaffected


def test_api_stamp_helper_matches_canonical():
    payload = {"foo": "bar"}
    result = response_stamp.stamp(payload)
    assert result["rf_schema_version"] == RF_SCHEMA_VERSION
    assert result is payload  # response_stamp.stamp is documented in-place


def test_api_stamp_helper_drift_is_actually_caught(monkeypatch):
    monkeypatch.setattr(response_stamp, "RF_SCHEMA_VERSION", "0.9.9-stale")
    drifted = response_stamp.stamp({})["rf_schema_version"]
    assert drifted == "0.9.9-stale"
    assert drifted != RF_SCHEMA_VERSION


def test_verification_result_dataclass_default_matches_canonical():
    result = VerificationResult(
        run_id="rf_run_x",
        passed=True,
        exit_code=int(ExitCode.OK),
        checks=[],
        verification_path=Path("/dev/null"),
        unsupported=[],
    )
    assert result.rf_schema_version == RF_SCHEMA_VERSION


# ===========================================================================
# 2. CLI structural scan — every dict-root --json call site accounted for
# ===========================================================================


def _classify_cli_json_dumps_sites(source: str) -> dict[str, list[int]]:
    lines = source.splitlines()
    stamped: list[int] = []
    array_excluded: list[int] = []
    field_echo: list[int] = []
    unclassified: list[int] = []

    for m in re.finditer(r"_json\.dumps\(", source):
        line_no = source.count("\n", 0, m.start()) + 1
        after = source[m.end() : m.end() + 200].lstrip()
        if after.startswith("_stamp("):
            stamped.append(line_no)
            continue
        ident_match = re.match(r"(\w+)", after)
        ident = ident_match.group(1) if ident_match else None
        preceding = "\n".join(lines[max(0, line_no - 6) : line_no - 1])
        if ident in {"summaries", "drafts"} and "bare JSON array" in preceding:
            array_excluded.append(line_no)
        elif ident in {"val", "value"} and "isinstance" in after:
            field_echo.append(line_no)
        else:
            unclassified.append(line_no)

    return {
        "stamped": stamped,
        "array_excluded": array_excluded,
        "field_echo": field_echo,
        "unclassified": unclassified,
    }


def test_cli_json_dumps_sites_fully_accounted_for():
    """Structural drift guard: fails red if a new dict-shaped ``--json``
    output is ever added to ``cli_commands.py`` without routing through
    ``_stamp()`` (or without the documented array-root/field-echo exclusion
    markers this test recognizes)."""

    source = CLI_COMMANDS_PATH.read_text()
    result = _classify_cli_json_dumps_sites(source)
    assert result["unclassified"] == [], (
        "Found _json.dumps( call site(s) not routed through _stamp() and not "
        f"carrying a recognized exclusion marker: lines {result['unclassified']}. "
        "Either wrap the payload in _stamp(...), or add the documented "
        "'NOTE: root is a bare JSON array' comment for an intentional "
        "array-root exclusion (see docs/dev/architecture/machine-surface-"
        "inventory.md)."
    )


def test_cli_json_dumps_site_counts_match_pinned_baseline():
    """Pinned to the current machine-surface-inventory.md count (26 stamped
    dict-root sites, 2 documented array-root exclusions, 2 unrelated
    single-field echo helpers = 30 total). Update this test's numbers
    alongside the inventory doc when CLI --json surfaces are deliberately
    added/removed — a silent count change here is itself a drift signal."""

    source = CLI_COMMANDS_PATH.read_text()
    result = _classify_cli_json_dumps_sites(source)
    assert len(result["stamped"]) == 26
    assert len(result["array_excluded"]) == 2
    assert len(result["field_echo"]) == 2


# ===========================================================================
# 3. Live presence/value smoke tests (representative per surface)
# ===========================================================================


def test_cli_catalog_stats_json_is_stamped(tmp_foundry):
    result = _invoke_cli(["catalog", "stats", "--json"], cwd=tmp_foundry.root)
    assert result.exit_code == 0, result.output
    import json as _json

    payload = _json.loads(result.output)
    assert payload["rf_schema_version"] == RF_SCHEMA_VERSION


def test_cli_run_list_json_is_not_stamped(tmp_foundry):
    """Documented array-root exclusion (machine-surface-inventory.md #2):
    ``rf run list --json`` emits a bare JSON array, so there is no top-level
    key namespace to stamp — this must stay unstamped, not silently regress
    into an untested gap."""

    result = _invoke_cli(["run", "list", "--json"], cwd=tmp_foundry.root)
    assert result.exit_code == 0, result.output
    import json as _json

    payload = _json.loads(result.output)
    assert isinstance(payload, list)


def test_verify_report_yaml_is_stamped(tmp_foundry):
    run_id = "rf_run_20260718_contract_drift_demo"
    result = verify_report(run_id, paths=tmp_foundry)
    assert result.rf_schema_version == RF_SCHEMA_VERSION
    persisted = load_yaml(tmp_foundry.run_paths(run_id).verification)
    assert persisted["rf_schema_version"] == RF_SCHEMA_VERSION


def test_verify_draft_yaml_is_stamped(tmp_foundry):
    draft = builder_service.create_draft(tmp_foundry, title="Contract Drift Draft")
    result = verify_draft(tmp_foundry, draft["report_draft_id"])
    assert result.rf_schema_version == RF_SCHEMA_VERSION
    verification_path = tmp_foundry.report_draft_dir(draft["report_draft_id"]) / "verification.yaml"
    persisted = load_yaml(verification_path)
    assert persisted["rf_schema_version"] == RF_SCHEMA_VERSION


def test_api_runs_detail_is_stamped_and_list_is_not(tmp_foundry):
    run_id = "rf_run_20260718_contract_drift_api"
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"run_id": run_id, "intent_id": f"intent_{run_id}", "status": "planned", "sensitivity": "public"},
        rp.run_yaml,
    )
    client = _make_client(tmp_foundry)

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["rf_schema_version"] == RF_SCHEMA_VERSION

    listing = client.get("/api/runs")
    assert listing.status_code == 200
    assert isinstance(listing.json(), list)


def test_api_reports_detail_is_stamped_and_list_is_not(tmp_foundry):
    draft = builder_service.create_draft(tmp_foundry, title="Contract Drift API Draft")
    client = _make_client(tmp_foundry)

    detail = client.get(f"/api/reports/{draft['report_draft_id']}")
    assert detail.status_code == 200
    assert detail.json()["rf_schema_version"] == RF_SCHEMA_VERSION

    listing = client.get("/api/reports")
    assert listing.status_code == 200
    assert isinstance(listing.json(), list)


def test_api_catalog_stats_is_stamped(tmp_foundry):
    client = _make_client(tmp_foundry)
    resp = client.get("/api/catalog/stats")
    assert resp.status_code == 200
    assert resp.json()["rf_schema_version"] == RF_SCHEMA_VERSION


def test_export_run_json_is_stamped(tmp_foundry):
    """Surface #4 (run-export generator, TASK-1.5 fix cycle): the actual
    ``export_service.export_run()`` function — whose output is written to
    the ``run.json`` files consumed by the runs-viewer static export build —
    must carry ``rf_schema_version`` alongside ``schema_version``, not just
    the TS type declaration for its output shape."""

    run_id = "rf_run_20260718_contract_drift_export"
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"run_id": run_id, "intent_id": f"intent_{run_id}", "status": "planned", "sensitivity": "public"},
        rp.run_yaml,
    )

    data = export_service.export_run(tmp_foundry, run_id)
    assert data["rf_schema_version"] == RF_SCHEMA_VERSION
    assert data["schema_version"] == export_service.EXPORT_SCHEMA_VERSION


# ===========================================================================
# 4. Fixture key-diff tests — additive-only, zero renamed/removed keys
# ===========================================================================


def test_keydiff_cli_catalog_stats_vs_raw_service_output(tmp_foundry):
    raw = catalog_service.stats(tmp_foundry, sensitivity_threshold=None)
    result = _invoke_cli(["catalog", "stats", "--json"], cwd=tmp_foundry.root)
    assert result.exit_code == 0, result.output
    import json as _json

    stamped = _json.loads(result.output)

    assert set(stamped) - set(raw) == {"rf_schema_version"}
    assert set(raw) - set(stamped) == set()
    for key, value in raw.items():
        assert stamped[key] == value, f"key {key!r} value changed by stamping"


def test_keydiff_api_catalog_stats_vs_raw_service_output(tmp_foundry):
    raw = catalog_service.stats(tmp_foundry, sensitivity_threshold=None)
    client = _make_client(tmp_foundry)
    stamped = client.get("/api/catalog/stats").json()

    assert set(stamped) - set(raw) == {"rf_schema_version"}
    assert set(raw) - set(stamped) == set()
    for key, value in raw.items():
        assert stamped[key] == value


def test_keydiff_api_runs_detail_vs_raw_export_gate(tmp_foundry):
    """``_enforce_existence_gate`` sources its "raw" dict from
    ``export_service.export_run()`` (surface #4), which the TASK-1.5 fix
    cycle now stamps directly — so unlike the other API key-diff tests here,
    ``raw`` already carries ``rf_schema_version`` before the router's
    ``stamp()`` helper (surface #5) runs. This is the intended additive
    behavior: two independent stamped surfaces compose without conflict
    (`stamp()` overwrites with the same canonical value, a no-op in effect),
    and no other key is renamed/removed by either layer."""

    run_id = "rf_run_20260718_contract_drift_keydiff"
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"run_id": run_id, "intent_id": f"intent_{run_id}", "status": "planned", "sensitivity": "public"},
        rp.run_yaml,
    )

    raw = _enforce_existence_gate(tmp_foundry, run_id, None)
    client = _make_client(tmp_foundry)
    stamped = client.get(f"/api/runs/{run_id}").json()

    assert raw["rf_schema_version"] == RF_SCHEMA_VERSION  # surface #4 (export_run) already stamps
    assert set(stamped) - set(raw) == set()
    assert set(raw) - set(stamped) == set()
    for key, value in raw.items():
        assert stamped[key] == value


def test_keydiff_api_reports_detail_vs_raw_load_draft(tmp_foundry):
    draft = builder_service.create_draft(tmp_foundry, title="Contract Drift Keydiff Draft")
    raw = builder_service.load_draft(tmp_foundry, draft["report_draft_id"])
    client = _make_client(tmp_foundry)
    stamped = client.get(f"/api/reports/{draft['report_draft_id']}").json()

    assert set(stamped) - set(raw) == {"rf_schema_version"}
    assert set(raw) - set(stamped) == set()
    for key, value in raw.items():
        assert stamped[key] == value


def test_keydiff_verify_report_record_vs_head():
    """Additive-only guarantee against the pinned pre-Phase-1 baseline (see
    module docstring / `_PRE_PHASE1_VERIFY_REPORT_RECORD_KEYS`): the stamped
    key is present, and no key that existed before Phase 1 has been removed.
    New additive keys are allowed and expected — e.g. Phase 2 also added
    `exact_passage_violations` to this same record — so this is intentionally
    not an exact-equality diff."""

    current_source = VERIFICATION_PATH.read_text()
    current_keys = _extract_record_keys(current_source, "def verify_report(")

    assert "rf_schema_version" in current_keys
    assert _PRE_PHASE1_VERIFY_REPORT_RECORD_KEYS - current_keys == set()


def test_keydiff_verify_draft_record_vs_head():
    current_source = VERIFICATION_PATH.read_text()
    current_keys = _extract_record_keys(current_source, "def verify_draft(")

    assert "rf_schema_version" in current_keys
    assert _PRE_PHASE1_VERIFY_DRAFT_RECORD_KEYS - current_keys == set()


def test_keydiff_run_export_ts_type_vs_head():
    current_source = RUN_EXPORT_TS_PATH.read_text()
    current_fields = _extract_ts_interface_fields(current_source, "RFRunExport")

    assert "rf_schema_version" in current_fields
    assert _PRE_PHASE1_RUN_EXPORT_TS_FIELDS - current_fields == set()

    # the added field must be optional (additive: absent on old cached exports)
    block = _extract_braced_block(current_source, "export interface RFRunExport ", "{")
    assert re.search(r"\brf_schema_version\?:\s*string;", block)

    # sibling type RFVerification deliberately does NOT get the field
    # (it's a derived subset of verification.yaml, not a mirror — see doc-comment)
    verification_fields_current = _extract_ts_interface_fields(current_source, "RFVerification")
    assert "rf_schema_version" not in verification_fields_current


def test_keydiff_export_run_vs_head():
    """Additive-only guarantee against the pinned pre-Phase-1 baseline: the
    ``rf_schema_version`` key added to ``export_run()``'s return dict in
    TASK-1.5's fix cycle must be present, and no key present before that fix
    (e.g. ``schema_version``) may have been removed."""

    current_source = EXPORT_SERVICE_PATH.read_text()
    current_keys = _extract_return_dict_keys(current_source, "def export_run(")

    assert "rf_schema_version" in current_keys
    assert _PRE_PHASE1_EXPORT_RUN_RETURN_KEYS - current_keys == set()


def test_keydiff_init_dunder_all_vs_head():
    current_source = INIT_PATH.read_text()
    current_all = _extract_dunder_all(current_source)

    assert "RF_SCHEMA_VERSION" in current_all
    assert _PRE_PHASE1_INIT_DUNDER_ALL - current_all == set()


def test_errors_exit_code_contract_is_unchanged_na_surface():
    """Surface #1 (errors.py exit-code contract) is explicitly N/A per
    TASK-1.2's finding: ExitCode is a process-exit contract, not a JSON
    payload, so it carries no rf_schema_version field. This test locks in
    that the enum itself was not touched by Phase 1 (the "no code change"
    claim), rather than silently omitting the surface from key-diff
    coverage."""

    assert {member.name: int(member) for member in ExitCode} == {
        "OK": 0,
        "USAGE": 1,
        "SCHEMA": 2,
        "GOVERNANCE": 3,
        "UNSUPPORTED": 4,
        "BUDGET": 5,
        "ADAPTER": 6,
        "HUMAN_REVIEW": 7,
    }
