"""Unit tests for ERI-4.2 — the SSRF-safe governed acquisition gate.

Every test uses either pure in-process functions (canonicalization,
forbidden-address category matrix) or an injected fake resolver/connector
(no real sockets) so the DNS-rebinding, mixed-answer, redirect, and
peer-verification scenarios are exercised deterministically with zero real
network access. One end-to-end smoke test spins up a genuine local
``http.server`` bound to ``127.0.0.1`` (loopback only, no egress) to prove
the real default resolver/connector wiring works, per the plan's "local
stub HTTP server" instruction.
"""

from __future__ import annotations

import http.server
import ipaddress
import io
import socket
import threading
from collections.abc import Sequence

import pytest

from research_foundry.services import source_acquisition_policy as sap

# ---------------------------------------------------------------------------
# A minimal, safe default policy dict (mirrors the schema-valid fixture at
# tests/fixtures/external_research_handoff/acquisition_policy/valid.yaml).
# ---------------------------------------------------------------------------


def _policy(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": "1.0",
        "type": "external_research_acquisition_policy",
        "allowed_schemes": ["https", "http"],
        "reject_embedded_credentials": True,
        "forbidden_address_categories": list(sap.DEFAULT_FORBIDDEN_CATEGORIES),
        "metadata_deny_set": list(sap.DEFAULT_METADATA_DENY_SET),
        "metadata_deny_set_version": "v1-2026-07-26",
        "special_purpose_address_registry_version": "iana-special-purpose-2026-07-26",
        "ipv6_transition_policy": {
            "well_known_prefixes": list(sap.DEFAULT_TRANSITION_PREFIXES),
            "decode_and_validate_embedded_ipv4": True,
            "operator_configured_nat64_prefixes": [],
        },
        "dns_policy": {"validate_every_answer": True, "bind_to_validated_address": True, "verify_connected_peer": True},
        "redirects": {"max_hops": 3, "revalidate_every_hop": True},
        "transport_fallback_allowed": False,
        "local_asset_carve_out": {
            "packet_internal_attachment_resolution": True,
            "out_of_packet_requires_operator_grant": True,
            "operator_grant_binds_path_and_digest": True,
            "producer_supplied_locator_type_hint_ignored": True,
        },
        "denial": {
            "leaks_denied_ids": False,
            "leaks_resolved_addresses": False,
            "leaks_text": False,
            "leaks_counts": False,
            "leaks_reason_code_differential": False,
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Canonicalization (contract §4.2.2, audit #3)
# ---------------------------------------------------------------------------


class TestCanonicalization:
    def test_ordinary_https_url_canonicalizes(self) -> None:
        canonical = sap.canonicalize_locator("https://Example.com/Path?q=1")
        assert canonical is not None
        assert canonical.host == "example.com"
        assert canonical.scheme == "https"
        assert canonical.port == 443
        assert canonical.path == "/Path"

    def test_non_http_scheme_rejected(self) -> None:
        assert sap.canonicalize_locator("file:///etc/passwd") is None
        assert sap.canonicalize_locator("ftp://example.com/") is None

    def test_embedded_credentials_rejected(self) -> None:
        assert sap.canonicalize_locator("http://user:pass@example.com/") is None
        assert sap.canonicalize_locator("http://user@example.com/") is None

    def test_percent_encoded_host_rejected(self) -> None:
        assert sap.canonicalize_locator("http://ex%61mple.com/") is None

    def test_ipv6_zone_id_rejected(self) -> None:
        assert sap.canonicalize_locator("http://[fe80::1%25eth0]/") is None

    @pytest.mark.parametrize(
        "locator",
        [
            "http://2130706433/",  # decimal-encoded 127.0.0.1
            "http://0x7f000001/",  # hex-encoded
            "http://127.1/",  # short dotted form
            "http://017700000001/",  # octal-looking single label
        ],
    )
    def test_ambiguous_numeric_host_rejected(self, locator: str) -> None:
        assert sap.canonicalize_locator(locator) is None

    def test_canonical_dotted_quad_ipv4_accepted_as_literal(self) -> None:
        canonical = sap.canonicalize_locator("http://93.184.216.34/")
        assert canonical is not None
        assert canonical.is_ip_literal is True
        assert str(canonical.ip) == "93.184.216.34"

    def test_multiple_trailing_dots_rejected(self) -> None:
        assert sap.canonicalize_locator("http://example.com../") is None

    def test_single_trailing_dot_stripped(self) -> None:
        canonical = sap.canonicalize_locator("http://example.com./")
        assert canonical is not None
        assert canonical.host == "example.com"

    def test_idna_hostname_normalizes(self) -> None:
        canonical = sap.canonicalize_locator("https://例え.jp/")
        assert canonical is not None
        assert canonical.host.startswith("xn--")

    def test_https_to_ip_literal_rejected(self) -> None:
        # SNI/cert-hostname verification is not meaningfully definable
        # against a bare IP literal -- v1 restricts HTTPS to named hosts.
        assert sap.canonicalize_locator("https://93.184.216.34/") is None

    def test_disallowed_scheme_by_policy(self) -> None:
        assert sap.canonicalize_locator("http://example.com/", allowed_schemes=("https",)) is None

    def test_oversize_locator_rejected(self) -> None:
        assert sap.canonicalize_locator("http://example.com/" + "a" * 9000) is None

    def test_control_characters_rejected(self) -> None:
        assert sap.canonicalize_locator("http://example.com/\r\nSet-Cookie: x") is None


# ---------------------------------------------------------------------------
# Forbidden-address category matrix (contract §4.2.4)
# ---------------------------------------------------------------------------


class TestForbiddenAddressCategories:
    @pytest.mark.parametrize(
        ("address", "expected_category"),
        [
            ("127.0.0.1", sap.CATEGORY_LOOPBACK),
            # "::1" and "::" are intentionally exercised separately below --
            # both fall within the frozen ::/96 (deprecated IPv4-compatible)
            # transition prefix by construction (their first 96 bits are
            # zero), so `forbidden_address_category` reports
            # ipv6_transition_or_translation for them (checked first) rather
            # than loopback/unspecified. Both categories deny identically;
            # this is a genuine overlap in the frozen policy's own prefix
            # list, not an implementation bug.
            ("10.0.0.5", sap.CATEGORY_PRIVATE),
            ("172.16.0.5", sap.CATEGORY_PRIVATE),
            ("192.168.1.5", sap.CATEGORY_PRIVATE),
            ("169.254.1.1", sap.CATEGORY_LINK_LOCAL),
            ("fe80::1", sap.CATEGORY_LINK_LOCAL),
            ("224.0.0.1", sap.CATEGORY_MULTICAST),
            ("0.0.0.0", sap.CATEGORY_UNSPECIFIED),
            ("100.64.0.1", sap.CATEGORY_CGNAT),
            ("192.0.2.1", sap.CATEGORY_BENCHMARK),
            ("198.51.100.1", sap.CATEGORY_BENCHMARK),
            ("203.0.113.1", sap.CATEGORY_BENCHMARK),
            ("198.18.0.1", sap.CATEGORY_BENCHMARK),
            ("2001:db8::1", sap.CATEGORY_BENCHMARK),
            ("169.254.169.254", sap.CATEGORY_METADATA),
            ("169.254.169.253", sap.CATEGORY_METADATA),
            ("100.100.100.200", sap.CATEGORY_METADATA),
            ("fd00:ec2::254", sap.CATEGORY_METADATA),
        ],
    )
    def test_denied_categories(self, address: str, expected_category: str) -> None:
        policy = _policy()
        result = sap.forbidden_address_category(ipaddress.ip_address(address), policy)
        assert result == expected_category

    def test_globally_routable_address_permitted(self) -> None:
        policy = _policy()
        assert sap.forbidden_address_category(ipaddress.ip_address("93.184.216.34"), policy) is None
        assert sap.forbidden_address_category(ipaddress.ip_address("2606:2800:220:1::1"), policy) is None

    @pytest.mark.parametrize("address", ["::1", "::"])
    def test_ipv4_compatible_overlap_addresses_still_denied(self, address: str) -> None:
        # Both fall within ::/96 (deprecated IPv4-compatible) by construction
        # -- denied either way, via the transition-prefix category checked
        # first (see the note above the parametrize table).
        policy = _policy()
        result = sap.forbidden_address_category(ipaddress.ip_address(address), policy)
        assert result in (sap.CATEGORY_IPV6_TRANSITION, sap.CATEGORY_LOOPBACK, sap.CATEGORY_UNSPECIFIED)

    @pytest.mark.parametrize(
        "address",
        [
            "64:ff9b::808:808",  # NAT64 well-known /96, embeds 8.8.8.8
            "64:ff9b:1::a00:2",  # NAT64 local-use /48
            "2002:c000:0201::1",  # 6to4
            "2001:0:4136:e378:8000:63bf:3fff:fdd2",  # Teredo
            "::ffff:127.0.0.1",  # IPv4-mapped
            "::7f00:1",  # IPv4-compatible (deprecated) 127.0.0.1
        ],
    )
    def test_ipv6_transition_prefixes_categorically_denied(self, address: str) -> None:
        policy = _policy()
        result = sap.forbidden_address_category(ipaddress.ip_address(address), policy)
        assert result == sap.CATEGORY_IPV6_TRANSITION

    def test_operator_configured_nat64_prefix_denied(self) -> None:
        policy = _policy(
            ipv6_transition_policy={
                "well_known_prefixes": list(sap.DEFAULT_TRANSITION_PREFIXES),
                "decode_and_validate_embedded_ipv4": True,
                "operator_configured_nat64_prefixes": ["2001:db8:64::/96"],
            }
        )
        result = sap.forbidden_address_category(
            ipaddress.ip_address("2001:db8:64::808:808"), policy, operator_nat64_prefixes=["2001:db8:64::/96"]
        )
        assert result == sap.CATEGORY_IPV6_TRANSITION

    def test_decode_embedded_ipv4_nat64(self) -> None:
        embedded = sap.decode_embedded_ipv4(ipaddress.IPv6Address("64:ff9b::808:808"))
        assert str(embedded) == "8.8.8.8"

    def test_decode_embedded_ipv4_6to4(self) -> None:
        embedded = sap.decode_embedded_ipv4(ipaddress.IPv6Address("2002:c000:0201::1"))
        assert str(embedded) == "192.0.2.1"

    def test_metadata_hostname_denied_by_name(self) -> None:
        policy = _policy()
        assert sap.hostname_denied_by_metadata_set("metadata.google.internal", policy) is True
        assert sap.hostname_denied_by_metadata_set("metadata.azure.com", policy) is True
        assert sap.hostname_denied_by_metadata_set("example.com", policy) is False

    def test_category_disabled_in_policy_is_permitted(self) -> None:
        # multicast is chosen because it does not overlap with any other
        # enabled category (unlike loopback, which stdlib ipaddress also
        # classifies as `is_private` -- disabling only `loopback` would
        # still deny via the broader `private` category).
        categories = [c for c in sap.DEFAULT_FORBIDDEN_CATEGORIES if c != sap.CATEGORY_MULTICAST]
        policy = _policy(forbidden_address_categories=categories)
        assert sap.forbidden_address_category(ipaddress.ip_address("224.0.0.1"), policy) is None


# ---------------------------------------------------------------------------
# Round-2 audit #10 -- IPv6 site-local (fec0::/10) must be categorically
# denied. Neither is_private nor is_reserved covers it under stdlib
# ipaddress, so it needs its own explicit category and prefix check.
# ---------------------------------------------------------------------------


class TestIPv6SiteLocalDenied:
    def test_site_local_denied_by_category(self) -> None:
        policy = _policy()
        result = sap.forbidden_address_category(ipaddress.ip_address("fec0::1"), policy)
        assert result == sap.CATEGORY_IPV6_SITE_LOCAL

    def test_site_local_not_caught_by_private_or_reserved_alone(self) -> None:
        # Documents WHY a dedicated category is required: stdlib classifies
        # fec0::1 as neither private nor reserved, so relying on those
        # broader checks alone (as before this fix) silently permits it.
        addr = ipaddress.ip_address("fec0::1")
        assert addr.is_private is False
        assert addr.is_reserved is False

    def test_acquire_denies_injected_resolver_returning_site_local(self) -> None:
        # Reproduces the auditor's exact scenario: an injected resolver
        # returns fec0::1 and it must be denied before any connection.
        connect, calls = _connector_sequence([_http_response(200)])
        outcome = sap.acquire(
            "http://example.com/report",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET6, "fec0::1")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == f"forbidden_address:{sap.CATEGORY_IPV6_SITE_LOCAL}"
        assert len(calls) == 0


# ---------------------------------------------------------------------------
# Round-2 audit #11 -- a malformed operator-configured NAT64 prefix must
# deny the WHOLE policy closed rather than being silently discarded.
# ---------------------------------------------------------------------------


class TestOperatorNat64PrefixFailsClosed:
    def test_non_canonical_prefix_raises_from_forbidden_address_category(self) -> None:
        # "2600:abcd:1234::1/96" has host bits set -- not a canonical
        # network -- and must raise rather than being silently dropped.
        policy = _policy(
            ipv6_transition_policy={
                "well_known_prefixes": list(sap.DEFAULT_TRANSITION_PREFIXES),
                "decode_and_validate_embedded_ipv4": True,
                "operator_configured_nat64_prefixes": ["2600:abcd:1234::1/96"],
            }
        )
        with pytest.raises(sap.AcquisitionPolicyError):
            sap.forbidden_address_category(
                ipaddress.ip_address("2606:2800:220:1::1"),
                policy,
                operator_nat64_prefixes=["2600:abcd:1234::1/96"],
            )

    def test_acquire_denies_whole_request_closed_before_any_dns_or_connect(self) -> None:
        connect, calls = _connector_sequence([_http_response(200)])

        def resolve(host: str, port: int) -> Sequence[tuple[int, str]]:
            raise AssertionError("DNS must never be consulted once the policy itself is invalid")

        policy = _policy(
            ipv6_transition_policy={
                "well_known_prefixes": list(sap.DEFAULT_TRANSITION_PREFIXES),
                "decode_and_validate_embedded_ipv4": True,
                "operator_configured_nat64_prefixes": ["2600:abcd:1234::1/96"],
            }
        )
        outcome = sap.acquire(
            "http://example.com/report",
            policy=policy,
            resolver=resolve,
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == sap.DENIAL_POLICY_INVALID
        assert len(calls) == 0

    def test_canonical_operator_prefix_still_works(self) -> None:
        # The fail-closed remediation must not break the legitimate,
        # additive use of operator_configured_nat64_prefixes.
        policy = _policy(
            ipv6_transition_policy={
                "well_known_prefixes": list(sap.DEFAULT_TRANSITION_PREFIXES),
                "decode_and_validate_embedded_ipv4": True,
                "operator_configured_nat64_prefixes": ["2001:db8:64::/96"],
            }
        )
        result = sap.forbidden_address_category(
            ipaddress.ip_address("2001:db8:64::808:808"),
            policy,
            operator_nat64_prefixes=["2001:db8:64::/96"],
        )
        assert result == sap.CATEGORY_IPV6_TRANSITION


# ---------------------------------------------------------------------------
# Fake socket/resolver doubles -- no real network access.
# ---------------------------------------------------------------------------


class _FakeSocket:
    def __init__(self, response: bytes, *, peer: tuple[str, int] = ("93.184.216.34", 443)) -> None:
        self._buf = io.BytesIO(response)
        self._peer = peer
        self.sent = b""
        self.closed = False

    def getpeername(self) -> tuple[str, int]:
        return self._peer

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def makefile(self, *_args: object, **_kwargs: object) -> io.BytesIO:
        return self._buf

    def close(self) -> None:
        self.closed = True


def _http_response(status: int = 200, headers: dict[str, str] | None = None, body: bytes = b"hello world") -> bytes:
    headers = dict(headers or {})
    headers.setdefault("Content-Length", str(len(body)))
    headers.setdefault("Content-Type", "text/plain")
    header_text = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    return f"HTTP/1.1 {status} STATUS\r\n{header_text}\r\n".encode("ascii") + body


def _resolver(answers: Sequence[tuple[int, str]]) -> sap.Resolver:
    def resolve(host: str, port: int) -> Sequence[tuple[int, str]]:
        return answers

    return resolve


def _connector_sequence(responses: Sequence[bytes], *, peers: Sequence[tuple[str, int]] | None = None) -> tuple[sap.Connector, list[tuple[str, int, int]]]:
    calls: list[tuple[str, int, int]] = []

    def connect(ip: str, port: int, family: int, timeout: float) -> socket.socket:
        idx = len(calls)
        calls.append((ip, port, family))
        response = responses[min(idx, len(responses) - 1)]
        peer = peers[idx] if peers else (ip, port)
        return _FakeSocket(response, peer=peer)  # type: ignore[return-value]

    return connect, calls


# ---------------------------------------------------------------------------
# acquire() -- happy path, mixed DNS answers, rebinding, redirects
# ---------------------------------------------------------------------------


class TestAcquireWithFakes:
    def test_successful_acquisition(self) -> None:
        connect, calls = _connector_sequence([_http_response(200, body=b"acquired content")])
        outcome = sap.acquire(
            "http://example.com/report",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is True
        assert outcome.content == b"acquired content"
        assert outcome.status_code == 200
        assert len(calls) == 1
        assert calls[0][0] == "93.184.216.34"

    def test_mixed_dns_answers_deny_without_connecting(self) -> None:
        connect, calls = _connector_sequence([_http_response(200)])
        outcome = sap.acquire(
            "http://example.com/report",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34"), (socket.AF_INET, "10.0.0.5")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code.startswith("forbidden_address:")
        assert len(calls) == 0  # never connects when any answer is forbidden

    def test_all_forbidden_dns_answers_deny(self) -> None:
        connect, calls = _connector_sequence([_http_response(200)])
        outcome = sap.acquire(
            "http://internal.example.com/",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "10.0.0.5")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == "forbidden_address:private"
        assert len(calls) == 0

    def test_dns_rebinding_peer_mismatch_denied(self) -> None:
        # Resolver validates a public address, but the actual connected peer
        # (simulating a post-validation rebind) is a different address --
        # this MUST be denied even though the validated answer was fine.
        connect, calls = _connector_sequence(
            [_http_response(200)], peers=[("10.0.0.9", 80)]
        )
        outcome = sap.acquire(
            "http://example.com/",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == "peer_mismatch"
        assert len(calls) == 1  # connected once, then denied before sending

    def test_no_dns_answers_denies(self) -> None:
        connect, calls = _connector_sequence([_http_response(200)])
        outcome = sap.acquire("http://nowhere.example.com/", policy=_policy(), resolver=_resolver([]), connect=connect)
        assert outcome.ok is False
        assert outcome.denial_code == sap.DENIAL_UNAVAILABLE
        assert len(calls) == 0

    def test_redirect_chain_followed_and_revalidated(self) -> None:
        connect, calls = _connector_sequence(
            [
                _http_response(302, headers={"Location": "http://example.com/final"}),
                _http_response(200, body=b"final content"),
            ]
        )
        outcome = sap.acquire(
            "http://example.com/start",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is True
        assert outcome.content == b"final content"
        assert outcome.hops == 1
        assert len(calls) == 2

    def test_redirect_limit_exceeded_denies(self) -> None:
        connect, calls = _connector_sequence(
            [_http_response(302, headers={"Location": "http://example.com/again"})]
        )
        outcome = sap.acquire(
            "http://example.com/start",
            policy=_policy(redirects={"max_hops": 1, "revalidate_every_hop": True}),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == "redirect_limit_exceeded"
        assert len(calls) == 2  # initial + one allowed hop, then denies on the second

    def test_redirect_to_forbidden_address_denies_on_revalidation(self) -> None:
        connect, calls = _connector_sequence(
            [_http_response(302, headers={"Location": "http://internal.example.com/secret"})]
        )

        def resolve(host: str, port: int) -> Sequence[tuple[int, str]]:
            if host == "internal.example.com":
                return [(socket.AF_INET, "10.0.0.5")]
            return [(socket.AF_INET, "93.184.216.34")]

        outcome = sap.acquire("http://example.com/start", policy=_policy(), resolver=resolve, connect=connect)
        assert outcome.ok is False
        assert outcome.denial_code == "forbidden_address:private"
        assert len(calls) == 1  # only the first (public) hop actually connected

    def test_redirect_with_malformed_ipv6_location_denies_closed(self) -> None:
        # Round-2 audit #12: `Location: http://[::1` (unterminated IPv6
        # literal) makes urljoin()/urlsplit() themselves raise ValueError.
        # This MUST deny closed, never propagate an unhandled exception and
        # abort the import.
        connect, calls = _connector_sequence(
            [_http_response(302, headers={"Location": "http://[::1"})]
        )
        outcome = sap.acquire(
            "http://example.com/start",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == "redirect_malformed_location"
        assert outcome.status_code == 302
        assert len(calls) == 1  # only the initial hop connects

    def test_redirect_to_non_http_scheme_denies(self) -> None:
        connect, calls = _connector_sequence(
            [_http_response(302, headers={"Location": "file:///etc/passwd"})]
        )
        outcome = sap.acquire(
            "http://example.com/start",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == "redirect_non_http_scheme"

    def test_non_2xx_status_denies(self) -> None:
        connect, _calls = _connector_sequence([_http_response(500, body=b"error")])
        outcome = sap.acquire(
            "http://example.com/",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is False
        assert outcome.status_code == 500
        assert outcome.denial_code == sap.DENIAL_UNAVAILABLE

    def test_connect_failure_denies_no_fallback(self) -> None:
        def failing_connect(ip: str, port: int, family: int, timeout: float) -> socket.socket:
            raise OSError("connection refused")

        outcome = sap.acquire(
            "http://example.com/",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=failing_connect,
        )
        assert outcome.ok is False
        assert outcome.denial_code == sap.DENIAL_UNAVAILABLE

    def test_ip_literal_locator_bypasses_dns_but_not_the_address_check(self) -> None:
        connect, calls = _connector_sequence([_http_response(200)])
        outcome = sap.acquire("http://127.0.0.1/", policy=_policy(), connect=connect)
        assert outcome.ok is False
        assert outcome.denial_code == "forbidden_address:loopback"
        assert len(calls) == 0

    def test_environment_proxy_variables_have_no_effect(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:3128")
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.internal:3128")
        monkeypatch.setenv("NO_PROXY", "")
        connect, calls = _connector_sequence([_http_response(200, body=b"direct")])
        outcome = sap.acquire(
            "http://example.com/",
            policy=_policy(),
            resolver=_resolver([(socket.AF_INET, "93.184.216.34")]),
            connect=connect,
        )
        assert outcome.ok is True
        assert outcome.content == b"direct"
        # The connector was called with the real target address, never a
        # proxy host -- this module never reads *_PROXY at all.
        assert calls[0][0] == "93.184.216.34"

    def test_metadata_hostname_denied_before_dns(self) -> None:
        def resolve(host: str, port: int) -> Sequence[tuple[int, str]]:
            raise AssertionError("DNS must never be consulted for a metadata-deny-listed hostname")

        outcome = sap.acquire("http://metadata.google.internal/latest", policy=_policy(), resolver=resolve)
        assert outcome.ok is False
        assert outcome.denial_code == f"forbidden_address:{sap.CATEGORY_METADATA}"


# ---------------------------------------------------------------------------
# Real local HTTP server smoke test (loopback only, no real network egress).
# ---------------------------------------------------------------------------


class _EchoHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        body = b"local stub server content"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def local_http_server() -> tuple[str, int]:
    server = http.server.HTTPServer(("127.0.0.1", 0), _EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "127.0.0.1", server.server_address[1]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_real_default_wiring_against_local_stub_server(local_http_server: tuple[str, int]) -> None:
    host, port = local_http_server
    # Loopback is forbidden by default policy -- this test constructs a
    # policy that permits it (test-only; production policies are always
    # schema-validated against the full, const-pinned category list, which
    # can never omit loopback) purely to prove the DEFAULT resolver/connect
    # wiring (real socket.getaddrinfo + real socket connect/peer-verify)
    # works end to end, not just the injectable seams. `private` is also
    # excluded because stdlib ipaddress classifies loopback as `is_private`
    # too, so it would otherwise still deny under the broader category.
    categories = [c for c in sap.DEFAULT_FORBIDDEN_CATEGORIES if c not in (sap.CATEGORY_LOOPBACK, sap.CATEGORY_PRIVATE)]
    outcome = sap.acquire(f"http://{host}:{port}/report", policy=_policy(forbidden_address_categories=categories))
    assert outcome.ok is True
    assert outcome.content == b"local stub server content"
    assert outcome.status_code == 200


def test_real_wiring_still_denies_loopback_under_default_policy(local_http_server: tuple[str, int]) -> None:
    host, port = local_http_server
    outcome = sap.acquire(f"http://{host}:{port}/report", policy=_policy())
    assert outcome.ok is False
    assert outcome.denial_code == "forbidden_address:loopback"
