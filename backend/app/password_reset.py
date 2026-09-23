"""
Password reset. No real email provider is configured, the reset link
is logged server-side instead of emailed, clearly labeled as a
stand-in so it's never mistaken for a real email having been sent.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app import models, security

logger = logging.getLogger("fraudlens")

RESET_TOKEN_EXPIRY_MINUTES = 30


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _deliver_reset_link(email: str, reset_link: str) -> None:
    logger.info(
        "[PASSWORD RESET - NO EMAIL PROVIDER CONFIGURED] Reset link for %s (would normally be emailed): %s",
        email,
        reset_link,
    )


def request_password_reset(db: Session, email: str, frontend_base_url: str) -> None:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        return

    raw_token = secrets.token_urlsafe(32)
    reset_token = models.PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    )
    db.add(reset_token)
    db.commit()

    reset_link = f"{frontend_base_url}/reset-password?token={raw_token}"
    _deliver_reset_link(user.email, reset_link)


def verify_reset_token(db: Session, raw_token: str):
    token_hash = _hash_token(raw_token)
    record = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if record is None or record.used_at is not None or record.expires_at < datetime.utcnow():
        return None

    return db.query(models.User).filter(models.User.id == record.user_id).first()


def consume_reset_token(db: Session, raw_token: str, new_password: str):
    token_hash = _hash_token(raw_token)
    record = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if record is None or record.used_at is not None or record.expires_at < datetime.utcnow():
        return None

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    if user is None:
        return None

    user.hashed_password = security.hash_password(new_password)
    user.tokens_valid_after = datetime.utcnow().replace(microsecond=0)
    record.used_at = datetime.utcnow()

    db.add(user)
    db.add(record)
    db.commit()
    return user
