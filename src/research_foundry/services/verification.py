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

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import FoundryConfig
from ..errors import ExitCode
from ..frontmatter import load_md
from ..ids import now_iso
from ..paths import FoundryPaths
from ..yamlio import append_jsonl, dump_yaml, load_yaml

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
    """Map source_card_id -> {sensitivity, has_locator, path} for the run."""

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
        index[sid] = {
            "sensitivity": meta.get("sensitivity"),
            "has_locator": has_locator,
            "path": str(p),
        }
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


def _resolve_report_path(rp, report_path: Path | None) -> Path | None:
    if report_path is not None:
        p = Path(report_path)
        return p if p.exists() else None
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
    paths: FoundryPaths | None = None,
) -> VerificationResult:
    """Verify a run's report against its claim ledger (spec §12.3).

    Returns a :class:`VerificationResult` whose ``exit_code`` is one of the
    stable :class:`~research_foundry.errors.ExitCode` integers, following the
    documented precedence. Writes ``reviews/verification.yaml`` and updates the
    ledger's ``verification_status``.
    """

    paths = paths or FoundryPaths.discover()
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    material_types, check_specs = _load_policy(paths)

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
    rpath = _resolve_report_path(rp, report_path)
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
    lpath = Path(claim_ledger_path) if claim_ledger_path else rp.claim_ledger
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


__all__ = ["CheckResult", "VerificationResult", "verify_report"]
