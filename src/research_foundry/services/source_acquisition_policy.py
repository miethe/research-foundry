"""External Research Report Interchange (ERI) v1 — Phase 4: SSRF-safe
governed acquisition gate (ERI-4.2).

Implements the frozen architecture at
``docs/dev/architecture/external-research-handoff-contract.md`` §4.2 and
closes CRITICAL/HIGH findings #1-#4 and #13 of
``.claude/findings/eri-p1-contract-audit-gpt56.md``:

**One actor owns the whole HTTP lifecycle (§4.2.0, audit #1).** This module
is not a pre-flight check that hands a URL to some other HTTP client —
:func:`acquire` *is* the HTTP client. Canonicalization, scheme/address/DNS
validation, connection binding, connected-peer verification, and
redirect-following with full re-validation at every hop all happen inside
one function, over one connection it opens and controls end to end. Callers
receive only already-acquired bytes plus minimal response metadata — never a
locator they could independently re-resolve and fetch a second time. There
is no "second fetch" for a DNS-rebind, a raced Happy-Eyeballs address, or a
reused pooled connection to happen inside.

**Direct transport only (§4.2.1, audit #2).** :func:`acquire` builds its own
socket and speaks raw HTTP/1.1 — it never calls ``urllib``/``httpx``/
``requests`` and never reads ``HTTP_PROXY``/``HTTPS_PROXY``/``NO_PROXY``/PAC
configuration, so there is no proxy-shaped code path that could exist for an
environment variable to influence in the first place.

**Single parse (§4.2.2, audit #3).** :func:`canonicalize_locator` parses a
locator exactly once with one strict implementation; the returned
:class:`CanonicalLocator` is the only authority object every later step
(DNS, connect, TLS SNI, the request line) consumes. Userinfo, percent-encoded
hosts, IPv6 zone IDs, ambiguous numeric hosts, and multiple trailing dots are
all rejected outright, never "helpfully" coerced.

**IPv6 transition/translation prefixes are categorically forbidden
(§4.2.4, audit #4).** NAT64/DNS64, 6to4, Teredo, and IPv4-mapped/compatible
addresses are denied by prefix membership — the same
``ipv6_transition_or_translation`` category the acquisition-policy schema
pins into ``forbidden_address_categories`` — with the embedded IPv4
destination additionally decoded and validated for audit purposes.

**IPv6 site-local addresses are categorically forbidden (round-2 audit
#10).** ``fec0::/10`` (RFC 3879 deprecated site-local) is denied via
:attr:`ipaddress.IPv6Address.is_site_local` — a category stdlib's
``is_private``/``is_reserved`` do not cover — closing a LAN-SSRF path an
injected resolver could otherwise route through.

**Operator-configured NAT64 prefixes fail the WHOLE policy closed if
malformed (round-2 audit #11).** A locally-configured NAT64 prefix that
does not parse as a canonical (no host bits set) IPv6 network raises
:class:`AcquisitionPolicyError`, which :func:`acquire` turns into an
immediate closed denial — never a silently-dropped entry that leaves the
deployment's real NAT64 route unenforced.

**Governed local ingest is a separate module (§4.5, audit #13).** This
module performs network acquisition only; it never resolves a packet-
supplied string as a filesystem path. Local-asset resolution belongs to
Phase 4's resolution module (``external_research_resolution.py``), which
classifies structurally (which pipeline receives the value) rather than by
inspecting the string's shape.

Every ``deny`` outcome carries a rich ``denial_code`` for this module's own
callers (audit-only) — never a caller-visible reason. ``external_research_
resolution.py`` collapses every acquisition-layer failure into exactly one
closed-vocabulary ``source_unavailable`` reason before it ever reaches an
``ActionResolution``, satisfying contract §4.3's "one generic denial, zero
reason-code differential" rule structurally rather than by careful
omission.
"""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

_idna: Any = None
_IDNA_AVAILABLE = False
try:  # pragma: no cover - exercised indirectly; idna ships transitively via httpx
    import idna as _idna_module

    _idna = _idna_module
    _IDNA_AVAILABLE = True
except ImportError:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# Frozen limits — mirrors the conservative posture of Limits in
# external_research_interchange.py; not independently configurable upward.
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RESPONSE_BYTES = 25_165_824  # 24 MiB
_MAX_LOCATOR_LENGTH = 8192

_ALLOWED_STATUS_2XX = range(200, 300)
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

# Internal-only denial codes (never one of the 19 closed-vocabulary reason
# codes; contract §4.3's "one generic denial" is what the resolution module
# maps every one of these down to before it can reach a caller).
DENIAL_INVALID_LOCATOR = "invalid_locator"
DENIAL_UNAVAILABLE = "source_unavailable"
# Round-2 audit #11: a malformed operator-configured NAT64 prefix denies the
# WHOLE policy rather than being silently dropped -- distinct denial code so
# this policy-configuration failure is never conflated with an ordinary
# transport-unavailable outcome in audit logs.
DENIAL_POLICY_INVALID = "policy_configuration_invalid"


class AcquisitionPolicyError(ValueError):
    """The acquisition policy configuration itself is malformed (round-2
    audit #11) -- e.g. an ``operator_configured_nat64_prefixes`` entry that
    is not a canonical IPv6 network. Raised by :func:`_parse_operator_
    nat64_prefixes`; :func:`acquire` catches it and denies the whole
    request closed rather than letting the bad entry be silently discarded
    and validation proceed on a partially-applied configuration.
    """

# ---------------------------------------------------------------------------
# Forbidden-address categories (contract §4.2.4)
# ---------------------------------------------------------------------------

CATEGORY_LOOPBACK = "loopback"
CATEGORY_PRIVATE = "private"
CATEGORY_RESERVED = "reserved"
CATEGORY_LINK_LOCAL = "link_local"
CATEGORY_MULTICAST = "multicast"
CATEGORY_UNSPECIFIED = "unspecified"
CATEGORY_CGNAT = "carrier_grade_nat"
CATEGORY_BENCHMARK = "benchmark_or_documentation"
CATEGORY_METADATA = "cloud_metadata"
CATEGORY_ENCODED = "encoded_or_obfuscated_host"
CATEGORY_IPV6_TRANSITION = "ipv6_transition_or_translation"
# Round-2 audit #10: fec0::/10 (RFC 3879 deprecated site-local) is neither
# is_private nor is_reserved under stdlib ipaddress -- a distinct category
# so it is never silently permitted by relying on those broader checks.
CATEGORY_IPV6_SITE_LOCAL = "ipv6_site_local"

DEFAULT_FORBIDDEN_CATEGORIES = (
    CATEGORY_LOOPBACK,
    CATEGORY_PRIVATE,
    CATEGORY_RESERVED,
    CATEGORY_LINK_LOCAL,
    CATEGORY_MULTICAST,
    CATEGORY_UNSPECIFIED,
    CATEGORY_CGNAT,
    CATEGORY_BENCHMARK,
    CATEGORY_METADATA,
    CATEGORY_ENCODED,
    CATEGORY_IPV6_TRANSITION,
    CATEGORY_IPV6_SITE_LOCAL,
)

# Versioned metadata deny-set (contract §4.2.4, audit #5) — hostnames and IP
# literals covering AWS, GCP, Azure, and Alibaba Cloud metadata endpoints.
DEFAULT_METADATA_DENY_SET = (
    "169.254.169.254",
    "fd00:ec2::254",
    "metadata.google.internal",
    "metadata.azure.com",
    "169.254.169.253",
    "100.100.100.200",
)
_CGNAT_NET = ipaddress.ip_network("100.64.0.0/10")
_BENCHMARK_NETS = (
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("2001:db8::/32"),
)

# IPv6 transition/translation prefixes (contract §4.2.4, audit #4) — always
# forbidden by prefix membership; the embedded IPv4 destination is decoded
# separately (see decode_embedded_ipv4) for audit-only purposes.
DEFAULT_TRANSITION_PREFIXES = (
    "64:ff9b::/96",
    "64:ff9b:1::/48",
    "2002::/16",
    "2001::/32",
    "::ffff:0:0/96",
    "::/96",
)


def _split_metadata_deny_set(entries: Sequence[str]) -> tuple[frozenset[str], frozenset[str]]:
    ip_literals: set[str] = set()
    hostnames: set[str] = set()
    for entry in entries:
        try:
            ipaddress.ip_address(entry)
        except ValueError:
            hostnames.add(entry.lower())
        else:
            ip_literals.add(entry)
    return frozenset(ip_literals), frozenset(hostnames)


_DEFAULT_METADATA_IPS, _DEFAULT_METADATA_HOSTNAMES = _split_metadata_deny_set(DEFAULT_METADATA_DENY_SET)


# ---------------------------------------------------------------------------
# Canonicalization (contract §4.2.2, audit #3)
# ---------------------------------------------------------------------------

_HEX_HOST_RE = re.compile(r"^0[xX][0-9a-fA-F]+$")
_ALL_DIGIT_LABEL_RE = re.compile(r"^\d+$")
_VALID_ASCII_HOST_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)


@dataclass(frozen=True)
class CanonicalLocator:
    """The one parsed-and-canonicalized authority object every later policy
    step and the transport connection itself consume (contract §4.2.2's
    ``shared_authority_object_for_transport``) — never re-derived from the
    original locator string a second time.
    """

    scheme: str
    host: str  # canonical ASCII A-label hostname, or a literal IP's text form
    is_ip_literal: bool
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    port: int
    path: str
    query: str

    def as_url(self) -> str:
        host = f"[{self.host}]" if self.is_ip_literal and self.ip is not None and self.ip.version == 6 else self.host
        default_port = 443 if self.scheme == "https" else 80
        netloc = host if self.port == default_port else f"{host}:{self.port}"
        query = f"?{self.query}" if self.query else ""
        return f"{self.scheme}://{netloc}{self.path or '/'}{query}"


def _parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    candidate = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def _looks_like_ambiguous_numeric_host(host: str) -> bool:
    """Decimal/octal/hex single-integer or partial-dotted numeric forms
    (contract §4.2.2 ``reject_ambiguous_numeric_host``) — rejected outright
    rather than "helpfully" normalized. Only called after
    :func:`_parse_ip_literal` has already failed, so a genuine canonical
    dotted-quad (four decimal octets, no leading zero, each 0-255) never
    reaches this function — it was already accepted as an IP literal.
    """

    if _HEX_HOST_RE.match(host):
        return True
    labels = host.split(".")
    return all(_ALL_DIGIT_LABEL_RE.match(label) for label in labels)


def _idna_encode(host: str) -> str | None:
    try:
        host.encode("ascii")
    except UnicodeEncodeError:
        is_ascii = False
    else:
        is_ascii = True

    if is_ascii:
        if not _VALID_ASCII_HOST_RE.match(host):
            return None
        return host.lower()

    if not _IDNA_AVAILABLE or _idna is None:  # pragma: no cover - idna ships transitively via httpx
        return None
    try:
        encoded = _idna.encode(host, uts46=True)
    except (_idna.IDNAError, UnicodeError, ValueError):
        return None
    try:
        return encoded.decode("ascii").lower()
    except UnicodeDecodeError:  # pragma: no cover - idna always emits ASCII
        return None


def canonicalize_locator(locator: str, *, allowed_schemes: Sequence[str] = ("https", "http")) -> CanonicalLocator | None:
    """Parse ``locator`` exactly once (contract §4.2.2). Returns ``None`` for
    anything ambiguous, malformed, or outside the allowed scheme set — never
    a "best effort" coercion.
    """

    if not isinstance(locator, str) or not locator or len(locator) > _MAX_LOCATOR_LENGTH:
        return None
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in locator):
        return None

    try:
        parsed = urlsplit(locator, allow_fragments=True)
    except ValueError:
        return None

    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes or scheme not in ("http", "https"):
        return None

    # Reject ANY userinfo component outright (contract §4.2.2
    # reject_userinfo) — strictly stronger than "credential-shaped only".
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        return None

    try:
        host_raw = parsed.hostname
    except ValueError:
        return None
    if not host_raw:
        return None

    # Percent-encoded host / IPv6 zone IDs both surface as a literal "%" in
    # the undecoded hostname component — reject either shape outright.
    if "%" in host_raw:
        return None

    # Trailing-dot handling: exactly one is canonicalization, more is
    # rejected as ambiguous.
    if host_raw.endswith(".."):
        return None
    if host_raw.endswith("."):
        host_raw = host_raw[:-1]
    if not host_raw or host_raw.endswith("."):
        return None

    try:
        port = parsed.port
    except ValueError:
        return None
    default_port = 443 if scheme == "https" else 80
    port = port if port is not None else default_port
    if port <= 0 or port > 65535:
        return None

    path = parsed.path or "/"
    if not path.startswith("/"):
        return None

    ip_literal = _parse_ip_literal(host_raw)
    if ip_literal is not None:
        if scheme == "https":
            # SNI/certificate-hostname verification is not meaningfully
            # definable against a bare IP literal; v1 restricts HTTPS
            # acquisition to named hosts (a documented, safe narrowing, not
            # an oversight).
            return None
        return CanonicalLocator(scheme, str(ip_literal), True, ip_literal, port, path, parsed.query)

    if _looks_like_ambiguous_numeric_host(host_raw):
        return None

    canonical_host = _idna_encode(host_raw)
    if canonical_host is None:
        return None
    return CanonicalLocator(scheme, canonical_host, False, None, port, path, parsed.query)


# ---------------------------------------------------------------------------
# Forbidden-address policy (contract §4.2.4)
# ---------------------------------------------------------------------------


def decode_embedded_ipv4(ip: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    """Decode the embedded IPv4 destination from an IPv6 transition/
    translation address, for audit-only purposes (contract §4.2.4
    ``decode_and_validate_embedded_ipv4``). The accept/deny decision itself
    never depends on this succeeding — every address matching a transition
    prefix is denied by prefix membership alone, in
    :func:`forbidden_address_category`.
    """

    packed = ip.packed
    try:
        if ip in ipaddress.ip_network("64:ff9b::/96") or ip in ipaddress.ip_network("::ffff:0:0/96") or ip in ipaddress.ip_network("::/96"):
            return ipaddress.IPv4Address(packed[12:16])
        if ip in ipaddress.ip_network("64:ff9b:1::/48"):
            # RFC 8215 local-use NAT64: embedded IPv4 occupies bytes 8-11
            # (bits 64-95), with bits 96-103 reserved as zero as u32 split.
            return ipaddress.IPv4Address(packed[8:12])
        if ip in ipaddress.ip_network("2002::/16"):
            # 6to4: embedded IPv4 occupies bits 16-47.
            return ipaddress.IPv4Address(packed[2:6])
        if ip in ipaddress.ip_network("2001::/32"):
            # Teredo (RFC 4380): client IPv4 is obscured by XOR with
            # 0xFFFFFFFF in the low 32 bits.
            raw = int.from_bytes(packed[12:16], "big") ^ 0xFFFFFFFF
            return ipaddress.IPv4Address(raw)
    except (ValueError, ipaddress.AddressValueError):  # pragma: no cover - defensive
        return None
    return None


def _parse_operator_nat64_prefixes(operator_prefixes: Sequence[str]) -> list[ipaddress.IPv6Network]:
    """Parse operator-configured NAT64 prefixes strictly (round-2 audit
    #11). Every entry MUST be a canonical IPv6 network (``strict=True`` --
    no host bits set); a single malformed or non-IPv6 entry raises
    :class:`AcquisitionPolicyError` rather than being silently discarded.
    A plausible address-form prefix like ``2600:abcd:1234::1/96`` (host
    bits set) must never be silently dropped -- that would leave this
    deployment's actual NAT64 route unenforced, permitting addresses that
    embed metadata/private IPv4 through it.
    """

    nets: list[ipaddress.IPv6Network] = []
    for raw in operator_prefixes:
        if not isinstance(raw, str) or not raw:
            raise AcquisitionPolicyError(f"operator-configured NAT64 prefix must be a non-empty string, got {raw!r}")
        try:
            net = ipaddress.ip_network(raw, strict=True)
        except ValueError as exc:
            raise AcquisitionPolicyError(
                f"operator-configured NAT64 prefix {raw!r} is not a canonical IPv6 network: {exc}"
            ) from exc
        if not isinstance(net, ipaddress.IPv6Network):
            raise AcquisitionPolicyError(f"operator-configured NAT64 prefix {raw!r} must be an IPv6 network")
        nets.append(net)
    return nets


def _transition_networks(operator_prefixes: Sequence[str]) -> list[ipaddress.IPv6Network]:
    nets: list[ipaddress.IPv6Network] = [ipaddress.IPv6Network(p) for p in DEFAULT_TRANSITION_PREFIXES]
    nets.extend(_parse_operator_nat64_prefixes(operator_prefixes))
    return nets


def hostname_denied_by_metadata_set(host: str, policy: Mapping[str, Any]) -> bool:
    """Reject a canonical hostname that exactly matches a metadata-service
    hostname in the deny-set (contract §4.2.4, audit #5) — checked before
    DNS resolution even runs, so a metadata hostname is denied by name
    regardless of what it might resolve to.
    """

    raw_entries = policy.get("metadata_deny_set", DEFAULT_METADATA_DENY_SET)
    _, hostnames = _split_metadata_deny_set(list(raw_entries))
    return host.lower() in hostnames


def forbidden_address_category(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    policy: Mapping[str, Any],
    *,
    operator_nat64_prefixes: Sequence[str] = (),
) -> str | None:
    """Return the first matching forbidden-address category, or ``None`` if
    ``ip`` is acceptable under every category currently enabled in
    ``policy["forbidden_address_categories"]``. Every returned category is
    audit-only; :mod:`external_research_resolution` never surfaces it past
    its own internal logging.
    """

    categories = frozenset(policy.get("forbidden_address_categories", DEFAULT_FORBIDDEN_CATEGORIES))
    ip_literals, _ = _split_metadata_deny_set(list(policy.get("metadata_deny_set", DEFAULT_METADATA_DENY_SET)))

    if CATEGORY_METADATA in categories and str(ip) in ip_literals:
        return CATEGORY_METADATA

    if isinstance(ip, ipaddress.IPv6Address) and CATEGORY_IPV6_TRANSITION in categories:
        if any(ip in net for net in _transition_networks(operator_nat64_prefixes)):
            return CATEGORY_IPV6_TRANSITION

    if isinstance(ip, ipaddress.IPv6Address) and CATEGORY_IPV6_SITE_LOCAL in categories and ip.is_site_local:
        return CATEGORY_IPV6_SITE_LOCAL

    if CATEGORY_LOOPBACK in categories and ip.is_loopback:
        return CATEGORY_LOOPBACK
    if CATEGORY_UNSPECIFIED in categories and ip.is_unspecified:
        return CATEGORY_UNSPECIFIED
    if CATEGORY_LINK_LOCAL in categories and ip.is_link_local:
        return CATEGORY_LINK_LOCAL
    if CATEGORY_MULTICAST in categories and ip.is_multicast:
        return CATEGORY_MULTICAST
    if CATEGORY_RESERVED in categories and ip.is_reserved:
        return CATEGORY_RESERVED

    if isinstance(ip, ipaddress.IPv4Address):
        if CATEGORY_CGNAT in categories and ip in _CGNAT_NET:
            return CATEGORY_CGNAT
        if CATEGORY_BENCHMARK in categories and any(ip in net for net in _BENCHMARK_NETS if net.version == 4):
            return CATEGORY_BENCHMARK
    else:
        if CATEGORY_BENCHMARK in categories and any(ip in net for net in _BENCHMARK_NETS if net.version == 6):
            return CATEGORY_BENCHMARK

    if CATEGORY_PRIVATE in categories and ip.is_private:
        return CATEGORY_PRIVATE
    return None


# ---------------------------------------------------------------------------
# DNS resolution + connection (contract §4.2.5, §4.2.6)
# ---------------------------------------------------------------------------

# (host, port) -> [(address_family, ip_text), ...]; every returned answer is
# validated (contract §4.2.5) — the default wraps socket.getaddrinfo, tests
# inject a controlled resolver to exercise mixed/forbidden/rebinding answers
# with zero real network access.
Resolver = Callable[[str, int], Sequence[tuple[int, str]]]
Connector = Callable[[str, int, int, float], socket.socket]


def _default_resolve(host: str, port: int) -> list[tuple[int, str]]:
    try:
        infos = socket.getaddrinfo(host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except OSError:
        return []
    seen: set[tuple[int, str]] = set()
    out: list[tuple[int, str]] = []
    for family, _socktype, _proto, _canonname, sockaddr in infos:
        ip_text = str(sockaddr[0])
        key = (int(family), ip_text)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _default_connect(ip_text: str, port: int, family: int, timeout: float) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((ip_text, port))
    return sock


def _family_of(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> int:
    return socket.AF_INET6 if ip.version == 6 else socket.AF_INET


# ---------------------------------------------------------------------------
# HTTP/1.1 request/response over the policy-owned connection
# ---------------------------------------------------------------------------


def _build_request(canonical: CanonicalLocator) -> bytes:
    target = canonical.path or "/"
    if canonical.query:
        target = f"{target}?{canonical.query}"
    host_header = f"[{canonical.host}]" if canonical.is_ip_literal and canonical.ip is not None and canonical.ip.version == 6 else canonical.host
    default_port = 443 if canonical.scheme == "https" else 80
    if canonical.port != default_port:
        host_header = f"{host_header}:{canonical.port}"
    lines = [
        f"GET {target} HTTP/1.1",
        f"Host: {host_header}",
        "User-Agent: research-foundry-eri/1",
        "Accept: */*",
        "Connection: close",
        "",
        "",
    ]
    return "\r\n".join(lines).encode("ascii", errors="strict")


def _read_response(sock: socket.socket, max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    response = http.client.HTTPResponse(sock, method="GET")
    response.begin()
    headers = {key.lower(): value for key, value in response.getheaders()}
    body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError("acquired response exceeds the configured byte ceiling")
    return response.status, headers, body


# ---------------------------------------------------------------------------
# Public result type + entry point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AcquisitionOutcome:
    """Result of :func:`acquire`. ``denial_code`` is audit/test-only detail
    — never one of the 19 closed-vocabulary reason codes, and never
    propagated past :mod:`external_research_resolution`'s own internal
    handling (contract §4.3/§4.6).
    """

    ok: bool
    content: bytes | None = None
    status_code: int | None = None
    content_type: str | None = None
    final_locator: str | None = None
    hops: int = 0
    denial_code: str = ""


def acquire(
    locator: str,
    *,
    policy: Mapping[str, Any],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    resolver: Resolver | None = None,
    connect: Connector | None = None,
) -> AcquisitionOutcome:
    """Acquire ``locator`` under the full contract §4.2 gate.

    Never raises for hostile/unreachable input (mirrors
    :func:`~research_foundry.services.external_research_interchange.inspect_packet`'s
    "never raises for hostile content" convention) — every failure mode is a
    typed, safe :class:`AcquisitionOutcome` with ``ok=False``.

    ``resolver``/``connect`` are injectable so tests can exercise mixed DNS
    answers, DNS-rebinding peer mismatches, and redirect chains without any
    real network access. Production callers never pass them; the defaults
    perform real ``getaddrinfo``/socket I/O with environment/PAC proxies
    never consulted (this module never imports a proxy-aware HTTP client in
    the first place — contract §4.2.1).
    """

    resolve_fn = resolver or _default_resolve
    connect_fn = connect or _default_connect
    allowed_schemes = tuple(policy.get("allowed_schemes", ("https", "http")))
    max_hops = int(policy.get("redirects", {}).get("max_hops", 3))
    operator_nat64 = list(policy.get("ipv6_transition_policy", {}).get("operator_configured_nat64_prefixes", []))

    # Round-2 audit #11: validate operator-configured NAT64 prefixes ONCE,
    # up front -- a malformed entry denies the WHOLE policy/request closed
    # rather than being silently discarded deep inside the per-hop category
    # check, which would leave this deployment's real NAT64 route
    # unenforced for every subsequent answer.
    try:
        _parse_operator_nat64_prefixes(operator_nat64)
    except AcquisitionPolicyError:
        return AcquisitionOutcome(ok=False, denial_code=DENIAL_POLICY_INVALID, hops=0)

    current = locator
    hop = 0
    while True:
        canonical = canonicalize_locator(current, allowed_schemes=allowed_schemes)
        if canonical is None:
            return AcquisitionOutcome(ok=False, denial_code=DENIAL_INVALID_LOCATOR, hops=hop)

        if not canonical.is_ip_literal and hostname_denied_by_metadata_set(canonical.host, policy):
            return AcquisitionOutcome(ok=False, denial_code=f"forbidden_address:{CATEGORY_METADATA}", hops=hop)

        if canonical.is_ip_literal:
            assert canonical.ip is not None
            answers: list[tuple[int, str]] = [(_family_of(canonical.ip), str(canonical.ip))]
        else:
            try:
                answers = list(resolve_fn(canonical.host, canonical.port))
            except Exception:  # noqa: BLE001 - resolver failures never propagate; fail closed
                answers = []
        if not answers:
            return AcquisitionOutcome(ok=False, denial_code=DENIAL_UNAVAILABLE, hops=hop)

        # Every DNS answer is validated -- not just the first (contract
        # §4.2.5). Any single forbidden answer denies the whole locator.
        validated: list[tuple[int, str, ipaddress.IPv4Address | ipaddress.IPv6Address]] = []
        for family, ip_text in answers:
            try:
                ip_obj = ipaddress.ip_address(ip_text)
            except ValueError:
                return AcquisitionOutcome(ok=False, denial_code=DENIAL_UNAVAILABLE, hops=hop)
            try:
                category = forbidden_address_category(ip_obj, policy, operator_nat64_prefixes=operator_nat64)
            except AcquisitionPolicyError:
                # Defense in depth: the up-front check above should already
                # have caught this, but a per-answer failure here must still
                # deny closed rather than propagate (never raise for
                # hostile/misconfigured input).
                return AcquisitionOutcome(ok=False, denial_code=DENIAL_POLICY_INVALID, hops=hop)
            if category is not None:
                return AcquisitionOutcome(ok=False, denial_code=f"forbidden_address:{category}", hops=hop)
            validated.append((family, ip_text, ip_obj))

        family, ip_text, ip_obj = validated[0]
        try:
            sock = connect_fn(ip_text, canonical.port, family, timeout)
        except Exception:  # noqa: BLE001 - connect failures fail closed, never fall back
            return AcquisitionOutcome(ok=False, denial_code=DENIAL_UNAVAILABLE, hops=hop)

        try:
            # Verify the CONNECTED PEER matches the validated address before
            # sending anything -- closes the DNS-rebinding window (contract
            # §4.2.6): resolve -> validate every answer -> bind -> verify.
            peer = sock.getpeername()
            peer_ip_text = str(peer[0]).split("%", 1)[0]
            try:
                peer_ip = ipaddress.ip_address(peer_ip_text)
            except ValueError:
                return AcquisitionOutcome(ok=False, denial_code="peer_verification_failed", hops=hop)
            if peer_ip != ip_obj:
                return AcquisitionOutcome(ok=False, denial_code="peer_mismatch", hops=hop)

            if canonical.scheme == "https":
                ctx = ssl.create_default_context()
                sock = ctx.wrap_socket(sock, server_hostname=canonical.host)

            sock.sendall(_build_request(canonical))
            status, headers, body = _read_response(sock, max_bytes)
        except Exception:  # noqa: BLE001 - no transport fallback; any failure denies closed
            return AcquisitionOutcome(ok=False, denial_code=DENIAL_UNAVAILABLE, hops=hop)
        finally:
            with suppress(Exception):
                sock.close()

        if status in _REDIRECT_STATUSES:
            location = headers.get("location")
            if not location:
                return AcquisitionOutcome(ok=False, denial_code=DENIAL_UNAVAILABLE, status_code=status, hops=hop)
            hop += 1
            if hop > max_hops:
                return AcquisitionOutcome(ok=False, denial_code="redirect_limit_exceeded", status_code=status, hops=hop)
            # Round-2 audit #12: a hostile Location header (e.g. an
            # unterminated IPv6 literal like `http://[::1`) can make
            # urljoin()/urlsplit() themselves raise ValueError. That must
            # deny closed exactly like every other transport failure in
            # this function -- never propagate and abort the import.
            try:
                next_locator = urljoin(canonical.as_url(), location)
                next_scheme = (urlsplit(next_locator).scheme or "").lower()
            except Exception:  # noqa: BLE001 - malformed redirect target fails closed
                return AcquisitionOutcome(ok=False, denial_code="redirect_malformed_location", status_code=status, hops=hop)
            if next_scheme not in ("http", "https"):
                return AcquisitionOutcome(ok=False, denial_code="redirect_non_http_scheme", status_code=status, hops=hop)
            current = next_locator
            continue

        if status not in _ALLOWED_STATUS_2XX:
            return AcquisitionOutcome(ok=False, denial_code=DENIAL_UNAVAILABLE, status_code=status, hops=hop)

        return AcquisitionOutcome(
            ok=True,
            content=body,
            status_code=status,
            content_type=headers.get("content-type"),
            final_locator=canonical.as_url(),
            hops=hop,
        )


__all__ = [
    "AcquisitionOutcome",
    "AcquisitionPolicyError",
    "CanonicalLocator",
    "DEFAULT_FORBIDDEN_CATEGORIES",
    "DEFAULT_METADATA_DENY_SET",
    "DEFAULT_TRANSITION_PREFIXES",
    "DENIAL_INVALID_LOCATOR",
    "DENIAL_POLICY_INVALID",
    "DENIAL_UNAVAILABLE",
    "acquire",
    "canonicalize_locator",
    "decode_embedded_ipv4",
    "forbidden_address_category",
    "hostname_denied_by_metadata_set",
]
