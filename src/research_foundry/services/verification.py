"""Report claim verifier — the differentiated value of Research Foundry.

``verify_report`` is the gate between "a model wrote some markdown" and "a report
you can rely on". It deterministically enforces spec §12.3: every material claim
in the report body must either carry a ``[claim:<id>]`` tag that resolves to the
run's claim ledger, or be explicitly labeled as an inference/speculation. It also
enforces ledger-side invariants (supported claims have source cards, inference
claims have a basis) and governance (work-sensitive sources may not leak into a
public report).

The verifier never calls the network and never needs an API key. Exit codes
follow the stable contract in :mod:`research_foundry.errors` with this
precedence (first that applies wins):

1. missing front matter / schema failure  -> ExitCode.SCHEMA (2)
2. work-sensitive source in a public report -> ExitCode.GOVERNANCE (3)
3. any unsupported material claim / unsupported ledger claim -> ExitCode.UNSUPPORTED (4)
4. otherwise                                -> ExitCode.OK (0)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from .. import RF_SCHEMA_VERSION
from ..config import FoundryConfig
from ..errors import ExitCode, RFError
from ..frontmatter import load_md
from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import append_jsonl, dump_yaml, load_yaml
from .export_service import DEFAULT_THRESHOLD, SENSITIVITY_ORDER, discover_run_yamls
from .governance import release_gate_blocked_by_unassessed_judgment
from .quote_fidelity import check_quote_fidelity

# Reverse map: rank → label, used by build_global_source_index to store the
# effective-sensitivity label rather than just the raw card-level field.
_SENSITIVITY_BY_RANK: dict[int, str] = {v: k for k, v in SENSITIVITY_ORDER.items()}

# --- Built-in defaults (used when config/claim_policy.yaml is absent) -------

_DEFAULT_MATERIAL_CLAIM_TYPES = [
    "factual",
    "quantitative",
    "comparative",
    "causal",
    "attribution",
    "recommendation",
    "prediction",
]

_DEFAULT_VERIFIER_CHECKS = [
    {"id": "report_has_frontmatter", "severity": "error"},
    {"id": "all_claim_ids_exist", "severity": "error"},
    {"id": "material_claims_have_claim_ids", "severity": "error"},
    {"id": "supported_claims_have_source_cards", "severity": "error"},
    {"id": "source_cards_have_locators", "severity": "warning"},
    {"id": "exact_passage_present", "severity": "warning"},
    {"id": "pediatric_cds_schema_invalid", "severity": "error"},
    # RFUP-1 P4-001: kept as "warning" so this new check's wiring cannot, by
    # itself, regress any existing run's exit code — see the call-site
    # comment (6d, below) and quote_fidelity.py's module docstring.
    {"id": "quote_fidelity", "severity": "warning"},
    {"id": "inferences_have_basis", "severity": "error"},
    {"id": "speculation_is_labeled", "severity": "error"},
    {"id": "unsupported_claims_block_publish", "severity": "error"},
    {"id": "work_sensitive_claims_block_public_report", "severity": "error"},
]

# Label markers that exempt a sentence from the "material claim needs a tag" rule.
_LABEL_PATTERNS = {
    "inference": re.compile(r"\*\*\s*Inference\s*:?\s*\*\*", re.IGNORECASE),
    "speculation": re.compile(r"\*\*\s*Speculation\s*:?\s*\*\*", re.IGNORECASE),
    "mixed": re.compile(r"\*\*\s*Mixed evidence\s*:?\s*\*\*", re.IGNORECASE),
    "contradicted": re.compile(r"\*\*\s*Contradicted", re.IGNORECASE),
}

_CLAIM_TAG = re.compile(r"\[claim:([A-Za-z0-9_\-]+)\]")

# Per-type heuristics for classifying a sentence as a material claim. These are
# intentionally conservative-but-real: they fire on the kinds of sentences a
# reader could rely on as fact (numbers, comparisons, attributions, advice,
# predictions). Sections like "Open questions" / "Sources" are excluded by the
# caller, and labeled/tagged sentences are exempt regardless.
_MATERIAL_HEURISTICS: dict[str, re.Pattern[str]] = {
    "quantitative": re.compile(
        r"\b\d[\d,\.]*\s*(?:%|percent|queries|tokens|ms|seconds|x|times|"
        r"million|billion|thousand|k\b|gb|mb|requests|docs|documents|cases|"
        r"samples|rows|users|hours|days|years)?\b",
        re.IGNORECASE,
    ),
    "comparative": re.compile(
        r"\b(?:more|less|faster|slower|better|worse|higher|lower|cheaper|"
        r"superior|inferior|outperform[s]?|than)\b",
        re.IGNORECASE,
    ),
    "recommendation": re.compile(
        r"\b(?:use|adopt|prefer|recommend(?:ed)?|should|must|avoid|choose)\b",
        re.IGNORECASE,
    ),
    "attribution": re.compile(
        r"\b(?:according to|says?|claims?|states?|reports?|per the|the vendor|"
        r"the authors?|the paper)\b",
        re.IGNORECASE,
    ),
    "causal": re.compile(
        r"\b(?:because|causes?|caused|leads? to|results? in|reduces?|increases?|"
        r"improves?|enables?|prevents?|due to)\b",
        re.IGNORECASE,
    ),
    "prediction": re.compile(
        r"\b(?:will|likely|expected to|going to|in the future|forecast|"
        r"projected)\b",
        re.IGNORECASE,
    ),
    # 'factual' is the broadest: a declarative sentence asserting a state of the
    # world ("X supports Y", "X is Y"). We require a finite verb signal so that
    # questions and fragments are not swept in.
    "factual": re.compile(
        r"\b(?:is|are|was|were|supports?|provides?|includes?|contains?|has|have|"
        r"requires?|consists? of|comprises?)\b",
        re.IGNORECASE,
    ),
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# HTML comment span. The synthesizer emits empty-section placeholders as whole-line
# comments (e.g. ``<!-- No supported findings for this run. -->``). We strip comment
# spans rather than dropping the whole line, so a real claim after an inline comment
# is still classified (closes the "<!-- note --> <claim>" laundering hole).
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single verifier check."""

    id: str
    severity: str  # error | warning
    status: str  # pass | fail | warn | skip
    detail: str
    locations: list[str]


@dataclass(frozen=True)
class VerificationResult:
    """Aggregate verifier outcome with the stable exit code."""

    run_id: str
    passed: bool
    exit_code: int  # int(ExitCode.*)
    checks: list[CheckResult]
    verification_path: Path
    unsupported: list[str]
    human_review_required: bool = False
    #: Stamped so any `--json` serialization of this dataclass (e.g. via
    #: dataclasses.asdict) carries the same top-level rf_schema_version field
    #: already written into verification.yaml's `record` dict below (PRD
    #: FR-4.1 / AC-RFUP4-1). Defaulted so existing keyword-arg construction
    #: sites are unaffected.
    rf_schema_version: str = RF_SCHEMA_VERSION
    #: Resolved ``verify.exact_passage`` mode for this run (PRD FR-3.2, OQ-1):
    #: ``"warn"`` (default) or ``"strict"``. Plumbing only in this phase — the
    #: eligibility check that consumes it is wired in a later task. Defaulted
    #: so existing keyword-arg construction sites are unaffected.
    exact_passage_mode: str = "warn"
    #: Claim ids flagged by the ``exact_passage_present`` check (TASK-2.2) as
    #: missing an exact-passage quote anchor — populated whenever there ARE
    #: violations, REGARDLESS of ``exact_passage_mode`` (PRD FR-3.3/FR-3.4,
    #: AC-RFUP3-4). Distinct from ``source_cards_have_locators``'s own
    #: ``CheckResult.locations`` (that check flags missing *locators*, not
    #: missing exact-passage *quotes* — the two must never be conflated).
    #: Defaulted to an empty list so existing keyword-arg construction sites,
    #: and any downstream consumer doing ``result.exact_passage_violations``
    #: or ``record.get("exact_passage_violations", [])``, are unaffected when
    #: there are zero violations (AC-RFUP3-5 resilience).
    exact_passage_violations: list[str] = field(default_factory=list)


# --- Parsing ----------------------------------------------------------------


@dataclass
class _Sentence:
    text: str
    heading: str
    has_tag: bool
    tag_ids: list[str]
    labeled: bool


def _segment_sentences(body: str) -> list[_Sentence]:
    """Split the report body into classified sentences, tracking the heading.

    The report discipline is *one claim per line*: a content line that carries a
    ``[claim:<id>]`` tag or an Inference/Speculation label is treated as a single
    unit so a sentence-ending period inside the claim text does not detach the
    trailing tag (which would spuriously flag the text as untagged). Lines with
    neither a tag nor a label are split into sub-sentences so that several
    injected untagged claims on one line are each caught.
    """

    out: list[_Sentence] = []
    heading = ""
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip().lower()
            continue
        # Strip any HTML comment spans (a whole-line comment becomes empty and is
        # skipped; a trailing real claim after an inline comment is preserved).
        line = _HTML_COMMENT.sub("", line).strip()
        if not line:
            continue
        # Bullet markers are content lines too; strip a leading list marker.
        content = re.sub(r"^[-*+]\s+", "", line).strip()
        if not content:
            continue
        line_tag_ids = _CLAIM_TAG.findall(content)
        line_labeled = any(p.search(content) for p in _LABEL_PATTERNS.values())
        if line_tag_ids or line_labeled:
            # Keep the whole line together; the tag/label binds to the claim text.
            pieces = [content]
        else:
            pieces = [p for p in _SENTENCE_SPLIT.split(content) if p.strip()]
        for piece in pieces:
            text = piece.strip()
            if not text:
                continue
            tag_ids = _CLAIM_TAG.findall(text)
            labeled = any(p.search(text) for p in _LABEL_PATTERNS.values())
            out.append(
                _Sentence(
                    text=text,
                    heading=heading,
                    has_tag=bool(tag_ids),
                    tag_ids=tag_ids,
                    labeled=labeled,
                )
            )
    return out


# Citation-list headings whose lines are never material report claims.
_CITATION_HEADINGS = {"sources", "references"}


def _is_material(sentence: _Sentence, material_types: list[str]) -> bool:
    """Heuristically decide if a sentence is a material claim of an active type."""

    # Sources/references are citation lists, never claims.
    if sentence.heading in _CITATION_HEADINGS:
        return False
    # Under "open questions", only genuine questions are exempt; a declarative
    # material assertion relocated here is still checked (closes the laundering hole).
    if sentence.heading == "open questions" and sentence.text.rstrip().endswith("?"):
        return False
    text = sentence.text
    # Strip the claim tag and any label marker before pattern-matching so the
    # tag/label tokens don't themselves trigger a heuristic.
    stripped = _CLAIM_TAG.sub("", text)
    for pat in _LABEL_PATTERNS.values():
        stripped = pat.sub("", stripped)
    for ctype in material_types:
        pat = _MATERIAL_HEURISTICS.get(ctype)
        if pat and pat.search(stripped):
            return True
    return False


# --- Source-card resolution -------------------------------------------------


def _index_source_cards(rp) -> dict[str, dict[str, Any]]:
    """Map source_card_id -> {sensitivity, has_locator, has_quote, path, points} for the run.

    ``has_quote`` (PRD FR-3.1) is ``True`` when the card has at least one
    ``extracted_points[]`` entry with a non-empty ``quote`` — i.e. the card
    can serve as an exact-passage anchor, not merely a locator-only citation.

    ``points`` is the card's raw (dict-filtered) ``extracted_points[]`` list —
    exposed so :func:`verify_report`'s ``pediatric_cds_schema_invalid`` check
    (RFUP-1 P2-002) can inspect each point's optional ``pediatric_cds`` block
    without a second read of the card's markdown file (AC-P2-6: zero new I/O).

    ``extraction_status`` is the card's raw front-matter field (RFUP-1
    P4-003) -- exposed so :func:`~.quote_fidelity.check_quote_fidelity` can
    distinguish an ``extraction_status: locator_only`` card (nothing stored
    to diff against, but genuinely unverifiable -> warn, AC-P4-7) from any
    other card that happens to have no stored quote for some other reason
    (unchanged silent skip). ``None`` when absent from front matter. Zero
    new I/O -- read from the same already-loaded ``meta``.
    """

    index: dict[str, dict[str, Any]] = {}
    sources_dir = rp.sources
    if not sources_dir.exists():
        return index
    for p in sorted(sources_dir.glob("*.md")):
        try:
            meta, _ = load_md(p)
        except Exception:  # noqa: BLE001 - a broken card is treated as missing
            continue
        sid = meta.get("source_card_id")
        if not sid:
            continue
        src = meta.get("source", {}) if isinstance(meta.get("source"), dict) else {}
        locator = src.get("locator", {}) if isinstance(src.get("locator"), dict) else {}
        has_locator = bool(locator) and any(
            v for v in locator.values() if v not in (None, "")
        )
        points = [pt for pt in (meta.get("extracted_points") or []) if isinstance(pt, dict)]
        has_quote = any(pt.get("quote") for pt in points)
        index[sid] = {
            "sensitivity": meta.get("sensitivity"),
            "has_locator": has_locator,
            "has_quote": has_quote,
            "path": str(p),
            "points": points,
            "extraction_status": meta.get("extraction_status"),
        }
    return index


# Sentinel key prefix used by build_global_source_index when a run's
# sources/ dir cannot be listed.  The check function treats any entry whose
# key starts with this prefix as a hard blocker (fail-closed).
_IO_ERROR_SENTINEL_PREFIX = "_io_error_"


def build_global_source_index(paths: FoundryPaths) -> dict[str, tuple[str, str]]:
    """Build a workspace-wide mapping: source_card_id -> (run_id, sensitivity).

    Mirrors the shape of _index_source_cards but iterates every run in the
    workspace rather than a single run.  Uses :func:`discover_run_yamls` so
    nested run layouts (e.g. ``runs/sub/<id>/``) are included at any depth up
    to 3, matching the export service's run discovery logic.

    *run_id* stored in the tuple is the run directory's path **relative to**
    ``paths.runs`` (e.g. ``"rf_run_abc"`` or ``"sub/rf_run_abc"``).  Consumers
    like :func:`check_report_body_sensitivity_global` reconstruct the
    ``sources/`` directory with ``paths.runs / run_id / "sources"``, which
    resolves correctly for both flat and nested layouts via pathlib's slash
    operator when the stored run_id contains a separator.

    *sensitivity* is the **effective** value — the maximum of the card-level
    ``meta.sensitivity`` and any per-point ``extracted_points[].sensitivity``
    — matching the logic in :func:`check_report_body_sensitivity` so that a
    card with a public card-level label but a work_sensitive extracted point
    is indexed at the higher rank.

    Fail-closed: if a run's sources/ dir cannot be read (I/O error, corrupt
    dir), that run is included as a sentinel ("unknown", "restricted") rather
    than silently omitted — preserving the fail-closed contract from
    export_service.DEFAULT_THRESHOLD.
    """
    index: dict[str, tuple[str, str]] = {}
    runs_dir = paths.runs
    if not runs_dir.exists():
        return index
    try:
        run_yamls = discover_run_yamls(runs_dir, max_depth=3)
    except OSError:
        return index

    for run_yaml in run_yamls:
        run_dir = run_yaml.parent
        # Store the path relative to runs_dir so nested layouts resolve via
        # paths.runs / run_id / "sources" in consumers.
        run_id = str(run_dir.relative_to(runs_dir))
        sources_dir = run_dir / "sources"
        if not sources_dir.exists():
            continue
        try:
            card_paths = sorted(sources_dir.glob("*.md"))
        except OSError:
            index[f"{_IO_ERROR_SENTINEL_PREFIX}{run_id}"] = ("unknown", "restricted")
            continue
        for card_path in card_paths:
            try:
                meta, _ = load_md(card_path)
            except Exception:  # noqa: BLE001 - a broken card is treated as missing
                continue
            sid = meta.get("source_card_id")
            if not sid:
                continue
            # Compute effective sensitivity: max(card-level rank, max point rank).
            card_rank = SENSITIVITY_ORDER.get(str(meta.get("sensitivity") or ""), len(SENSITIVITY_ORDER))
            points = [p for p in (meta.get("extracted_points") or []) if isinstance(p, dict)]
            effective_rank = card_rank
            for p in points:
                if p.get("sensitivity"):
                    effective_rank = max(
                        effective_rank,
                        SENSITIVITY_ORDER.get(str(p["sensitivity"]), len(SENSITIVITY_ORDER)),
                    )
            # Reverse-look up the canonical label; fall back to the raw card value
            # for unknown ranks so the consumer's fail-closed SENSITIVITY_ORDER
            # lookup still fires correctly.
            effective_label = _SENSITIVITY_BY_RANK.get(
                effective_rank, str(meta.get("sensitivity") or "")
            )
            index[str(sid)] = (run_id, effective_label)

    return index


# --- Helpers ----------------------------------------------------------------


def _load_policy(paths: FoundryPaths) -> tuple[list[str], list[dict[str, Any]]]:
    cfg = FoundryConfig(paths=paths)
    policy = cfg.claim_policy if isinstance(cfg.claim_policy, dict) else {}
    material = policy.get("material_claim_types") or _DEFAULT_MATERIAL_CLAIM_TYPES
    checks = policy.get("verifier_checks") or _DEFAULT_VERIFIER_CHECKS
    material = [str(m) for m in material if m]
    checks = [c for c in checks if isinstance(c, dict) and c.get("id")]
    return material, checks


def _severity_for(check_id: str, checks: list[dict[str, Any]]) -> str:
    for c in checks:
        if c.get("id") == check_id:
            return str(c.get("severity", "error"))
    return "error"


# --- pediatric_cds schema hard-gate (RFUP-1 P2-002, AC-P2-5/6/7) -----------
#
# Structural-completeness gate for the `pediatric_cds` evidence-card
# extension block (schemas/pediatric_cds.schema.json, P2-001). Mirrors
# resolve_exact_passage_mode's fail-closed convention: a broken *schema
# config* (missing file / bad JSON) raises RFError immediately, distinct
# from a card's *block content* failing validation against a good schema
# (which is a normal "fail" + unsupported[] outcome, not an RFError).

# services/verification.py -> parents[0]=services, [1]=research_foundry ->
# .../src/research_foundry/schemas/pediatric_cds.schema.json (package-bundled
# artifact; distinct from FoundryPaths.schemas, which resolves a *workspace's*
# schemas/ dir and is not where this file lives).
_PEDIATRIC_CDS_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "pediatric_cds.schema.json"
)


@lru_cache(maxsize=1)
def _load_pediatric_cds_schema() -> dict[str, Any]:
    """Load+cache the pediatric_cds JSON Schema.

    Raises
    ------
    RFError
        If the schema file is missing, is not valid JSON, or its top level is
        not a JSON object — a schema *configuration* problem that must fail
        closed rather than silently disabling the hard-gate (AC-P2-5).
        ``lru_cache`` does not memoize raised exceptions, so a transient
        misconfiguration is re-checked (and can succeed) on the next call.
    """

    try:
        raw = _PEDIATRIC_CDS_SCHEMA_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RFError(
            "pediatric_cds schema config invalid: cannot read "
            f"{_PEDIATRIC_CDS_SCHEMA_PATH}: {exc}"
        ) from exc
    try:
        schema = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RFError(
            "pediatric_cds schema config invalid: "
            f"{_PEDIATRIC_CDS_SCHEMA_PATH} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(schema, dict):
        raise RFError(
            "pediatric_cds schema config invalid: "
            f"{_PEDIATRIC_CDS_SCHEMA_PATH} top level must be a JSON object"
        )
    return schema


def _json_safe(obj: Any) -> Any:
    """Round-trip *obj* through JSON so YAML-native types match JSON Schema's.

    Source cards are loaded via ``yaml.safe_load`` (frontmatter.py ->
    yamlio.py), which auto-parses unquoted ISO date-like scalars (e.g.
    ``2026-07-22``) into ``datetime.date`` objects. The pediatric_cds schema
    declares those same fields as JSON Schema ``"type": "string"`` (with
    ``"format": "date"``), so validating the raw YAML-parsed value would
    produce a false-positive type failure unrelated to the block's actual
    content. ``default=str`` on the dump side stringifies any such object
    (``str(date(...))`` == ``date(...).isoformat()``) before jsonschema ever
    sees it — this is a type-normalization step, not a content change.
    """

    return json.loads(json.dumps(obj, default=str))


# The two mutually-exclusive `oneOf` branches the pediatric_cds schema
# accepts (P2-003 finding): the flat shape already produced by the 7
# existing verified bundles (aaa9d92) vs. the richer 9-section target shape
# from the pediatric-anemia-site design spec. See the schema's own
# ``$comment`` for the full rationale.
_PEDIATRIC_CDS_SCHEMA_VARIANTS = ("PediatricCdsBlockLegacy", "PediatricCdsBlockRich")


def _pediatric_cds_block_errors(block: Any) -> list[str]:
    """Validate one ``pediatric_cds`` block; sorted ``path: message`` strings.

    Empty list == valid. Error formatting mirrors
    :meth:`research_foundry.schemas.SchemaRegistry.validate` so `rf verify`
    output stays consistent with the rest of the codebase's schema-error
    reporting conventions.

    The schema's top level is a ``oneOf`` of two mutually-exclusive shapes
    (legacy flat vs. rich 9-section — P2-003). jsonschema's ``oneOf`` keyword
    only ever raises one generic "is not valid under any of the given
    schemas" error at the top level; the field-specific failures live in
    that error's ``.context`` and ``jsonschema.exceptions.best_match()`` is
    not reliable here because the two branches have entirely disjoint
    required-field sets, so a block failing both loses against each roughly
    equally. Instead: on failure, validate the block against each named
    branch *directly* and report whichever branch's own errors are fewest —
    i.e. the shape the block was clearly attempting — so the failure detail
    keeps naming the actual missing/mistyped field (AC-P2-7).
    """

    from jsonschema import Draft202012Validator

    schema = _load_pediatric_cds_schema()
    safe_block = _json_safe(block)
    validator = Draft202012Validator(schema)
    if validator.is_valid(safe_block):
        return []

    defs = schema.get("$defs", {})
    branch_error_sets: list[list[Any]] = []
    for variant in _PEDIATRIC_CDS_SCHEMA_VARIANTS:
        branch_schema = {**defs[variant], "$defs": defs}
        branch_validator = Draft202012Validator(branch_schema)
        branch_error_sets.append(
            sorted(branch_validator.iter_errors(safe_block), key=lambda e: list(e.path))
        )

    # min(..., key=len) picks the branch closest to valid (fewest errors);
    # a tie is resolved by list order (legacy first) — arbitrary but stable.
    errors_to_report = min(branch_error_sets, key=len)
    errors: list[str] = []
    for err in errors_to_report:
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


# Valid values for verify.exact_passage (PRD FR-3.2, decisions-block OQ-1).
_VALID_EXACT_PASSAGE_MODES = frozenset({"warn", "strict"})


def resolve_exact_passage_mode(paths: FoundryPaths, override: str | None = None) -> str:
    """Resolve the effective ``verify.exact_passage`` mode (PRD FR-3.2, OQ-1).

    Precedence: an explicit *override* (the CLI's ``--exact-passage`` flag)
    always wins over the ``verify.exact_passage`` key in
    ``config/claim_policy.yaml``. When neither is present or the config value
    is invalid/missing, the mode defaults to ``"warn"`` — the safe,
    non-regressing default for this whole phase (the actual eligibility check
    that consumes this mode is wired in a later task).

    Parameters
    ----------
    paths:
        Workspace paths, used to load ``config/claim_policy.yaml`` via
        :class:`~research_foundry.config.FoundryConfig` (mirrors
        :func:`_load_policy`'s loading style).
    override:
        Optional run-level value (typically sourced from a CLI flag). Must be
        ``"warn"`` or ``"strict"`` (case-insensitive) when provided.

    Returns
    -------
    str
        Either ``"warn"`` or ``"strict"``.

    Raises
    ------
    RFError
        If *override* is provided but is not one of ``warn``/``strict`` —
        fails closed rather than silently ignoring a bad flag.
    """
    if override is not None:
        normalized_override = str(override).strip().lower()
        if normalized_override not in _VALID_EXACT_PASSAGE_MODES:
            raise RFError(
                f"--exact-passage={override!r} is not valid; "
                f"must be one of: {', '.join(sorted(_VALID_EXACT_PASSAGE_MODES))}"
            )
        return normalized_override

    cfg = FoundryConfig(paths=paths)
    policy = cfg.claim_policy if isinstance(cfg.claim_policy, dict) else {}
    verify_block = policy.get("verify") if isinstance(policy, dict) else None
    if not isinstance(verify_block, dict):
        return "warn"
    raw = verify_block.get("exact_passage", "warn")
    normalized = str(raw).strip().lower() if raw else "warn"
    return normalized if normalized in _VALID_EXACT_PASSAGE_MODES else "warn"


# --- P3-001 clinical-eligibility filter (RFUP-1, PRD FR-5 / OQ-1) ----------
#
# Resolves the per-claim auto-strict override for exact_passage_present: a
# claim whose evidence is both a "threshold" assertion AND carries an
# explicit clinical-sensitivity signal is forced to strict mode for ITS OWN
# evaluation, independent of the run's configured/CLI exact_passage_mode
# (AC-P3-2). See ``claim_clinical_eligibility`` below for the full trigger
# definition and the fail-safe-to-non-eligible resolution (AC-P3-3).


def _pediatric_cds_assertion_kind(point: dict[str, Any]) -> str | None:
    """The point's ``pediatric_cds.implementable_statement.assertion_kind``,
    lowercased, or ``None`` when absent/indeterminate.

    Only the rich pediatric_cds shape (schemas/pediatric_cds.schema.json's
    ``PediatricCdsBlockRich``) carries ``implementable_statement`` at all —
    the legacy flat shape (the ONLY shape present on the 7 currently-verified
    pediatric-CDS bundles, commit aaa9d92) has no ``assertion_kind`` field
    anywhere. This function deliberately does not infer an assertion_kind
    from the legacy shape's ``classification``/``threshold`` fields: per the
    schema's own seam-boundary comment, interpreting those fields' clinical
    semantics is owned by pediatric-anemia-site, not rf. A legacy block (or
    any block missing this field) therefore always yields ``None`` here,
    which ``claim_clinical_eligibility`` resolves to "not eligible" rather
    than "eligible" (AC-P3-3) — this is also what keeps the 7 existing
    verified bundles from newly tripping into strict mode under this filter.
    """
    block = point.get("pediatric_cds") if isinstance(point, dict) else None
    if not isinstance(block, dict):
        return None
    stmt = block.get("implementable_statement")
    if not isinstance(stmt, dict):
        return None
    kind = stmt.get("assertion_kind")
    return str(kind).strip().lower() if kind else None


def _cited_card_has_elevated_sensitivity(card_entry: dict[str, Any]) -> bool:
    """True when a cited card (or one of its points) carries an explicit
    sensitivity classification above the default ``public`` baseline.

    Mirrors the card/point "effective sensitivity" convention already used
    by :func:`check_report_body_sensitivity` (card-level rank maxed with any
    point-level override) rather than introducing a second sensitivity
    model. A bare ``sensitivity: public`` — the default governance baseline
    present on nearly every card — deliberately does NOT count as "an
    existing sensitivity tag" here; only an elevated (non-public) rank is
    treated as an explicit clinical-sensitivity signal (PRD OQ-1). Counting
    "public" too would make this branch true for virtually every card and
    defeat the narrow-trigger intent behind PRD Risk 1 (over-broad
    hard-gating of runs that never asked for strict mode).
    """
    card_rank = SENSITIVITY_ORDER.get(str(card_entry.get("sensitivity") or ""), -1)
    if card_rank > 0:
        return True
    for pt in card_entry.get("points") or []:
        if isinstance(pt, dict) and pt.get("sensitivity"):
            if SENSITIVITY_ORDER.get(str(pt["sensitivity"]), -1) > 0:
                return True
    return False


def claim_clinical_eligibility(
    claim: dict[str, Any], source_index: dict[str, dict[str, Any]]
) -> bool:
    """Is *claim* eligible for the P3 auto-strict exact-passage override?

    Eligible == ``assertion_kind == "threshold"`` on >=1 of the claim's
    cited, resolvable source cards' pediatric_cds blocks, AND (a
    pediatric_cds block is present on >=1 cited card OR >=1 cited card
    carries an existing elevated-sensitivity tag) — the trigger resolved in
    the parent plan's decisions block, deliberately **not** "threshold
    alone" (PRD Risk 1: an over-broad trigger would hard-gate runs that
    never asked for strict mode).

    In today's schema the assertion_kind signal can only originate from a
    pediatric_cds block (see :func:`_pediatric_cds_assertion_kind`), so the
    first OR-branch is already implied whenever assertion_kind resolves to
    "threshold". This function still evaluates both branches independently
    — rather than collapsing the whole trigger to just the assertion_kind
    check — so the AND/OR shape stays correct if a future assertion_kind
    source is ever added outside the pediatric_cds namespace.

    AC-P3-3 — fail-safe direction (the deliberate asymmetry vs. P4's
    fidelity check, a separate task): when the assertion_kind signal cannot
    be determined at all for this claim (no cited card has ANY pediatric_cds
    block, or every present block lacks a recognizable assertion_kind), the
    claim defaults to **non-eligible** — today's warn-only behavior — rather
    than strict. P3 fails safe toward *under*-gating (avoid an unwanted hard
    gate on a non-clinical run) because its failure mode is a false-block;
    P4 fails safe toward *over*-visibility (never silently report "pass" on
    an indeterminate signal) because its failure mode is a missed
    corruption. Same "signal is indeterminate" shape, opposite resolution,
    because the two checks sit on opposite sides of the risk (PRD Risk 1).
    """
    cited_ids = [
        s.get("source_card_id") for s in (claim.get("sources") or []) if s.get("source_card_id")
    ]
    cited_cards = [source_index[sid] for sid in cited_ids if sid in source_index]
    if not cited_cards:
        return False

    assertion_kind_is_threshold = False
    pediatric_cds_present = False
    elevated_sensitivity_present = False
    for card in cited_cards:
        for pt in card.get("points") or []:
            if not isinstance(pt, dict):
                continue
            if isinstance(pt.get("pediatric_cds"), dict):
                pediatric_cds_present = True
            if _pediatric_cds_assertion_kind(pt) == "threshold":
                assertion_kind_is_threshold = True
        if _cited_card_has_elevated_sensitivity(card):
            elevated_sensitivity_present = True

    return assertion_kind_is_threshold and (pediatric_cds_present or elevated_sensitivity_present)


def _resolve_explicit_path(rp, given: Path | None, label: str) -> Path | None:
    """Resolve an explicitly-provided path: run-dir first, then CWD.

    When *given* is ``None`` the caller uses auto-discovery (not this function).
    When *given* is not ``None`` and cannot be found anywhere, raise ``RFError``
    with a clear message so the caller aborts *before* writing any output files.
    """
    if given is None:
        return None
    p = Path(given)
    if p.is_absolute():
        if p.exists():
            return p
        raise RFError(f"{label} path not found: {p}")
    # Relative path: try run directory first, then CWD.
    run_relative = rp.run / p
    if run_relative.exists():
        return run_relative
    cwd_relative = Path.cwd() / p
    if cwd_relative.exists():
        return cwd_relative
    raise RFError(f"{label} path not found: {p} (tried {run_relative} and {cwd_relative})")


def _resolve_report_path(rp) -> Path | None:
    """Auto-discover the report path within the run directory."""
    if rp.report_draft.exists():
        return rp.report_draft
    if rp.report_final.exists():
        return rp.report_final
    return None


def _trace(rp, **fields: Any) -> None:
    try:
        append_jsonl({"ts": now_iso(), **fields}, rp.run_trace)
    except Exception:  # noqa: BLE001 - tracing is best-effort
        pass


# --- The verifier -----------------------------------------------------------


def verify_report(
    run_id: str,
    *,
    report_path: Path | None = None,
    claim_ledger_path: Path | None = None,
    fail_on_unsupported: bool = True,
    exact_passage_override: str | None = None,
    paths: FoundryPaths | None = None,
    disposition: str = "internal_capture",
    evidence_judgment_bases: Sequence[str] | None = None,
) -> VerificationResult:
    """Verify a run's report against its claim ledger (spec §12.3).

    Returns a :class:`VerificationResult` whose ``exit_code`` is one of the
    stable :class:`~research_foundry.errors.ExitCode` integers, following the
    documented precedence. Writes ``reviews/verification.yaml`` and updates the
    ledger's ``verification_status``.

    ``disposition``/``evidence_judgment_bases`` wire the decisions-block OQ-6
    release gate (governance.py owns the boolean logic; this function is the
    CALLER, not a reimplementation — see
    :func:`research_foundry.services.governance.release_gate_blocked_by_unassessed_judgment`).
    Defaults (``"internal_capture"``, no evidence items) are fully
    non-blocking and backward compatible with every existing caller: pass
    ``disposition="commercial_release"`` plus the ``judgment_basis`` values of
    the evidence items involved to gate a release/disposition evaluation.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    material_types, check_specs = _load_policy(paths)
    exact_passage_mode = resolve_exact_passage_mode(paths, exact_passage_override)

    checks: list[CheckResult] = []
    unsupported: list[str] = []

    def add(check_id: str, status: str, detail: str, locations: list[str] | None = None) -> None:
        checks.append(
            CheckResult(
                id=check_id,
                severity=_severity_for(check_id, check_specs),
                status=status,
                detail=detail,
                locations=locations or [],
            )
        )

    # 1) Resolve & parse the report front matter -----------------------------
    # Explicit path: resolve against run dir first, CWD second; missing → RFError.
    # Bare invocation (no --report): auto-discover within the run directory.
    if report_path is not None:
        rpath: Path | None = _resolve_explicit_path(rp, report_path, "report")
    else:
        rpath = _resolve_report_path(rp)
    front: dict[str, Any] = {}
    body = ""
    frontmatter_ok = False
    if rpath is not None:
        try:
            front, body = load_md(rpath)
        except Exception:  # noqa: BLE001
            front, body = {}, ""
        frontmatter_ok = isinstance(front, dict) and bool(front) and bool(
            front.get("type") or front.get("report_id")
        )

    if frontmatter_ok:
        add("report_has_frontmatter", "pass", "report has front matter")
    else:
        add(
            "report_has_frontmatter",
            "fail",
            "report is missing front matter or could not be loaded"
            if rpath is not None
            else "no report file found for run",
            [str(rpath)] if rpath else [],
        )

    # 2) Load the claim ledger ----------------------------------------------
    # Explicit path: same run-dir-first resolution. Missing explicit path → RFError.
    if claim_ledger_path is not None:
        lpath: Path = _resolve_explicit_path(rp, claim_ledger_path, "claim-ledger") or rp.claim_ledger
    else:
        lpath = rp.claim_ledger
    ledger: dict[str, Any] = {}
    if lpath.exists():
        data = load_yaml(lpath)
        ledger = data if isinstance(data, dict) else {}
    claims = list(ledger.get("claims", []) or [])
    ledger_ids = {c.get("claim_id") for c in claims if c.get("claim_id")}

    source_index = _index_source_cards(rp)
    report_sensitivity = front.get("sensitivity") if isinstance(front, dict) else None

    # Parse body sentences (only meaningful when front matter is present).
    sentences = _segment_sentences(body) if frontmatter_ok else []
    report_tag_ids: list[str] = []
    for s in sentences:
        report_tag_ids.extend(s.tag_ids)

    # 3) all_claim_ids_exist -------------------------------------------------
    if frontmatter_ok:
        missing_ids = sorted({tid for tid in report_tag_ids if tid not in ledger_ids})
        if missing_ids:
            add(
                "all_claim_ids_exist",
                "fail",
                "report cites claim ids absent from the ledger: " + ", ".join(missing_ids),
                missing_ids,
            )
        else:
            add("all_claim_ids_exist", "pass", "all cited claim ids resolve to the ledger")
    else:
        add("all_claim_ids_exist", "skip", "skipped: report front matter missing")

    # 3b) claim_ids_unique — duplicate ids let one entry silently mask another.
    all_ids = [c.get("claim_id") for c in claims if c.get("claim_id")]
    dup_ids = sorted({cid for cid in all_ids if all_ids.count(cid) > 1})
    if dup_ids:
        add(
            "claim_ids_unique",
            "fail",
            "ledger has duplicate claim_id(s): " + ", ".join(dup_ids),
            dup_ids,
        )
    else:
        add("claim_ids_unique", "pass", "all ledger claim ids are unique")

    # 4) material_claims_have_claim_ids -> unsupported (exit 4) --------------
    if frontmatter_ok:
        # A material sentence must carry a [claim:] tag. A bold label alone does
        # NOT exempt it (otherwise any untagged claim could be laundered by
        # prefixing "**Inference:**"). The synthesizer always tags its labeled
        # lines, so legitimate output is unaffected.
        unsupported_sentences: list[str] = []
        for s in sentences:
            if s.has_tag:
                continue
            if _is_material(s, material_types):
                unsupported_sentences.append(s.text)
        if unsupported_sentences:
            unsupported.extend(unsupported_sentences)
            add(
                "material_claims_have_claim_ids",
                "fail",
                f"{len(unsupported_sentences)} material sentence(s) lack a [claim:] tag "
                "and are not labeled inference/speculation",
                unsupported_sentences,
            )
        else:
            add(
                "material_claims_have_claim_ids",
                "pass",
                "every material sentence carries a claim tag or label",
            )
    else:
        add("material_claims_have_claim_ids", "skip", "skipped: report front matter missing")

    # 5) supported_claims_have_source_cards ---------------------------------
    # A supported claim must cite at least one source card that ACTUALLY EXISTS in
    # the run (a dangling source_card_id string is not evidence). Iterate the raw
    # claims list so duplicate claim_ids cannot mask a bad entry.
    no_source: list[str] = []
    for c in claims:
        if c.get("status") != "supported":
            continue
        cited = [s.get("source_card_id") for s in (c.get("sources") or []) if s.get("source_card_id")]
        resolved = [sid for sid in cited if sid in source_index]
        if not resolved:
            cid = c.get("claim_id") or "<no-id>"
            detail = "no source_card_id" if not cited else "source_card_id(s) do not resolve to a card"
            no_source.append(f"{cid} ({detail})")
    if no_source:
        add(
            "supported_claims_have_source_cards",
            "fail",
            "supported claims without a resolvable source card: " + ", ".join(sorted(no_source)),
            sorted(no_source),
        )
    else:
        add(
            "supported_claims_have_source_cards",
            "pass",
            "all supported claims reference at least one existing source card",
        )

    # 6) source_cards_have_locators (warning) -------------------------------
    cited_source_ids: list[str] = []
    for c in claims:
        for s in c.get("sources", []) or []:
            sid = s.get("source_card_id")
            if sid and sid not in cited_source_ids:
                cited_source_ids.append(sid)
    no_locator = [
        sid
        for sid in cited_source_ids
        if sid in source_index and not source_index[sid]["has_locator"]
    ]
    if no_locator:
        add(
            "source_cards_have_locators",
            "warn",
            "cited source cards resolve but lack a locator: " + ", ".join(sorted(no_locator)),
            sorted(no_locator),
        )
    else:
        add(
            "source_cards_have_locators",
            "pass",
            "cited source cards that resolve have locators",
        )

    # 6b) exact_passage_present (PRD FR-3.1, AC-RFUP3-1/2) ------------------
    # Distinct from source_cards_have_locators above: a claim can have a
    # perfectly good locator (page/section reference) and still lack an exact
    # quoted passage a reader could match back to the source. This check
    # looks for at least one *quote* anchor (extracted_points[].quote) on any
    # of a supported claim's cited, resolvable source cards. Population is
    # "supported claims that cite >=1 source card" — a claim with zero cited
    # sources is already caught by supported_claims_have_source_cards above
    # and is out of scope here.
    #
    # Gating is mode-dependent (resolve_exact_passage_mode, TASK-2.1), with a
    # per-claim override layered on top (RFUP-1 P3-001, PRD FR-5/OQ-1):
    #   run's exact_passage_mode == "strict" -> every missing-anchor claim is
    #     strict, exactly as before this task.
    #   run's exact_passage_mode == "warn" (default) -> a claim is STILL
    #     bucketed as strict when claim_clinical_eligibility() (module-level,
    #     see its docstring for the full trigger and the fail-safe-to-
    #     non-eligible resolution) returns True for it. This is a per-claim
    #     override, not a global mode flip (AC-P3-2): the run's own
    #     exact_passage_mode value / result.exact_passage_mode is unchanged —
    #     only which bucket THIS claim's missing anchor lands in changes.
    #     Every other missing-anchor claim keeps today's warn behavior, so
    #     non-clinical warn-mode runs see zero regressions.
    #
    #   strict bucket -> CheckResult.status == "fail"; claim_ids added to
    #                     unsupported[] so they block publish exactly like
    #                     material_claims_have_claim_ids does above.
    #   warn bucket   -> CheckResult.status == "warn"; never added to
    #                     unsupported[]; passed/exit_code unchanged.
    missing_anchor_strict: list[str] = []
    missing_anchor_warn: list[str] = []
    for c in claims:
        if c.get("status") != "supported":
            continue
        cited = [s.get("source_card_id") for s in (c.get("sources") or []) if s.get("source_card_id")]
        if not cited:
            continue
        has_anchor = any(source_index.get(sid, {}).get("has_quote") for sid in cited)
        if has_anchor:
            continue
        cid = c.get("claim_id") or "<no-id>"
        if exact_passage_mode == "strict" or claim_clinical_eligibility(c, source_index):
            missing_anchor_strict.append(cid)
        else:
            missing_anchor_warn.append(cid)
    missing_anchor_strict = sorted(set(missing_anchor_strict))
    missing_anchor_warn = sorted(set(missing_anchor_warn) - set(missing_anchor_strict))
    # Dedicated, mode-independent violation list (AC-RFUP3-4/3-5, unchanged by
    # this task) — the union of both buckets, regardless of which bucket a
    # claim landed in.
    missing_anchor = sorted(set(missing_anchor_strict) | set(missing_anchor_warn))
    if missing_anchor_strict:
        detail = (
            "supported claims cite a source card but no exact-passage quote anchor "
            "resolves (strict — run default and/or per-claim clinical-eligibility "
            "override, RFUP-1 P3-001): " + ", ".join(missing_anchor_strict)
        )
        if missing_anchor_warn:
            detail += "; additional warn-only claim(s): " + ", ".join(missing_anchor_warn)
        add("exact_passage_present", "fail", detail, missing_anchor)
        unsupported.extend(f"[exact_passage] {cid}" for cid in missing_anchor_strict)
    elif missing_anchor_warn:
        add(
            "exact_passage_present",
            "warn",
            "supported claims cite a source card but no exact-passage quote anchor "
            "resolves: " + ", ".join(missing_anchor_warn),
            missing_anchor_warn,
        )
    else:
        add(
            "exact_passage_present",
            "pass",
            "every supported claim citing a source card has a matching exact-passage quote anchor",
        )

    # 6c) release_gate_judgment_basis_assessed (decisions-block OQ-6) -------
    # Bidirectional release gate: governance.py owns the boolean logic, this
    # is the verify-time CALLER (per the plan's resolution of OQ-6). Only
    # fires when the caller actually supplies evidence_judgment_bases — with
    # no evidence items passed (the default for every pre-existing caller),
    # this check is a no-op "skip" so behavior is unchanged. Blocks
    # disposition="commercial_release" when any evidence item's
    # judgment_basis is "unassessed"; the SAME unassessed item must never
    # block disposition="internal_capture" (release-gate asymmetry NFR).
    judgment_bases = tuple(evidence_judgment_bases or ())
    if judgment_bases:
        if release_gate_blocked_by_unassessed_judgment(
            judgment_bases, disposition=disposition
        ):
            add(
                "release_gate_judgment_basis_assessed",
                "fail",
                f"disposition={disposition!r} is blocked: at least one evidence "
                "item has judgment_basis: unassessed and release dispositions "
                "require every evidence item to be assessed first",
            )
        else:
            add(
                "release_gate_judgment_basis_assessed",
                "pass",
                f"no unassessed evidence item blocks disposition={disposition!r}",
            )
    else:
        add(
            "release_gate_judgment_basis_assessed",
            "skip",
            "skipped: no evidence_judgment_bases supplied to this verify_report call",
        )

    # 6d) pediatric_cds_schema_invalid (RFUP-1 P2-002, AC-P2-5/6/7) ----------
    # Structural-completeness hard-gate for the pediatric_cds evidence-card
    # extension block (schemas/pediatric_cds.schema.json, P2-001). Unlike
    # exact_passage_present above, this check is NOT scoped to claim-cited
    # cards — it scans every source card in the run's sources/ dir (already
    # loaded by _index_source_cards; AC-P2-6: zero new I/O) and validates any
    # extracted_points[].pediatric_cds entry that IS present. A point with no
    # pediatric_cds key (or an explicit null) is out of scope — absence of
    # the block is not itself a violation (AC-P2-4, enforced by P2-001's
    # schema-loader/validator boundary: only present blocks are ever passed
    # to _pediatric_cds_block_errors).
    #
    # _load_pediatric_cds_schema() is resolved unconditionally, before the
    # scan, so a broken schema artifact raises RFError on every `rf verify`
    # invocation (fail-closed) rather than being masked by a run with zero
    # pediatric_cds blocks.
    _load_pediatric_cds_schema()
    pediatric_cds_errors: list[str] = []
    for sid, entry in sorted(source_index.items()):
        for i, pt in enumerate(entry.get("points") or []):
            block = pt.get("pediatric_cds") if isinstance(pt, dict) else None
            if block is None:
                continue
            for err in _pediatric_cds_block_errors(block):
                pediatric_cds_errors.append(f"{sid}#extracted_points[{i}].pediatric_cds/{err}")
    if pediatric_cds_errors:
        add(
            "pediatric_cds_schema_invalid",
            "fail",
            f"{len(pediatric_cds_errors)} pediatric_cds block(s) failed schema validation: "
            + "; ".join(pediatric_cds_errors),
            pediatric_cds_errors,
        )
        unsupported.extend(f"[pediatric_cds_schema_invalid] {e}" for e in pediatric_cds_errors)
    else:
        add(
            "pediatric_cds_schema_invalid",
            "pass",
            "no pediatric_cds blocks present, or all present blocks are schema-valid",
        )

    # 6e) quote_fidelity (RFUP-1 P4-001/P4-002/P4-003, AC-P4-1..AC-P4-8) -----
    # New, dedicated check (services/quote_fidelity.py) comparing a claim's
    # cited-source extracted quote against that SAME source card's own
    # stored extracted_points[].quote text -- detecting extraction-time
    # corruption (e.g. a PMC fetch that silently strips a superscript,
    # ×10⁹/L -> ×10/L, before the quote was ever recorded) -- through the
    # module's two-stage normalization policy (P4-002): Stage 1 (NFKC,
    # whitespace collapsing, quote-mark style) is applied before diffing and
    # never itself triggers a flag; any residual difference after Stage 1 is
    # always material (flag/fail), never silently auto-corrected.
    #
    # Explicitly NOT check_anchor_hash_match (below, verify_draft's D13 #3
    # check): that check hashes a report-BUILDER-DRAFT block's OWN text
    # against a quote_text_hash recorded when a claim was linked, so it
    # detects *drift* -- the draft body edited after the quote was linked
    # (post-hoc tampering of an already-extracted quote, within one document,
    # over time). check_quote_fidelity instead compares two already-stored,
    # independently authored documents (the claim ledger and the cited
    # source card) exactly once, with nothing to "drift" -- either they agree
    # character-for-character (post Stage-1 normalization) or they never
    # did. No new fetch, no re-crawl, no I/O beyond source_index (already
    # loaded above); bounded by the cited card's already-bounded stored text
    # (AC-P4-3).
    #
    # qf_result.status is "pass" | "fail" | "error" | "warn" -- "error"
    # (AC-P4-4) means Stage-1 normalization itself raised for >=1 pair, so
    # fidelity could not be determined for it; "warn" (RFUP-1 P4-003,
    # AC-P4-7) means >=1 pair's cited card is extraction_status: locator_only
    # (nothing stored to diff against, but genuinely unverifiable rather
    # than confirmed pass/fail). All four are mutually distinguishable so a
    # caller can't misread "undetermined"/"unverifiable" as "verified". A
    # (claim, source) pair with nothing stored for any OTHER reason (not
    # locator_only) is still silently skipped here, unchanged from P4-001.
    #
    # Registered severity is "warning" (see _DEFAULT_VERIFIER_CHECKS above
    # and config/claim_policy.yaml's verifier_checks entry) so this check's
    # wiring cannot, on its own, regress any existing run's exit code
    # regardless of status -- error_fail (below) only triggers on
    # severity == "error", so an "error"- or "warn"-status quote_fidelity
    # finding is still surfaced (visible in checks[]/detail) without
    # flipping passed/exit_code. This module (verify_report) never calls
    # unsupported.extend(...) for quote_fidelity's findings of any status,
    # which is what keeps the locator_only warn (AC-P4-8) -- and every other
    # quote_fidelity status -- non-blocking; that is a property of this
    # call site never adding such a call, not of the check's severity alone.
    qf_result = check_quote_fidelity(claims, source_index)
    add("quote_fidelity", qf_result.status, qf_result.detail, qf_result.locations)

    # 7) inferences_have_basis ----------------------------------------------
    no_basis = []
    for c in claims:
        if c.get("status") != "inference":
            continue
        basis = c.get("inference_basis") or {}
        from_claims = basis.get("from_claims") if isinstance(basis, dict) else None
        if not from_claims:
            no_basis.append(c.get("claim_id") or "<no-id>")
    if no_basis:
        add(
            "inferences_have_basis",
            "fail",
            "inference claims missing inference_basis.from_claims: "
            + ", ".join(sorted(no_basis)),
            sorted(no_basis),
        )
    else:
        add(
            "inferences_have_basis",
            "pass",
            "all inference claims declare an inference basis",
        )

    # 8) <status>_is_labeled (inference / mixed / contradicted / speculation) -
    # spec §12.2 marks all four statuses report_label_required: true. A claim of
    # one of these statuses cited in the body MUST carry the corresponding bold
    # label, else it is presented to the reader as an unqualified finding. The
    # most dangerous case is a 'contradicted' claim (evidence disproves it) shown
    # without the "Contradicted / do not use as finding" caveat.
    for status, label_key in (
        ("inference", "inference"),
        ("mixed", "mixed"),
        ("contradicted", "contradicted"),
        ("speculation", "speculation"),
    ):
        check_id = f"{status}_is_labeled"
        status_claims = [c.get("claim_id") for c in claims if c.get("status") == status and c.get("claim_id")]
        if not frontmatter_ok:
            add(check_id, "skip", "skipped: report front matter missing")
            continue
        unlabeled: list[str] = []
        for cid in status_claims:
            carrying = [s for s in sentences if cid in s.tag_ids]
            if not carrying:
                continue  # claim not rendered in the body -> nothing to mislabel
            if not any(_LABEL_PATTERNS[label_key].search(s.text) for s in carrying):
                unlabeled.append(cid)
        if unlabeled:
            add(
                check_id,
                "fail",
                f"{status} claims rendered without the required label: " + ", ".join(sorted(unlabeled)),
                sorted(unlabeled),
            )
        else:
            add(check_id, "pass", f"{status} claims in the report are labeled (or absent)")

    # 9) unsupported_claims_block_publish -> exit 4 -------------------------
    # Iterate the RAW claims list (not the deduped map) so a duplicate claim_id
    # cannot overwrite and hide an unsupported entry.
    unsupported_ledger_claims = [c for c in claims if c.get("status") == "unsupported"]
    unsupported_ledger = sorted({c.get("claim_id") or "<no-id>" for c in unsupported_ledger_claims})
    if unsupported_ledger_claims:
        add(
            "unsupported_claims_block_publish",
            "fail",
            "ledger contains unsupported claims: " + ", ".join(unsupported_ledger),
            unsupported_ledger,
        )
        # Record them in unsupported[] for the result summary.
        for c in unsupported_ledger_claims:
            cid = c.get("claim_id") or "<no-id>"
            txt = c.get("text") or cid
            unsupported.append(f"[{cid}] {txt}")
    else:
        add(
            "unsupported_claims_block_publish",
            "pass",
            "no unsupported claims in the ledger",
        )

    # 10) work_sensitive_claims_block_public_report -> exit 3 (GOVERNANCE) --
    governance_violation = False
    if report_sensitivity == "public":
        leaking = [
            sid
            for sid in cited_source_ids
            if sid in source_index
            and source_index[sid]["sensitivity"] in {"work_sensitive", "client_sensitive"}
        ]
        if leaking:
            governance_violation = True
            add(
                "work_sensitive_claims_block_public_report",
                "fail",
                "public report cites work/client-sensitive source cards: "
                + ", ".join(sorted(leaking)),
                sorted(leaking),
            )
        else:
            add(
                "work_sensitive_claims_block_public_report",
                "pass",
                "no sensitive source cards leak into the public report",
            )
    else:
        add(
            "work_sensitive_claims_block_public_report",
            "pass",
            f"report sensitivity is {report_sensitivity!r}; public-leak check not applicable",
        )

    # --- Exit-code precedence ---------------------------------------------
    schema_fail = any(c.id == "report_has_frontmatter" and c.status == "fail" for c in checks)
    error_fail = any(c.severity == "error" and c.status == "fail" for c in checks)
    unsupported_present = bool(unsupported)

    if schema_fail:
        exit_code = int(ExitCode.SCHEMA)
    elif governance_violation:
        exit_code = int(ExitCode.GOVERNANCE)
    elif unsupported_present and fail_on_unsupported:
        exit_code = int(ExitCode.UNSUPPORTED)
    elif error_fail:
        # Any other error-severity failure (e.g. all_claim_ids_exist,
        # supported_claims_have_source_cards, inferences_have_basis,
        # speculation_is_labeled) blocks publication via SCHEMA-class failure.
        exit_code = int(ExitCode.SCHEMA)
    else:
        exit_code = int(ExitCode.OK)

    passed = exit_code == int(ExitCode.OK)

    # Human-review surfacing: expose the flag, do NOT change the exit code here
    # (the CLI maps that to ExitCode.HUMAN_REVIEW when no approval exists).
    human_review_required = _intent_requires_review(ledger, paths)

    # --- Persist verification.yaml ----------------------------------------
    record = {
        "rf_schema_version": RF_SCHEMA_VERSION,
        "run_id": run_id,
        "passed": passed,
        "exit_code": exit_code,
        "generated_at": now_iso(),
        "report_path": str(rpath) if rpath else None,
        "claim_ledger_path": str(lpath),
        "human_review_required": human_review_required,
        "checks": [
            {
                "id": c.id,
                "severity": c.severity,
                "status": c.status,
                "detail": c.detail,
                "locations": c.locations,
            }
            for c in checks
        ],
        "unsupported": list(unsupported),
        # AC-RFUP3-4/AC-RFUP3-5: dedicated, mode-independent violation list
        # (see missing_anchor above) — distinct key from the
        # source_cards_have_locators check's own locations. Always present
        # (empty list when there are zero violations) to match this dict's
        # existing convention for optional list fields (e.g. "unsupported").
        "exact_passage_violations": list(missing_anchor),
    }
    dump_yaml(record, rp.verification)

    # --- Update the ledger's verification_status --------------------------
    if lpath.exists() and isinstance(ledger, dict) and ledger:
        ledger["verification_status"] = "passed" if passed else "failed"
        try:
            dump_yaml(ledger, lpath)
        except Exception:  # noqa: BLE001 - never fail verification on a write error
            pass

    _trace(rp, stage="verify", run_id=run_id, exit_code=exit_code, passed=passed)

    return VerificationResult(
        run_id=run_id,
        passed=passed,
        exit_code=exit_code,
        checks=checks,
        verification_path=rp.verification,
        unsupported=list(unsupported),
        human_review_required=human_review_required,
        exact_passage_mode=exact_passage_mode,
        exact_passage_violations=list(missing_anchor),
    )


def _intent_requires_review(ledger: dict[str, Any], paths: FoundryPaths) -> bool:
    """Best-effort: does the linked intent require human review (no approval)?"""

    intent_id = ledger.get("intent_id") if isinstance(ledger, dict) else None
    if not intent_id:
        return False
    candidate = paths.intents_active / f"{intent_id}.yaml"
    intent: dict[str, Any] = {}
    if candidate.exists():
        data = load_yaml(candidate)
        intent = data if isinstance(data, dict) else {}
    else:
        for p in paths.intents.rglob(f"{intent_id}.yaml"):
            data = load_yaml(p)
            intent = data if isinstance(data, dict) else {}
            break
    gov = intent.get("governance", {}) if isinstance(intent, dict) else {}
    return bool(isinstance(gov, dict) and gov.get("requires_human_review"))


# ---------------------------------------------------------------------------
# Report Builder draft checks (public-multiuser-release P3 Wave D — plan D13)
# ---------------------------------------------------------------------------
# Deterministic, standalone checks over a builder draft's in-memory state
# (blocks[]/claim_links[]/source_links[]) — the equivalent gate to
# verify_report() above, but for Report Builder drafts (services.builder_
# service) rather than a run's flat report_draft.md. verify_draft() is what
# Wave E wires to `rf report verify` + the publish-preview endpoint (spec §7
# Verification Additions, §11 sensitivity gates).

_DRAFT_CLAIM_TAG_RE = re.compile(r"\[claim:(clm_\w+)\]")

# Block types whose markdown is expected to carry material, claim-linkable
# prose (spec §7: "every material paragraph"). Headings/tables/quotes are not
# gated by this check — a quote block's provenance belongs in source_links,
# not claim_links.
_SUPPORT_GATED_BLOCK_TYPES = frozenset({"paragraph", "evidence_summary"})


def check_paragraph_has_support(blocks: list[dict[str, Any]]) -> CheckResult:
    """D13 #1 — every material paragraph/evidence_summary block has >=1 claim
    link, or is explicitly marked non-material (``materiality``
    ``narrative``/``background``)."""

    offenders = sorted(
        b["block_id"]
        for b in blocks
        if b.get("block_type") in _SUPPORT_GATED_BLOCK_TYPES
        and b.get("materiality", "material") == "material"
        and not b.get("linked_claim_ids")
    )
    if offenders:
        return CheckResult(
            id="paragraph_has_support",
            severity="error",
            status="fail",
            detail=(
                f"{len(offenders)} material block(s) have no claim link and are not "
                "marked narrative/background"
            ),
            locations=offenders,
        )
    return CheckResult(
        id="paragraph_has_support",
        severity="error",
        status="pass",
        detail="every material paragraph/evidence_summary block has a claim link or is exempt",
        locations=[],
    )


def check_claim_tags_resolve(
    blocks: list[dict[str, Any]], known_claim_ids: set[str]
) -> CheckResult:
    """D13 #2 — every ``[claim:clm_xxx]`` tag in block markdown resolves.

    ``known_claim_ids`` is caller-supplied (the draft's own resolved
    claim_links, or a richer cross-run/catalog resolution from Wave E) so
    this check stays a pure function with no file or network I/O of its own.
    """

    unresolved: set[str] = set()
    for block in blocks:
        for m in _DRAFT_CLAIM_TAG_RE.finditer(block.get("markdown") or ""):
            cid = m.group(1)
            if cid not in known_claim_ids:
                unresolved.add(cid)
    if unresolved:
        return CheckResult(
            id="claim_tags_resolve",
            severity="error",
            status="fail",
            detail="unresolved [claim:] tags: " + ", ".join(sorted(unresolved)),
            locations=sorted(unresolved),
        )
    return CheckResult(
        id="claim_tags_resolve",
        severity="error",
        status="pass",
        detail="every [claim:] tag resolves to a known claim",
        locations=[],
    )


def check_anchor_hash_match(
    blocks: list[dict[str, Any]], claim_links: list[dict[str, Any]]
) -> CheckResult:
    """D13 #3 — every claim_link's ``quote_text_hash`` still matches the
    current text at its stored span (drift detection). Reuses the
    ``export_service`` D8 hash recipe so builder anchors and P2's
    ``report_anchors`` share one hash contract — see
    ``builder_service.add_claim_link`` for where the hash is first computed.
    """

    # Local import: internal reuse of P2's private hash/normalize helpers
    # (not re-exported — see builder_service module docstring for the same
    # convention). Deferred here purely to keep this module's top-level
    # imports limited to the two public export_service names it always needs.
    from .export_service import _anchor_text_hash as _hash
    from .export_service import _normalize_anchor_text as _normalize

    blocks_by_id = {b["block_id"]: b for b in blocks}
    stale: list[str] = []
    for link in claim_links:
        block = blocks_by_id.get(link.get("block_id"))
        stored_hash = link.get("quote_text_hash")
        if block is None or stored_hash is None:
            continue
        normalized = _normalize(block.get("markdown") or "")
        start, end = link.get("span_start"), link.get("span_end")
        substring = (
            normalized[start:end]
            if isinstance(start, int) and isinstance(end, int)
            else normalized
        )
        if _hash(substring) != stored_hash:
            stale.append(link.get("claim_link_id") or link.get("claim_id") or "<unknown>")
    if stale:
        return CheckResult(
            id="anchor_hash_match",
            severity="warning",
            status="fail",
            detail=f"{len(stale)} claim link(s) point at drifted text: " + ", ".join(sorted(stale)),
            locations=sorted(stale),
        )
    return CheckResult(
        id="anchor_hash_match",
        severity="warning",
        status="pass",
        detail="every claim link's anchored text is unchanged since it was linked",
        locations=[],
    )


def check_report_body_sensitivity(
    paths: FoundryPaths,
    blocks: list[dict[str, Any]],
    source_links: list[dict[str, Any]],
    *,
    claim_links: list[dict[str, Any]] | None = None,
    source_run_id: str | None = None,
    sensitivity_threshold: str | None = None,
) -> CheckResult:
    """D13 #4 — a public/shared draft body must not embed a raw quote from a
    source whose sensitivity exceeds the resolved threshold (spec §11:
    "Public/shared reports must fail verification if raw sensitive quotes
    appear outside governed source evidence fields"). Fail-closed: an
    unrecognized sensitivity label ranks stricter than every known level, so
    it can never silently pass.

    R2 CRITICAL fix: this check used to only scan source cards that already
    had a matching ``source_links[]`` entry — i.e. it only caught a *linked*
    sensitive quote. Spec §11's actual danger case is the opposite: raw
    sensitive text pasted into a block with NO governance trail at all (no
    claim_link, no source_link) sailed straight through. To close that hole,
    the candidate quote corpus is drawn from every source card in every run
    this draft is *reachable* from — its own ``source_run_id`` (set when the
    draft was created ``from_run``), every ``claim_links[].source_run_id``,
    and every ``source_links[].run_id`` — not merely the source cards an
    author happened to attach a ``source_link`` to. An explicit link is still
    the common case and remains fully covered (its ``run_id`` is one of the
    reachable runs), but it is no longer a precondition for detection.
    """

    threshold = sensitivity_threshold or DEFAULT_THRESHOLD
    threshold_rank = SENSITIVITY_ORDER.get(threshold, len(SENSITIVITY_ORDER))
    body_text = "\n".join(b.get("markdown") or "" for b in blocks)

    run_ids: set[str] = set()
    if source_run_id:
        run_ids.add(source_run_id)
    for link in source_links:
        rid = link.get("run_id")
        if rid:
            run_ids.add(rid)
    for cl in claim_links or []:
        rid = cl.get("source_run_id")
        if rid:
            run_ids.add(rid)

    leaks: list[str] = []
    for run_id in sorted(run_ids):
        rp = paths.run_paths(run_id)
        sources_dir = rp.sources
        if not sources_dir.exists():
            continue
        for card_path in sorted(sources_dir.glob("*.md")):
            try:
                meta, _ = load_md(card_path)
            except Exception:  # noqa: BLE001 - an unreadable card is not a leak signal
                continue
            source_card_id = str(meta.get("source_card_id") or card_path.stem)

            card_rank = SENSITIVITY_ORDER.get(str(meta.get("sensitivity")), len(SENSITIVITY_ORDER))
            points = [p for p in (meta.get("extracted_points") or []) if isinstance(p, dict)]
            point_rank = card_rank
            for p in points:
                if p.get("sensitivity"):
                    point_rank = max(point_rank, SENSITIVITY_ORDER.get(str(p["sensitivity"]), len(SENSITIVITY_ORDER)))
            effective_rank = max(card_rank, point_rank)
            if effective_rank <= threshold_rank:
                continue

            # Sensitive source — only a *raw quote leak* is a failure; a
            # governed reference (via claim_links/[claim:] tags, redacted at
            # export time) is not.
            quotes = [str(p.get("quote")) for p in points if p.get("quote")]
            if any(q and q in body_text for q in quotes):
                leaks.append(f"{source_card_id} (run {run_id})")

    if leaks:
        return CheckResult(
            id="report_body_sensitivity",
            severity="error",
            status="fail",
            detail=(
                f"draft body embeds raw sensitive-source text above threshold {threshold!r}: "
                + ", ".join(sorted(leaks))
            ),
            locations=sorted(leaks),
        )
    return CheckResult(
        id="report_body_sensitivity",
        severity="error",
        status="pass",
        detail=f"no raw sensitive-source text embedded above threshold {threshold!r}",
        locations=[],
    )


def check_report_body_sensitivity_global(
    paths: FoundryPaths,
    blocks: list[dict[str, Any]],
    global_source_index: dict[str, tuple[str, str]],
    *,
    sensitivity_threshold: str | None = None,
) -> CheckResult:
    """D13 global sensitivity check — scans the draft body against a
    workspace-wide source index, closing the blank-origin-draft residual gap.

    Complements (does not replace) :func:`check_report_body_sensitivity`.
    The per-run check covers drafts with declared source runs; this check
    closes the residual case where ``run_ids`` is empty (no ``source_run_id``,
    no ``source_links``, no ``claim_links``) so the per-run check exits early
    without scanning anything, and also the cross-run-quote case where a quote
    originates from a run not listed in the draft's declared sources.

    Fail-closed: any sentinel entry in ``global_source_index`` (added by
    :func:`build_global_source_index` when a run's ``sources/`` dir was
    unreadable) immediately fails the check — an unverifiable run cannot be
    confirmed safe.
    """
    threshold = sensitivity_threshold or DEFAULT_THRESHOLD
    threshold_rank = SENSITIVITY_ORDER.get(threshold, len(SENSITIVITY_ORDER))
    body_text = "\n".join(b.get("markdown") or "" for b in blocks)

    # Fail-closed: unverifiable runs block immediately.
    sentinel_keys = [k for k in global_source_index if k.startswith(_IO_ERROR_SENTINEL_PREFIX)]
    if sentinel_keys:
        unverifiable_runs = sorted({global_source_index[k][0] for k in sentinel_keys})
        return CheckResult(
            id="report_body_sensitivity_global",
            severity="error",
            status="fail",
            detail=(
                "cannot verify body sensitivity — unreadable sources/ dir in run(s): "
                + ", ".join(unverifiable_runs)
            ),
            locations=unverifiable_runs,
        )

    # Group above-threshold source_card_ids by run_id so each run's sources/
    # directory is read at most once.
    runs_to_check: dict[str, set[str]] = {}
    for sid, (run_id, sensitivity) in global_source_index.items():
        card_rank = SENSITIVITY_ORDER.get(sensitivity, len(SENSITIVITY_ORDER))
        if card_rank > threshold_rank:
            runs_to_check.setdefault(run_id, set()).add(sid)

    leaks: list[str] = []
    for run_id, card_ids in sorted(runs_to_check.items()):
        sources_dir = paths.runs / run_id / "sources"
        if not sources_dir.exists():
            continue
        for card_path in sorted(sources_dir.glob("*.md")):
            try:
                meta, _ = load_md(card_path)
            except Exception:  # noqa: BLE001 - a broken card is not a leak signal
                continue
            sid = str(meta.get("source_card_id") or card_path.stem)
            if sid not in card_ids:
                continue
            # Compute effective rank (card level + per-point sensitivity) to
            # match the same logic used by check_report_body_sensitivity.
            card_rank = SENSITIVITY_ORDER.get(str(meta.get("sensitivity")), len(SENSITIVITY_ORDER))
            points = [p for p in (meta.get("extracted_points") or []) if isinstance(p, dict)]
            point_rank = card_rank
            for p in points:
                if p.get("sensitivity"):
                    point_rank = max(
                        point_rank,
                        SENSITIVITY_ORDER.get(str(p["sensitivity"]), len(SENSITIVITY_ORDER)),
                    )
            effective_rank = max(card_rank, point_rank)
            if effective_rank <= threshold_rank:
                continue
            quotes = [str(p.get("quote")) for p in points if p.get("quote")]
            if any(q and q in body_text for q in quotes):
                leaks.append(f"{sid} (run {run_id})")

    if leaks:
        return CheckResult(
            id="report_body_sensitivity_global",
            severity="error",
            status="fail",
            detail=(
                f"draft body embeds raw sensitive-source text above threshold {threshold!r} "
                "(global scan): " + ", ".join(sorted(leaks))
            ),
            locations=sorted(leaks),
        )
    return CheckResult(
        id="report_body_sensitivity_global",
        severity="error",
        status="pass",
        detail=f"no raw sensitive-source text embedded above threshold {threshold!r} (global scan)",
        locations=[],
    )


def verify_draft(
    paths: FoundryPaths,
    report_draft_id: str,
    *,
    known_claim_ids: set[str] | None = None,
    sensitivity_threshold: str | None = None,
) -> VerificationResult:
    """Run every D13 check against a Report Builder draft (spec §7/§8/§11).

    Loads the draft via ``builder_service`` (deferred import — breaks the
    module-load cycle, since ``builder_service`` never imports this
    function). ``known_claim_ids`` lets a caller that already resolved the
    draft's linked runs/catalog items pass that resolution in directly; when
    omitted, every claim_link the draft itself believes resolved
    (``link_status == "linked"``) is used, so a stray untracked ``[claim:]``
    tag is still caught by :func:`check_claim_tags_resolve`.

    Reuses :class:`VerificationResult`'s ``run_id`` field to carry
    *report_draft_id* — a deliberate reuse (not a run) so run-report and
    builder-draft verification share one result vocabulary; writes
    ``<draft_dir>/verification.yaml`` (a derived, recomputable artifact, not
    draft truth — see ``builder_service`` module docstring).
    """

    from .builder_service import load_draft  # deferred: breaks the import cycle

    draft = load_draft(paths, report_draft_id)
    blocks = draft.get("blocks") or []
    claim_links = draft.get("claim_links") or []
    source_links = draft.get("source_links") or []

    if known_claim_ids is None:
        known_claim_ids = {cl["claim_id"] for cl in claim_links if cl.get("link_status") == "linked"}

    resolved_threshold = sensitivity_threshold or draft.get("sensitivity")
    global_source_index = build_global_source_index(paths)
    checks = [
        check_paragraph_has_support(blocks),
        check_claim_tags_resolve(blocks, known_claim_ids),
        check_anchor_hash_match(blocks, claim_links),
        check_report_body_sensitivity(
            paths,
            blocks,
            source_links,
            claim_links=claim_links,
            source_run_id=draft.get("source_run_id"),
            sensitivity_threshold=resolved_threshold,
        ),
        check_report_body_sensitivity_global(
            paths,
            blocks,
            global_source_index,
            sensitivity_threshold=resolved_threshold,
        ),
    ]

    error_fail = any(c.severity == "error" and c.status == "fail" for c in checks)
    passed = not error_fail
    exit_code = int(ExitCode.OK) if passed else int(ExitCode.UNSUPPORTED)

    record = {
        "rf_schema_version": RF_SCHEMA_VERSION,
        "report_draft_id": report_draft_id,
        "passed": passed,
        "exit_code": exit_code,
        "generated_at": now_iso(),
        "checks": [
            {
                "id": c.id,
                "severity": c.severity,
                "status": c.status,
                "detail": c.detail,
                "locations": c.locations,
            }
            for c in checks
        ],
    }
    verification_path = paths.report_draft_dir(report_draft_id) / "verification.yaml"
    dump_yaml(record, verification_path)

    return VerificationResult(
        run_id=report_draft_id,
        passed=passed,
        exit_code=exit_code,
        checks=checks,
        verification_path=verification_path,
        unsupported=[c.detail for c in checks if c.status == "fail"],
    )


__all__ = [
    "CheckResult",
    "VerificationResult",
    "verify_report",
    "check_paragraph_has_support",
    "check_claim_tags_resolve",
    "check_anchor_hash_match",
    "check_report_body_sensitivity",
    "build_global_source_index",
    "check_report_body_sensitivity_global",
    "verify_draft",
]
