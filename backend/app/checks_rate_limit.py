"""
Per-user rate limiting on /checks, the core feature and the most
likely target for automated abuse (someone scripting repeated
submissions to exhaust resources, or, once the AI layer exists, to run
up API or compute cost). A fixed-window counter, stored on the User
row so it survives a server restart and works correctly even with
multiple worker processes, unlike an in-memory counter.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
from app.event_bus import bus

MAX_CHECKS_PER_WINDOW = 20
WINDOW_MINUTES = 5


def check_and_record_check_call(db: Session, user) -> bool:
    """
    Returns True if this call is allowed (and records it), False if
    the user has hit the rate limit for the current window. Call this
    before doing any real work in the /checks endpoint, if it returns
    False, the caller should reject the request with 429 rather than
    silently skip part of the analysis. Unlike the LLM layer's fallback
    pattern, this endpoint's entire value IS the analysis, so there is
    no partial or degraded result to fall back to.
    """
    now = datetime.utcnow()
    window_start = user.checks_window_start

    window_expired = (
        window_start is None
        or now - window_start > timedelta(minutes=WINDOW_MINUTES)
    )

    if window_expired:
        user.checks_window_start = now
        user.checks_in_window = 1
        db.add(user)
        db.commit()
        return True

    if user.checks_in_window >= MAX_CHECKS_PER_WINDOW:
        try:
            bus.publish("rate_limit_hit", {"user_id": user.id, "email": getattr(user, "email", None)})
        except Exception:
            pass
        return False

    user.checks_in_window += 1
    db.add(user)
    db.commit()
    return True
