from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime
from typing import Optional, List


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_email_verified: bool = False
    role: str = "user"
    is_active: bool = True

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=10, max_length=500)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetTokenCheck(BaseModel):
    is_valid: bool


class EmailVerificationConfirmIn(BaseModel):
    token: str = Field(min_length=10, max_length=500)


class AccountDeleteIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ApiKeyIn(BaseModel):
    api_key: str = Field(min_length=10, max_length=200)


class ApiKeyStatus(BaseModel):
    is_set: bool
    masked_key: Optional[str] = None
    last_used_at: Optional[datetime] = None


class AuditLogEntry(BaseModel):
    id: int
    event_type: str
    detail: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class CheckCreate(BaseModel):
    """
    Exactly one of message_text or source_url should be provided when
    submitting as JSON — image upload (the third input mode) goes
    through a separate multipart endpoint (POST /checks/from-image),
    since file uploads and JSON bodies don't mix cleanly in one
    request. See app/routers/checks.py for how all three modes
    converge on the same underlying analysis pipeline afterward.
    """
    message_text: Optional[str] = Field(default=None, max_length=5000)
    source_url: Optional[str] = Field(default=None, max_length=2000, description="A URL to fetch and analyze instead of pasted text")
    claimed_sender: Optional[str] = Field(default=None, max_length=200)
    save_check: bool = Field(
        default=True,
        description="If false, the check is analyzed and returned but never persisted to the database. Use for messages containing sensitive data (OTPs, account numbers) the user doesn't want stored.",
    )

    @model_validator(mode="after")
    def exactly_one_input_mode(self):
        provided = [bool(self.message_text and self.message_text.strip()), bool(self.source_url and self.source_url.strip())]
        if sum(provided) != 1:
            raise ValueError("Provide exactly one of message_text or source_url, not both and not neither.")
        return self


class EvidenceItem(BaseModel):
    """
    One piece of evidence behind a verdict, structured so a frontend
    can render a real evidence list (type, human-readable description,
    severity) without needing its own hardcoded mapping of internal
    flag codes to labels — that mapping already exists server-side
    (see app/routers/checks.py's _INDICATOR_DESCRIPTIONS) and is reused
    to build this list, rather than duplicated on the client.
    """
    category: str = Field(description='"registry", "indicator", "domain", or "phone"')
    code: str = Field(description="A stable internal identifier, e.g. \"requests_otp\" or \"domain_mismatch\"")
    description: str = Field(description="A human-readable explanation of this specific piece of evidence")
    severity: str = Field(description='"info", "suspicious", or "high_risk"')


class CheckOut(BaseModel):
    id: int
    message_text: str
    claimed_sender: Optional[str]
    sender_auto_detected: bool = False
    sender_detection_source_text: Optional[str] = None
    detected_language: str = "en"
    registry_match_status: str
    registry_matched_entity: Optional[str]
    registry_match_score: Optional[float]
    registry_status_detail: Optional[str] = None
    ai_risk_score: Optional[float]
    ai_flags: Optional[List[str]]
    ai_explanation: Optional[str]
    explanation_source: Optional[str]
    overall_verdict: str
    user_feedback: Optional[str] = None
    repeat_sender_summary: Optional[str] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class CheckFeedbackIn(BaseModel):
    is_correct: bool = Field(description="True if the verdict was correct, false if it was wrong")


class CheckSummary(BaseModel):
    total_checks: int
    safe_count: int
    suspicious_count: int
    high_risk_count: int
    checks_with_feedback: int
    feedback_marked_correct: int
    feedback_marked_incorrect: int
    most_checked_senders: List[dict]


# ---------------------------------------------------------------------------
# Admin dashboard (app/routers/admin.py) — read models for cross-user views.
# Deliberately separate from the user-facing schemas above rather than
# reusing them with extra optional fields, so an admin-only field can
# never accidentally leak through a user-facing response_model.
# ---------------------------------------------------------------------------

class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    is_email_verified: bool
    created_at: datetime
    checks_count: int
    high_risk_checks_count: int
    last_login_at: Optional[datetime] = None


class AdminCheckOut(BaseModel):
    id: int
    user_id: int
    user_email: EmailStr
    claimed_sender: Optional[str]
    registry_match_status: str
    overall_verdict: str
    ai_flags: Optional[List[str]]
    user_feedback: Optional[str] = None
    created_at: datetime


class AdminRoleIn(BaseModel):
    role: str = Field(description="'admin' or 'user'")


class AdminOverviewOut(BaseModel):
    server_started_at: datetime
    uptime_seconds: float
    users_total: int
    users_active: int
    users_suspended: int
    admins_total: int
    checks_total: int
    checks_last_24h: int
    verdict_breakdown: dict
    verdict_breakdown_24h: dict
    registry_entities_total: int
    registry_last_synced_at: Optional[datetime] = None
    failed_logins_last_24h: int
    active_lockouts: int
    live_event_counters: dict
    live_subscribers: int


class AdminAuditLogEntry(BaseModel):
    id: int
    user_id: Optional[int]
    user_email: Optional[str] = None
    event_type: str
    detail: Optional[str] = None
    timestamp: datetime


class AdminLoginAttemptOut(BaseModel):
    id: int
    email: str
    attempted_at: datetime
    successful: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Education companion (app/routers/education.py) — chat, daily advice, quizzes
# ---------------------------------------------------------------------------

class DailyAdviceOut(BaseModel):
    title: str
    body: str
    category: str
    is_personalized: bool = Field(
        description="True if this topic was selected based on the user's own past quiz mistakes, "
                    "rather than plain rotation — see app/education_ai.py's select_daily_advice_topic."
    )


class EducationChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class EducationChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    is_ai_generated: bool = Field(
        default=False,
        description="False today — every reply is a deterministic stand-in (see app/education_ai.py). "
                    "Will become True once the real local model is wired in, so the frontend can show "
                    "this distinction honestly rather than implying a full AI conversation exists today.",
    )

    class Config:
        from_attributes = True


class QuizQuestionOut(BaseModel):
    id: int
    prompt: str
    options: List[dict]
    category: str
    source: str

    class Config:
        from_attributes = True


class QuizAnswerIn(BaseModel):
    selected_option_id: str


class QuizAnswerOut(BaseModel):
    was_correct: bool
    correct_option_id: str
    explanation: str
