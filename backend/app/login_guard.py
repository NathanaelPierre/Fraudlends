"""
Login brute-force protection: lockout after too many failed attempts
in a time window, keyed by email (not user_id) so it works identically
against unknown emails — an attacker can't distinguish "wrong password"
from "no such account" by how the lockout behaves.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models

MAX_FAILURES_PER_WINDOW = 5
LOCKOUT_WINDOW_MINUTES = 15


def check_login_allowed(db: Session, email: str):
    window_start = datetime.utcnow() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    recent_failures = (
        db.query(models.LoginAttempt)
        .filter(
            models.LoginAttempt.email == email,
            models.LoginAttempt.successful == False,  # noqa: E712
            models.LoginAttempt.attempted_at >= window_start,
        )
        .order_by(models.LoginAttempt.attempted_at.asc())
        .all()
    )
    if len(recent_failures) < MAX_FAILURES_PER_WINDOW:
        return True, 0

    oldest = recent_failures[0].attempted_at
    minutes_remaining = LOCKOUT_WINDOW_MINUTES - int((datetime.utcnow() - oldest).total_seconds() // 60)
    return False, max(minutes_remaining, 1)


def record_failed_login(db: Session, email: str):
    attempt = models.LoginAttempt(email=email, successful=False)
    db.add(attempt)
    db.commit()


def record_successful_login(db: Session, email: str):
    attempt = models.LoginAttempt(email=email, successful=True)
    db.add(attempt)
    db.commit()
