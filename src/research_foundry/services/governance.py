"""Governance guard service (spec §7.1/§7.2) — ``rf guard``.

Deterministic, network-free enforcement of the non-negotiable policy rules.
Loads ``config/governance.yaml`` (key_profiles + policy_rules + secret_patterns)
via :class:`FoundryConfig` and falls back to built-ins when the config is absent.

The guard never prints — it returns a frozen :class:`GuardResult` carrying the
exit code so the CLI/hooks render and exit. Exit codes follow the contract:
``0`` ok, ``3`` block, ``7`` require_approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import FoundryConfig
from ..errors import ExitCode
from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import append_jsonl

# --- Sensitivity classes ---------------------------------------------------

_PERSONAL_SENSITIVITIES = {"public", "personal"}
_WORK_SENSITIVITIES = {"work_sensitive", "client_sensitive"}

# --- Built-in fallbacks (mirror config/governance.yaml) --------------------

_BUILTIN_SECRET_PATTERNS: tuple[str, ...] = (
    r"sk-[A-Za-z0-9]{20,}",
    r"sk-ant-[A-Za-z0-9_\-]{20,}",
    r"ghp_[A-Za-z0-9]{36,}",
    r"gho_[A-Za-z0-9]{36,}",
    r"github_pat_[A-Za-z0-9_]{22,}",
    r"AKIA[0-9A-Z]{16}",
    r"ASIA[0-9A-Z]{16}",
    r"AIza[0-9A-Za-z\-_]{35}",
    r"xox[baprse]-[0-9A-Za-z\-]{10,}",
    r"xapp-[0-9]-[A-Za-z0-9\-]{10,}",
    r"glpat-[0-9A-Za-z\-_]{20,}",
    r"(?:sk|rk)_live_[0-9A-Za-z]{20,}",
    r"SG\.[A-Za-z0-9_\-]{22,}\.[A-Za-z0-9_\-]{43,}",
    r"SK[0-9a-fA-F]{32}",
    r"AC[0-9a-fA-F]{32}",
    r"(?i)aws_secret[_a-z]*\s*[:=]\s*['\"]?[A-Za-z0-9/+]{40}",
    r"(?i)bearer\s+[A-Za-z0-9_\-\.=]{16,}",
    r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|client[_-]?secret)"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?\S{8,}",
    r"-----BEGIN[ A-Z]*PRIVATE KEY-----",
    r"-----BEGIN OPENSSH PRIVATE KEY-----",
    r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
)

# Severity → contributing exit code (worst severity wins).
_BLOCK = "block"
_REQUIRE_APPROVAL = "require_approval"
_WARN = "warn"


# --- Result dataclasses ----------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """A single fired policy rule."""

    rule_id: str
    severity: str  # block|require_approval|warn
    message: str
    detail: str = ""


@dataclass(frozen=True)
class GuardResult:
    """Aggregate outcome of a governance check."""

    passed: bool
    exit_code: int  # 0 ok, 3 block, 7 require_approval
    violations: list[Violation] = field(default_factory=list)


@dataclass(frozen=True)
class GuardContext:
    """Inputs to :func:`guard_check` (all optional; deterministic)."""

    profile: str = "personal"  # runtime key profile
    run_id: str | None = None
    sensitivity: str | None = None  # run/bundle sensitivity
    source_sensitivities: tuple[str, ...] = ()  # sensitivities of involved source cards
    model_provider: str | None = None
    writeback_targets: tuple[str, ...] = ()
    intent_key_profile_allowed: str | None = None
    artifact_paths: tuple[Path, ...] = ()  # files to secret-scan
    unmapped_material_claims: int = 0  # >0 -> material_claims_must_be_mapped fires
    unsupported_claims: int = 0


# --- Config loading helpers ------------------------------------------------


def _config_for(config: FoundryConfig | None, paths: FoundryPaths | None) -> FoundryConfig:
    if config is not None:
        return config
    return FoundryConfig(paths=paths or FoundryPaths.discover())


def _secret_patterns(config: FoundryConfig) -> list[str]:
    gov = config.governance or {}
    pats = gov.get("secret_patterns") if isinstance(gov, dict) else None
    if isinstance(pats, list) and pats:
        return [p for p in pats if isinstance(p, str)]
    return list(_BUILTIN_SECRET_PATTERNS)


def _approved_providers(config: FoundryConfig) -> set[str]:
    gov = config.governance or {}
    provs = gov.get("approved_work_providers") if isinstance(gov, dict) else None
    if isinstance(provs, list):
        return {str(p) for p in provs}
    return set()


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue
    return compiled


# --- Secret scanning -------------------------------------------------------


def scan_secrets(text: str, *, config: FoundryConfig | None = None) -> list[str]:
    """Return the list of secret-pattern matches found in ``text`` (may be empty)."""

    if not text:
        return []
    cfg = config if config is not None else FoundryConfig(paths=FoundryPaths.discover())
    matches: list[str] = []
    for rx in _compile(_secret_patterns(cfg)):
        for m in rx.finditer(text):
            matches.append(m.group(0))
    return matches


def scan_paths(
    paths_to_scan: list[Path], *, config: FoundryConfig | None = None
) -> list[Violation]:
    """Secret-scan each readable file; one ``block`` Violation per hit file."""

    cfg = config if config is not None else FoundryConfig(paths=FoundryPaths.discover())
    violations: list[Violation] = []
    for p in paths_to_scan or []:
        path = Path(p)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = scan_secrets(text, config=cfg)
        if hits:
            violations.append(
                Violation(
                    rule_id="no_secret_in_markdown",
                    severity=_BLOCK,
                    message="Potential secret detected in Markdown/YAML artifact.",
                    detail=f"{path}: {len(hits)} match(es) (e.g. {_redact(hits[0])})",
                )
            )
    return violations


def _redact(secret: str) -> str:
    """Shorten a matched secret so it is never echoed in full."""

    s = secret.strip()
    if len(s) <= 8:
        return s[:2] + "***"
    return f"{s[:4]}…{s[-2:]}"


# --- Rule evaluation -------------------------------------------------------


def _rule_message(config: FoundryConfig, rule_id: str, default: str) -> str:
    for rule in config.policy_rules():
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return str(rule.get("message") or default)
    return default


def guard_check(
    ctx: GuardContext, *, paths: FoundryPaths | None = None
) -> GuardResult:
    """Evaluate the §7.2 policy rules against ``ctx`` and return a GuardResult."""

    paths = paths or FoundryPaths.discover()
    cfg = _config_for(None, paths)
    violations: list[Violation] = []

    sources = list(ctx.source_sensitivities or ())
    targets = list(ctx.writeback_targets or ())

    # 1. no_work_keys_for_personal_runs (block)
    if ctx.intent_key_profile_allowed == "personal" and ctx.profile == "work_approved":
        violations.append(
            Violation(
                rule_id="no_work_keys_for_personal_runs",
                severity=_BLOCK,
                message=_rule_message(
                    cfg,
                    "no_work_keys_for_personal_runs",
                    "Work-provided keys cannot be used for personal research.",
                ),
                detail=(
                    "intent.governance.key_profile_allowed=personal "
                    "but runtime.key_profile=work_approved"
                ),
            )
        )

    # 2. no_work_sensitive_to_unapproved_provider (block)
    if ctx.sensitivity in _WORK_SENSITIVITIES and ctx.model_provider:
        if ctx.model_provider not in _approved_providers(cfg):
            violations.append(
                Violation(
                    rule_id="no_work_sensitive_to_unapproved_provider",
                    severity=_BLOCK,
                    message=_rule_message(
                        cfg,
                        "no_work_sensitive_to_unapproved_provider",
                        "Sensitive work/client data cannot be sent to non-approved providers.",
                    ),
                    detail=(
                        f"sensitivity={ctx.sensitivity}, provider={ctx.model_provider!r} "
                        "not in approved_work_providers"
                    ),
                )
            )

    # 3. no_mixed_personal_work_bundle (block)
    has_personal = any(s in _PERSONAL_SENSITIVITIES for s in sources)
    has_work = any(s in _WORK_SENSITIVITIES for s in sources)
    if has_personal and has_work:
        violations.append(
            Violation(
                rule_id="no_mixed_personal_work_bundle",
                severity=_BLOCK,
                message=_rule_message(
                    cfg,
                    "no_mixed_personal_work_bundle",
                    "Personal and work-sensitive source cards cannot be mixed "
                    "in one evidence bundle.",
                ),
                detail=f"source_sensitivities={sorted(set(sources))}",
            )
        )

    # 4. no_secret_in_markdown (block) — scan provided artifact paths.
    violations.extend(scan_paths(list(ctx.artifact_paths or ()), config=cfg))

    # 5. work_writeback_requires_review (require_approval)
    personal_mw_target = any("meatywiki" in t and "personal" in t for t in targets) or (
        "meatywiki" in targets
    )
    work_source = any(s in _WORK_SENSITIVITIES for s in sources) or (
        ctx.sensitivity in _WORK_SENSITIVITIES
    )
    if personal_mw_target and work_source:
        violations.append(
            Violation(
                rule_id="work_writeback_requires_review",
                severity=_REQUIRE_APPROVAL,
                message=_rule_message(
                    cfg,
                    "work_writeback_requires_review",
                    "Work-sensitive content requires sanitization and approval "
                    "before personal MeatyWiki writeback.",
                ),
                detail=f"targets={targets}, sensitivity={ctx.sensitivity}",
            )
        )

    # 6. material_claims_must_be_mapped (block)
    if ctx.unmapped_material_claims > 0 or ctx.unsupported_claims > 0:
        violations.append(
            Violation(
                rule_id="material_claims_must_be_mapped",
                severity=_BLOCK,
                message=_rule_message(
                    cfg,
                    "material_claims_must_be_mapped",
                    "Every material claim must map to a source card or be "
                    "labeled inference/speculation.",
                ),
                detail=(
                    f"unmapped={ctx.unmapped_material_claims}, "
                    f"unsupported={ctx.unsupported_claims}"
                ),
            )
        )

    result = _resolve(violations)
    _trace(paths, ctx, result)
    return result


def load_run_context(
    run_id: str,
    *,
    profile: str = "personal",
    model_provider: str | None = None,
    writeback_targets: tuple[str, ...] = (),
    paths: FoundryPaths | None = None,
) -> GuardContext:
    """Build a :class:`GuardContext` from a planned run's on-disk artifacts.

    Resolves the run's ``run.yaml`` → linked intent (``intents/active/<id>.yaml``)
    to read ``governance.key_profile_allowed`` and sensitivity, scans the run's
    ``sources/*.md`` front matter for their sensitivities, and collects the run's
    Markdown/YAML artifact paths for the secret scan. Missing pieces degrade to
    empty values so the guard is still evaluable. Raises :class:`NotFoundError`
    when the run directory itself is absent.
    """

    from ..errors import NotFoundError  # local import to avoid cycle at module load

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    if not rp.run.exists():
        raise NotFoundError(f"run not found: {run_id} ({rp.run})")

    run_doc = _safe_load_yaml(rp.run_yaml)
    intent_id = run_doc.get("intent_id") if isinstance(run_doc, dict) else None
    run_sensitivity = run_doc.get("sensitivity") if isinstance(run_doc, dict) else None

    key_profile_allowed: str | None = None
    intent_sensitivity: str | None = None
    if intent_id:
        intent = _load_intent_doc(str(intent_id), paths)
        gov = intent.get("governance") if isinstance(intent.get("governance"), dict) else {}
        key_profile_allowed = gov.get("key_profile_allowed")
        intent_sensitivity = intent.get("sensitivity") or gov.get("sensitivity")

    source_sensitivities = _scan_source_sensitivities(rp.sources)
    artifact_paths = _collect_run_artifacts(rp.run)

    return GuardContext(
        profile=profile,
        run_id=run_id,
        sensitivity=intent_sensitivity or run_sensitivity,
        source_sensitivities=tuple(source_sensitivities),
        model_provider=model_provider,
        writeback_targets=tuple(writeback_targets),
        intent_key_profile_allowed=key_profile_allowed,
        artifact_paths=tuple(artifact_paths),
    )


def _safe_load_yaml(path: Path) -> dict:
    from ..yamlio import load_yaml

    try:
        data = load_yaml(path)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_intent_doc(intent_id: str, paths: FoundryPaths) -> dict:
    """Resolve an intent by id under ``intents/active/`` (recursive fallback)."""

    candidate = paths.intents_active / f"{intent_id}.yaml"
    if not candidate.exists():
        matches = sorted(paths.intents.rglob(f"{intent_id}.yaml")) if paths.intents.exists() else []
        candidate = matches[0] if matches else candidate
    return _safe_load_yaml(candidate) if candidate.exists() else {}


def _scan_source_sensitivities(sources_dir: Path) -> list[str]:
    """Collect the ``sensitivity`` front-matter value from each source card."""

    if not sources_dir.exists():
        return []
    from ..frontmatter import load_md

    out: list[str] = []
    for md in sorted(sources_dir.glob("*.md")):
        try:
            meta, _ = load_md(md)
        except (OSError, ValueError):
            continue
        sens = meta.get("sensitivity") if isinstance(meta, dict) else None
        if isinstance(sens, str) and sens:
            out.append(sens)
    return out


def _collect_run_artifacts(run_dir: Path) -> list[Path]:
    """Gather Markdown/YAML files under a run dir for the secret scan."""

    if not run_dir.exists():
        return []
    files: list[Path] = []
    for pattern in ("*.md", "*.yaml", "*.yml"):
        files.extend(run_dir.rglob(pattern))
    return sorted(set(files))


def preflight(
    intent: dict,
    ibom: dict,
    routing: dict,
    profile: str,
    *,
    paths: FoundryPaths | None = None,
) -> GuardResult:
    """Pre-run governance check derived from intent/ibom/routing artifacts."""

    paths = paths or FoundryPaths.discover()
    intent = intent or {}
    ibom = ibom or {}
    routing = routing or {}

    gov = intent.get("governance") if isinstance(intent.get("governance"), dict) else {}
    key_profile_allowed = gov.get("key_profile_allowed")

    sensitivity = (
        intent.get("sensitivity")
        or gov.get("sensitivity")
        or ibom.get("sensitivity")
    )

    provider = (
        routing.get("model_provider")
        or routing.get("provider")
        or (routing.get("selected") or {}).get("provider")
        if isinstance(routing, dict)
        else None
    )

    writeback_targets = gov.get("allowed_writebacks") or []
    if not isinstance(writeback_targets, (list, tuple)):
        writeback_targets = []

    ctx = GuardContext(
        profile=profile,
        run_id=None,
        sensitivity=sensitivity,
        source_sensitivities=(),
        model_provider=provider,
        writeback_targets=tuple(writeback_targets),
        intent_key_profile_allowed=key_profile_allowed,
        artifact_paths=(),
    )
    return guard_check(ctx, paths=paths)


# --- Outcome aggregation + trace ------------------------------------------


def _resolve(violations: list[Violation]) -> GuardResult:
    severities = {v.severity for v in violations}
    if _BLOCK in severities:
        return GuardResult(passed=False, exit_code=int(ExitCode.GOVERNANCE), violations=violations)
    if _REQUIRE_APPROVAL in severities:
        return GuardResult(
            passed=False, exit_code=int(ExitCode.HUMAN_REVIEW), violations=violations
        )
    return GuardResult(passed=True, exit_code=int(ExitCode.OK), violations=violations)


def _trace(paths: FoundryPaths, ctx: GuardContext, result: GuardResult) -> None:
    """Best-effort run-trace record; never fail the guard on trace error."""

    if not ctx.run_id:
        return
    try:
        rp = paths.run_paths(ctx.run_id)
        append_jsonl(
            {
                "stage": "guard",
                "ts": now_iso(),
                "run_id": ctx.run_id,
                "passed": result.passed,
                "exit_code": result.exit_code,
                "violations": [v.rule_id for v in result.violations],
            },
            rp.run_trace,
        )
    except Exception:  # noqa: BLE001 — tracing is best-effort
        pass


__all__ = [
    "Violation",
    "GuardResult",
    "GuardContext",
    "guard_check",
    "preflight",
    "load_run_context",
    "scan_secrets",
    "scan_paths",
]
