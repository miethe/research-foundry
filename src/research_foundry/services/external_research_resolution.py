"""External Research Report Interchange (ERI) v1 — Phase 4: exact
resolution, quarantine, and promotion (ERI-4.1, ERI-4.3, ERI-4.4).

Plugs into ``external_research_interchange.py``'s injectable
``resolve_source``/``resolve_candidate`` seam (that module's Phase 2 scope
is staging/receipt mechanics only; it introduces no second source-edition,
passage, source-assertion, extraction, or citation-tuple authority — see its
module docstring and contract §3.5). This module is the real acquisition/
resolution pipeline Phase 2's conservative defaults explicitly deferred.

Three responsibilities, matching the plan's task breakdown:

* **ERI-4.1 (normalization).** :func:`normalize_source`/:func:`normalize_candidate`
  convert untrusted packet records into typed dataclasses, touching only
  the fields the schemas define. Every value stays inert data (contract
  §4.1) — none of it is ever used to build a route, path, command, schema
  selector, or execution argument; ``extensions``/``selector`` are carried
  opaquely and are compared, never trusted, when they resemble an
  authoritative claim (see ``_selector_hint`` / the "vendor-provided ID
  conflict" handling in :meth:`ExternalResearchResolver._resolve_candidate_impl`).
* **ERI-4.2 (wired here, built in ``source_acquisition_policy.py``).** All
  network acquisition goes through :func:`source_acquisition_policy.acquire`,
  which owns the complete HTTP lifecycle end to end (contract §4.2.0). This
  module never opens a socket, never imports ``urllib``/``httpx`` for
  acquisition, and never hands a locator to any other extraction/provider
  call (contract §3.2's frozen v1 entry points: ``extract_pdf(bytes)`` plus
  this module's own net-new byte-accepting text/HTML extractor,
  :func:`extract_bytes` — never ``run_search``/``_first_extraction_provider``).
* **ERI-4.3 (exact passage resolution).** Every candidate quote is matched
  against the SAME bound edition via ``AssertionRegistry.find_exact_passages``
  — zero/multiple/mismatched-edition all quarantine; there is no
  newer-edition or similarity fallback (mirrors
  ``find_exact_passages``'s own docstring invariant, contract §3.3).
* **ERI-4.4 (promotion seam).** :func:`default_promote` stages a
  ``passage_resolved`` candidate into a run's source cards
  (``source_cards.ingest_source``) when ``target_run_id`` is set — it never
  self-assigns ``verified``. Only the existing RF verifier/materializer
  (``verify_report`` + ``assertion_materialization.py``) holds that
  authority (contract §2.4.1); this module adds no second decision-maker.

**Cross-workspace safety.** :class:`ExternalResearchResolver` is bound to
exactly one ``workspace_id`` at construction and reads/writes only that
workspace's ``AssertionRegistry`` root. Every resolve call additionally
re-checks the caller-supplied :class:`ResolutionContext.workspace_id`
against the resolver's own bound workspace before touching the registry —
never derived from packet content (contract §4.1) — and denies
``cross_workspace_denied`` on any mismatch (a resolver construction/wiring
defect, not a packet-triggerable condition, but cheap and worth catching).

**Dry-run safety (cross-phase interlock note for Phase 5/ERI-5.3).**
``external_research_interchange.stage(..., dry_run=True)`` invokes the
injected ``resolve_source``/``resolve_candidate`` callables directly with no
``dry_run`` signal threaded through ``ResolutionContext`` — that dataclass
carries only ``workspace_id``/``target_run_id``/``policy`` and this module
must not modify ``external_research_interchange.py`` to add one. Because
Phase 2's own default resolvers are pure functions with no I/O, this was
harmless for Phase 2 but would NOT be harmless for Phase 4's real resolver,
which performs live network acquisition and registry writes. This module
closes that gap at its OWN boundary: :class:`ExternalResearchResolver`
takes its own ``dry_run`` constructor flag. When true, it performs every
read-only step (authorization computation, existing-edition reuse via
``find_exact_passages``) but skips fresh acquisition, passage registration,
and promotion staging entirely — reporting the same conservative floor
Phase 2's default resolvers report for anything it cannot determine without
writing. **Phase 5's CLI must construct two resolver instances (or one
resolver whose ``dry_run`` flag mirrors ``--dry-run``) and pass the
dry-run instance's bound methods whenever it calls ``stage(dry_run=True)``**
— passing a live (``dry_run=False``) resolver into a dry-run ``stage()``
call would silently perform real acquisition/writes despite the caller
asking for a dry run. Recorded here so Phase 5 does not rediscover it.

**``canonical_refs`` / ``effect_digest`` gap (cross-phase interlock note).**
``ExternalResearchInterchange._effect_digest`` (private, not importable) and
the frozen ``ActionResolution`` dataclass it consumes hardcode
``canonical_refs: {}`` for every action — Phase 2's own docstring says so
explicitly, because Phase 2 predates Phase 4's acquisition/materialization
capability. ``ActionResolution`` has no field to carry the real downstream
refs (``source_edition_id``/``passage_id``/``source_card_id``) this module
now produces, and this module must not edit ``external_research_interchange.py``
to add one. :class:`ResolvedActionResolution` (an additive
``ActionResolution`` subclass with a ``canonical_refs`` field) carries that
information forward without discarding it, but until a future patch threads
it into ``_effect_digest``, the persisted ``effect_digest`` for every
``passage_resolved``/staged action does not yet vary with which edition/
passage/source-card it actually bound — a genuine, currently-unclosed gap
in replay-integrity precision (not a security hole: ``action_id`` already
binds each effect to exactly one action, contract §1.3a) that the next pass
touching ``external_research_interchange.py`` should close.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from ..errors import NotFoundError
from ..paths import FoundryPaths
from .assertion_registry import AssertionRegistry
from .external_research_interchange import (
    CANDIDATE_REASON_CODES,
    SOURCE_REASON_CODES,
    ActionResolution,
    ResolutionContext,
)
from .extractors.pdf_extractor import extract_pdf
from .sensitivity import SENSITIVITY_RANK
from .source_acquisition_policy import AcquisitionOutcome
from .source_acquisition_policy import acquire as _default_acquire
from .source_cards import ingest_source as _default_ingest_source

# ---------------------------------------------------------------------------
# ERI-4.1: normalization
# ---------------------------------------------------------------------------

_ALLOWED_ACCESS_STATUSES = frozenset({"open-access", "public-domain", "paywalled", "unknown"})
_ALLOWED_RELATIONS = frozenset({"supports", "contradicts", "context", "unknown", None})
_ALLOWED_CLASSIFICATIONS = frozenset({"assertion", "inference", "annotation"})


@dataclass(frozen=True)
class NormalizedLocator:
    doi: str | None
    url: str | None

    @property
    def present(self) -> bool:
        return bool(self.doi or self.url)

    @property
    def identity_key(self) -> str | None:
        """Deterministic key AssertionRegistry hashes into a workspace-scoped
        ``source_id`` — never a raw filesystem path or route (contract
        §4.1a; the only permitted sink for a locator besides the
        acquisition pipeline is this kind of fixed, non-dynamic identity
        derivation).
        """

        if self.url:
            return f"url:{self.url}"
        if self.doi:
            return f"doi:{self.doi}"
        return None


@dataclass(frozen=True)
class NormalizedSource:
    source_id: str
    title: str | None
    locator: NormalizedLocator
    access_status: str
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedCandidate:
    candidate_id: str
    statement: str
    classification: str
    source_refs: tuple[str, ...]
    relation: str | None
    quote: str | None
    selector: Mapping[str, Any] | None
    extensions: Mapping[str, Any]
    producer_confidence: float | None = None


def normalize_source(record: Mapping[str, Any]) -> NormalizedSource | None:
    """ERI-4.1: typed, inert-data view of one ``sources.yaml`` record.

    Returns ``None`` for a structurally unusable record (defensive only —
    schema validation has already run by the time a resolver sees this).
    Every field is read, never interpolated into a route/path/command; see
    the module docstring's inert-data note.
    """

    if not isinstance(record, Mapping):
        return None
    source_id = record.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        return None
    access_status = record.get("access_status")
    if access_status not in _ALLOWED_ACCESS_STATUSES:
        return None
    locator_raw = record.get("locator")
    locator_map = locator_raw if isinstance(locator_raw, Mapping) else {}
    doi = locator_map.get("doi")
    url = locator_map.get("url")
    extensions_raw = record.get("extensions")
    extensions = extensions_raw if isinstance(extensions_raw, Mapping) else {}
    title = record.get("title")
    return NormalizedSource(
        source_id=source_id,
        title=title if isinstance(title, str) else None,
        locator=NormalizedLocator(doi=doi if isinstance(doi, str) else None, url=url if isinstance(url, str) else None),
        access_status=access_status,
        extensions=extensions,
    )


def normalize_candidate(record: Mapping[str, Any]) -> NormalizedCandidate | None:
    """ERI-4.1: typed, inert-data view of one ``assertion_candidates.yaml``
    record. ``selector`` is carried opaquely — it is compared against
    independently-resolved results for safety (never trusted as a route or
    an authoritative claim); see the "vendor-provided ID conflict" handling
    in :meth:`ExternalResearchResolver._resolve_candidate_impl`.
    """

    if not isinstance(record, Mapping):
        return None
    candidate_id = record.get("candidate_id")
    statement = record.get("statement")
    classification = record.get("classification")
    if not isinstance(candidate_id, str) or not candidate_id:
        return None
    if not isinstance(statement, str) or not statement:
        return None
    if classification not in _ALLOWED_CLASSIFICATIONS:
        return None
    refs_raw = record.get("source_refs")
    refs = tuple(r for r in refs_raw if isinstance(r, str)) if isinstance(refs_raw, list) else ()
    relation = record.get("relation")
    if relation not in _ALLOWED_RELATIONS:
        relation = None
    quote = record.get("quote")
    selector_raw = record.get("selector")
    extensions_raw = record.get("extensions")
    confidence_raw = record.get("producer_confidence")
    return NormalizedCandidate(
        candidate_id=candidate_id,
        statement=statement,
        classification=classification,
        source_refs=refs,
        relation=relation,
        quote=quote if isinstance(quote, str) and quote else None,
        selector=selector_raw if isinstance(selector_raw, Mapping) else None,
        extensions=extensions_raw if isinstance(extensions_raw, Mapping) else {},
        producer_confidence=confidence_raw if isinstance(confidence_raw, (int, float)) else None,
    )


@dataclass(frozen=True)
class CitationTuple:
    """Optional intake-citation-tuple input (ERI-4.1's "optional intake
    citation tuples"). Mirrors the field shape documented by the draft,
    unexecuted Intake Citation Adapters contract
    (``docs/project_plans/feature_contracts/features/intake-citation-adapters.md``,
    ``status: draft``, confirmed on this tree to define no
    ``CitationTuple``/adapter symbol anywhere) purely as a naming
    convention — this module calls no adapter or dedup module from that
    contract, because none exists on this tree (contract §3.4). A future
    Intake Citation Adapters integration can supply this same shape without
    a rename.
    """

    span: str
    source: str
    relation: str | None = None
    confidence: float | None = None


def normalize_citation_tuple(tuple_like: CitationTuple | Mapping[str, Any], *, candidate_id: str) -> NormalizedCandidate | None:
    """Map an intake citation tuple onto the same :class:`NormalizedCandidate`
    shape packet-declared candidates use, so callers get one resolution path
    regardless of origin. ``candidate_id`` is caller-supplied (packet-local
    IDs are producer data; a citation tuple has none, so the caller mints a
    stable one) — never derived from tuple content.
    """

    span: Any
    source: Any
    relation: Any
    confidence: Any
    if isinstance(tuple_like, CitationTuple):
        span, source, relation, confidence = tuple_like.span, tuple_like.source, tuple_like.relation, tuple_like.confidence
    elif isinstance(tuple_like, Mapping):
        span, source = tuple_like.get("span"), tuple_like.get("source")
        relation, confidence = tuple_like.get("relation"), tuple_like.get("confidence")
    else:
        return None
    if not isinstance(span, str) or not span or not isinstance(source, str) or not source:
        return None
    if relation not in _ALLOWED_RELATIONS:
        relation = None
    return NormalizedCandidate(
        candidate_id=candidate_id,
        statement=span,
        classification="assertion",
        source_refs=(source,),
        relation=relation,
        quote=span,
        selector=None,
        extensions={},
        producer_confidence=confidence if isinstance(confidence, (int, float)) else None,
    )


# ---------------------------------------------------------------------------
# ERI-4.1's byte-accepting, network-free extractor (contract §3.2/§4.2.9,
# audit #1/#19) -- structurally mirrors extract_pdf(bytes) -> result.
# ---------------------------------------------------------------------------

_MAX_EXTRACT_CHARS = 100_000
STATUS_FULL_TEXT = "full_text"
STATUS_PARTIAL = "partial"
STATUS_LOCATOR_ONLY = "locator_only"


class _VisibleTextExtractor(HTMLParser):
    """Minimal, stdlib-only HTML-to-text: drops script/style content and
    tags, keeps everything else as inert display text. Never executes
    anything from the markup — this is text extraction, not rendering.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: D401
        return None

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self._chunks.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self._chunks).split())


@dataclass(frozen=True)
class ExtractionResult:
    text: str | None
    status: str
    media_type: str
    diagnostics: tuple[str, ...] = ()


def extract_bytes(data: bytes, content_type: str | None) -> ExtractionResult:
    """Never raises (mirrors :func:`extract_pdf`'s convention). Dispatches to
    the existing zero-I/O PDF extractor for PDF content; otherwise decodes
    and, for HTML, strips markup down to visible text via the stdlib-only
    parser above. This is the net-new byte-accepting extractor the contract
    (§3.2) requires Phase 4 to build — it performs no I/O of its own and is
    never handed a locator, only bytes an acquisition call already fetched.
    """

    if not data:
        return ExtractionResult(None, STATUS_LOCATOR_ONLY, "text/plain", ("empty content",))

    ct = (content_type or "").split(";", 1)[0].strip().lower()
    if ct == "application/pdf" or data[:5] == b"%PDF-":
        pdf_result = extract_pdf(data)
        return ExtractionResult(pdf_result.text, pdf_result.status, "application/pdf", tuple(pdf_result.diagnostics))

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - never raise; degrade
            return ExtractionResult(None, STATUS_LOCATOR_ONLY, "text/plain", ("undecodable content",))

    looks_html = ct == "text/html" or "<html" in text[:2048].lower() or "<!doctype html" in text[:2048].lower()
    media_type = "text/plain"
    if looks_html:
        try:
            parser = _VisibleTextExtractor()
            parser.feed(text)
            parser.close()
            text = parser.text()
            media_type = "text/html"
        except Exception:  # noqa: BLE001 - never raise; degrade to raw text
            return ExtractionResult(None, STATUS_LOCATOR_ONLY, "text/html", ("html parse failed",))

    if not text:
        return ExtractionResult(None, STATUS_LOCATOR_ONLY, media_type, ("no extractable text",))
    if len(text) > _MAX_EXTRACT_CHARS:
        return ExtractionResult(text[:_MAX_EXTRACT_CHARS], STATUS_PARTIAL, media_type, ("truncated",))
    return ExtractionResult(text, STATUS_FULL_TEXT, media_type, ())


# ---------------------------------------------------------------------------
# Per-item authorization (contract §2.4 step 2) -- caller/operator-supplied
# only, never driven by packet content (contract §4.1).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorizationPolicy:
    denied_access_statuses: frozenset[str] = frozenset()
    require_rights_for_access_statuses: frozenset[str] = frozenset({"paywalled"})


def _authorize_source(normalized: NormalizedSource, policy: AuthorizationPolicy) -> str | None:
    if normalized.access_status in policy.denied_access_statuses:
        return "sensitivity_denied"
    if normalized.access_status in policy.require_rights_for_access_statuses:
        return "rights_metadata_missing"
    return None


def _access_scope_for(access_status: str) -> str:
    scope = "public" if access_status in ("open-access", "public-domain") else "private"
    assert scope in SENSITIVITY_RANK  # defensive: reuse the one shared vocabulary, never a second one
    return scope


# ---------------------------------------------------------------------------
# ERI-4.4: promotion seam
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionRequest:
    workspace_id: str
    target_run_id: str
    source_key: str
    locator: NormalizedLocator
    title: str | None
    content: str
    extraction_status: str
    paths: FoundryPaths | None = None


@dataclass(frozen=True)
class PromotionOutcome:
    ok: bool
    source_card_id: str | None = None
    error: str | None = None


Promote = Callable[[PromotionRequest], PromotionOutcome]


def default_promote(request: PromotionRequest) -> PromotionOutcome:
    """Stage a ``passage_resolved`` candidate's source into the run's
    existing source-card pipeline (contract §2.4.1). This is a staging
    action only — it never assigns ``verified``. Only ``verify_report`` plus
    ``assertion_materialization.py`` hold that authority; this seam adds no
    second decision-maker (AC ERI-4).
    """

    locator_text = request.locator.url or (f"doi:{request.locator.doi}" if request.locator.doi else request.source_key)
    try:
        result = _default_ingest_source(
            locator_text,
            run_id=request.target_run_id,
            source_type="other",
            sensitivity="personal",
            title=request.title,
            created_by_agent="external_research_interchange",
            fetch=False,
            content=request.content,
            assertion_registry_workspace_id=request.workspace_id,
            extraction_status=request.extraction_status,
            paths=request.paths,
        )
    except NotFoundError:
        return PromotionOutcome(ok=False, error="target_run_not_found")
    except Exception:  # noqa: BLE001 - staging failure never crashes the import
        return PromotionOutcome(ok=False, error="promotion_failed")
    return PromotionOutcome(ok=True, source_card_id=result.source_card_id)


# ---------------------------------------------------------------------------
# ResolvedActionResolution -- forward-compat canonical_refs carrier (see
# module docstring's "canonical_refs / effect_digest gap" note).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedActionResolution(ActionResolution):
    canonical_refs: Mapping[str, str] = field(default_factory=dict)


def _quarantine(reason_code: str, *, family: frozenset[str]) -> ActionResolution:
    assert reason_code in family, f"reason_code {reason_code!r} outside its closed vocabulary"
    return ActionResolution("quarantined", None, reason_code)


def _source_quarantine(reason_code: str) -> ActionResolution:
    return _quarantine(reason_code, family=SOURCE_REASON_CODES)


def _candidate_quarantine(reason_code: str) -> ActionResolution:
    return _quarantine(reason_code, family=CANDIDATE_REASON_CODES)


# ---------------------------------------------------------------------------
# Internal per-source resolution state
# ---------------------------------------------------------------------------


@dataclass
class _SourceOutcome:
    source_key: str
    tier: str | None  # "source_resolved" when an edition is bound, else None
    edition: dict[str, Any] | None
    content: str | None
    extraction_status: str | None
    title: str | None
    locator: NormalizedLocator | None
    reason_code: str | None = None  # meaningful only when tier is None
    # exact quote text -> "resolved" | "not_found" | "ambiguous"
    passage_status: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ExternalResearchResolver
# ---------------------------------------------------------------------------

AcquireFn = Callable[..., AcquisitionOutcome]


class ExternalResearchResolver:
    """Stateful ERI-4.1/4.2/4.3/4.4 resolver bound to one workspace.

    Exposes :meth:`resolve_source`/:meth:`resolve_candidate` matching
    ``external_research_interchange``'s ``ResolveSource``/``ResolveCandidate``
    callable shapes so they can be passed directly to ``stage()``. Must be
    constructed with the packet's full candidate-record set up front
    (``candidate_records``) because a source action alone (per
    ``ResolveSource``'s signature) never sees which candidates cite it —
    this resolver precomputes, per source_id, every distinct quote that
    cites it, so a source's own acquisition can register all of its known
    exact passages in one pass (contract §2.4 steps 3-7 collapsed onto the
    source action; candidate actions then only need read-only exact-match
    lookups, matching the packet's own canonical action order — sources
    before candidates, contract §1.3a).
    """

    def __init__(
        self,
        *,
        workspace_id: str,
        acquisition_policy: Mapping[str, Any],
        candidate_records: Sequence[Mapping[str, Any]] = (),
        registry: AssertionRegistry | None = None,
        authorization_policy: AuthorizationPolicy | None = None,
        acquire: AcquireFn = _default_acquire,
        promote: Promote | None = default_promote,
        dry_run: bool = False,
        timeout: float | None = None,
        paths: FoundryPaths | None = None,
    ) -> None:
        if not workspace_id or not workspace_id.strip():
            raise ValueError("workspace_id is required")
        self._workspace_id = workspace_id
        self._acquisition_policy: Mapping[str, Any] = acquisition_policy
        self._paths = paths
        self._registry = registry or AssertionRegistry(workspace_id=workspace_id, paths=paths)
        self._authorization_policy = authorization_policy or AuthorizationPolicy()
        self._acquire = acquire
        self._promote = promote
        self._dry_run = dry_run
        self._timeout = timeout
        self._source_outcomes: dict[str, _SourceOutcome] = {}
        self._quotes_by_source_id = self._collect_quotes(candidate_records)

    @staticmethod
    def _collect_quotes(candidate_records: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
        by_source: dict[str, list[str]] = {}
        seen: dict[str, set[str]] = {}
        for record in candidate_records:
            normalized = normalize_candidate(record) if isinstance(record, Mapping) else None
            if normalized is None or not normalized.quote:
                continue
            for ref in normalized.source_refs:
                bucket = by_source.setdefault(ref, [])
                seen_set = seen.setdefault(ref, set())
                if normalized.quote not in seen_set:
                    seen_set.add(normalized.quote)
                    bucket.append(normalized.quote)
        return by_source

    # --- public seam methods ------------------------------------------------

    def resolve_source(self, record: Mapping[str, Any], context: ResolutionContext) -> ActionResolution:
        if context.workspace_id != self._workspace_id:
            # Structurally unreachable via packet content (contract §4.1) --
            # a resolver/wiring defect, not a packet-triggerable condition.
            # No matching SOURCE reason code exists for "wrong workspace"
            # (only the candidate family has cross_workspace_denied), so
            # this fails the only way a source action can: invalid_locator.
            return _source_quarantine("invalid_locator")

        normalized = normalize_source(record)
        if normalized is None:
            return _source_quarantine("invalid_locator")

        outcome = self._resolve_source_impl(normalized)
        self._source_outcomes[normalized.source_id] = outcome
        if outcome.tier is None:
            assert outcome.reason_code is not None  # set below whenever tier is None
            return _source_quarantine(outcome.reason_code)
        return ResolvedActionResolution(
            "completed",
            outcome.tier,
            None,
            canonical_refs={"source_edition_id": (outcome.edition or {}).get("source_edition_id", "")},
        )

    def resolve_candidate(
        self,
        record: Mapping[str, Any],
        sources_by_id: Mapping[str, Mapping[str, Any]],
        context: ResolutionContext,
    ) -> ActionResolution:
        if context.workspace_id != self._workspace_id:
            return _candidate_quarantine("cross_workspace_denied")

        normalized = normalize_candidate(record)
        if normalized is None or not normalized.source_refs:
            return _candidate_quarantine("basis_incomplete")

        resolvable_refs = [r for r in normalized.source_refs if r in sources_by_id]
        if not resolvable_refs:
            return _candidate_quarantine("citation_unresolved")
        if normalized.relation not in _ALLOWED_RELATIONS:
            return _candidate_quarantine("relation_invalid")
        if not normalized.quote:
            return _candidate_quarantine("citation_unresolved")

        # Cross-batch resume safety (Phase 5): the packet's canonical action
        # order places every source action before every candidate action
        # (contract §1.3a), so by the time ANY candidate is resolved, every
        # source it could possibly cite has ALREADY run -- either earlier in
        # THIS call, or in a PRIOR call whose effect is already durably
        # persisted (`ExternalResearchInterchange._execute` then never
        # re-invokes `resolve_source` for it). `self._source_outcomes` is
        # this resolver INSTANCE's own per-call memory, populated only by
        # `resolve_source` actually running -- a fresh resolver instance in a
        # later batched call never learns about a source resolved in an
        # earlier one on its own. Without this reconstruction step, a
        # candidate whose cited source was resolved in an earlier batch call
        # would falsely quarantine `citation_unresolved` even though the
        # source is genuinely `source_resolved` in the persistent registry --
        # diverging from what a single unbatched call over the same packet
        # would produce.
        for ref in resolvable_refs:
            self._ensure_source_outcome(ref, sources_by_id)

        return self._resolve_candidate_impl(normalized, resolvable_refs, context)

    def _ensure_source_outcome(self, ref: str, sources_by_id: Mapping[str, Mapping[str, Any]]) -> None:
        """Lazily reconstruct ``self._source_outcomes[ref]`` from the
        PERSISTENT registry (never from fresh acquisition, never a write)
        when `ref`'s source action did not run via `resolve_source` on THIS
        resolver instance -- see the cross-batch resume-safety note in
        :meth:`resolve_candidate`. A no-op when already known. When the
        read-only reconstruction finds nothing (the source was never
        `source_resolved` -- e.g. it was itself quarantined, in this call or
        an earlier one), `_source_outcomes` is deliberately left unset and
        the candidate quarantines exactly as it would in a single unbatched
        call reaching the same underlying state.
        """

        if ref in self._source_outcomes:
            return
        record = sources_by_id.get(ref)
        if not isinstance(record, Mapping):
            return
        normalized = normalize_source(record)
        if normalized is None or not normalized.locator.present:
            return
        source_key = normalized.locator.identity_key or f"packet-local:{normalized.source_id}"
        reused = self._existing_edition_reuse(normalized, source_key)
        if reused is not None:
            self._source_outcomes[ref] = reused

    # --- ERI-4.2/4.3: source acquisition + passage registration ------------

    def _existing_edition_reuse(self, normalized: NormalizedSource, source_key: str) -> _SourceOutcome | None:
        """Contract §2.4 step 3: read-only, dry-run-safe, zero-network-I/O
        lookup for an already-registered exact edition + this source's own
        citing quotes' passage status. Tries every quote this source's
        candidates cite for a pre-existing exact match before
        ``_resolve_source_impl`` ever considers fresh acquisition, AND is
        reused by :meth:`_ensure_source_outcome` to reconstruct a source's
        outcome across a batch-call boundary without ever touching the
        network or writing to the registry.
        """

        quotes = self._quotes_by_source_id.get(normalized.source_id, [])
        for quote in quotes:
            matches = self._registry.find_exact_passages(source_key, quote)
            if matches:
                edition = matches[0][0]
                # `content=None, extraction_status=None`: `AssertionRegistry`
                # persists the immutable rendition bytes (`_load_edition_content`
                # / `_content_path`) but exposes no PUBLIC getter for them --
                # and never persists extraction_status at all -- so a reused
                # edition's content is genuinely unrecoverable here without a
                # forbidden re-fetch/re-extract; promotion of this outcome
                # fails closed via quarantine in `_finish_passage_resolved`.
                outcome = _SourceOutcome(source_key, "source_resolved", edition, None, None, normalized.title, normalized.locator)
                for q in quotes:
                    same_edition = [
                        (ed, ps)
                        for ed, ps in self._registry.find_exact_passages(source_key, q)
                        if ed.get("source_edition_id") == edition.get("source_edition_id")
                    ]
                    if len(same_edition) == 1:
                        outcome.passage_status[q] = "resolved"
                    elif len(same_edition) > 1:
                        outcome.passage_status[q] = "ambiguous"
                    else:
                        outcome.passage_status[q] = "not_found"
                return outcome
        return None

    def _resolve_source_impl(self, normalized: NormalizedSource) -> _SourceOutcome:
        source_key = normalized.locator.identity_key or f"packet-local:{normalized.source_id}"

        auth_reason = _authorize_source(normalized, self._authorization_policy)
        if auth_reason is not None:
            return _SourceOutcome(source_key, None, None, None, None, normalized.title, normalized.locator, reason_code=auth_reason)

        if not normalized.locator.present:
            return _SourceOutcome(source_key, None, None, None, None, normalized.title, normalized.locator, reason_code="invalid_locator")

        # contract §2.4 step 3: existing-edition reuse, read-only, dry-run
        # safe -- try every known quote for a pre-existing exact match
        # before ever considering fresh acquisition.
        reused = self._existing_edition_reuse(normalized, source_key)
        if reused is not None:
            return reused

        quotes = self._quotes_by_source_id.get(normalized.source_id, [])

        if self._dry_run:
            # Never perform a fresh network fetch or registry write in a
            # dry run (see module docstring's dry-run interlock note) --
            # report the same conservative floor Phase 2's own default
            # resolver reports.
            return _SourceOutcome(source_key, "locator_only", None, None, None, normalized.title, normalized.locator)

        acquisition = self._acquire(
            normalized.locator.url or f"doi:{normalized.locator.doi}",
            policy=self._acquisition_policy,
            **({"timeout": self._timeout} if self._timeout is not None else {}),
        )
        if not acquisition.ok or acquisition.content is None:
            return _SourceOutcome(source_key, None, None, None, None, normalized.title, normalized.locator, reason_code="source_unavailable")

        extraction = extract_bytes(acquisition.content, acquisition.content_type)
        if extraction.text is None:
            return _SourceOutcome(source_key, None, None, None, None, normalized.title, normalized.locator, reason_code="source_unavailable")

        access_scope = _access_scope_for(normalized.access_status)
        allowed_use = {"basis": "producer_declared_access_status", "access_status": normalized.access_status}
        retrieval_locator = {"url": acquisition.final_locator or normalized.locator.url, "doi": normalized.locator.doi}

        result = self._registry.ingest(
            source_key,
            extraction.text,
            media_type=extraction.media_type,
            access_scope=access_scope,
            allowed_use=allowed_use,
            retrieval_locator=retrieval_locator,
            # `passages=None` (AssertionRegistry's own default) rather than
            # `passages=[]`: an empty explicit list still unconditionally
            # publishes a passage-pointer file with `passage_ids: []` on
            # first ingest (`AssertionRegistry.ingest`/`_publish_passages`),
            # which that same registry's own `_load_passages` then rejects
            # on every SUBSEQUENT read ("must contain unique passage_ids")
            # -- a latent landmine in existing, unowned registry code this
            # module must not trigger. `passages=None` reuses the registry's
            # own well-exercised default (the whole raw text as one initial
            # passage) so the publication pointer is never empty.
        )
        if result.edition is None:
            reason = "rights_metadata_missing" if result.reason == "missing_rights_metadata" else "source_unavailable"
            return _SourceOutcome(source_key, None, None, None, None, normalized.title, normalized.locator, reason_code=reason)

        outcome = _SourceOutcome(
            source_key,
            "source_resolved",
            result.edition,
            extraction.text,
            extraction.status,
            normalized.title,
            normalized.locator,
        )
        for quote in quotes:
            quoted = self._registry.ingest(
                source_key,
                extraction.text,
                media_type=extraction.media_type,
                access_scope=access_scope,
                allowed_use=allowed_use,
                retrieval_locator=retrieval_locator,
                passages=[quote],
            )
            if quoted.created or quoted.reusable:
                outcome.passage_status[quote] = "resolved"
            elif quoted.reason == "ambiguous_selector":
                outcome.passage_status[quote] = "ambiguous"
            else:
                outcome.passage_status[quote] = "not_found"
        return outcome

    # --- ERI-4.3/4.4: candidate exact-match + promotion ---------------------

    def _resolve_candidate_impl(
        self,
        normalized: NormalizedCandidate,
        resolvable_refs: Sequence[str],
        context: ResolutionContext,
    ) -> ActionResolution:
        bound: _SourceOutcome | None = None
        for ref in resolvable_refs:
            candidate_outcome = self._source_outcomes.get(ref)
            if candidate_outcome is not None and candidate_outcome.tier == "source_resolved":
                bound = candidate_outcome
                break
        if bound is None:
            return _candidate_quarantine("citation_unresolved")
        assert bound.edition is not None
        assert normalized.quote is not None

        # A selector claiming a REAL, already-known passage_id in the bound
        # edition is checked first, directly via resolve_passage -- this is
        # the "vendor-provided ID conflict" / "drift" path (contract §3.3):
        # the vendor's claimed anchor is genuine, but the candidate's own
        # CURRENT quote text may no longer match what is actually recorded
        # there (drift), or the independently-resolved quote match may name
        # a different passage entirely (conflict). The claimed ID itself
        # never decides anything by being present -- it only changes WHICH
        # existing-registry check runs, never bypasses one.
        hinted = self._resolve_via_selector_hint(normalized, bound, context)
        if hinted is not None:
            return hinted

        bound_edition_id = bound.edition.get("source_edition_id")
        status = bound.passage_status.get(normalized.quote, "not_found")
        if status == "ambiguous":
            return _candidate_quarantine("citation_ambiguous")
        if status != "resolved":
            return _candidate_quarantine("citation_unresolved")

        matches = self._registry.find_exact_passages(bound.source_key, normalized.quote)
        same_edition = [(ed, ps) for ed, ps in matches if ed.get("source_edition_id") == bound_edition_id]
        if len(same_edition) == 0:
            # Exists elsewhere (a different, non-bound edition) but never in
            # the one this import actually acquired/reused -- never a
            # fallback to another edition (contract §3.3's "never a
            # newer-edition... fallback").
            return _candidate_quarantine("citation_mismatch") if matches else _candidate_quarantine("citation_unresolved")
        if len(same_edition) > 1:
            return _candidate_quarantine("citation_ambiguous")

        edition, passage = same_edition[0]
        if self._selector_conflicts_with(normalized, edition, passage):
            return _candidate_quarantine("passage_binding_conflict")

        refs = {"source_edition_id": edition.get("source_edition_id", ""), "passage_id": passage.get("passage_id", "")}
        return self._finish_passage_resolved(normalized, bound, refs, context)

    def _resolve_via_selector_hint(
        self, normalized: NormalizedCandidate, bound: _SourceOutcome, context: ResolutionContext
    ) -> ActionResolution | None:
        """When ``selector.passage_id`` names a REAL passage already present
        in the bound edition, resolve through it directly via
        ``AssertionRegistry.resolve_passage`` -- this is what makes "drift"
        reachable: the vendor's claimed anchor is genuine, but the
        candidate's own CURRENT ``quote`` text may no longer match what is
        actually recorded there (the source content changed since the
        vendor's citation was made). Returns ``None`` when the selector
        names no such real ID, so the caller falls through to ordinary
        quote-based exact-match resolution — the hint never decides
        anything by merely being present; it only changes which existing,
        already-governed check runs.
        """

        selector = normalized.selector
        if not isinstance(selector, Mapping):
            return None
        claimed_passage_id = selector.get("passage_id")
        if not isinstance(claimed_passage_id, str):
            return None
        assert bound.edition is not None
        edition_id = bound.edition.get("source_edition_id")
        if not isinstance(edition_id, str):
            return None

        real_ids = {p.get("passage_id") for p in self._registry.list_passages(bound.source_key, edition_id)}
        if claimed_passage_id not in real_ids:
            return None  # foreign/fabricated ID -- never trusted, falls through

        resolution = self._registry.resolve_passage(bound.source_key, edition_id, claimed_passage_id, normalized.quote or "")
        if not resolution.reusable:
            # Real anchor, but the candidate's current quote no longer
            # matches what is recorded there (contract's "drift" scenario).
            return _candidate_quarantine("citation_mismatch")

        assert resolution.passage is not None
        refs = {"source_edition_id": edition_id, "passage_id": claimed_passage_id}
        return self._finish_passage_resolved(normalized, bound, refs, context)

    def _selector_conflicts_with(self, normalized: NormalizedCandidate, edition: Mapping[str, Any], passage: Mapping[str, Any]) -> bool:
        """``True`` when a ``selector`` hint names a specific passage/edition
        ID that disagrees with what independent quote-based resolution just
        found (contract's "vendor-provided ID conflict" scenario) — checked
        only after :meth:`_resolve_via_selector_hint` has already ruled out
        the hint naming a real, already-known ID (that path resolves or
        drifts on its own and never reaches here).
        """

        if not isinstance(normalized.selector, Mapping):
            return False
        claimed_passage_id = normalized.selector.get("passage_id")
        claimed_edition_id = normalized.selector.get("source_edition_id")
        real_passage_id = passage.get("passage_id")
        real_edition_id = edition.get("source_edition_id")
        return bool(
            (isinstance(claimed_passage_id, str) and claimed_passage_id != real_passage_id)
            or (isinstance(claimed_edition_id, str) and claimed_edition_id != real_edition_id)
        )

    def _finish_passage_resolved(
        self,
        normalized: NormalizedCandidate,
        bound: _SourceOutcome,
        refs: dict[str, str],
        context: ResolutionContext,
    ) -> ActionResolution:
        """Shared tail (ERI-4.4): stage promotion when a run context is
        present and this resolver is not in dry-run mode, else report
        ``passage_resolved`` as-is. Never self-assigns ``verified`` -- only
        ``verify_report`` + the existing materializer hold that authority
        (contract §2.4.1); staging is as far as this seam goes.
        """

        if context.target_run_id is None or self._dry_run or self._promote is None:
            return ResolvedActionResolution("completed", "passage_resolved", None, canonical_refs=refs)

        if bound.content is None or bound.extraction_status is None:
            # `bound` came from `_existing_edition_reuse` (either the in-call
            # reuse path or `_ensure_source_outcome`'s cross-batch resume
            # reconstruction) -- that path is read-only and never
            # re-extracts source text, and `AssertionRegistry` exposes no
            # public getter for the immutable rendition bytes it stores (see
            # the comment at its call site above). A legitimately-resolvable
            # candidate whose bound edition was reused rather than freshly
            # acquired therefore has no content to stage into a source card;
            # fail closed into quarantine instead of crashing the import or
            # fabricating evidence.
            return _candidate_quarantine("verification_failed")

        request = PromotionRequest(
            workspace_id=self._workspace_id,
            target_run_id=context.target_run_id,
            source_key=bound.source_key,
            locator=bound.locator or NormalizedLocator(None, None),
            title=bound.title,
            content=bound.content,
            extraction_status=bound.extraction_status,
            paths=self._paths,
        )
        promotion = self._promote(request)
        if not promotion.ok:
            return _candidate_quarantine("verification_failed")
        refs = {**refs, "source_card_id": promotion.source_card_id or ""}
        return ResolvedActionResolution("completed", "passage_resolved", None, canonical_refs=refs)


__all__ = [
    "AuthorizationPolicy",
    "CitationTuple",
    "ExternalResearchResolver",
    "ExtractionResult",
    "NormalizedCandidate",
    "NormalizedLocator",
    "NormalizedSource",
    "PromotionOutcome",
    "PromotionRequest",
    "ResolvedActionResolution",
    "default_promote",
    "extract_bytes",
    "normalize_candidate",
    "normalize_citation_tuple",
    "normalize_source",
]
