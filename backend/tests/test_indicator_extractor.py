"""
Indicator extraction tests. One real precision bug was found and fixed
during development, encoded here as a permanent regression test:

A message merely containing the word "OTP" is ambiguous. "Your OTP is
483921" (a bank legitimately notifying someone of their own one-time
code, completely normal) and "Reply with your OTP to verify" (a
scammer asking someone to hand theirs over, a real red flag) both
matched the same broad keyword identically under the first version of
this module, even though they describe opposite situations. Only a
message requesting the OTP is actually suspicious. Fixed by requiring
a request verb (send, reply, share, provide, enter, confirm, give)
near the OTP mention, or trailing language like "required" or
"to verify".
"""
from app.indicator_extractor import extract_indicators


def test_legitimate_otp_notice_does_not_flag():
    """The core regression test: a bank sending someone their own OTP
    is completely normal and must not be treated as suspicious."""
    result = extract_indicators("Your OTP is 483921. Do not share with anyone.")
    assert result.requests_otp is False
    assert "requests_otp" not in result.flags


def test_otp_request_flags_as_suspicious():
    result = extract_indicators("Please reply with your OTP to verify your account")
    assert result.requests_otp is True
    assert "requests_otp" in result.flags


def test_send_otp_request_flags():
    result = extract_indicators("Send us your OTP to confirm")
    assert result.requests_otp is True


def test_enter_otp_request_flags():
    result = extract_indicators("Enter your OTP to proceed")
    assert result.requests_otp is True


def test_verify_your_otp_phrasing_flags():
    """
    Regression test: found missing during end-to-end multi-input
    testing. "Verify your OTP" is a common, real-world scam phrasing
    (a message urging someone to "verify" by handing over their code)
    that the original verb list (send, reply, share, provide, enter,
    confirm, give) did not include.
    """
    result = extract_indicators("MCB: verify your OTP to continue")
    assert result.requests_otp is True


def test_verification_code_notice_does_not_flag():
    result = extract_indicators("MCB verification code: 483921")
    assert result.requests_otp is False


def test_casual_mention_of_receiving_otp_does_not_flag():
    result = extract_indicators("Thanks, I received the OTP fine")
    assert result.requests_otp is False


def test_url_is_extracted():
    result = extract_indicators("Verify at http://mcb-secure-login.com now")
    assert "http://mcb-secure-login.com" in result.urls


def test_www_url_without_scheme_is_extracted():
    result = extract_indicators("Visit www.suspicious-site.com today")
    assert any("suspicious-site.com" in u for u in result.urls)


def test_phone_number_is_extracted():
    result = extract_indicators("Call +230 5789 1234 now")
    assert len(result.phone_numbers) == 1


def test_card_detail_request_flags():
    result = extract_indicators("Enter your card number and CVV to confirm")
    assert result.requests_card_details is True


def test_urgency_language_flags():
    result = extract_indicators("URGENT: your account will be suspended within 24 hours")
    assert result.creates_urgency is True


def test_money_transfer_request_flags():
    result = extract_indicators("Send money now to claim your prize")
    assert result.requests_money_transfer is True


def test_investment_promise_flags():
    result = extract_indicators("Guaranteed returns of 300% with this investment opportunity")
    assert result.mentions_investment_returns is True


def test_ordinary_message_has_no_flags():
    result = extract_indicators("Hey, are we still meeting for lunch tomorrow?")
    assert result.flags == []


def test_flags_property_reflects_multiple_triggers():
    result = extract_indicators(
        "URGENT: Enter your card number and CVV to confirm your identity within 24 hours."
    )
    assert set(result.flags) == {"requests_card_details", "urgency"}


def test_extraction_is_a_pure_function():
    """Same input must always produce an identical result, no hidden
    state, no randomness, matching this project's explainability
    principle."""
    text = "URGENT: Send your OTP to verify at http://fake.com"
    result1 = extract_indicators(text)
    result2 = extract_indicators(text)
    assert result1.flags == result2.flags
    assert result1.urls == result2.urls
