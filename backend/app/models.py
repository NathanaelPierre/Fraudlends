"""
Core data models.

User carries the full auth/security feature set proven out in an
earlier build (password reset, email verification, login lockout, JWT
revocation, LLM key management) since that infrastructure is
domain-agnostic and directly reusable here.

Check and RegistryEntity are new, specific to FraudLens: a Check is one
submitted message/request a user wants verified; RegistryEntity is a
locally-cached snapshot of the FSC Register of Licensees and the Bank
of Mauritius list of licensed banks, since checking a live external
site on every request would be slow and fragile for a demo.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    xai_api_key_encrypted = Column(Text, nullable=True)
    xai_key_last_used_at = Column(DateTime, nullable=True)

    llm_calls_window_start = Column(DateTime, nullable=True)
    llm_calls_in_window = Column(Integer, default=0)

    # Rate limiting for POST /checks — see app/checks_rate_limit.py
    checks_window_start = Column(DateTime, nullable=True)
    checks_in_window = Column(Integer, default=0)

    tokens_valid_after = Column(DateTime, nullable=True)

    email_verified_at = Column(DateTime, nullable=True)

    # Admin dashboard: role-gated access (see app/routers/admin.py) and
    # a suspension switch that piggybacks on the existing JWT
    # revocation mechanism (tokens_valid_after) so a suspended user's
    # existing sessions die immediately, not just their next login.
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    attempted_at = Column(DateTime, default=datetime.utcnow)
    successful = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String, nullable=False, index=True)
    detail = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class RegistryEntity(Base):
    __tablename__ = "registry_entities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    normalized_name = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    license_type = Column(String, nullable=True)
    status = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow)


class Check(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    message_text = Column(Text, nullable=False)
    claimed_sender = Column(String, nullable=True)

    registry_match_status = Column(String, nullable=False)
    registry_matched_entity = Column(String, nullable=True)
    registry_match_score = Column(Float, nullable=True)

    ai_risk_score = Column(Float, nullable=True)
    ai_flags = Column(JSON, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    explanation_source = Column(String, nullable=True)

    overall_verdict = Column(String, nullable=False)

    # User feedback on whether this verdict was correct — a real,
    # honest way to describe improvement over time (see README), not
    # an unverifiable claim. "correct" | "incorrect" | None (not yet
    # given). Deliberately not required at submission time; feedback
    # is a follow-up action a user takes after reading the result, not
    # part of the check itself.
    user_feedback = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
