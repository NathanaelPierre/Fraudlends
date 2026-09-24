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


class EducationTopic(Base):
    """
    A single fraud-awareness lesson snippet — the content bank behind
    both the daily-advice rotation and the chat companion's factual
    grounding. Deliberately a plain content table, not AI-generated:
    the actual fraud-awareness FACTS (never share an OTP, verify
    through official channels, etc.) are stable, well-established
    guidance that doesn't need — and shouldn't wait for — an AI model
    to state correctly. The AI layer's future role is explaining and
    personalizing THIS content conversationally, not inventing the
    underlying advice from scratch.
    """
    __tablename__ = "education_topics"

    id = Column(Integer, primary_key=True, index=True)
    # Stored as {"en": "...", "fr": "...", "cr": "..."} rather than a
    # separate row per language — this is a small, fixed content bank
    # (not user-generated data), so keeping one row per topic avoids
    # duplicating ids across languages and keeps daily-advice rotation
    # (app/education_ai.py's select_daily_advice_topic) working against
    # a single, stable set of topic ids regardless of which language a
    # given user is shown. A language missing from either dict falls
    # back to English at read time (see routers/education.py).
    title = Column(JSON, nullable=False)
    body = Column(JSON, nullable=False)
    category = Column(String, nullable=False)  # e.g. "otp", "urgency", "impersonation", "general"
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizQuestion(Base):
    """
    A single fraud-awareness quiz question. `source` distinguishes a
    hand-written seed question from one an AI model will eventually
    generate (see app/education_ai.py's # AI HOOK) — kept as real,
    queryable data from day one, per the explicit decision to build
    the AI-generation seam before the AI itself exists, rather than
    retrofit it later.
    """
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    # prompt, options, and explanation are all stored per-language,
    # same {"en": ..., "fr": ..., "cr": ...} pattern as
    # EducationTopic.title/body — see that model's comment for why one
    # row per question (not per language) is the right shape here.
    # options is a dict of dicts: {"en": [{"id": "a", "text": "..."}],
    # "fr": [...], "cr": [...]} — option ids ("a", "b", "c") stay
    # identical across languages so correct_option_id (below) doesn't
    # need to vary by language at all.
    prompt = Column(JSON, nullable=False)
    options = Column(JSON, nullable=False)
    correct_option_id = Column(String, nullable=False)
    explanation = Column(JSON, nullable=False)
    category = Column(String, nullable=False)
    source = Column(String, nullable=False, default="seed")  # "seed" | "ai_generated"
    created_at = Column(DateTime, default=datetime.utcnow)


class UserQuizAttempt(Base):
    """
    One user's answer to one quiz question. This is what lets daily
    advice and future chat personalization be genuinely informed by a
    specific user's own history (which categories they've gotten
    wrong) rather than generic rotation — see
    app/education_advice.py's use of this table.
    """
    __tablename__ = "user_quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False, index=True)
    selected_option_id = Column(String, nullable=False)
    was_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, default=datetime.utcnow)


class EducationChatMessage(Base):
    """
    One turn of the education companion chat, stored so a
    conversation has continuity across page loads and so future
    personalization (once the AI layer exists) has real history to
    draw on. Deliberately a SEPARATE table from Check — this is
    educational conversation, never a fraud-check submission, and
    keeping them apart avoids any risk of the two purposes' data
    (and their very different retention/privacy considerations)
    blurring together.
    """
    __tablename__ = "education_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
class Check(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    message_text = Column(Text, nullable=False)
    claimed_sender = Column(String, nullable=True)
    # True when claimed_sender was inferred from the message text
    # itself (app/sender_extractor.py) rather than explicitly provided
    # by the caller. Lets the frontend distinguish "you said this is
    # from X" from "Klaro noticed this looks like it's from X" —
    # different levels of confidence worth showing differently.
    sender_auto_detected = Column(Boolean, nullable=False, default=False)
    # The exact substring of the user's own message that triggered
    # auto-detection (e.g. "MCB"), kept separate from claimed_sender
    # (which stores the resolved formal registry name) so the frontend
    # can quote the user's own words back to them as reasoning, rather
    # than only the canonical name they may not recognize as a match.
    sender_detection_source_text = Column(String, nullable=True)
    # The language detected at creation time (see
    # app/language_detector.py), stored so GET /checks/{id}'s evidence
    # reconstruction (_build_evidence_list_from_stored_check) can
    # rebuild explanations in the SAME language the check was
    # originally analyzed and explained in, rather than silently
    # defaulting back to English on every read — the stored
    # message_text alone doesn't reliably convey this (it's already
    # PII-scrubbed, which can remove some of the very words a
    # re-detection would need).
    detected_language = Column(String, nullable=False, default="en")

    registry_match_status = Column(String, nullable=False)
    registry_matched_entity = Column(String, nullable=True)
    registry_match_score = Column(Float, nullable=True)
    # The registry's actual stored status for the matched entity,
    # whatever it is (e.g. "Active" for a normal verified match, or
    # the specific sourced detail for a revoked/surrendered license
    # such as "Surrendered — Global Business & Investment Dealer
    # licence, 30 June 2026"). Most useful when
    # registry_match_status == "revoked", where it carries the
    # specific reason worth surfacing, but populated consistently for
    # any exact match rather than special-cased to null otherwise —
    # the field's purpose is to expose whatever the registry actually
    # has on file. Previously only embedded in the free-text
    # ai_explanation string; added as its own structured field so a
    # frontend or future feature can filter/query on it without
    # parsing prose.
    registry_status_detail = Column(String, nullable=True)

    ai_risk_score = Column(Float, nullable=True)
    ai_flags = Column(JSON, nullable=True)
    ai_explanation = Column(Text, nullable=True)
    explanation_source = Column(String, nullable=True)

    # Stores the SPECIFIC values behind a domain_mismatch or
    # phone_mismatch flag (which domain, which entity it doesn't
    # match, etc.) — without this, a later GET could only reconstruct
    # a generic "a link doesn't match a known domain" evidence item,
    # not the specific "secure.mcb.mu.verify-account.xyz is not a
    # known domain for MCB Ltd" the create-time response showed. Found
    # via a direct comparison test: create-time and GET-time evidence
    # for the same check were producing different descriptions for the
    # same finding. A generic {} rather than null when there's nothing
    # to add, so callers don't need a None-check before indexing into it.
    evidence_detail = Column(JSON, nullable=True)

    overall_verdict = Column(String, nullable=False)

    # User feedback on whether this verdict was correct — a real,
    # honest way to describe improvement over time (see README), not
    # an unverifiable claim. "correct" | "incorrect" | None (not yet
    # given). Deliberately not required at submission time; feedback
    # is a follow-up action a user takes after reading the result, not
    # part of the check itself.
    user_feedback = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
