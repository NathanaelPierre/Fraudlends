"""
Domain analysis tests. This module resolves the specific scenario that
motivated its design: a message linking to a lookalike domain that
embeds a real institution's name (e.g. "mcb-online-secure.net" or a
subdomain trick like "secure.mcb.mu.verify-account.xyz") to appear
legitimate.

One real bug was found and fixed during development: an IP address's
dot-separated octets were incorrectly triggering the
excessive_subdomain_depth check (meant for actual subdomain nesting),
producing a nonsensical combination of flags for a raw IP URL.
"""
from app.domain_analyzer import analyze_domain

MCB = "The Mauritius Commercial Bank Ltd"


def test_real_domain_matches_claimed_entity():
    result = analyze_domain("http://mcb.mu/login", MCB)
    assert result.status == "matches_claimed_entity"
    assert result.domain == "mcb.mu"


def test_lookalike_domain_flagged_as_mismatch():
    result = analyze_domain("http://mcb-online-secure.net/verify", MCB)
    assert result.status == "known_domain_mismatch"
    assert result.matched_entity == MCB


def test_subdomain_trick_embedding_real_domain_flagged():
    result = analyze_domain("http://secure.mcb.mu.verify-account.xyz/login", MCB)
    assert result.status == "known_domain_mismatch"
    assert "excessive_subdomain_depth" in result.suspicious_reasons
    assert "uncommon_or_high_abuse_tld" in result.suspicious_reasons


def test_different_real_banks_domain_flagged_as_mismatch_not_verified():
    result = analyze_domain("http://absa.mu/login", MCB)
    assert result.status == "known_domain_mismatch"


def test_unknown_domain_with_no_claimed_sender():
    result = analyze_domain("http://totally-unknown-site.com", None)
    assert result.status == "unknown_domain"
    assert result.matched_entity is None


def test_raw_ip_address_flagged():
    result = analyze_domain("http://192.168.1.1/verify", MCB)
    assert "domain_is_raw_ip_address" in result.suspicious_reasons


def test_raw_ip_address_does_not_also_get_excessive_subdomain_flag():
    """
    Regression test for the real bug found during development: an IP
    address's dot-separated octets were incorrectly triggering
    excessive_subdomain_depth, a check meant for actual domain
    subdomain nesting, not IP notation.
    """
    result = analyze_domain("http://192.168.1.1/verify", MCB)
    assert "excessive_subdomain_depth" not in result.suspicious_reasons


def test_punycode_domain_flagged():
    result = analyze_domain("http://xn--mcb-verify-abc123.com", MCB)
    assert "punycode_domain" in result.suspicious_reasons


def test_suspicious_tld_flagged():
    result = analyze_domain("http://mcb-verify.tk", MCB)
    assert "uncommon_or_high_abuse_tld" in result.suspicious_reasons


def test_ordinary_common_tld_not_flagged():
    result = analyze_domain("http://mcb.mu", MCB)
    assert "uncommon_or_high_abuse_tld" not in result.suspicious_reasons


def test_no_url_returns_no_url_status():
    result = analyze_domain("not a url at all", None)
    assert result.status == "no_url"


def test_www_prefixed_url_without_scheme_is_handled():
    result = analyze_domain("www.mcb.mu", MCB)
    assert result.domain == "mcb.mu"
    assert result.status == "matches_claimed_entity"


def test_claimed_entity_with_no_known_domains_falls_back_to_generic_check():
    """An entity that is in the registry but has no entry in
    KNOWN_OFFICIAL_DOMAINS (most entities, since this table is
    deliberately small) must not error, and must not be reported as a
    false known_domain_mismatch against an entity we simply have no
    domain data for at all."""
    result = analyze_domain("http://some-random-site.com", "Some Entity With No Known Domain")
    assert result.status == "unknown_domain"
