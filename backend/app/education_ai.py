"""
The AI-generation seam for the education companion: chat responses and
dynamically-generated quiz questions. Deliberately built and wired in
now, before the actual AI layer exists, the explicit decision behind
this file's existence, so the real model can be dropped in later
without restructuring any of the calling code in routers/education.py.

Every function here is currently a deterministic stand-in, not a
placeholder that silently returns nonsense: each one does the best
honest job possible with the real content bank (education_content.py)
alone, and is clearly labeled as a stand-in wherever its output is
shown to the user (see routers/education.py's is_ai_generated fields).
This mirrors the exact pattern already used for the fraud-check
pipeline's own AI hook in routers/checks.py, deterministic-first,
AI-enhanced later, never AI-required.
"""
import random
from typing import List, Optional
from sqlalchemy.orm import Session

from app import models


def generate_chat_reply(db: Session, user_message: str, conversation_history: List[dict], language: str = "en") -> str:
    """
    AI HOOK: once the local model exists, replace this function's body
    with a real call, passing conversation_history as context and
    probably retrieving relevant EducationTopic rows as grounding
    (retrieval-augmented, not free-form) so the model explains and
    personalizes this project's own vetted content rather than
    inventing fraud advice from scratch, same "AI explains, code
    decides" principle used throughout this project.

    Today's stand-in: a simple keyword match against the topic bank's
    category field, falling back to a general response. Deliberately
    honest about being a stand-in rather than pretending to converse
    freely, see routers/education.py's is_ai_generated=False on every
    response this produces.

    `language` selects which language's keyword list to check the
    user's message against, and which language's topic body to return
    — a French or Kreol question should get a French or Kreol answer,
    not an English one silently mismatched to what was asked.
    """
    lowered = user_message.lower()

    keyword_to_category_by_language = {
        "en": {
            "otp": "otp", "code": "otp", "password": "otp",
            "urgent": "urgency", "deadline": "urgency", "suspend": "urgency",
            "bank": "impersonation", "impersonat": "impersonation", "fake": "impersonation", "link": "impersonation",
            "invest": "investment", "return": "investment", "crypto": "investment",
        },
        "fr": {
            "otp": "otp", "code": "otp", "mot de passe": "otp",
            "urgent": "urgency", "délai": "urgency", "suspend": "urgency",
            "banque": "impersonation", "usurpat": "impersonation", "faux": "impersonation", "lien": "impersonation",
            "invest": "investment", "rendement": "investment", "crypto": "investment",
        },
        "cr": {
            "otp": "otp", "kod": "otp",
            "irzan": "urgency", "delai": "urgency", "sispann": "urgency",
            "labank": "impersonation", "inperson": "impersonation", "fos": "impersonation", "lien": "impersonation",
            "investisman": "investment", "retour": "investment", "crypto": "investment",
        },
    }
    keyword_to_category = keyword_to_category_by_language.get(language, keyword_to_category_by_language["en"])

    matched_category = None
    for keyword, category in keyword_to_category.items():
        if keyword in lowered:
            matched_category = category
            break

    if matched_category:
        topic = (
            db.query(models.EducationTopic)
            .filter(models.EducationTopic.category == matched_category)
            .first()
        )
        if topic:
            body = topic.body.get(language) or topic.body.get("en") if isinstance(topic.body, dict) else topic.body
            follow_up = {
                "en": "Want a quick quiz question on this topic to check your understanding?",
                "fr": "Voulez-vous une question de quiz rapide sur ce sujet pour vérifier votre compréhension ?",
                "cr": "Ou anvi enn kestion kiz vit lor sa size la pou verifie ou konpreansion?",
            }.get(language, "Want a quick quiz question on this topic to check your understanding?")
            return f"{body}\n\n{follow_up}"

    fallback_replies = {
        "en": (
            "I can help explain common scam patterns — try asking about OTPs, urgent messages, "
            "bank impersonation, or investment scams. You can also ask me for a quiz question "
            "any time."
        ),
        "fr": (
            "Je peux vous aider à expliquer les schémas d'arnaque courants — essayez de me poser "
            "des questions sur les OTP, les messages urgents, l'usurpation d'identité bancaire, ou "
            "les arnaques à l'investissement. Vous pouvez aussi me demander une question de quiz "
            "à tout moment."
        ),
        "cr": (
            "Mo kapav ed ou konpran bann model eskrokri komen — esey demann mwa lor OTP, mesaz "
            "irzan, inpersonasion labank, ouswa eskrokri investisman. Ou kapav osi demann mwa "
            "enn kestion kiz nenport ler."
        ),
    }
    return fallback_replies.get(language, fallback_replies["en"])


def select_daily_advice_topic(db: Session, user_id: int):
    """
    AI HOOK: once personalization is warranted, replace this with
    logic that weighs a specific user's own quiz-attempt history (see
    models.UserQuizAttempt), favoring categories they've gotten wrong
    more often, or haven't seen recently, rather than the deterministic
    rotation below.

    Today's stand-in: picks whichever topic aligns with a category the
    user has gotten wrong before, deterministically rotated by user id
    and date (not random) so refreshing the page doesn't change the
    answer, but different users on the same day still see different
    topics if they've made different mistakes. Falls back to plain
    round-robin by user id and date if they have no quiz history yet.
    This is a genuine, if simple, per-user rule, not a random pick, so
    "daily advice" already means something different for different
    users today, without needing an AI model to do it.
    """
    topics = db.query(models.EducationTopic).all()
    if not topics:
        return None

    wrong_categories = (
        db.query(models.QuizQuestion.category)
        .join(models.UserQuizAttempt, models.UserQuizAttempt.question_id == models.QuizQuestion.id)
        .filter(models.UserQuizAttempt.user_id == user_id, models.UserQuizAttempt.was_correct.is_(False))
        .all()
    )
    wrong_category_names = {c[0] for c in wrong_categories}

    from datetime import date

    if wrong_category_names:
        prioritized = [t for t in topics if t.category in wrong_category_names]
        if prioritized:
            index = (user_id + date.today().toordinal()) % len(prioritized)
            return prioritized[index]

    index = (user_id + date.today().toordinal()) % len(topics)
    return topics[index]


def generate_quiz_question(db: Session, category: Optional[str] = None):
    """
    AI HOOK: once the local model exists, this can generate a genuinely
    new question (source="ai_generated" on the stored row) rather than
    selecting from the fixed seed bank, see models.QuizQuestion's
    `source` field, already built to distinguish the two.

    Today's stand-in: selects a random existing question, optionally
    filtered by category, from the seed bank (education_content.py).
    """
    query = db.query(models.QuizQuestion)
    if category:
        query = query.filter(models.QuizQuestion.category == category)

    questions = query.all()
    if not questions:
        return None
    return random.choice(questions)
