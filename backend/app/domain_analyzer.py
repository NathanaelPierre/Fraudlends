"""
Domain and URL analysis: given a URL found in a message (see
app/indicator_extractor.py, which already extracts these), checks
whether its domain plausibly belongs to whichever institution the
message claims to be from.

This resolves a real gap the registry/entity check alone cannot:
"MCB: verify at mcb-online-secure.net" has a sender name that may or
may not verify, but the actual danger is the domain, a lookalike of
the real mcb.mu the message is trying to pass off as legitimate. This
module is deliberately deterministic and local, same reasoning as
entity_matcher.py: checking a small, curated table of known official
domains (registry_data.py's KNOWN_OFFICIAL_DOMAINS) is instant and
reliable; a live "is this really MCB's domain" web search would be
slow, would not actually resolve the ambiguity in most cases (most
institutions don't publish a definitive list of their own domains),
and would reintroduce the external network dependency the local-only
architecture is built to avoid.

Deliberately does not fetch the URL's content, inspecting a URL string
is safe, making the server request an arbitrary user-submitted URL is
a real SSRF risk (an attacker could point it at an internal service)
and is out of scope here. If live URL content fetching is ever added,
it must go through an isolated fetch service with strict network
restrictions, see README's "Known limitations" for this being named
explicitly rather than silently skipped.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, List
from urllib.parse import urlparse

from app.registry_data import KNOWN_OFFICIAL_DOMAINS

_DOMAIN_TO_ENTITY = {}
for _entity_name, _domains in KNOWN_OFFICIAL_DOMAINS.items():
    for _domain in _domains:
        _DOMAIN_TO_ENTITY[_domain.lower()] = _entity_name


@dataclass
class DomainAnalysisResult:
    url: str
    domain: Optional[str] = None
    status: str = "no_url"
    matched_entity: Optional[str] = None
    suspicious_reasons: List[str] = field(default_factory=list)


def _extract_root_domain(url: str) -> Optional[str]:
    """
    Pulls the hostname out of a URL, tolerating URLs missing a scheme
    (indicator_extractor.py's URL regex also matches bare
    "www.example.com" text without "http://").

    Two real bugs were found and fixed here during testing:

    1. Arbitrary non-URL text (e.g. "not a url at all") was silently
       treated as a valid hostname once "http://" was prepended
       unconditionally — urlparse doesn't reject a string just because
       it isn't shaped like a real domain. Fixed by requiring the
       input to contain at least one dot and no whitespace before
       attempting to parse it as a URL at all.

    2. A "www."-prefixed URL (e.g. "www.mcb.mu") returned
       "www.mcb.mu" as the domain, which never matches
       KNOWN_OFFICIAL_DOMAINS' bare-domain entries ("mcb.mu") — this
       would have made the feature silently fail to recognize the
       real domain for the huge fraction of real-world URLs that
       include the www. prefix. Fixed by stripping a leading "www."
       before comparison.
    """
    if not url or " " in url.strip() or "." not in url:
        return None

    candidate = url if "://" in url else f"http://{url}"
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    hostname = parsed.hostname
    if not hostname:
        return None

    hostname = hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def _check_suspicious_structure(domain: str) -> List[str]:
    """
    Deterministic red flags in a domain's own structure, independent
    of whether it matches any known entity, these are worth surfacing
    even for a domain not claiming to be a specific institution at all.
    """
    reasons = []

    is_raw_ip = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain))
    if is_raw_ip:
        reasons.append("domain_is_raw_ip_address")

    if "xn--" in domain:
        reasons.append("punycode_domain")

    # Only meaningful for an actual domain name — an IP address's
    # dot-separated octets are not "subdomains" and must not trigger
    # this check (found during testing: 192.168.1.1 was incorrectly
    # flagged with excessive_subdomain_depth on top of the already-
    # correct domain_is_raw_ip_address, a nonsensical combination since
    # the "reason" doesn't actually describe what's happening).
    if not is_raw_ip and domain.count(".") >= 3:
        reasons.append("excessive_subdomain_depth")

    suspicious_tlds = {"tk", "ml", "ga", "cf", "gq", "top", "xyz", "click", "link"}
    tld = domain.rsplit(".", 1)[-1] if "." in domain and not is_raw_ip else ""
    if tld in suspicious_tlds:
        reasons.append("uncommon_or_high_abuse_tld")

    return reasons


def analyze_domain(url: str, claimed_sender_entity: Optional[str] = None) -> DomainAnalysisResult:
    """
    claimed_sender_entity is the registry-matched entity name (e.g.
    from entity_matcher.match_entity()'s "matched_entity" field), not
    the raw user-typed claimed sender text — passing the raw text would
    make matching depend on the user having typed the exact formal
    name, defeating the point of already having resolved that via the
    registry and alias matching.
    """
    domain = _extract_root_domain(url)
    if domain is None:
        return DomainAnalysisResult(url=url, status="no_url")

    structural_flags = _check_suspicious_structure(domain)
    owning_entity = _DOMAIN_TO_ENTITY.get(domain)

    if claimed_sender_entity and owning_entity == claimed_sender_entity:
        return DomainAnalysisResult(
            url=url, domain=domain, status="matches_claimed_entity",
            matched_entity=owning_entity, suspicious_reasons=structural_flags,
        )

    if claimed_sender_entity and claimed_sender_entity in KNOWN_OFFICIAL_DOMAINS:
        return DomainAnalysisResult(
            url=url, domain=domain, status="known_domain_mismatch",
            matched_entity=claimed_sender_entity, suspicious_reasons=structural_flags,
        )

    if owning_entity:
        return DomainAnalysisResult(
            url=url, domain=domain, status="known_domain_mismatch",
            matched_entity=owning_entity, suspicious_reasons=structural_flags,
        )

    status = "suspicious_structure" if structural_flags else "unknown_domain"
    return DomainAnalysisResult(url=url, domain=domain, status=status, suspicious_reasons=structural_flags)
