"""
Email verification, tracked but NOT enforced. Signing up, logging in,
and using every feature work identically whether or not the email has
been verified, deliberate for a hackathon demo where forcing
verification would block a judge or teammate from trying the app
immediately with a real-looking but unreachable email.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger("fraudlens")

VERIFICATION_TOKEN_EXPIRY_HOURS = 24


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _deliver_verification_link(email: str, verify_link: str) -> None:
    logger.info(
        "[EMAIL VERIFICATION - NO EMAIL PROVIDER CONFIGURED] Verification link for %s (would normally be emailed): %s",
        email,
        verify_link,
    )


def send_verification_email(db: Session, user, frontend_base_url: str) -> None:
    raw_token = secrets.token_urlsafe(32)
    token = models.EmailVerificationToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS),
    )
    db.add(token)
    db.commit()

    verify_link = f"{frontend_base_url}/verify-email?token={raw_token}"
    _deliver_verification_link(user.email, verify_link)


def confirm_email_verification(db: Session, raw_token: str):
    token_hash = _hash_token(raw_token)
    record = (
        db.query(models.EmailVerificationToken)
        .filter(models.EmailVerificationToken.token_hash == token_hash)
        .first()
    )
    if record is None or record.used_at is not None or record.expires_at < datetime.utcnow():
        return None

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if user is None:
        return None

    user.email_verified_at = datetime.utcnow()
    record.used_at = datetime.utcnow()

    db.add(user)
    db.add(record)
    db.commit()
    return user


def resend_verification_email(db: Session, email: str, frontend_base_url: str) -> None:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or user.email_verified_at is not None:
        return
    send_verification_email(db, user, frontend_base_url)
