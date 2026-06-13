"""CLI-level governance + workspace tests (adversarial audit closure).

Covers the gaps the audit found:
* ``rf guard check`` actually blocks work/personal key mixing (exit 3) and
  passes a clean personal run (exit 0) — both via the Typer CLI.
* ``rf init`` scaffolds a fresh workspace (folders + copied schemas/config/
  templates) and is idempotent.
* ``rf schema validate foundry.yaml`` exits 0.
* the new secret-scanner patterns are detected.
* governance preflight is wired into ``rf plan`` (work profile on a personal
  intent blocks; a normal personal plan succeeds).
* ``rf redact`` masks claims backed by work/client-sensitive source cards.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import planning, workspace
from research_foundry.services.governance import scan_secrets
from research_foundry.yamlio import dump_yaml

runner = CliRunner()


# --- helpers ---------------------------------------------------------------


def _write_intent(paths: FoundryPaths, *, key_profile_allowed: str = "personal") -> str:
    intent_id = "intent_research_20260613_demo_topic"
    intent = {
        "id": intent_id,
        "title": "Demo research topic",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Investigate the demo topic deterministically.",
        "governance": {
            "sensitivity": "personal",
            "key_profile_allowed": key_profile_allowed,
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{intent_id}.yaml")
    return intent_id


def _invoke(args: list[str], cwd: Path):
    """Run the CLI from ``cwd`` so workspace discovery resolves to the tmp root."""

    import os

    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(prev)


# --- rf guard check (the headline fix) -------------------------------------


def test_guard_check_blocks_work_profile_on_personal_run(tmp_foundry):
    intent_id = _write_intent(tmp_foundry, key_profile_allowed="personal")
    result = planning.plan_run(intent_id, profile="personal", paths=tmp_foundry)

    out = _invoke(
        ["guard", "check", "--profile", "work_approved", "--run", result.run_id],
        tmp_foundry.root,
    )
    assert out.exit_code == 3, out.output
    assert "no_work_keys_for_personal_runs" in out.output


def test_guard_check_passes_clean_personal_run(tmp_foundry):
    intent_id = _write_intent(tmp_foundry, key_profile_allowed="personal")
    result = planning.plan_run(intent_id, profile="personal", paths=tmp_foundry)

    out = _invoke(
        ["guard", "check", "--profile", "personal", "--run", result.run_id],
        tmp_foundry.root,
    )
    assert out.exit_code == 0, out.output
    assert "guard passed" in out.output


def test_guard_check_standalone_boundary_blocks(tmp_foundry):
    out = _invoke(
        ["guard", "check", "--profile", "work_approved", "--key-profile-allowed", "personal"],
        tmp_foundry.root,
    )
    assert out.exit_code == 3, out.output
    assert "no_work_keys_for_personal_runs" in out.output


def test_guard_check_standalone_unapproved_provider_blocks(tmp_foundry):
    out = _invoke(
        [
            "guard", "check", "--profile", "work_approved",
            "--sensitivity", "work_sensitive", "--provider", "someunapproved",
        ],
        tmp_foundry.root,
    )
    assert out.exit_code == 3, out.output
    assert "no_work_sensitive_to_unapproved_provider" in out.output


# --- preflight wired into rf plan ------------------------------------------


def test_plan_run_blocks_work_profile_on_personal_intent(tmp_foundry):
    from research_foundry.errors import GovernanceError

    intent_id = _write_intent(tmp_foundry, key_profile_allowed="personal")
    with pytest.raises(GovernanceError):
        planning.plan_run(intent_id, profile="work_approved", paths=tmp_foundry)


def test_plan_run_personal_still_succeeds(tmp_foundry):
    intent_id = _write_intent(tmp_foundry, key_profile_allowed="personal")
    result = planning.plan_run(intent_id, paths=tmp_foundry)  # default profile
    assert result.run_id
    assert (tmp_foundry.runs / result.run_id / "run.yaml").exists()


# --- rf init ---------------------------------------------------------------


def test_init_scaffolds_fresh_workspace(tmp_path):
    target = tmp_path / "new-foundry"
    res = workspace.init_workspace(target)

    # Core folders exist.
    for sub in ("config", "schemas", "templates", "inbox/raw_ideas",
                "intents/active", "runs", "registries", "intenttree/nodes"):
        assert (target / sub).is_dir(), sub
    # Distribution assets copied.
    assert (target / "foundry.yaml").exists()
    assert any((target / "schemas").glob("*.schema.yaml"))
    assert (target / "config" / "governance.yaml").exists()
    assert any((target / "templates").iterdir())
    assert "foundry.yaml" in res.copied


def test_init_is_idempotent(tmp_path):
    target = tmp_path / "idem-foundry"
    workspace.init_workspace(target)
    second = workspace.init_workspace(target)
    # Second run copies nothing new (everything already present).
    assert second.copied == []
    assert "foundry.yaml" in second.already_present


def test_init_via_cli(tmp_path):
    target = tmp_path / "cli-foundry"
    out = runner.invoke(app, ["init", str(target)])
    assert out.exit_code == 0, out.output
    assert (target / "foundry.yaml").exists()
    assert (target / "schemas").is_dir()


# --- rf schema validate foundry.yaml ---------------------------------------


def test_schema_validate_foundry_yaml_exits_zero(tmp_foundry):
    out = _invoke(["schema", "validate", "foundry.yaml"], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert "valid" in out.output


# --- new secret patterns ---------------------------------------------------


@pytest.mark.parametrize(
    "secret",
    [
        "sk_live_4eC39HqLyjWDarjtT1zdp7dc",
        "rk_live_4eC39HqLyjWDarjtT1zdp7dc",
        "SG.aaaaaaaaaaaaaaaaaaaaaa.bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "SK0123456789abcdef0123456789abcdef",
        "AC0123456789abcdef0123456789abcdef",
        "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "github_pat_11ABCDEFG0abcdefghijkl_xyz0123456789",
        "Authorization: Bearer abcdef1234567890ABCDEF",
        "xoxb-0123456789ab",
        "xoxe-0123456789ab",
        "xapp-1-A012345678-abcdefghij",
    ],
)
def test_new_secret_patterns_detected(tmp_foundry, secret):
    cfg = FoundryConfig(paths=tmp_foundry)
    assert scan_secrets(secret, config=cfg), f"expected detection: {secret}"


def test_secret_patterns_no_false_positive_on_prose(tmp_foundry):
    cfg = FoundryConfig(paths=tmp_foundry)
    for benign in (
        "A clean personal research note about evidence bundles.",
        "Set the api key in the dashboard before running.",
        "The bearer of this news is happy to share an update today.",
    ):
        assert scan_secrets(benign, config=cfg) == [], benign


# --- rf redact -------------------------------------------------------------


def test_redact_masks_work_sensitive_claims(tmp_foundry):
    rp = tmp_foundry.run_paths("rf_run_redact_demo").ensure_scaffold()
    dump_md(
        {"type": "source_card", "source_card_id": "src_work",
         "sensitivity": "work_sensitive", "source": {"title": "w"}},
        "# w", rp.sources / "src_work.md",
    )
    dump_md(
        {"type": "source_card", "source_card_id": "src_pers",
         "sensitivity": "personal", "source": {"title": "p"}},
        "# p", rp.sources / "src_pers.md",
    )
    dump_yaml(
        {"id": "cl", "claims": [
            {"claim_id": "clm_001", "sources": [{"source_card_id": "src_work"}]},
            {"claim_id": "clm_002", "sources": [{"source_card_id": "src_pers"}]},
        ]},
        rp.claim_ledger,
    )
    body = (
        "## Findings\n\nWork finding. [claim:clm_001]\n\n"
        "Personal finding. [claim:clm_002]\n"
    )
    dump_md({"type": "research_report", "report_id": "r1", "sensitivity": "personal"},
            body, rp.report_draft)

    res = workspace.redact_run("rf_run_redact_demo", target="public", paths=tmp_foundry)
    assert res.redacted_claims == ["clm_001"]
    meta, out = load_md(res.redacted_path)
    assert "[REDACTED" in out
    assert "Work finding." not in out
    assert "Personal finding. [claim:clm_002]" in out
    assert meta.get("redacted") is True
    assert meta.get("sensitivity") == "public"


def test_redact_clean_report_masks_nothing(tmp_foundry):
    rp = tmp_foundry.run_paths("rf_run_clean_redact").ensure_scaffold()
    dump_md(
        {"type": "source_card", "source_card_id": "src_pers",
         "sensitivity": "personal", "source": {"title": "p"}},
        "# p", rp.sources / "src_pers.md",
    )
    dump_yaml(
        {"id": "cl", "claims": [
            {"claim_id": "clm_001", "sources": [{"source_card_id": "src_pers"}]},
        ]},
        rp.claim_ledger,
    )
    dump_md({"type": "research_report", "report_id": "r1", "sensitivity": "personal"},
            "## Findings\n\nAll personal. [claim:clm_001]\n", rp.report_draft)

    res = workspace.redact_run("rf_run_clean_redact", target="public", paths=tmp_foundry)
    assert res.redacted_claims == []
    _, out = load_md(res.redacted_path)
    assert "All personal. [claim:clm_001]" in out


# --- intent show / tree add-node via service-level resolution ---------------


def test_tree_add_node_writes_valid_node(tmp_foundry):
    intent_id = _write_intent(tmp_foundry)
    out = _invoke(
        ["tree", "add-node", "--intent", intent_id, "--title", "Demo node title"],
        tmp_foundry.root,
    )
    assert out.exit_code == 0, out.output
    nodes = list(tmp_foundry.intenttree_nodes.glob("*.yaml"))
    assert nodes, "expected a node file"


def test_intent_show_prints_yaml(tmp_foundry):
    intent_id = _write_intent(tmp_foundry)
    out = _invoke(["intent", "show", intent_id], tmp_foundry.root)
    assert out.exit_code == 0, out.output
    assert intent_id in out.output
