"""
Tests for derive_verdict()'s combination of the registry signal, the
deterministic indicator signal, and the (optional) AI signal.

The most important property tested here: registry verification does
not mean a message is safe. A verified sender combined with a message
that requests an OTP must still surface as high_risk, this is the
"identity verification is not the same as message verification"
principle this project is built around, not an incidental detail.
"""
from app.verdict import derive_verdict

VERIFIED = {"status": "verified", "matched_entity": "MCB Ltd", "score": 1.0}
NOT_FOUND = {"status": "not_found", "matched_entity": None, "score": 0.3}
NAME_MISMATCH = {"status": "name_mismatch", "matched_entity": "MCB Ltd", "score": 0.85}
NO_SENDER = {"status": "no_sender_given", "matched_entity": None, "score": None}


REVOKED = {"status": "revoked", "matched_entity": "Trade T Capital Markets", "score": 1.0, "status_detail": "Surrendered, 30 June 2026"}


def test_verified_sender_with_no_other_signal_is_safe():
    assert derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=None) == "safe"


def test_not_found_sender_with_no_other_signal_is_suspicious():
    assert derive_verdict(NOT_FOUND, ai_risk_score=None, indicator_flags=None) == "suspicious"


def test_name_mismatch_with_no_other_signal_is_high_risk():
    assert derive_verdict(NAME_MISMATCH, ai_risk_score=None, indicator_flags=None) == "high_risk"


def test_revoked_entity_with_no_other_signal_is_suspicious():
    """A revoked/surrendered entity match is a real, sourced reason for
    caution (suspicious), but distinct from active impersonation of a
    still-legitimate name (high_risk) — the claimed identity is
    accurate, the concern is that entity's current standing."""
    assert derive_verdict(REVOKED, ai_risk_score=None, indicator_flags=None) == "suspicious"


def test_revoked_entity_with_otp_request_escalates_to_high_risk():
    result = derive_verdict(REVOKED, ai_risk_score=None, indicator_flags=["requests_otp"])
    assert result == "high_risk"


def test_no_sender_given_with_no_other_signal_is_safe():
    assert derive_verdict(NO_SENDER, ai_risk_score=None, indicator_flags=None) == "safe"


def test_verified_sender_with_otp_request_is_still_high_risk():
    """
    The core property this project is built around: a verified sender
    name does not make a message safe. A real institution's name can
    be attached to a fraudulent message just as easily as a fake one.
    """
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=["requests_otp"])
    assert result == "high_risk"


def test_verified_sender_with_card_request_is_still_high_risk():
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=["requests_card_details"])
    assert result == "high_risk"


def test_verified_sender_with_urgency_only_is_suspicious_not_high_risk():
    """Urgency alone is common enough in legitimate messages that it
    should raise concern (suspicious) without reaching the same
    severity as an explicit credential request (high_risk)."""
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=["urgency"])
    assert result == "suspicious"


def test_not_found_sender_with_otp_request_is_high_risk_not_diluted():
    """Two independently concerning signals must not cancel out or
    average down, the more severe one wins."""
    result = derive_verdict(NOT_FOUND, ai_risk_score=None, indicator_flags=["requests_otp"])
    assert result == "high_risk"


def test_verified_sender_with_no_indicator_flags_stays_safe():
    """A verified sender with a genuinely clean message (empty flags
    list) must not be dragged down by an empty-but-not-None list."""
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=[])
    assert result == "safe"


def test_verified_sender_with_only_a_url_stays_safe():
    """
    Regression test: a bare link alone must not push a genuinely clean
    message to "suspicious" — most legitimate business messages
    contain a link (a real bank's own statement link, a courier
    tracking link). This was found in live end-to-end testing: a real
    bank name plus its own real domain was landing on "suspicious"
    purely for containing a URL at all, which undermines trust in the
    "safe" verdict for completely ordinary messages.
    """
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=["contains_url"])
    assert result == "safe"


def test_high_ai_score_overrides_safe_registry_result():
    result = derive_verdict(VERIFIED, ai_risk_score=0.9, indicator_flags=None)
    assert result == "high_risk"


def test_low_ai_score_does_not_downgrade_high_risk_registry_result():
    """A low AI score must not dilute a high_risk registry finding,
    severity only ever goes up when combining signals, never down."""
    result = derive_verdict(NAME_MISMATCH, ai_risk_score=0.1, indicator_flags=None)
    assert result == "high_risk"


def test_all_three_signals_combine_to_worst_case():
    result = derive_verdict(NAME_MISMATCH, ai_risk_score=0.9, indicator_flags=["requests_otp"])
    assert result == "high_risk"


def test_multiple_indicator_flags_still_only_reach_high_risk_not_beyond():
    """There is no severity level beyond high_risk, multiple
    high-risk-triggering flags together must not error or produce an
    unexpected value."""
    result = derive_verdict(
        VERIFIED, ai_risk_score=None, indicator_flags=["requests_otp", "requests_card_details", "urgency"]
    )
    assert result == "high_risk"


def test_verified_sender_with_domain_mismatch_is_high_risk():
    """The core scenario domain_analyzer.py exists for: a verified
    sender name whose message links to a domain that does not belong
    to that sender — this must reach high_risk on its own, the same
    severity as an explicit credential request, since it represents a
    checked, confirmed identity-spoofing signal."""
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=["domain_mismatch"])
    assert result == "high_risk"


def test_suspicious_domain_structure_alone_is_suspicious_not_high_risk():
    """A structurally unusual domain (unfamiliar TLD, deep subdomain
    nesting) without a confirmed mismatch against a known sender
    domain is a real signal but a weaker one than an outright
    mismatch, landing at suspicious rather than high_risk."""
    result = derive_verdict(VERIFIED, ai_risk_score=None, indicator_flags=["suspicious_domain_structure"])
    assert result == "suspicious"
