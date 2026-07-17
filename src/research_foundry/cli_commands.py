"""CLI command wiring (spec §10, contract §12).

A single :func:`register` attaches every ``rf`` command/sub-app onto the Typer
app defined in ``cli.py``. The CLI stays thin: parse args → call a service →
render with Rich → translate result exit codes. Services are imported lazily
inside command bodies so the CLI module imports even while the service layer is
still being built.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .errors import ExitCode, RFError

console = Console()
err_console = Console(stderr=True)


def _fail(exc: Exception, code: ExitCode = ExitCode.USAGE) -> NoReturn:
    err_console.print(f"[red]{exc}[/red]")
    raise typer.Exit(int(getattr(exc, "exit_code", code)))


def _arc_council_via(run_id: str, console: Console, err_console: Console, svc: object) -> None:
    """Submit a council review to ARC; fall back to local if unreachable.

    Exit 0 on approve, 7 on concern|block. When ARC is unreachable, falls back
    to the local deterministic council with a printed note.
    """

    try:
        from .integrations.arc import ArcClient
        from .paths import FoundryPaths

        client = ArcClient.from_config()
        if not client.available():
            console.print("[yellow]ARC unreachable — falling back to local council review[/yellow]")
            _local_council_fallback(run_id, console, svc)
            return

        paths = FoundryPaths.discover()
        rp = paths.run_paths(run_id)
        rp.ensure_scaffold()

        # Build a minimal evidence bundle if not present.
        from .services.writeback import (
            _ledger,
            _load_bundle,
            _render_arc_council,
            _sensitivity,
            build_bundle,
        )

        bundle = _load_bundle(rp)
        if not bundle:
            build_bundle(run_id, verify=True, paths=paths)
            bundle = _load_bundle(rp)
        bundle_ident = str((bundle or {}).get("id") or run_id)
        ledger = _ledger(rp)
        sensitivity = _sensitivity(rp)

        arc_path = _render_arc_council(
            rp,
            paths,
            bundle_ident=bundle_ident,
            ledger=ledger,
            sensitivity=sensitivity,
            requires_review=False,
        )

        # Read back the candidate to get verdict + exit code.
        from .yamlio import load_yaml
        candidate = load_yaml(arc_path) or {}
        verdict = candidate.get("verdict")
        rf_exit = int(candidate.get("rf_exit_code", 7))
        status = candidate.get("status", "proposed")

        if verdict:
            color = "green" if verdict == "approve" else "red"
            console.print(f"[{color}]ARC verdict: {verdict}[/{color}] (status: {status})")
        else:
            console.print(f"[yellow]ARC run submitted; verdict pending (status: {status})[/yellow]")
        console.print(f"  review request: {arc_path}")
        raise typer.Exit(rf_exit)

    except typer.Exit:
        raise
    except Exception:  # noqa: BLE001 — any error falls back to local
        console.print("[yellow]ARC error — falling back to local council review[/yellow]")
        _local_council_fallback(run_id, console, svc)


def _local_council_fallback(run_id: str, console: Console, svc: object) -> None:
    """Run the local deterministic council (used as ARC fallback)."""

    from .errors import RFError

    try:
        path = svc.council_review(  # type: ignore[attr-defined]
            run_id,
            roles=["critic", "domain_reviewer", "governance_officer", "executive_translator"],
            vote="approve-concern-block",
        )
    except RFError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
    console.print(f"[green]council review (local)[/green] {path}")


def _validate_nonloopback_bind(
    config: Any,
    effective_bind_host: str,
    effective_auth_mode: str,
    env: Any,
) -> None:
    """Validate that a non-loopback bind is safe before any port is opened.

    Raises ``ValueError`` with an actionable message when the bind is unsafe.
    The ``rf serve`` command calls this and converts ``ValueError`` → exit 1.

    Checks (in order):

    1. Auth must be enabled — either ``config.is_auth_enabled()`` (covers
       both the new ``auth.provider`` path and the legacy
       ``viewer.auth_mode`` path) or the CLI-override
       ``effective_auth_mode`` resolves to ``"token"``.
    2. At least one resolvable token must exist:
       - ``auth.provider=local_static``: at least one configured
         ``token_env`` env var must be non-empty.
       - Legacy path: the ``viewer.auth_token_env`` env var must be
         non-empty.

    Args:
        config: :class:`~research_foundry.config.FoundryConfig` instance.
        effective_bind_host: The resolved bind address (e.g. ``"0.0.0.0"``).
        effective_auth_mode: Resolved auth mode string (``"none"`` or
            ``"token"``); may come from a CLI flag override.
        env: Mapping to look up env var values (pass ``os.environ``).
    """
    # Gate 1: auth must be enabled (from config OR CLI override to "token").
    if not config.is_auth_enabled() and effective_auth_mode != "token":
        raise ValueError(
            f"Cannot bind to non-loopback address {effective_bind_host!r}: "
            "no auth is configured. Set auth.provider=local_static in "
            "foundry.yaml or pass --auth-mode token."
        )

    # Gate 2: verify at least one resolvable token exists.
    _auth_provider = "none"
    try:
        _auth_provider = config.auth_provider()
    except ValueError:
        pass  # Unimplemented/unrecognised provider — fall through to legacy check.

    if _auth_provider == "local_static":
        # New canonical path: at least one local_static token env var must be set.
        token_configs = config.auth_local_static_tokens()
        has_any_token = any(
            bool(env.get(cfg.get("token_env", ""), ""))
            for cfg in token_configs
            if cfg.get("token_env")
        )
        if not has_any_token:
            token_envs = [
                cfg.get("token_env", "")
                for cfg in token_configs
                if cfg.get("token_env")
            ]
            env_desc = ", ".join(token_envs) if token_envs else "RF_SERVE_TOKEN_*, etc."
            raise ValueError(
                f"Cannot bind to non-loopback address: "
                f"auth.provider=local_static is configured but no token env vars "
                f"({env_desc}) are set. Set at least one token env var before "
                f"binding to {effective_bind_host}."
            )
    else:
        # Legacy path: viewer.auth_mode=token requires the token env var to be set.
        token_env_var = config.viewer_auth_token_env()
        token_value = env.get(token_env_var, "")
        if not token_value:
            raise ValueError(
                f"{token_env_var} not set; refusing to bind on {effective_bind_host}"
            )


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
        backlog_idea_ref: str | None = typer.Option(
            None,
            "--backlog-idea-ref",
            help="Link to a backlog idea by RIB-NNN ref (validated against the backlog).",
        ),
    ) -> None:
        """Capture a raw idea into the inbox (spec §10.2).

        Pass ``--backlog-idea-ref RIB-NNN`` to link the captured idea to an
        entry in ``backlog/research_idea_backlog.yaml``.  The ref is validated
        before the idea is written; an unrecognised ref exits with an error.
        """

        from .paths import FoundryPaths
        from .services import capture as svc
        from .services.backlog_metadata import backlog_exists, lookup_metadata

        # Validate the backlog ref before writing anything.
        if backlog_idea_ref is not None:
            _bpaths = FoundryPaths.discover()
            if not backlog_exists(_bpaths):
                err_console.print(
                    "[yellow]warning:[/yellow] backlog/research_idea_backlog.yaml not found; "
                    "--backlog-idea-ref will be stored but cannot be validated."
                )
            else:
                _bmeta = lookup_metadata(backlog_idea_ref, _bpaths)
                if _bmeta is None:
                    err_console.print(
                        f"[red]error:[/red] backlog idea ref '{backlog_idea_ref}' not found "
                        "in backlog/research_idea_backlog.yaml."
                    )
                    raise typer.Exit(int(ExitCode.USAGE))

        try:
            r = svc.capture_idea(
                text, title=title, captured_from=from_, sensitivity=sensitivity,
                urgency=urgency, tags=list(tag) if tag else None,
                backlog_idea_ref=backlog_idea_ref,
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
        project: str | None = typer.Option(None, "--project", help="project slug (sets run.yaml project field and NLM correlation)"),
        notebook_mode: str | None = typer.Option(None, "--notebook-mode", help="NotebookLM correlation mode override: project|run|explicit (default: config)"),
        notebook_id: str | None = typer.Option(None, "--notebook-id", help="explicit notebook id (for --notebook-mode explicit)"),
    ) -> None:
        """Plan a research swarm: brief + swarm plan + routing decision (spec §10.4).

        Pass ``--project`` to associate this run with a project slug (used for
        NotebookLM correlation).  ``--notebook-mode`` and ``--notebook-id``
        control how the run is mapped to a NotebookLM notebook.
        """

        from .services import planning as svc

        try:
            r = svc.plan_run(
                intent_id, depth=depth, audience=audience,
                max_cost_usd=max_cost, freshness_days=freshness, profile=profile,
                project=project,
            )
        except RFError as e:
            _fail(e)  # GovernanceError carries exit_code=3; others default to usage
        console.print(f"[green]planned[/green] run {r.run_id}")
        typer.echo(f"run={r.run_id}")  # plain (unwrapped) for scripting
        for p in (r.brief_path, r.swarm_path, r.routing_path):
            typer.echo(str(p))
        # Best-effort NLM correlation (fail-soft — never blocks planning).
        if notebook_mode or notebook_id:
            _apply_notebook_options(
                r.run_id,
                project=notebook_id if notebook_mode == "explicit" else project,
                mode=notebook_mode,
            )

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
        via: str = typer.Option("local", "--via", help="Review backend: 'arc' to submit to ARC, 'local' for deterministic local review (default: local). Falls back to local when ARC is unreachable."),
    ) -> None:
        """Run a council review (spec §10.11).

        With ``--via arc`` submits the run's evidence bundle to ARC for review
        and exits 0 on 'approve', 7 on 'concern' or 'block'. Falls back to local
        review when ARC is unreachable.
        """

        from .services import writeback as svc

        if via == "arc":
            # Try ARC path first; fall back to local on error or unavailability.
            _arc_council_via(run, console, err_console, svc)
            return

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
        targets: str = typer.Option(
            "meatywiki,skillmeat,ccdash",
            "--targets",
            help="Comma-separated targets: meatywiki,skillmeat,ccdash,intenttree,arc,notebooklm",
        ),
        require_review: bool = typer.Option(False, "--require-review/--no-require-review"),
        decision_record_only: bool = typer.Option(
            False,
            "--decision-record-only",
            help=(
                "Re-render only the decision_record writeback for this run. "
                "Leaves all other writeback files untouched. "
                "No-ops silently when the ledger has zero inference claims."
            ),
        ),
    ) -> None:
        """Generate writebacks to MeatyWiki / SkillMeat / CCDash / IntentTree (spec §10.13).

        The ``notebooklm`` target is an opt-in addition — include it in
        ``--targets`` to push the run's report and source cards to the
        associated NotebookLM notebook.  The notebook must already exist (or be
        resolvable via the correlation registry).

        Pass ``--decision-record-only`` to re-render only the decision_record
        writeback for an existing run without disturbing other writeback files.
        Used for the backfill path over already-completed runs.
        """

        if decision_record_only:
            from .ids import bundle_id as make_bundle_id
            from .paths import FoundryPaths
            from .services.writeback import (
                _inference_claims,
                _ledger,
                _load_bundle,
                _render_decision_record,
                _sensitivity,
            )

            paths = FoundryPaths.discover()
            rp = paths.run_paths(run)
            if not rp.run.exists():
                err_console.print(f"[red]run not found: {run} ({rp.run})[/red]")
                raise typer.Exit(1)

            ledger = _ledger(rp)
            if not _inference_claims(ledger):
                console.print("[yellow]no inference claims — decision_record skipped[/yellow]")
                return

            bundle = _load_bundle(rp)
            bundle_ident = str(bundle.get("id") or make_bundle_id(run))
            sensitivity = _sensitivity(rp)
            _WORK_SENSITIVITIES = {"work_sensitive", "client_sensitive"}
            requires_review = bool(require_review) or sensitivity in _WORK_SENSITIVITIES

            out = _render_decision_record(
                rp,
                paths,
                bundle_ident=bundle_ident,
                sensitivity=sensitivity,
                ledger=ledger,
                requires_review=requires_review,
            )
            if out:
                console.print(f"  {out}")
            return

        from .services import writeback as svc

        try:
            r = svc.writeback(
                run, targets=tuple(t.strip() for t in targets.split(",")),
                require_review=require_review,
            )
        except RFError as e:
            _fail(e)
        all_paths = [
            r.meatywiki_path,
            r.decision_record_path,
            r.skillbom_path,
            r.ccdash_path,
            r.intenttree_update_path,
            r.arc_review_path,
            getattr(r, "notebooklm_update_path", None),
        ]
        for p in all_paths:
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
        adapters: str = typer.Option(
            "gpt_researcher,paperqa2",
            "--adapters",
            help="Comma-separated adapter ids (e.g. gpt_researcher,paperqa2,notebooklm).",
        ),
        profile: str = typer.Option("personal", "--profile"),
        dry_run: bool = typer.Option(False, "--dry-run/--execute"),
        project: str | None = typer.Option(None, "--project", help="project slug (sets run.yaml project field and NLM correlation)"),
        notebook_mode: str | None = typer.Option(None, "--notebook-mode", help="NotebookLM correlation mode override: project|run|explicit (default: config)"),
        notebook_id: str | None = typer.Option(None, "--notebook-id", help="explicit notebook id (for --notebook-mode explicit)"),
    ) -> None:
        """Run enabled discovery adapters (degraded-safe) to produce source candidates.

        Pass ``--project`` to associate this run with a project slug used for
        NotebookLM correlation.  Add ``notebooklm`` to ``--adapters`` to also
        push sources to the linked notebook.  ``--notebook-mode`` and
        ``--notebook-id`` refine how the run maps to a notebook.
        """

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
        # Best-effort NLM correlation before adapter dispatch (fail-soft).
        if project or notebook_mode or notebook_id:
            _apply_notebook_options(
                run,
                project=notebook_id if notebook_mode == "explicit" else project,
                mode=notebook_mode,
            )
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
    status_app = typer.Typer(help="Status commands.")

    @status_app.callback(invoke_without_command=True)
    def status(ctx: typer.Context) -> None:
        """Show foundry status: runs, intents, sources (spec §10.15)."""

        if ctx.invoked_subcommand is not None:
            return

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

    @status_app.command("push")
    def status_push(
        run: str = typer.Option(..., "--run", help="run id"),
        to: str = typer.Option("intenttree", "--to", help="integration target (intenttree)"),
        stage: str = typer.Option("bundle_written", "--stage",
                                  help="milestone stage: discovery_started, sources_ingested, verify_passed, bundle_written"),
    ) -> None:
        """Push run status to an integration target (best-effort)."""

        from .services import telemetry as svc

        if to != "intenttree":
            err_console.print(f"[yellow]unknown target {to!r}; only 'intenttree' supported[/yellow]")
            raise typer.Exit(1)

        pushed = svc.push_status(run, stage)
        if pushed:
            console.print(f"[green]pushed[/green] stage={stage} to {to} for run {run}")
        else:
            console.print(f"[yellow]skipped[/yellow] stage={stage} to {to} (offline or no node linked)")

    app.add_typer(status_app, name="status")

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

    # ----- intake (spec §3.3: IntentTree inbound) -----
    intake_app = typer.Typer(help="Inbound intake from external systems (spec §3.3).")

    @intake_app.command("intenttree")
    def intake_intenttree(
        node_id: str = typer.Argument(..., help="IntentTree node id to pull"),
        from_file: Path | None = typer.Option(
            None, "--from-file", help="Load node from a local YAML file (offline mode)"
        ),
        do_plan: bool = typer.Option(False, "--plan/--no-plan", help="Also run plan after triage"),
        sensitivity: str = typer.Option("personal", "--sensitivity", help="Governance sensitivity"),
        profile: str | None = typer.Option(None, "--profile", help="Runtime key profile for planning"),
    ) -> None:
        """Pull an IntentTree node and run capture→triage→(optional)plan.

        Closes the Phase 1 loop: the resulting intent's intenttree_node_ref is
        set to the source node_id so subsequent writebacks update the originating
        IntentTree node rather than a locally-minted placeholder.
        """

        from .services.intake import intake_from_intenttree

        try:
            r = intake_from_intenttree(
                node_id,
                from_file=from_file,
                do_plan=do_plan,
                sensitivity=sensitivity,
                profile=profile,
            )
        except RFError as e:
            _fail(e)
        console.print(f"[green]intake[/green] node {r.node_id}")
        typer.echo(f"raw_idea={r.raw_idea_id}")
        if r.intent_id:
            typer.echo(f"intent={r.intent_id}")
        if r.run_id:
            typer.echo(f"run={r.run_id}")
        if r.raw_idea_path:
            typer.echo(str(r.raw_idea_path))
        if r.intent_path:
            typer.echo(str(r.intent_path))

    @intake_app.command("notebooklm")
    def intake_notebooklm(
        notebook_id: str = typer.Argument(..., help="NotebookLM notebook id to pull"),
        project: str | None = typer.Option(None, "--project", help="project slug to associate with this intake"),
    ) -> None:
        """Pull a NotebookLM notebook into RF as a new captured research idea.

        Creates a raw idea and intent from the notebook metadata.  The
        ``notebooklm_notebook_ref`` is back-patched onto the resulting intent
        so downstream writebacks and the correlation layer can find the
        originating notebook.

        This operation is fail-soft: if the NotebookLM client is unavailable
        the intake still completes with ``offline=True`` using the notebook_id
        as context.
        """

        from .services.intake import intake_from_notebooklm

        try:
            r = intake_from_notebooklm(notebook_id, project=project)
        except RFError as e:
            _fail(e)
        offline_tag = " [yellow](offline)[/yellow]" if r.offline else ""
        console.print(f"[green]intake[/green] notebook {r.notebook_id}{offline_tag}")
        typer.echo(f"raw_idea={r.raw_idea_id}")
        if r.intent_id:
            typer.echo(f"intent={r.intent_id}")
        if r.raw_idea_path:
            typer.echo(str(r.raw_idea_path))
        if r.intent_path:
            typer.echo(str(r.intent_path))

    app.add_typer(intake_app, name="intake")

    # ----- notebooklm command group -----
    notebooklm_app = typer.Typer(help="NotebookLM integration management.")

    @notebooklm_app.command("resolve")
    def notebooklm_resolve(
        run: str = typer.Option(..., "--run", help="RF run id"),
        project: str | None = typer.Option(None, "--project", help="project slug (or explicit notebook_id when --mode explicit)"),
        mode: str | None = typer.Option(None, "--mode", help="correlation mode override: project|run|explicit"),
        notebook_id: str | None = typer.Option(None, "--notebook-id", help="explicit notebook id (short-form for --mode explicit)"),
        create: bool = typer.Option(False, "--create/--no-create", help="create the notebook if it does not exist yet (requires NLM client)"),
    ) -> None:
        """Resolve (and optionally create) the NotebookLM notebook for a run.

        Prints the resolved notebook_id and metadata as Rich output.  With
        ``--create`` a new notebook may be created via the NotebookLM client;
        prints a clear message when the client is unavailable (fail-soft).
        """

        from .services.notebook_correlation import correlation_mode as _cfg_mode
        from .services.notebook_correlation import resolve_notebook

        # --notebook-id is a convenience alias for --mode explicit + project=<id>.
        effective_mode = mode
        effective_project = project
        if notebook_id and not effective_mode:
            effective_mode = "explicit"
            effective_project = notebook_id
        elif notebook_id:
            effective_project = notebook_id

        nlm_client = None
        if create:
            try:
                from .integrations import get_notebooklm_client
                nlm_client = get_notebooklm_client()
            except Exception:  # noqa: BLE001 — fail-soft
                console.print("[yellow]NLM client unavailable — notebook creation skipped[/yellow]")

        result = resolve_notebook(
            run,
            project=effective_project,
            mode=effective_mode,
            create=create,
            client=nlm_client,
        )

        if result is None:
            console.print(
                f"[yellow]no notebook resolved for run {run!r}"
                f" (mode={effective_mode or _cfg_mode()})[/yellow]"
            )
            raise typer.Exit(1)

        table = Table(title=f"notebook for run {run}")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("notebook_id", result.get("notebook_id", ""))
        table.add_row("notebook_title", result.get("notebook_title", ""))
        table.add_row("project", result.get("project", ""))
        table.add_row("mode", result.get("mode", ""))
        console.print(table)
        typer.echo(result.get("notebook_id", ""))  # plain for scripting

    @notebooklm_app.command("status")
    def notebooklm_status() -> None:
        """Show NotebookLM client availability, correlation mode, and registry summary."""

        from .services.notebook_correlation import (
            _read_registry,
        )
        from .services.notebook_correlation import (
            correlation_mode as _cfg_mode,
        )

        # Client availability (fail-soft).
        available = False
        try:
            from .integrations import get_notebooklm_client
            available = get_notebooklm_client().available()
        except Exception:  # noqa: BLE001
            pass

        mode = _cfg_mode()
        registry = _read_registry()

        project_count = len(registry.get("projects") or {})
        run_count = len(registry.get("runs") or {})

        table = Table(title="rf notebooklm status")
        table.add_column("Key")
        table.add_column("Value")
        table.add_row("client available", "[green]yes[/green]" if available else "[yellow]no[/yellow]")
        table.add_row("correlation_mode", mode)
        table.add_row("projects in registry", str(project_count))
        table.add_row("runs in registry", str(run_count))
        console.print(table)

    @notebooklm_app.command("sync")
    def notebooklm_sync(
        run: str = typer.Option(..., "--run", help="RF run id"),
        project: str | None = typer.Option(None, "--project", help="project slug (for notebook resolution)"),
    ) -> None:
        """Print the notebooklm-sync batch command for a run's Markdown files.

        Resolves the notebook for the given run (read-only, no creation), then
        prints the exact command the operator should run to sync the run's
        Markdown output files to the notebook.  Does NOT execute the command.
        """

        from .paths import FoundryPaths
        from .services.notebook_correlation import resolve_notebook

        paths = FoundryPaths.discover()
        rp = paths.run_paths(run)

        result = resolve_notebook(run, project=project)
        if result is None:
            err_console.print(
                f"[red]no notebook resolved for run {run!r}"
                " — run 'rf notebooklm resolve --run <run> --create' first[/red]"
            )
            raise typer.Exit(1)

        notebook_id_val = result["notebook_id"]

        # Collect Markdown files in the run directory.
        md_files: list[str] = []
        if rp.run.exists():
            for md in sorted(rp.run.rglob("*.md")):
                md_files.append(str(md))

        console.print(f"[green]notebook:[/green] {notebook_id_val}")
        console.print("[cyan]Run the following command to sync:[/cyan]")
        if md_files:
            files_arg = " ".join(f'"{f}"' for f in md_files)
            console.print(
                f"  notebooklm add-source --notebook {notebook_id_val} {files_arg}"
            )
        else:
            console.print(
                f"  notebooklm add-source --notebook {notebook_id_val} <no .md files found in {rp.run}>"
            )

    app.add_typer(notebooklm_app, name="notebooklm")

    # ----- backlog -----
    backlog_app = typer.Typer(help="Backlog lifecycle management.")

    @backlog_app.command("reconcile")
    def backlog_reconcile(
        dry_run: bool = typer.Option(True, "--dry-run/--write",
                                     help="Print diff only (default). Pass --write to apply."),
    ) -> None:
        """Reconcile run→backlog lifecycle: fill missing status and links fields.

        Scans ``runs/*/run.yaml`` for ``backlog_idea_ref``, maps each back to
        the matching idea in ``backlog/research_idea_backlog.yaml``, and
        advances ``status`` (forward only) and fills null ``links.*`` fields.

        Defaults to ``--dry-run`` — prints the proposed diff as a table
        without writing.  Pass ``--write`` to apply changes atomically.

        Also reports inverse drift:
        * Backlog ideas marked ``completed`` with no matching run directory.
        * Run directories that carry no ``backlog_idea_ref`` field.
        """

        from .paths import FoundryPaths
        from .services.backlog_metadata import reconcile_backlog

        paths = FoundryPaths.discover()

        try:
            diffs, orphaned_completed, runs_without_ref = reconcile_backlog(
                paths, dry_run=dry_run
            )
        except Exception as exc:  # noqa: BLE001
            err_console.print(f"[red]reconcile error:[/red] {exc}")
            raise typer.Exit(1) from exc

        mode_label = "dry-run" if dry_run else "write"

        # --- changes table ---
        if diffs:
            diff_table = Table(
                title=f"backlog reconcile ({mode_label}) -- {len(diffs)} change(s)",
                show_header=True,
                header_style="bold",
            )
            diff_table.add_column("ref")
            diff_table.add_column("field")
            diff_table.add_column("old")
            diff_table.add_column("new")
            for d in diffs:
                diff_table.add_row(
                    d.ref,
                    d.field,
                    str(d.old) if d.old is not None else "null",
                    f"[green]{d.new}[/green]",
                )
            console.print(diff_table)
        else:
            console.print(f"[green]backlog reconcile ({mode_label}):[/green] no changes needed")

        # --- inverse drift ---
        if orphaned_completed:
            console.print(
                f"\n[yellow]orphaned completed ideas[/yellow] "
                f"(marked completed but no run dir): {len(orphaned_completed)}"
            )
            for ref in orphaned_completed:
                console.print(f"  {ref}")

        if runs_without_ref:
            console.print(
                f"\n[yellow]runs without backlog_idea_ref[/yellow]: {len(runs_without_ref)}"
            )
            for rid in runs_without_ref:
                console.print(f"  {rid}")

        if not dry_run and diffs:
            console.print(f"\n[green]applied {len(diffs)} change(s) to backlog[/green]")

    app.add_typer(backlog_app, name="backlog")

    # ----- run (runs-frontend export contract, Phase 1) -----
    run_app = typer.Typer(help="Run export contract for the read-only runs viewer.")

    @run_app.command("export")
    def run_export(
        run_id: str = typer.Option(None, "--run-id", help="run id to export"),
        all_runs: bool = typer.Option(False, "--all", help="export every discovered run"),
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON output (the only format)"),
        stdout: bool = typer.Option(False, "--stdout", help="write to stdout instead of run.json"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="override foundry.yaml viewer.sensitivity_threshold",
        ),
    ) -> None:
        """Export a denormalized run.json claim graph (deterministic; no LLM)."""

        import json as _json
        import sys as _sys

        from .paths import FoundryPaths
        from .services import export_service as svc

        paths = FoundryPaths.discover()
        try:
            if all_runs:
                written = svc.export_all(paths, sensitivity_threshold=sensitivity_threshold)
                for path in written:
                    console.print(f"[green]exported[/green] {path}")
                if not written:
                    console.print("[yellow]no runs found[/yellow]")
                return
            if not run_id:
                _fail(RFError("provide --run-id or --all"))
            if stdout:
                data = svc.export_run(
                    paths, run_id, sensitivity_threshold=sensitivity_threshold
                )
                typer.echo(_json.dumps(data, ensure_ascii=False, indent=2))
            else:
                out = svc.export_to_file(
                    paths, run_id, sensitivity_threshold=sensitivity_threshold
                )
                console.print(f"[green]exported[/green] {out}")
        except svc.ExportError as exc:
            print(_json.dumps(exc.as_payload()), file=_sys.stderr)
            raise typer.Exit(int(exc.exit_code)) from exc

    @run_app.command("list")
    def run_list(
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
    ) -> None:
        """List discovered runs with derived status (recursive, depth <= 3)."""

        import json as _json

        from .paths import FoundryPaths
        from .services import export_service as svc

        paths = FoundryPaths.discover()
        summaries = svc.list_runs(paths)
        typer.echo(_json.dumps(summaries, ensure_ascii=False, indent=2))

    app.add_typer(run_app, name="run")

    # ----- catalog (shared evidence catalog, public-multiuser-release Phase 1) -----
    catalog_app = typer.Typer(help="Shared evidence catalog — search/import claims, sources, "
                                    "inferences, reports across runs.")

    @catalog_app.command("import")
    def catalog_import(
        run_id: str = typer.Argument(None, help="run id to import (omit with --all)"),
        all_runs: bool = typer.Option(False, "--all", help="import every discovered run"),
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
    ) -> None:
        """(Re)import a run — or every discovered run — into the catalog (idempotent)."""

        import json as _json
        import sys as _sys

        from .paths import FoundryPaths
        from .services import catalog_service as svc

        paths = FoundryPaths.discover()
        if all_runs:
            result = svc.import_all(paths)
            typer.echo(_json.dumps(result, ensure_ascii=False, indent=2))
            return
        if not run_id:
            _fail(RFError("provide RUN_ID or --all"))
        try:
            result = svc.import_run(paths, run_id)
        except svc.CatalogError as exc:
            print(_json.dumps(exc.as_payload()), file=_sys.stderr)
            raise typer.Exit(int(exc.exit_code)) from exc
        typer.echo(_json.dumps(result, ensure_ascii=False, indent=2))

    @catalog_app.command("search")
    def catalog_search(
        q: str = typer.Option(None, "--q", help="free-text search query"),
        item_type: str = typer.Option(None, "--item-type", help="filter: claim|inference|source|report|reusable_output|writeback"),
        project: str = typer.Option(None, "--project"),
        status: str = typer.Option(None, "--status"),
        sensitivity: str = typer.Option(None, "--sensitivity"),
        run_id: str = typer.Option(None, "--run-id"),
        sort: str = typer.Option("updated", "--sort", help="updated|title|confidence"),
        page: int = typer.Option(1, "--page"),
        page_size: int = typer.Option(25, "--page-size"),
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override foundry.yaml viewer.sensitivity_threshold (default: public)",
        ),
    ) -> None:
        """Search the catalog (over-threshold items are excluded, fail-closed)."""

        import json as _json

        from .paths import FoundryPaths
        from .services import catalog_service as svc

        paths = FoundryPaths.discover()
        result = svc.search(
            paths,
            q=q,
            item_type=item_type,
            project=project,
            status=status,
            sensitivity=sensitivity,
            run_id=run_id,
            sort=sort,
            page=page,
            page_size=page_size,
            sensitivity_threshold=sensitivity_threshold,
        )
        if json_out:
            typer.echo(_json.dumps(result, ensure_ascii=False, indent=2))
            return
        table = Table(title="rf catalog search")
        table.add_column("ID")
        table.add_column("Type")
        table.add_column("Title")
        table.add_column("Status")
        table.add_column("Sensitivity")
        for item in result["items"]:
            table.add_row(
                item["catalog_item_id"],
                item["item_type"],
                item["title"] or "",
                item["status"] or "",
                item["sensitivity"] or "",
            )
        console.print(table)
        console.print(
            f"[dim]{result['total']} total — page {result['page']} "
            f"(page_size={result['page_size']})[/dim]"
        )

    @catalog_app.command("show")
    def catalog_show(
        catalog_item_id: str = typer.Argument(..., help="catalog_item_id (ci_...)"),
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override foundry.yaml viewer.sensitivity_threshold (default: public)",
        ),
    ) -> None:
        """Show full detail (summary + payload + links) for a catalog item."""

        import json as _json

        from .paths import FoundryPaths
        from .services import catalog_service as svc

        paths = FoundryPaths.discover()
        item = svc.get_item(paths, catalog_item_id, sensitivity_threshold=sensitivity_threshold)
        if item is None:
            _fail(RFError(f"catalog item not found (or excluded by sensitivity threshold): "
                          f"{catalog_item_id}"))
        typer.echo(_json.dumps(item, ensure_ascii=False, indent=2))

    @catalog_app.command("stats")
    def catalog_stats(
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON output"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override foundry.yaml viewer.sensitivity_threshold (default: public)",
        ),
    ) -> None:
        """Show catalog aggregate counts (visible items only)."""

        import json as _json

        from .paths import FoundryPaths
        from .services import catalog_service as svc

        paths = FoundryPaths.discover()
        result = svc.stats(paths, sensitivity_threshold=sensitivity_threshold)
        if json_out:
            typer.echo(_json.dumps(result, ensure_ascii=False, indent=2))
            return
        table = Table(title="rf catalog stats")
        table.add_column("Item type")
        table.add_column("Count")
        for item_type, count in result["counts"].items():
            table.add_row(item_type, str(count))
        console.print(table)
        console.print(
            f"runs indexed: {result['runs_indexed']}  "
            f"last import: {result['last_import_at']}"
        )

    @catalog_app.command("rebuild")
    def catalog_rebuild() -> None:
        """Drop + recreate the catalog schema, then re-import every discovered run."""

        from .paths import FoundryPaths
        from .services import catalog_service as svc

        paths = FoundryPaths.discover()
        result = svc.rebuild(paths)
        console.print(f"[green]rebuilt[/green] {result['runs']} run(s), {result['items']} item(s)")
        for err in result["errors"]:
            err_console.print(f"[yellow]{err['run_id']}: {err['error']}[/yellow]")

    app.add_typer(catalog_app, name="catalog")

    # ----- workspace (public-multiuser-release Phase 5, WKSP-301) -----
    workspace_app = typer.Typer(help="Workspace isolation management.")

    @workspace_app.command("migrate-dry-run")
    def workspace_migrate_dry_run(
        json_out: bool = typer.Option(False, "--json/--no-json", help="Machine-parseable JSON output"),
    ) -> None:
        """Dry-run workspace isolation migration: report what would change (no writes).

        Counts on-disk ``draft.yaml`` files missing ``workspace_id``/``created_by``
        fields and the total ``catalog_items`` row count (all workspace-less pre-
        migration).  Performs **zero writes** to any file or database.

        Use ``--json`` for the machine-parseable ``DryRunReport`` payload.
        """
        import json as _json

        from .paths import FoundryPaths
        from .services.workspace_migration_service import dry_run as _dry_run

        paths = FoundryPaths.discover()
        report = _dry_run(paths)

        if json_out:
            typer.echo(
                _json.dumps(
                    {
                        "total_drafts": report.total_drafts,
                        "drafts_missing_workspace_id": report.drafts_missing_workspace_id,
                        "drafts_missing_created_by": report.drafts_missing_created_by,
                        "total_catalog_items": report.total_catalog_items,
                        "target_workspace_id": report.target_workspace_id,
                        "caller_impact_summary": report.caller_impact_summary,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        table = Table(title="rf workspace migrate-dry-run", show_header=True, header_style="bold")
        table.add_column("Field")
        table.add_column("Value")
        table.add_row("total_drafts", str(report.total_drafts))
        table.add_row(
            "drafts_missing_workspace_id",
            str(report.drafts_missing_workspace_id),
        )
        table.add_row(
            "drafts_missing_created_by",
            str(report.drafts_missing_created_by),
        )
        table.add_row("total_catalog_items", str(report.total_catalog_items))
        table.add_row("target_workspace_id", report.target_workspace_id)
        console.print(table)
        console.print(f"[dim]{report.caller_impact_summary}[/dim]")

    @workspace_app.command("migrate")
    def workspace_migrate(
        apply: bool = typer.Option(
            False, "--apply/--dry-run-only",
            help="Apply the forward backfill (stamp workspace_id on legacy records). "
                 "Without --apply, prints what would change without writing anything.",
        ),
        workspace_id_arg: str = typer.Option(
            "default",
            "--workspace-id",
            help="workspace_id to stamp on all pre-migration records (default: 'default').",
        ),
        json_out: bool = typer.Option(False, "--json/--no-json", help="Machine-parseable JSON output"),
    ) -> None:
        """Apply (or preview) the workspace isolation forward migration.

        Without ``--apply``: equivalent to ``migrate-dry-run`` — shows what
        would change without writing anything (zero writes).

        With ``--apply``: stamps ``workspace_id`` on every legacy record that
        lacks one, rebuilds the catalog with the new ``workspace_id`` column,
        and writes a rollback manifest to
        ``<workspace>/.rf_state/migrations/<run_id>-workspace-backfill.json``.

        Idempotent: if all records already have ``workspace_id`` set, reports
        "already migrated" and exits 0 without writing a new manifest.

        Use ``rf workspace rollback <migration_run_id>`` to reverse the operation
        if needed (see runbook at
        docs/dev/architecture/runbooks/workspace-migration-rollback.md).
        """
        import json as _json

        from .paths import FoundryPaths
        from .services.workspace_migration_service import (
            _catalog_has_workspace_id_column,
            backfill as _backfill,
            dry_run as _dry_run,
        )

        paths = FoundryPaths.discover()

        # Always run a dry-run first to assess the current state.
        preview = _dry_run(paths)

        if not apply:
            # Dry-run-only mode: display the preview without writing anything.
            if json_out:
                typer.echo(
                    _json.dumps(
                        {
                            "mode": "dry_run_only",
                            "total_drafts": preview.total_drafts,
                            "drafts_missing_workspace_id": preview.drafts_missing_workspace_id,
                            "drafts_missing_created_by": preview.drafts_missing_created_by,
                            "total_catalog_items": preview.total_catalog_items,
                            "target_workspace_id": preview.target_workspace_id,
                            "caller_impact_summary": preview.caller_impact_summary,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return
            table = Table(title="rf workspace migrate (dry-run)", show_header=True, header_style="bold")
            table.add_column("Field")
            table.add_column("Value")
            table.add_row("total_drafts", str(preview.total_drafts))
            table.add_row("drafts_missing_workspace_id", str(preview.drafts_missing_workspace_id))
            table.add_row("drafts_missing_created_by", str(preview.drafts_missing_created_by))
            table.add_row("total_catalog_items", str(preview.total_catalog_items))
            table.add_row("target_workspace_id", preview.target_workspace_id)
            console.print(table)
            console.print("[dim]Pass --apply to execute the migration.[/dim]")
            return

        # Idempotency gate: skip the backfill only when BOTH conditions hold:
        #   1. no draft records need workspace_id stamping, AND
        #   2. the catalog schema already has the workspace_id column (v3+).
        # If drafts are done but catalog is still pre-v3, fall through to
        # backfill() which will trigger the catalog schema rebuild.
        if preview.drafts_missing_workspace_id == 0 and _catalog_has_workspace_id_column(paths):
            already_msg = "workspace migration already applied -- all draft records have workspace_id set"
            if json_out:
                typer.echo(
                    _json.dumps(
                        {"status": "already_migrated", "message": already_msg},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                console.print(f"[green]{already_msg}[/green]")
            return

        # Apply the backfill.
        report = _backfill(paths, workspace_id_arg)

        if json_out:
            typer.echo(
                _json.dumps(
                    {
                        "status": "applied",
                        "migration_run_id": report.migration_run_id,
                        "target_workspace_id": report.target_workspace_id,
                        "total_attempted": report.total_attempted,
                        "total_succeeded": report.total_succeeded,
                        "total_failed": report.total_failed,
                        "catalog_rebuild_ok": report.catalog_rebuild_ok,
                        "catalog_rebuild_error": report.catalog_rebuild_error,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            if report.total_failed or not report.catalog_rebuild_ok:
                raise typer.Exit(1)
            return

        color = "green" if not report.total_failed and report.catalog_rebuild_ok else "yellow"
        console.print(
            f"[{color}]workspace migrate (applied)[/{color}]  "
            f"run={report.migration_run_id}"
        )
        console.print(f"  attempted:  {report.total_attempted}")
        console.print(f"  succeeded:  {report.total_succeeded}")
        if report.total_failed:
            err_console.print(f"  [red]failed:     {report.total_failed}[/red]")
        if not report.catalog_rebuild_ok:
            err_console.print(
                Panel(
                    f"catalog rebuild failed: {report.catalog_rebuild_error}",
                    title="[red]Catalog Rebuild Error[/red]",
                    border_style="red",
                )
            )
        console.print(
            f"  [dim]rollback: rf workspace rollback {report.migration_run_id}[/dim]"
        )
        if report.total_failed or not report.catalog_rebuild_ok:
            raise typer.Exit(1)

    @workspace_app.command("rollback")
    def workspace_rollback(
        migration_run_id: str = typer.Argument(
            ..., help="migration_run_id from the BackfillReport (printed by migrate-dry-run --json or backfill)"
        ),
        dry_run_flag: bool = typer.Option(
            False, "--dry-run/--execute",
            help="Print what would be reverted without writing anything."
        ),
        json_out: bool = typer.Option(False, "--json/--no-json", help="Machine-parseable JSON output"),
    ) -> None:
        """Reverse a prior workspace backfill run (rollback runbook).

        Reads the manifest written by ``rf workspace migrate-dry-run`` /
        ``backfill`` for ``MIGRATION_RUN_ID`` and restores each draft's
        ``workspace_id`` / ``created_by`` fields to their pre-migration values.

        For ``catalog_items``: there is no coded per-row reverter.  The rollback
        report's ``catalog_item_note`` explains the manual steps required
        (revert schema_version + ``rf catalog rebuild``).

        INVARIANT: never keys on ``workspace_id == "default"``; uses only the
        explicit record-id list from the stored manifest.

        See docs/dev/architecture/runbooks/workspace-migration-rollback.md for
        the full step-by-step runbook.
        """
        import json as _json

        from .paths import FoundryPaths
        from .services.workspace_migration_service import rollback as _rollback

        paths = FoundryPaths.discover()
        try:
            report = _rollback(paths, migration_run_id, dry_run=dry_run_flag)
        except FileNotFoundError as exc:
            err_console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(1) from exc

        if json_out:
            typer.echo(
                _json.dumps(
                    {
                        "migration_run_id": report.migration_run_id,
                        "total_attempted": report.total_attempted,
                        "total_reverted_drafts": report.total_reverted_drafts,
                        "total_failed": report.total_failed,
                        "catalog_item_note": report.catalog_item_note,
                        "is_dry_run": report.is_dry_run,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            if report.total_failed:
                raise typer.Exit(1)
            return

        mode_label = "dry-run" if report.is_dry_run else "applied"
        color = "green" if not report.total_failed else "yellow"
        console.print(
            f"[{color}]workspace rollback ({mode_label})[/{color}] "
            f"run={migration_run_id}"
        )
        console.print(f"  attempted:       {report.total_attempted}")
        console.print(f"  reverted drafts: {report.total_reverted_drafts}")
        if report.total_failed:
            err_console.print(f"  [red]failed:          {report.total_failed}[/red]")
        console.print(f"  [dim]{report.catalog_item_note}[/dim]")
        if report.total_failed:
            raise typer.Exit(1)

    app.add_typer(workspace_app, name="workspace")

    # ----- report (P2 Wave B: read-only report surface) -----
    report_app = typer.Typer(help="Report surface — read anchors, verify, (P3: draft).")

    @report_app.command("anchors")
    def report_anchors(
        run_id: str = typer.Argument(..., help="run id"),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output (default: rich table)"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override foundry.yaml viewer.sensitivity_threshold (default: public)",
        ),
    ) -> None:
        """Print the report anchors (block/paragraph locations + claim links) for a run.

        404-equivalent error when the run is unknown or excluded by the resolved
        sensitivity threshold (same behavior as the API endpoint — no existence
        leak).  Pass ``--sensitivity-threshold`` to override the workspace default.
        """

        import json as _json

        from .paths import FoundryPaths
        from .services.export_service import (
            SENSITIVITY_ORDER,
            ExportError,
            export_run,
            resolve_threshold,
        )

        paths = FoundryPaths.discover()

        try:
            threshold = resolve_threshold(paths, sensitivity_threshold)
        except ExportError as exc:
            _fail(exc)

        threshold_rank = SENSITIVITY_ORDER[threshold]

        # Pass the already-resolved threshold through so export-time claim
        # filtering (and thus the derived anchors) honors the same override
        # used for the existence gate below, instead of export_run falling
        # back to its own default re-resolve.
        try:
            data = export_run(paths, run_id, sensitivity_threshold=threshold)
        except ExportError as exc:
            _fail(RFError(f"run not found: {run_id}"))

        # No-existence-leak gate (landmine #4/#5).
        run_sensitivity = data.get("sensitivity") or "public"
        run_rank = SENSITIVITY_ORDER.get(str(run_sensitivity), len(SENSITIVITY_ORDER))
        if run_rank > threshold_rank:
            _fail(RFError(f"run not found: {run_id}"))

        anchors = data.get("report_anchors")

        if json_out:
            typer.echo(_json.dumps({"run_id": run_id, "report_anchors": anchors}, ensure_ascii=False, indent=2))
            return

        if anchors is None:
            console.print(f"[yellow]no report anchors for run {run_id} (no report draft)[/yellow]")
            return

        if not anchors:
            console.print(f"[yellow]report has no anchored paragraphs[/yellow]")
            return

        table = Table(title=f"report anchors: {run_id}", show_header=True, header_style="bold")
        table.add_column("block_id")
        table.add_column("section_id")
        table.add_column("ordinal")
        table.add_column("text_hash")
        table.add_column("claim_links")
        for block in anchors:
            claim_parts = []
            for cl in block.get("claim_links") or []:
                status = cl.get("link_status", "?")
                cid = cl.get("claim_id", "?")
                color = {"linked": "green", "stale": "yellow", "missing_claim": "red"}.get(status, "")
                if color:
                    claim_parts.append(f"[{color}]{cid}[/{color}]")
                else:
                    claim_parts.append(cid)
            table.add_row(
                str(block.get("block_id") or ""),
                str(block.get("section_id") or "(root)"),
                str(block.get("paragraph_ordinal", "")),
                str(block.get("text_hash") or ""),
                ", ".join(claim_parts) if claim_parts else "-",
            )
        console.print(table)

    # ----- report draft (P3 Wave E: builder draft CRUD + verify + publish-preview) -----
    draft_app = typer.Typer(help="Report Builder draft management (P3 Wave E).")

    @draft_app.command("create")
    def draft_create(
        title: str = typer.Argument("Untitled Draft", help="Draft title"),
        origin: str = typer.Option("blank", "--origin", help="blank|template|run|collection"),
        source_run_id: str = typer.Option(None, "--from-run", help="Seed from run id (origin=run)"),
        catalog_item_ids: list[str] = typer.Option(None, "--catalog-item", help="Catalog item id(s) (origin=collection; repeatable)"),
        audience: str = typer.Option("self", "--audience", help="self|technical|executive|public|client"),
        sensitivity: str = typer.Option("public", "--sensitivity", help="public|personal|work_sensitive|client_sensitive"),
        sensitivity_threshold: str = typer.Option(None, "--sensitivity-threshold", help="Override threshold for from-run/from-collection seeding"),
        created_by: str = typer.Option(None, "--created-by", help="Creator identity (optional, unenforced)"),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
    ) -> None:
        """Create a new report draft (blank, from a run, or from catalog items)."""

        import json as _json

        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            if origin == "run":
                if not source_run_id:
                    _fail(RFError("--from-run is required when origin=run"))
                draft = bsvc.create_draft_from_run(
                    paths,
                    run_id=source_run_id,
                    title=title if title != "Untitled Draft" else None,
                    audience=audience,
                    sensitivity=sensitivity if sensitivity != "public" else None,
                    created_by=created_by,
                    sensitivity_threshold=sensitivity_threshold or "client_sensitive",
                )
            elif origin == "collection":
                ids_ = list(catalog_item_ids) if catalog_item_ids else []
                if not ids_:
                    _fail(RFError("--catalog-item is required when origin=collection"))
                draft = bsvc.create_draft_from_collection(
                    paths,
                    catalog_item_ids=ids_,
                    title=title,
                    audience=audience,
                    sensitivity=sensitivity,
                    created_by=created_by,
                    sensitivity_threshold=sensitivity_threshold or "client_sensitive",
                )
            else:
                draft = bsvc.create_draft(
                    paths,
                    title=title,
                    origin=origin,
                    audience=audience,
                    sensitivity=sensitivity,
                    created_by=created_by,
                )
        except bsvc.BuilderError as exc:
            _fail(exc)

        if json_out:
            typer.echo(_json.dumps(draft, ensure_ascii=False, indent=2))
            return
        console.print(f"[green]created[/green] {draft['report_draft_id']}  ({draft['title']})")

    @draft_app.command("list")
    def draft_list(
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
    ) -> None:
        """List all on-disk report drafts."""

        import json as _json

        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        drafts = bsvc.list_drafts(paths)
        if json_out:
            typer.echo(_json.dumps(drafts, ensure_ascii=False, indent=2))
            return
        if not drafts:
            console.print("[yellow]no drafts found[/yellow]")
            return
        table = Table(title="report drafts", show_header=True, header_style="bold")
        table.add_column("id")
        table.add_column("title")
        table.add_column("status")
        table.add_column("sensitivity")
        table.add_column("blocks")
        table.add_column("updated_at")
        for d in drafts:
            table.add_row(
                d.get("report_draft_id", ""),
                d.get("title", ""),
                d.get("status", ""),
                d.get("sensitivity", ""),
                str(d.get("block_count", 0)),
                str(d.get("updated_at", "")),
            )
        console.print(table)

    @draft_app.command("show")
    def draft_show(
        report_id: str = typer.Argument(..., help="Draft id (rpt_...)"),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
    ) -> None:
        """Show full draft state."""

        import json as _json

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            draft = bsvc.load_draft(paths, report_id)
        except NotFoundError as exc:
            _fail(exc)

        if json_out:
            typer.echo(_json.dumps(draft, ensure_ascii=False, indent=2))
            return
        console.print(f"[bold]{draft['report_draft_id']}[/bold]  {draft['title']}")
        console.print(f"  status={draft.get('status')}  sensitivity={draft.get('sensitivity')}  blocks={len(draft.get('blocks', []))}")

    @draft_app.command("add-block")
    def draft_add_block(
        report_id: str = typer.Argument(..., help="Draft id"),
        markdown: str = typer.Option("", "--markdown", "-m", help="Block markdown text"),
        block_type: str = typer.Option("paragraph", "--type", help="heading|paragraph|table|quote|callout|evidence_summary"),
        materiality: str = typer.Option("material", "--materiality", help="material|narrative|background"),
        json_out: bool = typer.Option(False, "--json/--no-json"),
    ) -> None:
        """Append a block to a draft."""

        import json as _json

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            draft = bsvc.add_block(paths, report_id, block_type=block_type, markdown=markdown, materiality=materiality)
        except (NotFoundError, bsvc.BuilderError) as exc:
            _fail(exc)

        if json_out:
            typer.echo(_json.dumps(draft, ensure_ascii=False, indent=2))
            return
        blk = draft["blocks"][-1]
        console.print(f"[green]added block[/green] {blk['block_id']}  (type={blk['block_type']})")

    @draft_app.command("update-block")
    def draft_update_block(
        report_id: str = typer.Argument(..., help="Draft id"),
        block_id: str = typer.Argument(..., help="Block id"),
        markdown: str = typer.Option(None, "--markdown", "-m"),
        block_type: str = typer.Option(None, "--type"),
        materiality: str = typer.Option(None, "--materiality"),
        json_out: bool = typer.Option(False, "--json/--no-json"),
    ) -> None:
        """Update markdown/type/materiality on a block."""

        import json as _json

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            draft = bsvc.update_block(paths, report_id, block_id, markdown=markdown, block_type=block_type, materiality=materiality)
        except (NotFoundError, bsvc.BuilderError) as exc:
            _fail(exc)

        if json_out:
            typer.echo(_json.dumps(draft, ensure_ascii=False, indent=2))
        else:
            console.print(f"[green]updated block[/green] {block_id}")

    @draft_app.command("delete-block")
    def draft_delete_block(
        report_id: str = typer.Argument(..., help="Draft id"),
        block_id: str = typer.Argument(..., help="Block id"),
    ) -> None:
        """Delete a block and its associated links from a draft."""

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            bsvc.delete_block(paths, report_id, block_id)
        except NotFoundError as exc:
            _fail(exc)
        console.print(f"[green]deleted block[/green] {block_id}")

    @draft_app.command("reorder")
    def draft_reorder(
        report_id: str = typer.Argument(..., help="Draft id"),
        block_ids: list[str] = typer.Argument(..., help="Block ids in desired order"),
    ) -> None:
        """Reorder blocks by specifying all block ids in the desired order."""

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            bsvc.reorder_blocks(paths, report_id, list(block_ids))
        except (NotFoundError, bsvc.BuilderError) as exc:
            _fail(exc)
        console.print(f"[green]reordered[/green] {len(block_ids)} blocks")

    # claim-link sub-sub-app
    claim_link_app = typer.Typer(help="Manage claim links on a draft.")

    @claim_link_app.command("add")
    def draft_claim_link_add(
        report_id: str = typer.Argument(..., help="Draft id"),
        block_id: str = typer.Option(..., "--block", "-b", help="Block id to link to"),
        claim_id: str = typer.Option(..., "--claim", "-c", help="Claim id (clm_...)"),
        relation: str = typer.Option(None, "--relation", help="supports|contradicts|context|inferred_from|cited_nearby"),
        source_run_id: str = typer.Option(None, "--run", help="Source run id for claim resolution"),
        catalog_item_id: str = typer.Option(None, "--catalog-item", help="Catalog item id"),
        no_tag: bool = typer.Option(False, "--no-tag", help="Do not insert [claim:] tag into block markdown"),
        json_out: bool = typer.Option(False, "--json/--no-json"),
    ) -> None:
        """Add a claim link to a draft block."""

        import json as _json

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            draft = bsvc.add_claim_link(
                paths,
                report_id,
                block_id=block_id,
                claim_id=claim_id,
                relation=relation,
                source_run_id=source_run_id,
                catalog_item_id=catalog_item_id,
                insert_tag=not no_tag,
            )
        except (NotFoundError, bsvc.BuilderError) as exc:
            _fail(exc)
        if json_out:
            typer.echo(_json.dumps(draft, ensure_ascii=False, indent=2))
        else:
            console.print(f"[green]linked[/green] claim {claim_id} to block {block_id}")

    @claim_link_app.command("remove")
    def draft_claim_link_remove(
        report_id: str = typer.Argument(..., help="Draft id"),
        claim_link_id: str = typer.Argument(..., help="Claim link id (rl_...)"),
    ) -> None:
        """Remove a claim link from a draft."""

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            bsvc.remove_claim_link(paths, report_id, claim_link_id)
        except NotFoundError as exc:
            _fail(exc)
        console.print(f"[green]removed claim link[/green] {claim_link_id}")

    draft_app.add_typer(claim_link_app, name="claim-link")

    @draft_app.command("verify")
    def draft_verify(
        report_id: str = typer.Argument(..., help="Draft id"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override sensitivity threshold for body-sensitivity check",
        ),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
    ) -> None:
        """Run D13 verification checks against a draft.

        Exit 0 = pass, non-zero = fail. Use --json for machine-readable output.
        """

        import json as _json

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services.verification import verify_draft as _verify_draft

        paths = FoundryPaths.discover()
        try:
            result = _verify_draft(paths, report_id, sensitivity_threshold=sensitivity_threshold)
        except NotFoundError as exc:
            _fail(exc)

        if json_out:
            typer.echo(_json.dumps({
                "report_draft_id": report_id,
                "passed": result.passed,
                "exit_code": result.exit_code,
                "checks": [
                    {"id": c.id, "severity": c.severity, "status": c.status,
                     "detail": c.detail, "locations": c.locations}
                    for c in result.checks
                ],
            }, ensure_ascii=False, indent=2))
            raise typer.Exit(0 if result.passed else result.exit_code)

        color = "green" if result.passed else "red"
        console.print(f"[{color}]{'PASSED' if result.passed else 'FAILED'}[/{color}] ({report_id})")
        for check in result.checks:
            status_color = "green" if check.status == "pass" else ("yellow" if check.status in ("warn", "skip") else "red")
            console.print(f"  [{status_color}]{check.status}[/{status_color}] {check.id}: {check.detail}")
        raise typer.Exit(0 if result.passed else result.exit_code)

    @draft_app.command("publish-preview")
    def draft_publish_preview(
        report_id: str = typer.Argument(..., help="Draft id"),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override sensitivity threshold (default: draft's own sensitivity)",
        ),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output"),
    ) -> None:
        """Run D13 checks FAIL-CLOSED; print Markdown preview on pass.

        Exit 0 = ready to publish (preview printed). Non-zero = blocked.
        Raw sensitive quotes in the body ALWAYS block (spec §11).
        """

        import json as _json

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc
        from .services.verification import verify_draft as _verify_draft

        paths = FoundryPaths.discover()
        try:
            result = _verify_draft(paths, report_id, sensitivity_threshold=sensitivity_threshold)
        except NotFoundError as exc:
            _fail(exc)

        check_dicts = [
            {"id": c.id, "severity": c.severity, "status": c.status,
             "detail": c.detail, "locations": c.locations}
            for c in result.checks
        ]
        blocking = [c for c in check_dicts if c["severity"] == "error" and c["status"] == "fail"]

        if blocking:
            if json_out:
                typer.echo(_json.dumps({"ok": False, "blocking": blocking, "checks": check_dicts}, ensure_ascii=False, indent=2))
            else:
                err_console.print(f"[red]BLOCKED[/red] publish-preview failed for {report_id}")
                for c in blocking:
                    err_console.print(f"  [red]{c['id']}[/red]: {c['detail']}")
            raise typer.Exit(result.exit_code)

        try:
            preview_md = bsvc.export_markdown(paths, report_id)
        except NotFoundError as exc:  # pragma: no cover
            _fail(exc)

        if json_out:
            typer.echo(_json.dumps({"ok": True, "preview_markdown": preview_md, "checks": check_dicts}, ensure_ascii=False, indent=2))
        else:
            console.print(f"[green]PASS[/green] publish-preview ({report_id})")
            console.print(preview_md)

    @draft_app.command("export")
    def draft_export(
        report_id: str = typer.Argument(..., help="Draft id"),
        output: str = typer.Option(None, "--output", "-o", help="Write to file instead of stdout"),
    ) -> None:
        """Export a draft as Markdown with YAML frontmatter."""

        from .errors import NotFoundError
        from .paths import FoundryPaths
        from .services import builder_service as bsvc

        paths = FoundryPaths.discover()
        try:
            md = bsvc.export_markdown(paths, report_id)
        except NotFoundError as exc:
            _fail(exc)

        if output:
            from pathlib import Path
            Path(output).write_text(md, encoding="utf-8")
            console.print(f"[green]exported[/green] {report_id} -> {output}")
        else:
            typer.echo(md)

    report_app.add_typer(draft_app, name="draft")

    app.add_typer(report_app, name="report")

    # ----- agent-job (FR-20) -----
    from .cli.commands.agent_job import agent_job_app

    app.add_typer(agent_job_app, name="agent-job")

    # ----- audit (public-multiuser-release Phase 5 — AUDIT-003/AUDIT-004) -----
    audit_app = typer.Typer(help="Audit log commands.")

    @audit_app.command("list")
    def audit_list(
        mutation_type: str | None = typer.Option(None, "--mutation-type", help="Filter by mutation type"),
        actor: str | None = typer.Option(None, "--actor", help="Filter by actor user id"),
        workspace: str | None = typer.Option(None, "--workspace", help="Filter by workspace id"),
        since: str | None = typer.Option(None, "--since", help="ISO-8601 lower bound (inclusive)"),
        until: str | None = typer.Option(None, "--until", help="ISO-8601 upper bound (inclusive)"),
        limit: int = typer.Option(50, "--limit", help="Page size (1–200)"),
        cursor: str | None = typer.Option(None, "--cursor", help="Pagination cursor from prior page"),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output (default: rich table)"),
    ) -> None:
        """List audit events (most-recent-first, cursor-paginated)."""

        import json as _json

        from .paths import FoundryPaths
        from .services import audit_service as svc

        paths = FoundryPaths.discover()
        result = svc.list_events(
            paths,
            mutation_type=mutation_type,
            actor_user_id=actor,
            workspace_id=workspace,
            since=since,
            until=until,
            limit=limit,
            cursor=cursor,
        )
        if json_out:
            typer.echo(_json.dumps(result, ensure_ascii=False, indent=2))
            return
        table = Table(title="rf audit list")
        table.add_column("audit_event_id", no_wrap=True)
        table.add_column("created_at", no_wrap=True)
        table.add_column("mutation_type")
        table.add_column("action")
        table.add_column("actor")
        table.add_column("result")
        for item in result["items"]:
            table.add_row(
                item.get("audit_event_id") or "",
                item.get("created_at") or "",
                item.get("mutation_type") or "",
                item.get("action") or "",
                item.get("actor_user_id") or "",
                item.get("result") or "",
            )
        console.print(table)
        if result.get("next_cursor"):
            console.print(f"[dim]next_cursor: {result['next_cursor']}[/dim]")

    @audit_app.command("show")
    def audit_show(
        audit_event_id: str = typer.Argument(..., help="audit_event_id (UUID)"),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output (default: rich key-value)"),
    ) -> None:
        """Show full detail for a single audit event."""

        import json as _json

        from .paths import FoundryPaths
        from .services import audit_service as svc

        paths = FoundryPaths.discover()
        event = svc.get_event(paths, audit_event_id)
        if event is None:
            err_console.print(f"[red]audit event not found: {audit_event_id}[/red]")
            raise typer.Exit(int(ExitCode.USAGE))
        if json_out:
            typer.echo(_json.dumps(event, ensure_ascii=False, indent=2))
            return
        # Rich key-value table — show all non-null fields.
        table = Table(title=f"rf audit show {audit_event_id}", show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        for key, val in event.items():
            if val is None:
                continue
            display_val = _json.dumps(val, ensure_ascii=False) if isinstance(val, dict) else str(val)
            table.add_row(key, display_val)
        console.print(table)

    @audit_app.command("health")
    def audit_health_cmd(
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output (default: rich display)"),
        probe: bool = typer.Option(False, "--probe", help="Run a live write-then-read probe (default: read cached state)"),
    ) -> None:
        """Show the health state of the audit store.

        By default reads the last persisted probe result.  Pass ``--probe``
        to run a live write-then-read round-trip and update the persisted state.

        Exit 0 when healthy, exit 1 when degraded.
        """

        import json as _json

        from .paths import FoundryPaths
        from .services import audit_service as svc

        paths = FoundryPaths.discover()
        if probe:
            state = svc.health_check(paths)
        else:
            state = svc.get_health_state(paths)

        if json_out:
            typer.echo(_json.dumps({
                "healthy": state.healthy,
                "last_probe_at": state.last_probe_at,
                "last_success_at": state.last_success_at,
                "error_detail": state.error_detail,
            }, indent=2))
            if not state.healthy:
                raise typer.Exit(1)
            return

        if state.healthy:
            console.print("[green]HEALTHY[/green]", state.last_probe_at or "never probed")
        else:
            console.print(Panel(
                f"[red]DEGRADED[/red]\n{state.error_detail or 'unknown error'}\nLast success: {state.last_success_at or 'never'}",
                title="[red]Audit Store Degraded[/red]",
                border_style="red",
            ))
            raise typer.Exit(1)

    app.add_typer(audit_app, name="audit")

    # ----- assertion (reusable assertion ledger — Phase 2 backfill) -----
    assertion_app = typer.Typer(help="Reusable assertion ledger — backfill and readiness operations.")

    @assertion_app.command("backfill")
    def assertion_backfill(
        dry_run: bool = typer.Option(
            False,
            "--dry-run",
            help="Preview only: report candidate claim ledgers without writing anything.",
        ),
        run: list[str] = typer.Option(
            None,
            "--run",
            help="Backfill only this run id (repeatable). Default: every run with a claim ledger.",
        ),
        workspace_id: str = typer.Option(
            "default",
            "--workspace-id",
            help="assertion_registry_workspace_id to write under "
            "(single-operator convention: 'default' — see assertion_workspace.py).",
        ),
        json_out: bool = typer.Option(False, "--json/--no-json", help="JSON output (default: rich table)"),
    ) -> None:
        """Historical claim-to-assertion backfill (Phase 2).

        Explicit, operator-gated: this command is never invoked automatically
        on startup or on any request path. Requires
        ``foundry.assertion_ledger.ledger_write_enabled: true``; otherwise it
        reports the write-disabled reason and performs zero writes.

        Without ``--dry-run``, resolves the workspace via P1's fail-closed
        gate before any write and reports the actually measured per-run and
        aggregate materialized/abstained counts — never an assumed yield.
        """

        import json as _json

        from .paths import FoundryPaths
        from .services import assertion_rollout as rollout

        paths = FoundryPaths.discover()

        if dry_run:
            receipt = rollout.backfill_dry_run(paths=paths)
        else:
            receipt = rollout.backfill_corpus(
                assertion_registry_workspace_id=workspace_id,
                paths=paths,
                run_ids=list(run) if run else None,
            )

        if json_out:
            typer.echo(_json.dumps(receipt, ensure_ascii=False, indent=2))
        else:
            table = Table(
                title="rf assertion backfill" + (" (--dry-run)" if dry_run else ""),
                show_header=False,
            )
            table.add_column("Field", style="bold")
            table.add_column("Value")
            for key, value in receipt.items():
                if key == "runs":
                    table.add_row("runs", str(len(value)))
                    continue
                display = _json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                table.add_row(key, display)
            console.print(table)

        if not dry_run and receipt.get("allowed") is False:
            raise typer.Exit(1)

    app.add_typer(assertion_app, name="assertion")

    # ----- serve (loopback API) -----
    @app.command()
    def serve(
        port: int = typer.Option(
            7432,
            "--port",
            help="TCP port to bind (default 7432; avoids MeatyWiki API at 8765)",
        ),
        bind_host: str = typer.Option("127.0.0.1", "--bind-host", help="Host address to bind"),
        auth_mode: str = typer.Option(
            None,
            "--auth-mode",
            help="Authentication mode: none | token (default: from foundry.yaml viewer.auth_mode)",
        ),
        sensitivity_threshold: str = typer.Option(
            None,
            "--sensitivity-threshold",
            help="Override foundry.yaml viewer.sensitivity_threshold (default: public)",
        ),
    ) -> None:
        """Start the Research Foundry loopback HTTP API (spec §loopback-api-v1).

        Requires the ``serve`` extra::

            pip install 'research-foundry[serve]'

        The server binds to ``bind_host:port`` and exposes a read-only JSON API
        consumed by the runs viewer.

        LAN exposure (``--bind-host 0.0.0.0``) requires ``--auth-mode token``
        AND the token env var (named by ``viewer.auth_token_env``, default
        ``RF_SERVE_TOKEN``) to be non-empty.  Both checks fail closed before
        any port is opened.

        Example::

            rf serve --port 7432 --bind-host 127.0.0.1
            rf serve --bind-host 0.0.0.0 --auth-mode token  # RF_SERVE_TOKEN must be set
        """
        import os as _os

        # --- lazy import guard -----------------------------------------------
        try:
            import uvicorn

            from .api.app import create_app
        except ImportError as exc:
            err_console.print(
                "[red]serve requires fastapi and uvicorn.[/red] "
                "Install with: pip install 'research-foundry[serve]'"
            )
            raise typer.Exit(1) from exc

        from .config import FoundryConfig

        config = FoundryConfig.load()

        # Resolve effective auth_mode: CLI flag takes precedence over config.
        effective_auth_mode = auth_mode if auth_mode is not None else config.viewer_auth_mode()
        if effective_auth_mode not in ("none", "token"):
            err_console.print(
                f"[red]unknown auth-mode {effective_auth_mode!r}; use 'none' or 'token'[/red]"
            )
            raise typer.Exit(1)

        # Resolve effective bind_host: CLI flag takes precedence over config.
        effective_bind_host = bind_host  # CLI always provides a default

        # --- Step 1: Apply ALL CLI overrides to config BEFORE the gate runs -----
        # Architectural invariant: the gate and create_app must read the SAME
        # already-overridden config object. Applying overrides AFTER the gate
        # created a P1 bypass: the gate saw viewer.auth_mode=token (from YAML),
        # passed, then create_app saw auth_mode=none (from the CLI override
        # applied afterwards) and installed no middleware — server bound to LAN
        # with no auth protection.
        #
        # Scope of --auth-mode CLI flag: mutates viewer["auth_mode"] (the legacy
        # viewer.auth_mode path ONLY). The new auth.provider block (foundry.yaml
        # `auth:` section) is intentionally NOT overrideable via --auth-mode.
        # Use foundry.yaml to change auth.provider. This is the safer choice:
        # a stray --auth-mode none on a deployment using auth.provider=local_static
        # must NOT silently disable provider-level auth.
        if auth_mode is not None:
            config.viewer["auth_mode"] = effective_auth_mode
        if sensitivity_threshold is not None:
            config.viewer["sensitivity_threshold"] = sensitivity_threshold

        # --- Step 2: Fail-closed pre-bind validation (security invariants 1 & 2)
        # Both checks happen AFTER all CLI overrides are applied and BEFORE any
        # call to create_app or uvicorn.run so that no port is opened when the
        # configuration is unsafe. Single source of truth: gate and create_app
        # both read the same already-mutated config instance. Accepts EITHER the
        # new auth.provider=local_static path (P5) OR the legacy
        # viewer.auth_mode=token path — see _validate_nonloopback_bind.
        _LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
        is_loopback = effective_bind_host in _LOOPBACK_HOSTS

        if not is_loopback:
            try:
                _validate_nonloopback_bind(
                    config, effective_bind_host, effective_auth_mode, _os.environ
                )
            except ValueError as _gate_err:
                err_console.print(f"[red]error:[/red] {_gate_err}")
                raise typer.Exit(1) from _gate_err

        fastapi_app = create_app(config)

        console.print(f"[green]rf serve[/green] listening on {effective_bind_host}:{port}")
        console.print(
            f"  auth_mode={effective_auth_mode}  "
            f"sensitivity_threshold={sensitivity_threshold or 'public (default)'}"
        )

        uvicorn.run(fastapi_app, host=effective_bind_host, port=port)


def _apply_notebook_options(
    run_id: str,
    *,
    project: str | None,
    mode: str | None,
) -> None:
    """Best-effort NLM correlation update from CLI options.

    Called after a run is created (``plan`` or ``swarm run``) to apply
    ``--notebook-mode`` / ``--notebook-id`` / ``--project`` overrides to the
    correlation registry.  All errors are swallowed — the pipeline must never
    fail due to an NLM issue.
    """
    try:
        from .services.notebook_correlation import resolve_notebook

        resolve_notebook(run_id, project=project, mode=mode)
    except Exception:  # noqa: BLE001 — fail-soft; never block the caller
        pass


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
