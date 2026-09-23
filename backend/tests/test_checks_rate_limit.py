"""
Rate limiting on POST /checks: a fixed-window counter per user,
preventing automated abuse of the core feature.
"""
from datetime import datetime
from app.checks_rate_limit import check_and_record_check_call, MAX_CHECKS_PER_WINDOW


def _make_user(db_session, email="ratelimit@fraudlens.mu"):
    from app import models, security
    user = models.User(email=email, hashed_password=security.hash_password("testpass123"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_first_call_is_allowed(db_session):
    user = _make_user(db_session)
    assert check_and_record_check_call(db_session, user) is True
    assert user.checks_in_window == 1


def test_calls_within_limit_are_allowed(db_session):
    user = _make_user(db_session)
    for _ in range(MAX_CHECKS_PER_WINDOW):
        assert check_and_record_check_call(db_session, user) is True


def test_call_over_limit_is_rejected(db_session):
    user = _make_user(db_session)
    for _ in range(MAX_CHECKS_PER_WINDOW):
        check_and_record_check_call(db_session, user)
    assert check_and_record_check_call(db_session, user) is False


def test_rate_limit_is_per_user(db_session):
    user_a = _make_user(db_session, email="ratelimita@fraudlens.mu")
    user_b = _make_user(db_session, email="ratelimitb@fraudlens.mu")

    for _ in range(MAX_CHECKS_PER_WINDOW):
        check_and_record_check_call(db_session, user_a)
    assert check_and_record_check_call(db_session, user_a) is False

    assert check_and_record_check_call(db_session, user_b) is True


def test_endpoint_returns_429_when_rate_limited(client, auth_headers, db_session):
    """
    End-to-end: once the limit is hit, /checks itself must return 429,
    not silently degrade — unlike the LLM fallback pattern, this
    endpoint has no partial result to fall back to, the whole feature
    IS the analysis.
    """
    from app import models

    headers = auth_headers(email="endpointlimit@fraudlens.mu")
    user = db_session.query(models.User).filter(models.User.email == "endpointlimit@fraudlens.mu").first()
    user.checks_window_start = datetime.utcnow()
    user.checks_in_window = MAX_CHECKS_PER_WINDOW
    db_session.add(user)
    db_session.commit()

    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    assert r.status_code == 429


def test_endpoint_works_normally_under_the_limit(client, auth_headers):
    headers = auth_headers(email="normallimit@fraudlens.mu")
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    assert r.status_code == 200
