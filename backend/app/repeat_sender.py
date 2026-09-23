"""
Repeat-sender detection: surfaces a user's own history of checks
against the same claimed sender, so a pattern like "you've checked
this sender 3 times, 2 were flagged" is visible rather than each check
being evaluated in isolation with no memory of prior encounters.

Deliberately scoped to a single user's own history, not a cross-user
signal, this project's data isolation guarantees (see
test_security.py) mean one user's checks are never visible to another,
and this feature respects that boundary rather than quietly creating a
shared cross-user reputation system, which would be a different,
larger feature with its own privacy implications worth a separate,
explicit decision rather than an incidental side effect of this one.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app import models


def build_repeat_sender_summary(db: Session, user_id: int, claimed_sender: Optional[str], exclude_check_id: Optional[int] = None) -> Optional[str]:
    """
    Returns a short, plain-language summary of this user's past checks
    against the same claimed sender (exact string match on
    claimed_sender, not fuzzy, this is about literal repeat submissions
    of the same typed name, not registry-level entity matching), or
    None if there's no prior history to mention.

    exclude_check_id lets a caller exclude the check currently being
    created or viewed from its own history count, so "you've checked
    this sender N times" doesn't include the current check itself.
    """
    if not claimed_sender or not claimed_sender.strip():
        return None

    query = db.query(models.Check).filter(
        models.Check.user_id == user_id,
        models.Check.claimed_sender == claimed_sender,
    )
    if exclude_check_id is not None:
        query = query.filter(models.Check.id != exclude_check_id)

    past_checks = query.all()

    if len(past_checks) < 1:
        return None

    total = len(past_checks)
    flagged = sum(1 for c in past_checks if c.overall_verdict in ("suspicious", "high_risk"))

    if flagged == 0:
        return f'You\'ve checked "{claimed_sender}" {total} time{"s" if total != 1 else ""} before, all came back safe.'
    elif flagged == total:
        return f'You\'ve checked "{claimed_sender}" {total} time{"s" if total != 1 else ""} before, all were flagged.'
    else:
        return f'You\'ve checked "{claimed_sender}" {total} time{"s" if total != 1 else ""} before, {flagged} of those were flagged.'
