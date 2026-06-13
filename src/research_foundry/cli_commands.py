"""CLI command wiring (spec §10, contract §12).

A single :func:`register` attaches every ``rf`` command/sub-app onto the Typer
app defined in ``cli.py``. The CLI stays thin: parse args → call a service →
render with Rich → translate result exit codes. Services are imported lazily
inside command bodies so the CLI module imports even while the service layer is
still being built.
"""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.table import Table

from .errors import ExitCode, RFError

console = Console()
err_console = Console(stderr=True)


def _fail(exc: Exception, code: ExitCode = ExitCode.USAGE) -> NoReturn:
    err_console.print(f"[red]{exc}[/red]")
    raise typer.Exit(int(getattr(exc, "exit_code", code)))


def register(app: typer.Typer) -> None:  # noqa: C901 - flat command wiring
    # ----- capture -----
    @app.command()
    def capture(
        text: str = typer.Argument(..., help="Raw idea text"),
        from_: str = typer.Option("manual", "--from", help="capture source"),
        sensitivity: str = typer.Option("personal", "--sensitivity"),
        tag: list[str] = typer.Option(None, "--tag", help="repeatable tag"),
        urgency: str = typer.Option("medium", "--urgency"),
        title: str | None = typer.Option(None, "--title"),
    ) -> None:
        """Capture a raw idea into the inbox (spec §10.2)."""

        from .services import capture as svc

        try:
            r = svc.capture_idea(
                text, title=title, captured_from=from_, sensitivity=sensitivity,
                urgency=urgency, tags=list(tag) if tag else None,
            )
        except RFError as e:
            _fail(e)
        console.print(f"[green]captured[/green] {r.raw_idea_id}")
        typer.echo(str(r.path))  # plain (unwrapped) for scripting

    # ----- triage -----
    @app.command()
    def triage(
        raw_ref: str = typer.Argument(..., help="raw_idea.md path or id"),
        create_intent: bool = typer.Option(True, "--create-intent/--no-create-intent"),
        create_ibom: bool = typer.Option(True, "--create-ibom/--no-create-ibom"),
        create_tree_node: bool = typer.Option(True, "--create-tree-node/--no-create-tree-node"),
    ) -> None:
        """Triage a raw idea into intent + I-BOM + IntentTree node (spec §10.3)."""

        from .services import capture as svc

        try:
            r = svc.triage_idea(
                raw_ref, create_intent=create_intent, create_ibom=create_ibom,
                create_tree_node=create_tree_node,
            )
        except RFError as e:
            _fail(e)
        console.print("[green]triaged[/green]")
        for label, ident in (("intent", r.intent_id), ("ibom", r.ibom_id), ("node", r.node_id)):
            if ident:
                typer.echo(f"{label}={ident}")  # plain (unwrapped) for scripting

    # ----- plan -----
    @app.command()
    def plan(
        intent_id: str = typer.Argument(...),
        depth: str = typer.Option("standard", "--depth"),
        audience: str = typer.Option("technical", "--audience"),
        max_cost: float = typer.Option(5.0, "--max-cost"),
        freshness: int = typer.Option(180, "--freshness", help="max source age (days)"),
        profile: str | None = typer.Option(None, "--profile", help="runtime key profile"),
    ) -> None:
        """Plan a research swarm: brief + swarm plan + routing decision (spec §10.4)."""

        from .services import planning as svc

        try:
            r = svc.plan_run(
                intent_id, depth=depth, audience=audience,
                max_cost_usd=max_cost, freshness_days=freshness, profile=profile,
            )
        except RFError as e:
            _fail(e)  # GovernanceError carries exit_code=3; others default to usage
        console.print(f"[green]planned[/green] run {r.run_id}")
        typer.echo(f"run={r.run_id}")  # plain (unwrapped) for scripting
        for p in (r.brief_path, r.swarm_path, r.routing_path):
            typer.echo(str(p))

    # ----- ingest / source-card -----
    @app.command()
    def ingest(
        locator: str = typer.Argument(..., help="URL or file path"),
        run: str = typer.Option(..., "--run", help="run id"),
        source_type: str = typer.Option("other", "--source-type"),
        sensitivity: str = typer.Option("personal", "--sensitivity"),
        title: str | None = typer.Option(None, "--title"),
        fetch: bool = typer.Option(False, "--fetch/--no-fetch", help="attempt URL fetch"),
    ) -> None:
        """Ingest a source into a run and create a source card (spec §10.5)."""

        from .services import source_cards as svc

        try:
            r = svc.ingest_source(
                locator, run_id=run, source_type=source_type,
                sensitivity=sensitivity, title=title, fetch=fetch,
            )
        except RFError as e:
            _fail(e)
        tag = " [yellow](degraded)[/yellow]" if r.degraded else ""
        console.print(f"[green]source card[/green] {r.source_card_id}{tag}")
        typer.echo(str(r.path))  # plain (unwrapped) for scripting

    source_card_app = typer.Typer(help="Source card operations.")

    @source_card_app.command("create")
    def source_card_create(
        locator: str = typer.Argument(...),
        run: str = typer.Option(..., "--run"),
        source_type: str = typer.Option("other", "--source-type"),
        sensitivity: str = typer.Option("personal", "--sensitivity"),
        title: str | None = typer.Option(None, "--title"),
    ) -> None:
        """Create a source card (alias of ingest)."""

        from .services import source_cards as svc

        try:
            r = svc.create_source_card(
                locator=locator, run_id=run, source_type=source_type,
                sensitivity=sensitivity, title=title,
            )
        except RFError as e:
            _fail(e)
        console.print(f"[green]source card[/green] {r.source_card_id}")

    app.add_typer(source_card_app, name="source-card")

    # ----- extract -----
    @app.command()
    def extract(
        run: str = typer.Argument(...),
        model_profile: str = typer.Option("rf_extract_cheap", "--model-profile"),
    ) -> None:
        """Create extraction cards from a run's source cards (spec §10.7)."""

        from .services import extraction as svc

        try:
            r = svc.extract_run(run, model_profile=model_profile)
        except RFError as e:
            _fail(e)
        console.print(f"[green]extracted[/green] {r.count} card(s)")

    # ----- claim-map -----
    @app.command("claim-map")
    def claim_map(run: str = typer.Argument(...)) -> None:
        """Build the claim ledger from extraction cards (spec §10.8)."""

        from .services import claim_mapping as svc

        try:
            r = svc.build_claim_ledger(run)
        except RFError as e:
            _fail(e)
        console.print(f"[green]claim ledger[/green] {r.claims_total} claim(s)")
        for status, n in sorted(r.by_status.items()):
            console.print(f"  {status}: {n}")

    # ----- synthesize -----
    @app.command()
    def synthesize(
        run: str = typer.Argument(...),
        model_profile: str = typer.Option("rf_synthesize_deep", "--model-profile"),
        final: bool = typer.Option(False, "--final/--draft"),
        llm: bool = typer.Option(False, "--llm/--deterministic"),
    ) -> None:
        """Synthesize a report from the claim ledger (spec §10.9)."""

        from .services import synthesis as svc

        try:
            r = svc.synthesize_report(run, model_profile=model_profile, final=final, llm=llm)
        except RFError as e:
            _fail(e)
        console.print(f"[green]report[/green] {r.report_path} ({len(r.claims_cited)} claims cited)")

    # ----- verify -----
    @app.command()
    def verify(
        run: str = typer.Argument(...),
        report: str | None = typer.Option(None, "--report"),
        claim_ledger: str | None = typer.Option(None, "--claim-ledger"),
        fail_on_unsupported: bool = typer.Option(True, "--fail-on-unsupported/--no-fail-on-unsupported"),
    ) -> None:
        """Verify every material claim maps or is labeled (spec §10.10). Exit codes per §10.10."""

        from .services import verification as svc

        try:
            r = svc.verify_report(
                run,
                report_path=Path(report) if report else None,
                claim_ledger_path=Path(claim_ledger) if claim_ledger else None,
                fail_on_unsupported=fail_on_unsupported,
            )
        except RFError as e:
            _fail(e, ExitCode.SCHEMA)
        _render_checks(r.checks)
        if r.passed:
            console.print("[green]✓ verification passed[/green]")
        else:
            err_console.print(f"[red]✗ verification failed (exit {r.exit_code})[/red]")
            for u in r.unsupported:
                err_console.print(f"  unsupported: {u}")
        raise typer.Exit(r.exit_code)

    # ----- council -----
    @app.command()
    def council(
        run: str = typer.Argument(...),
        roles: str = typer.Option("critic,domain_reviewer,governance_officer,executive_translator", "--roles"),
        vote: str = typer.Option("approve-concern-block", "--vote"),
    ) -> None:
        """Run a council review (spec §10.11)."""

        from .services import writeback as svc

        try:
            path = svc.council_review(run, roles=[r.strip() for r in roles.split(",")], vote=vote)
        except RFError as e:
            _fail(e)
        console.print(f"[green]council review[/green] {path}")

    # ----- bundle -----
    @app.command()
    def bundle(
        run: str = typer.Argument(...),
        verify_flag: bool = typer.Option(True, "--verify/--no-verify"),
    ) -> None:
        """Publish an evidence bundle (spec §10.12)."""

        from .services import writeback as svc

        try:
            r = svc.build_bundle(run, verify=verify_flag)
        except RFError as e:
            _fail(e)
        state = "[green]verified[/green]" if r.verified else "[yellow]draft[/yellow]"
        console.print(f"evidence bundle {r.bundle_id} {state}")
        for k, v in r.counts.items():
            console.print(f"  {k}: {v}")

    # ----- writeback -----
    @app.command()
    def writeback(
        run: str = typer.Argument(...),
        targets: str = typer.Option("meatywiki,skillmeat,ccdash", "--targets"),
        require_review: bool = typer.Option(False, "--require-review/--no-require-review"),
    ) -> None:
        """Generate writebacks to MeatyWiki / SkillMeat / CCDash (spec §10.13)."""

        from .services import writeback as svc

        try:
            r = svc.writeback(
                run, targets=tuple(t.strip() for t in targets.split(",")),
                require_review=require_review,
            )
        except RFError as e:
            _fail(e)
        for p in (r.meatywiki_path, r.skillbom_path, r.ccdash_path):
            if p:
                console.print(f"  {p}")
        if r.requires_review:
            console.print("[yellow]writebacks require human review before promotion[/yellow]")

    # ----- guard -----
    guard_app = typer.Typer(help="Governance guard (spec §10.15).")

    @guard_app.command("check")
    def guard_check(
        profile: str = typer.Option("personal", "--profile"),
        run: str | None = typer.Option(None, "--run"),
        sensitivity: str | None = typer.Option(None, "--sensitivity"),
        provider: str | None = typer.Option(None, "--provider"),
        writeback: list[str] = typer.Option(None, "--writeback", help="repeatable target"),
        key_profile: str | None = typer.Option(
            None, "--key-profile", help="alias of --profile (runtime key)"
        ),
        key_profile_allowed: str | None = typer.Option(
            None, "--key-profile-allowed", help="intent's allowed key profile (standalone form)"
        ),
    ) -> None:
        """Check governance policy for a profile/run.

        With ``--run``, the run's intent + source cards populate the context so
        the §7.2 rules can actually fire. Without a run, the boundary is testable
        standalone via ``--key-profile-allowed`` / ``--sensitivity`` / ``--provider``.
        """

        from .services import governance as svc

        eff_profile = key_profile or profile
        targets = tuple(writeback) if writeback else ()
        try:
            if run:
                ctx = svc.load_run_context(
                    run,
                    profile=eff_profile,
                    model_provider=provider,
                    writeback_targets=targets,
                    paths=None,
                )
                # CLI overrides take precedence over derived run values.
                if sensitivity or key_profile_allowed:
                    ctx = svc.GuardContext(
                        profile=ctx.profile,
                        run_id=ctx.run_id,
                        sensitivity=sensitivity or ctx.sensitivity,
                        source_sensitivities=ctx.source_sensitivities,
                        model_provider=provider or ctx.model_provider,
                        writeback_targets=ctx.writeback_targets,
                        intent_key_profile_allowed=(
                            key_profile_allowed or ctx.intent_key_profile_allowed
                        ),
                        artifact_paths=ctx.artifact_paths,
                    )
            else:
                ctx = svc.GuardContext(
                    profile=eff_profile,
                    sensitivity=sensitivity,
                    model_provider=provider,
                    writeback_targets=targets,
                    intent_key_profile_allowed=key_profile_allowed,
                )
            r = svc.guard_check(ctx)
        except RFError as e:
            _fail(e, ExitCode.GOVERNANCE)
        if r.passed:
            console.print(f"[green]✓ guard passed[/green] (profile {eff_profile})")
        else:
            for v in r.violations:
                err_console.print(f"[red]{v.severity}[/red] {v.rule_id}: {v.message}")
        raise typer.Exit(r.exit_code)

    app.add_typer(guard_app, name="guard")

    # ----- skillbom -----
    skillbom_app = typer.Typer(help="SkillBOM candidates (spec §10.14).")

    @skillbom_app.command("propose")
    def skillbom_propose(run: str = typer.Argument(...)) -> None:
        from .services import writeback as svc

        try:
            path = svc.skillbom_propose(run)
        except RFError as e:
            _fail(e)
        console.print(f"[green]skillbom candidate[/green] {path}")

    @skillbom_app.command("promote")
    def skillbom_promote(
        candidate_id: str = typer.Argument(...),
        reviewer: str = typer.Option(..., "--reviewer"),
    ) -> None:
        from .services import writeback as svc

        try:
            path = svc.skillbom_promote(candidate_id, reviewer=reviewer)
        except RFError as e:
            _fail(e)
        console.print(f"[green]promoted[/green] {path}")

    app.add_typer(skillbom_app, name="skillbom")

    # ----- ccdash -----
    ccdash_app = typer.Typer(help="CCDash telemetry (spec §10.15).")

    @ccdash_app.command("summarize")
    def ccdash_summarize(period: str = typer.Option("daily", "--period")) -> None:
        from .services import telemetry as svc

        try:
            path = svc.summarize(period)
        except RFError as e:
            _fail(e)
        console.print(f"[green]ccdash summary[/green] {path}")

    app.add_typer(ccdash_app, name="ccdash")

    # ----- swarm (thin adapter orchestration) -----
    swarm_app = typer.Typer(help="Run swarm adapters per swarm_plan (spec §10.6).")

    @swarm_app.command("run")
    def swarm_run(
        run: str = typer.Argument(...),
        adapters: str = typer.Option("gpt_researcher,paperqa2", "--adapters"),
        profile: str = typer.Option("personal", "--profile"),
        dry_run: bool = typer.Option(False, "--dry-run/--execute"),
    ) -> None:
        """Run enabled discovery adapters (degraded-safe) to produce source candidates."""

        from .adapters import get_adapter, load_all
        from .frontmatter import load_md
        from .paths import FoundryPaths
        from .yamlio import dump_yaml

        load_all()
        paths = FoundryPaths.discover()
        rp = paths.run_paths(run)
        wanted = [a.strip() for a in adapters.split(",")]
        # research_brief.md is front-mattered Markdown, not pure YAML.
        brief = load_md(rp.research_brief)[0] if rp.research_brief.exists() else {}
        if dry_run:
            console.print(f"[cyan]dry-run[/cyan] would run: {', '.join(wanted)}")
            return
        candidates: list[dict] = []
        for aid in wanted:
            ad = get_adapter(aid)
            if ad is None:
                err_console.print(f"[yellow]unknown adapter {aid}[/yellow]")
                continue
            res = ad.run({"brief": brief, "profile": profile})
            candidates.extend(res.source_candidates)
            mark = " (degraded)" if res.degraded else ""
            console.print(f"  {aid}: {len(res.source_candidates)} candidate(s){mark}")
        dump_yaml({"source_candidates": candidates}, rp.source_candidates)
        console.print(f"[green]source candidates[/green] {rp.source_candidates}")

    app.add_typer(swarm_app, name="swarm")

    # ----- status -----
    @app.command()
    def status() -> None:
        """Show foundry status: runs, intents, sources (spec §10.15)."""

        from .config import FoundryConfig

        cfg = FoundryConfig.load()
        p = cfg.paths
        table = Table(title="rf status")
        table.add_column("Area")
        table.add_column("Count")
        table.add_row("intents (active)", str(_count(p.intents_active, "*.yaml")))
        table.add_row("runs", str(_count(p.runs, "rf_run_*", dirs=True)))
        table.add_row("raw ideas", str(_count(p.raw_ideas, "*.md")))
        console.print(table)

    # ----- cost -----
    @app.command()
    def cost(run: str = typer.Argument(..., help="run id or glob")) -> None:
        """Summarize estimated cost for a run (spec §10.15)."""

        from .config import FoundryConfig
        from .yamlio import load_yaml

        cfg = FoundryConfig.load()
        rp = cfg.paths.run_paths(run)
        total = 0.0
        if rp.token_costs.exists():
            data = load_yaml(rp.token_costs) or {}
            total = float(data.get("total_cost_usd", 0.0)) if isinstance(data, dict) else 0.0
        console.print(f"run {run}: estimated ${total:.4f}")

    # ----- index -----
    index_app = typer.Typer(help="Registry indexes (spec §10.15).")

    @index_app.command("rebuild")
    def index_rebuild() -> None:
        from .services import telemetry as svc

        rebuild = getattr(svc, "rebuild_indexes", None)
        if callable(rebuild):
            rebuild()
            console.print("[green]indexes rebuilt[/green]")
        else:
            console.print("[yellow]index rebuild not implemented[/yellow]")

    app.add_typer(index_app, name="index")

    # ----- init (spec §10.1 / §16 Day-1) -----
    @app.command()
    def init(
        path: str = typer.Argument(".", help="target workspace path"),
        profile: str = typer.Option("personal", "--profile", help="default key profile"),
    ) -> None:
        """Initialize a new foundry workspace (folders + schemas/config/templates)."""

        from .services import workspace as svc

        try:
            r = svc.init_workspace(path, profile=profile)
        except RFError as e:
            _fail(e)
        console.print(f"[green]initialized[/green] foundry at {r.root}")
        if r.created_dirs:
            console.print(f"  created {len(r.created_dirs)} dir(s)")
        if r.copied:
            console.print(f"  copied: {', '.join(r.copied)}")
        if r.already_present:
            console.print(f"  already present: {', '.join(sorted(set(r.already_present)))}")

    # ----- redact (spec §10.15) -----
    @app.command()
    def redact(
        run: str = typer.Argument(..., help="run id"),
        target: str = typer.Option("public", "--target", help="redaction audience"),
    ) -> None:
        """Write a target-audience-redacted copy of a run's report (spec §10.15)."""

        from .services import workspace as svc

        try:
            r = svc.redact_run(run, target=target)
        except RFError as e:
            _fail(e)
        console.print(f"[green]redacted[/green] {r.redacted_path}")
        console.print(f"  masked {len(r.redacted_claims)} sensitive claim(s)")

    # ----- intent (spec §16 Day-2: rf intent show) -----
    intent_app = typer.Typer(help="Research intent operations (spec §16 Day-2).")

    @intent_app.command("show")
    def intent_show(intent_id: str = typer.Argument(...)) -> None:
        """Print a research intent's YAML (resolve active, then recursive search)."""

        from .paths import FoundryPaths
        from .yamlio import dumps_yaml, load_yaml

        paths = FoundryPaths.discover()
        candidate = paths.intents_active / f"{intent_id}.yaml"
        if not candidate.exists() and paths.intents.exists():
            matches = sorted(paths.intents.rglob(f"{intent_id}.yaml"))
            candidate = matches[0] if matches else candidate
        if not candidate.exists():
            err_console.print(f"[red]intent not found: {intent_id}[/red]")
            raise typer.Exit(int(ExitCode.USAGE))
        typer.echo(dumps_yaml(load_yaml(candidate)).rstrip())

    app.add_typer(intent_app, name="intent")

    # ----- tree (spec §16 Day-2: rf tree add-node) -----
    tree_app = typer.Typer(help="IntentTree operations (spec §16 Day-2).")

    @tree_app.command("add-node")
    def tree_add_node(
        intent: str = typer.Option(..., "--intent", help="intent id this node serves"),
        title: str = typer.Option(..., "--title", help="node title"),
        level: str = typer.Option("L4", "--level"),
        status: str = typer.Option("ready", "--status"),
        priority: str = typer.Option("medium", "--priority"),
        parent: str | None = typer.Option(None, "--parent"),
    ) -> None:
        """Create/append an IntentTree node YAML (validated vs intenttree_node)."""

        from .ids import tree_node_id
        from .paths import FoundryPaths
        from .schemas import SchemaRegistry
        from .yamlio import dump_yaml

        paths = FoundryPaths.discover()
        node_id = tree_node_id(title)
        node = {
            "node_id": node_id,
            "level": level,
            "title": title,
            "intent_id": intent,
            "status": status,
            "priority": priority,
            "expected_artifacts": ["evidence_bundle"],
        }
        if parent:
            node["parent"] = parent
        reg = SchemaRegistry()
        if reg.has("intenttree_node"):
            result = reg.validate(node, "intenttree_node")
            if not result.ok:
                err_console.print("[red]invalid intenttree node[/red]")
                for e in result.errors:
                    err_console.print(f"  - {e}")
                raise typer.Exit(int(ExitCode.SCHEMA))
        out_path = paths.intenttree_nodes / f"{node_id}.yaml"
        dump_yaml(node, out_path)
        console.print(f"[green]tree node[/green] {node_id}")
        typer.echo(str(out_path))

    app.add_typer(tree_app, name="tree")


def _render_checks(checks) -> None:
    table = Table(title="verifier checks", show_header=True, header_style="bold")
    table.add_column("check")
    table.add_column("severity")
    table.add_column("status")
    for c in checks:
        color = {"pass": "green", "warn": "yellow", "fail": "red", "skip": "dim"}.get(c.status, "")
        table.add_row(c.id, c.severity, f"[{color}]{c.status}[/{color}]" if color else c.status)
    console.print(table)


def _count(directory: Path, pattern: str, *, dirs: bool = False) -> int:
    if not directory.exists():
        return 0
    items = directory.glob(pattern)
    return sum(1 for i in items if (i.is_dir() if dirs else i.is_file()))


__all__ = ["register"]
