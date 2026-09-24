"""
Security-event audit logging. Deliberately narrow scope — logins,
signups, settings changes, session revocations. Never logs passwords,
API keys, or message content submitted for checking. Best-effort: a
logging failure never blocks the actual action it's recording.
"""
from sqlalchemy.orm import Session
from app import models
from app.event_bus import bus


def log_event(db: Session, user_id, event_type: str, detail: str = None):
    try:
        entry = models.AuditLog(user_id=user_id, event_type=event_type, detail=detail)
        db.add(entry)
        db.commit()

        # Every audit event also feeds the admin dashboard's live security
        # feed. Best-effort, same as the DB write above: a broadcast
        # failure must never block the action being logged.
        try:
            bus.publish("audit", {"event_type": event_type, "user_id": user_id, "detail": detail})
        except Exception:
            pass
    except Exception:
        db.rollback()
