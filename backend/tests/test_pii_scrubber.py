"""
PII scrubber tests. Two real bugs were found and fixed during
development, both encoded here as permanent regression tests:

1. Sequential regex passes (each running over the previous pass's
   output) caused the OTP pattern to re-match digits inside an
   already-inserted card-mask placeholder, e.g. "[CARD ENDING 1111]"
   had its own "1111" re-redacted into "[CARD ENDING [REDACTED CODE]]".
   Fixed by matching every pattern against the original text once,
   then applying non-overlapping replacements by position.

2. The card-number regex greedily matched one trailing separator
   character past the last real digit, matching "4111 1111 1111 1111 "
   with a trailing space, which ate the space before the next word
   once replaced. Fixed by requiring the pattern to end on a digit.
"""
from app.pii_scrubber import scrub_message


def test_otp_shaped_code_is_masked():
    result = scrub_message("Your OTP is 483921, do not share it")
    assert "483921" not in result
    assert "[REDACTED CODE]" in result


def test_card_number_masked_showing_only_last_four():
    result = scrub_message("Card number: 4111 1111 1111 1111 expires soon")
    assert "4111 1111 1111" not in result
    assert "[CARD ENDING 1111]" in result


def test_card_number_does_not_eat_trailing_space():
    """
    Regression test for the greedy-trailing-separator bug: the space
    between the masked card number and the following word must be
    preserved, not consumed by the regex match.
    """
    result = scrub_message("Card number: 4111 1111 1111 1111 expires soon")
    assert "1111] expires" in result
    assert "1111]expires" not in result


def test_card_mask_is_not_itself_re_redacted_as_otp():
    """
    Regression test for the sequential-pass corruption bug: the "1111"
    inside "[CARD ENDING 1111]" must survive intact, not get caught by
    the OTP pattern in a later pass.
    """
    result = scrub_message("Card number: 4111 1111 1111 1111 expires soon")
    assert "[CARD ENDING 1111]" in result
    assert "[CARD ENDING [REDACTED CODE]]" not in result


def test_email_address_partially_masked():
    result = scrub_message("Contact us at support@fakebank.com")
    assert "support@fakebank.com" not in result
    assert "@fakebank.com" in result
    assert result.startswith("Contact us at s")


def test_short_email_local_part_fully_masked():
    result = scrub_message("Email: ab@test.com")
    assert "ab@test.com" not in result
    assert "**@test.com" in result


def test_phone_number_masked():
    result = scrub_message("Call us on +230 5789 1234 immediately")
    assert "5789" not in result
    assert "[REDACTED PHONE]" in result


def test_short_digit_run_treated_as_otp():
    result = scrub_message("Your account 1234 will be suspended")
    assert "1234" not in result
    assert "[REDACTED CODE]" in result


def test_message_with_no_pii_is_unchanged():
    text = "No sensitive data here at all"
    assert scrub_message(text) == text


def test_multiple_pii_types_in_one_message_all_masked():
    result = scrub_message("Card 4111-1111-1111-1111 and OTP 4829 both in one message")
    assert "4111-1111-1111-1111" not in result
    assert "4829" not in result
    assert "[CARD ENDING 1111]" in result
    assert "[REDACTED CODE]" in result
    assert "both in one message" in result


def test_realistic_scam_message_fully_scrubbed():
    original = "MCB: Your account has been suspended. Send your OTP to 483921 now."
    result = scrub_message(original)
    assert "483921" not in result
    assert "MCB" in result
    assert "suspended" in result
