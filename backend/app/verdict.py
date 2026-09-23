"""
Combines the registry match result, the deterministic indicator
extraction result, and the (currently stubbed) AI pattern-match result
into a single overall verdict.

This is deliberately its own module, separate from entity_matcher.py,
indicator_extractor.py, and wherever the AI call eventually lives, so
the combination logic is visible and testable on its own. This is the
"AI explains, code decides" principle in concrete form: this function
is what actually decides the verdict, and it works correctly today
using the registry and indicator signals alone, with the AI signal
folded in as a third input once it exists.
"""
from typing import Optional, List

AI_HIGH_RISK_SCORE = 0.7
AI_SUSPICIOUS_SCORE = 0.4

# Indicator flags treated as high-risk on their own — these describe a
# message actively asking for a credential or money movement, or a
# link that has been checked and found to actively misrepresent its
# origin, not just a topic mention. Requiring the SAME message to also
# fail the registry check before reaching high_risk (see
# derive_verdict) would under-flag a well-crafted scam impersonating a
# sender name that doesn't happen to be in the registry snapshot at
# all (no_sender_given) — these flags are serious enough to matter
# independent of the registry outcome.
HIGH_RISK_INDICATOR_FLAGS = {"requests_otp", "requests_card_details", "domain_mismatch", "phone_mismatch"}

# Indicator flags that raise concern but are common enough in
# legitimate messages (a real limited-time offer, a real courier
# tracking link, a domain with an unusual but not inherently malicious
# structure) that they alone should only bump the verdict to
# "suspicious", not "high_risk". Deliberately does NOT include
# "contains_url" on its own — a bare link is present in most
# legitimate business messages (a real bank's own statement link,
# a courier tracking link) and is not itself a red flag; what actually
# matters about a URL is covered more precisely by domain_mismatch
# (high risk) and suspicious_domain_structure (here) once a domain has
# actually been checked. Found in testing: a genuinely legitimate
# message with a real bank's real domain was landing on "suspicious"
# purely for containing a link at all, which is too aggressive and
# undermines trust in the "safe" verdict for completely ordinary
# messages.
SUSPICIOUS_INDICATOR_FLAGS = {"urgency", "payment_request", "investment_promise", "suspicious_domain_structure"}


def _indicator_verdict(indicator_flags: Optional[List[str]]) -> str:
    if not indicator_flags:
        return "safe"
    flag_set = set(indicator_flags)
    if flag_set & HIGH_RISK_INDICATOR_FLAGS:
        return "high_risk"
    if flag_set & SUSPICIOUS_INDICATOR_FLAGS:
        return "suspicious"
    return "safe"


def derive_verdict(registry_result: dict, ai_risk_score, indicator_flags: Optional[List[str]] = None) -> str:
    """
    Returns one of: safe, suspicious, high_risk.

    Three independent signals are combined by taking whichever is most
    severe — never averaged, never allowed to cancel each other out.
    A message from a VERIFIED sender that also requests an OTP must
    still surface as high_risk: registry verification establishes the
    claimed sender's name is real, it says nothing about whether THIS
    message is legitimate (a real institution's name can be attached
    to a fraudulent message just as easily as a fake one). See this
    module's docstring and README's "Responsible use" section for why
    that distinction is treated as load-bearing throughout this project,
    not just a footnote.

    Must work correctly with ai_risk_score=None and indicator_flags=None,
    since the AI layer is not wired in yet, and every check made before
    it exists still needs a sensible result from the other two signals.
    """
    registry_status = registry_result["status"]

    if registry_status == "name_mismatch":
        # A name that closely matches a real entity but doesn't exactly
        # verify is inherently the most suspicious registry outcome,
        # the shape of a potential impersonation attempt, not just an
        # unknown sender.
        registry_verdict = "high_risk"
    elif registry_status == "revoked":
        # An exact match to a real entity whose license is no longer
        # active — a genuine, sourced reason for caution, but distinct
        # from active impersonation of a still-legitimate name. Landed
        # at suspicious rather than high_risk: the claim IS accurate
        # about which entity it's referencing, the concern is that
        # entity's current standing, not a spoofed identity.
        registry_verdict = "suspicious"
    elif registry_status == "not_found":
        registry_verdict = "suspicious"
    elif registry_status == "verified":
        registry_verdict = "safe"
    else:
        # no_sender_given or registry_unavailable — the registry signal
        # is not meaningful either way, so it contributes nothing to
        # the combined verdict rather than defaulting to "safe" and
        # potentially masking a real indicator or AI signal.
        registry_verdict = "safe"

    indicator_verdict = _indicator_verdict(indicator_flags)

    if ai_risk_score is None:
        ai_verdict = "safe"
    elif ai_risk_score >= AI_HIGH_RISK_SCORE:
        ai_verdict = "high_risk"
    elif ai_risk_score >= AI_SUSPICIOUS_SCORE:
        ai_verdict = "suspicious"
    else:
        ai_verdict = "safe"

    severity_order = {"safe": 0, "suspicious": 1, "high_risk": 2}
    return max(
        [registry_verdict, indicator_verdict, ai_verdict],
        key=lambda v: severity_order[v],
    )
