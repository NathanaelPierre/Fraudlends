"""
The education companion: daily advice, chat, and quizzes. Deliberately
separate from checks.py's fraud-analysis pipeline, this is proactive
learning, not reactive message-checking, and the two features have
genuinely different data and privacy shapes.

MULTILINGUAL: content (EducationTopic, QuizQuestion) is stored per
language as {"en": ..., "fr": ..., "cr": ...} dicts on each row — see
app/education_content.py's module docstring. Every endpoint here takes
a `language` query parameter (default "en") and selects the right
value at read time, falling back to English if a given row is missing
that language entirely (should not happen for the seed content, which
has all three, but keeps a partially-translated future addition from
crashing).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app import models, schemas, security
from app.education_ai import generate_chat_reply, select_daily_advice_topic, generate_quiz_question

router = APIRouter(prefix="/education", tags=["education"])

SUPPORTED_LANGUAGES = ("en", "fr", "cr")


def _localized(value_dict, language: str, fallback_language: str = "en"):
    """
    Selects `language` from a per-language dict, falling back to
    English if that specific language is missing from this row (see
    module docstring). Never raises — a row with no English fallback
    either would be a real data problem worth crashing loudly on
    instead, so that case is deliberately NOT caught here.
    """
    if not isinstance(value_dict, dict):
        # Defensive: a row created before the multilingual migration
        # (or any future non-dict content) is returned as-is rather
        # than crashing — this should not occur for anything loaded
        # via education_sync.py, but a stray old-shaped row must not
        # 500 the whole endpoint.
        return value_dict
    return value_dict.get(language) or value_dict.get(fallback_language)


def _localize_options(options_dict, language: str, fallback_language: str = "en"):
    if not isinstance(options_dict, dict):
        return options_dict
    return options_dict.get(language) or options_dict.get(fallback_language)


@router.get("/daily-advice", response_model=schemas.DailyAdviceOut)
def get_daily_advice(
    language: str = Query(default="en"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    topic = select_daily_advice_topic(db, current_user.id)
    if topic is None:
        raise HTTPException(status_code=503, detail="No education content is loaded yet.")

    has_wrong_attempts = (
        db.query(models.UserQuizAttempt)
        .filter(models.UserQuizAttempt.user_id == current_user.id, models.UserQuizAttempt.was_correct.is_(False))
        .first()
        is not None
    )

    return schemas.DailyAdviceOut(
        title=_localized(topic.title, language),
        body=_localized(topic.body, language),
        category=topic.category,
        is_personalized=has_wrong_attempts,
    )


@router.get("/chat/history", response_model=List[schemas.EducationChatMessageOut])
def get_chat_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Chat messages are NOT stored per-language dicts — unlike the fixed
    topic/quiz content bank, chat is free-form user and generated text
    in whatever language it was actually written/replied in (see
    app/education_ai.py's generate_chat_reply, which already responds
    using the same content bank's language-aware body when it matches
    a topic). No language parameter is needed here.
    """
    return (
        db.query(models.EducationChatMessage)
        .filter(models.EducationChatMessage.user_id == current_user.id)
        .order_by(models.EducationChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )


@router.post("/chat", response_model=schemas.EducationChatMessageOut)
def send_chat_message(
    body: schemas.EducationChatIn,
    language: str = Query(default="en"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Stores the user's message, generates a reply (currently a
    deterministic stand-in, see app/education_ai.py), stores the
    reply, and returns the reply. Both messages are persisted so
    /education/chat/history has real continuity across page loads.
    """
    user_message = models.EducationChatMessage(
        user_id=current_user.id, role="user", content=body.message
    )
    db.add(user_message)
    db.commit()

    history = (
        db.query(models.EducationChatMessage)
        .filter(models.EducationChatMessage.user_id == current_user.id)
        .order_by(models.EducationChatMessage.created_at.asc())
        .all()
    )
    history_dicts = [{"role": m.role, "content": m.content} for m in history]

    reply_text = generate_chat_reply(db, body.message, history_dicts, language=language)

    assistant_message = models.EducationChatMessage(
        user_id=current_user.id, role="assistant", content=reply_text
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return assistant_message


@router.get("/quiz", response_model=schemas.QuizQuestionOut)
def get_quiz_question(
    category: Optional[str] = Query(default=None),
    language: str = Query(default="en"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Returns options without correct_option_id or explanation, those
    are only revealed via POST /education/quiz/{id}/answer, so a quiz
    actually tests something rather than shipping the answer key in
    the question payload itself.
    """
    question = generate_quiz_question(db, category)
    if question is None:
        raise HTTPException(status_code=503, detail="No quiz questions are loaded yet.")

    return schemas.QuizQuestionOut(
        id=question.id,
        prompt=_localized(question.prompt, language),
        options=_localize_options(question.options, language),
        category=question.category,
        source=question.source,
    )


@router.post("/quiz/{question_id}/answer", response_model=schemas.QuizAnswerOut)
def answer_quiz_question(
    question_id: int,
    body: schemas.QuizAnswerIn,
    language: str = Query(default="en"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    question = db.query(models.QuizQuestion).filter(models.QuizQuestion.id == question_id).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Quiz question not found")

    was_correct = body.selected_option_id == question.correct_option_id

    attempt = models.UserQuizAttempt(
        user_id=current_user.id,
        question_id=question.id,
        selected_option_id=body.selected_option_id,
        was_correct=was_correct,
    )
    db.add(attempt)
    db.commit()

    return schemas.QuizAnswerOut(
        was_correct=was_correct,
        correct_option_id=question.correct_option_id,
        explanation=_localized(question.explanation, language),
    )
