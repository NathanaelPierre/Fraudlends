"""
Loads education_content.py's seed data into the EducationTopic and
QuizQuestion tables. Idempotent (clears and reloads), same pattern as
app/registry_sync.py.

Usage:
    python -m app.education_sync
"""
from datetime import datetime
from app.database import SessionLocal, engine, Base
from app import models
from app.education_content import EDUCATION_TOPICS, QUIZ_QUESTIONS


def sync_education_content():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(models.EducationTopic).delete()
        db.query(models.QuizQuestion).filter(models.QuizQuestion.source == "seed").delete()
        db.commit()

        for topic in EDUCATION_TOPICS:
            db.add(models.EducationTopic(
                title=topic["title"],
                body=topic["body"],
                category=topic["category"],
                created_at=datetime.utcnow(),
            ))

        for q in QUIZ_QUESTIONS:
            db.add(models.QuizQuestion(
                prompt=q["prompt"],
                options=q["options"],
                correct_option_id=q["correct_option_id"],
                explanation=q["explanation"],
                category=q["category"],
                source="seed",
                created_at=datetime.utcnow(),
            ))

        db.commit()

        topics_count = db.query(models.EducationTopic).count()
        questions_count = db.query(models.QuizQuestion).count()
        print(f"Education content sync complete: {topics_count} topics, {questions_count} quiz questions loaded.")
    finally:
        db.close()


if __name__ == "__main__":
    sync_education_content()
