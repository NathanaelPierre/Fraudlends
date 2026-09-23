"""
Admin dashboard API — a SIEM-flavored console layered on top of the
same data every other router already writes: users, checks, the audit
log, and login attempts. Nothing here is a new data source; it's a
cross-user, operator-facing view of data that's normally scoped to
"the current user" everywhere else in the app.

Access model: there is deliberately no second login system. Every
route in this router depends on `require_admin`, which reuses the same
JWT `get_current_user` check as the rest of the API and then checks
`role == "admin"` on top of it. One account, one token, two surfaces —
the regular app at `/app` and the console at `/admin` — separated by
authorization, not by a separate credential. See RUNNING.md for how an
account becomes an admin in the first place.

Live data: GET /admin/stream is a Server-Sent Events endpoint fed by
app/event_bus.py, which every write path in the app (audit_log.log_event,
check creation, rate-limit hits) already publishes to. Everything else
here is a normal polling GET — the frontend refreshes it on an interval
— which is the right tradeoff for tabular/aggregate views; only the
security event ticker needs to be push-based.
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app import models, schemas, security
from app.event_bus import bus
from app.audit_log import log_event
from app.login_guard import MAX_FAILURES_PER_WINDOW, LOCKOUT_WINDOW_MINUTES

router = APIRouter(prefix="/admin", tags=["admin"])


def _paginate(limit: int, offset: int, max_limit: int = 200):
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset


# ---------------------------------------------------------------------------
# Overview — the numbers a SIEM landing page needs at a glance.
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=schemas.AdminOverviewOut)
def overview(db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)):
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)

    users_total = db.query(func.count(models.User.id)).scalar()
    users_active = db.query(func.count(models.User.id)).filter(models.User.is_active.is_(True)).scalar()
    admins_total = db.query(func.count(models.User.id)).filter(models.User.role == "admin").scalar()

    checks_total = db.query(func.count(models.Check.id)).scalar()
    checks_last_24h = db.query(func.count(models.Check.id)).filter(models.Check.created_at >= day_ago).scalar()

    def verdict_counts(since=None):
        q = db.query(models.Check.overall_verdict, func.count(models.Check.id))
        if since is not None:
            q = q.filter(models.Check.created_at >= since)
        rows = q.group_by(models.Check.overall_verdict).all()
        return {verdict: count for verdict, count in rows}

    registry_total = db.query(func.count(models.RegistryEntity.id)).scalar()
    registry_last_synced = db.query(func.max(models.RegistryEntity.last_synced_at)).scalar()

    failed_logins_24h = (
        db.query(func.count(models.LoginAttempt.id))
        .filter(models.LoginAttempt.successful.is_(False), models.LoginAttempt.attempted_at >= day_ago)
        .scalar()
    )

    lockout_window_start = now - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    lockout_rows = (
        db.query(models.LoginAttempt.email, func.count(models.LoginAttempt.id))
        .filter(models.LoginAttempt.successful.is_(False), models.LoginAttempt.attempted_at >= lockout_window_start)
        .group_by(models.LoginAttempt.email)
        .all()
    )
    active_lockouts = sum(1 for _, cnt in lockout_rows if cnt >= MAX_FAILURES_PER_WINDOW)

    return schemas.AdminOverviewOut(
        server_started_at=datetime.utcfromtimestamp(bus.started_at),
        uptime_seconds=now.timestamp() - bus.started_at,
        users_total=users_total or 0,
        users_active=users_active or 0,
        users_suspended=(users_total or 0) - (users_active or 0),
        admins_total=admins_total or 0,
        checks_total=checks_total or 0,
        checks_last_24h=checks_last_24h or 0,
        verdict_breakdown=verdict_counts(),
        verdict_breakdown_24h=verdict_counts(since=day_ago),
        registry_entities_total=registry_total or 0,
        registry_last_synced_at=registry_last_synced,
        failed_logins_last_24h=failed_logins_24h or 0,
        active_lockouts=active_lockouts,
        live_event_counters=bus.counters(),
        live_subscribers=bus.subscriber_count(),
    )


# ---------------------------------------------------------------------------
# Checks — the SIEM investigation surface, across every user.
# ---------------------------------------------------------------------------

@router.get("/checks", response_model=List[schemas.AdminCheckOut])
def list_all_checks(
    limit: int = 25,
    offset: int = 0,
    verdict: Optional[str] = None,
    registry_status: Optional[str] = None,
    user_email: Optional[str] = None,
    claimed_sender: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    limit, offset = _paginate(limit, offset)
    q = db.query(models.Check, models.User.email).join(models.User, models.Check.user_id == models.User.id)

    if verdict:
        q = q.filter(models.Check.overall_verdict == verdict)
    if registry_status:
        q = q.filter(models.Check.registry_match_status == registry_status)
    if user_email:
        q = q.filter(models.User.email.ilike(f"%{user_email}%"))
    if claimed_sender:
        q = q.filter(models.Check.claimed_sender.ilike(f"%{claimed_sender}%"))

    rows = q.order_by(models.Check.created_at.desc()).offset(offset).limit(limit).all()

    return [
        schemas.AdminCheckOut(
            id=check.id,
            user_id=check.user_id,
            user_email=email,
            claimed_sender=check.claimed_sender,
            registry_match_status=check.registry_match_status,
            overall_verdict=check.overall_verdict,
            ai_flags=check.ai_flags,
            user_feedback=check.user_feedback,
            created_at=check.created_at,
        )
        for check, email in rows
    ]


@router.get("/checks/{check_id}", response_model=schemas.AdminCheckOut)
def get_any_check(
    check_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    row = (
        db.query(models.Check, models.User.email)
        .join(models.User, models.Check.user_id == models.User.id)
        .filter(models.Check.id == check_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Check not found")
    check, email = row
    return schemas.AdminCheckOut(
        id=check.id,
        user_id=check.user_id,
        user_email=email,
        claimed_sender=check.claimed_sender,
        registry_match_status=check.registry_match_status,
        overall_verdict=check.overall_verdict,
        ai_flags=check.ai_flags,
        user_feedback=check.user_feedback,
        created_at=check.created_at,
    )


# ---------------------------------------------------------------------------
# Users — management surface.
# ---------------------------------------------------------------------------

@router.get("/users", response_model=List[schemas.AdminUserOut])
def list_users(
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    limit, offset = _paginate(limit, offset)
    query = db.query(models.User)
    if q:
        query = query.filter(models.User.email.ilike(f"%{q}%"))
    users = query.order_by(models.User.id.asc()).offset(offset).limit(limit).all()

    results = []
    for u in users:
        checks_count = db.query(func.count(models.Check.id)).filter(models.Check.user_id == u.id).scalar() or 0
        high_risk_count = (
            db.query(func.count(models.Check.id))
            .filter(models.Check.user_id == u.id, models.Check.overall_verdict == "high_risk")
            .scalar()
            or 0
        )
        last_login = (
            db.query(func.max(models.LoginAttempt.attempted_at))
            .filter(models.LoginAttempt.email == u.email, models.LoginAttempt.successful.is_(True))
            .scalar()
        )
        results.append(
            schemas.AdminUserOut(
                id=u.id,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                is_email_verified=u.is_email_verified,
                created_at=u.created_at,
                checks_count=checks_count,
                high_risk_checks_count=high_risk_count,
                last_login_at=last_login,
            )
        )
    return results


@router.post("/users/{user_id}/role", response_model=schemas.AdminUserOut)
def set_user_role(
    user_id: int,
    payload: schemas.AdminRoleIn,
    db: Session = Depends(get_db),
    admin: models.User = Depends(security.require_admin),
):
    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'user'")

    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and payload.role == "user":
        raise HTTPException(status_code=400, detail="You can't demote your own account.")

    target.role = payload.role
    db.add(target)
    db.commit()
    db.refresh(target)

    log_event(db, user_id=admin.id, event_type="admin_role_change", detail=f"target={target.email} role={payload.role}")
    bus.publish("admin_action", {"action": "role_change", "target": target.email, "role": payload.role, "by": admin.email})

    return _user_out(db, target)


def _set_active(user_id: int, active: bool, db: Session, admin: models.User) -> models.User:
    target = db.query(models.User).filter(models.User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and not active:
        raise HTTPException(status_code=400, detail="You can't suspend your own account.")

    target.is_active = active
    if not active:
        # Kill every existing session immediately, the same mechanism
        # "log out everywhere" and a password change already use.
        target.tokens_valid_after = datetime.utcnow()
    db.add(target)
    db.commit()
    db.refresh(target)

    event = "admin_user_suspended" if not active else "admin_user_reactivated"
    log_event(db, user_id=admin.id, event_type=event, detail=f"target={target.email}")
    bus.publish("admin_action", {"action": event, "target": target.email, "by": admin.email})
    return target


def _user_out(db: Session, target: models.User) -> schemas.AdminUserOut:
    checks_count = db.query(func.count(models.Check.id)).filter(models.Check.user_id == target.id).scalar() or 0
    high_risk_count = (
        db.query(func.count(models.Check.id))
        .filter(models.Check.user_id == target.id, models.Check.overall_verdict == "high_risk")
        .scalar()
        or 0
    )
    last_login = (
        db.query(func.max(models.LoginAttempt.attempted_at))
        .filter(models.LoginAttempt.email == target.email, models.LoginAttempt.successful.is_(True))
        .scalar()
    )
    return schemas.AdminUserOut(
        id=target.id, email=target.email, role=target.role, is_active=target.is_active,
        is_email_verified=target.is_email_verified, created_at=target.created_at,
        checks_count=checks_count, high_risk_checks_count=high_risk_count, last_login_at=last_login,
    )


@router.post("/users/{user_id}/suspend", response_model=schemas.AdminUserOut)
def suspend_user(user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(security.require_admin)):
    target = _set_active(user_id, False, db, admin)
    return _user_out(db, target)


@router.post("/users/{user_id}/activate", response_model=schemas.AdminUserOut)
def activate_user(user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(security.require_admin)):
    target = _set_active(user_id, True, db, admin)
    return _user_out(db, target)


# ---------------------------------------------------------------------------
# Security — global audit log and login-attempt history.
# ---------------------------------------------------------------------------

@router.get("/audit-log", response_model=List[schemas.AdminAuditLogEntry])
def global_audit_log(
    limit: int = 50,
    offset: int = 0,
    event_type: Optional[str] = None,
    user_email: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    limit, offset = _paginate(limit, offset)
    q = db.query(models.AuditLog, models.User.email).outerjoin(models.User, models.AuditLog.user_id == models.User.id)
    if event_type:
        q = q.filter(models.AuditLog.event_type == event_type)
    if user_email:
        q = q.filter(models.User.email.ilike(f"%{user_email}%"))
    rows = q.order_by(models.AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return [
        schemas.AdminAuditLogEntry(
            id=entry.id, user_id=entry.user_id, user_email=email,
            event_type=entry.event_type, detail=entry.detail, timestamp=entry.timestamp,
        )
        for entry, email in rows
    ]


@router.get("/login-attempts", response_model=List[schemas.AdminLoginAttemptOut])
def login_attempts(
    limit: int = 50,
    offset: int = 0,
    email: Optional[str] = None,
    successful: Optional[bool] = None,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    limit, offset = _paginate(limit, offset)
    q = db.query(models.LoginAttempt)
    if email:
        q = q.filter(models.LoginAttempt.email.ilike(f"%{email}%"))
    if successful is not None:
        q = q.filter(models.LoginAttempt.successful.is_(successful))
    rows = q.order_by(models.LoginAttempt.attempted_at.desc()).offset(offset).limit(limit).all()
    return rows


# ---------------------------------------------------------------------------
# Registry — snapshot freshness, the thing this whole product is verified against.
# ---------------------------------------------------------------------------

@router.get("/registry")
def registry_summary(db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)):
    rows = (
        db.query(models.RegistryEntity.source, models.RegistryEntity.status, func.count(models.RegistryEntity.id))
        .group_by(models.RegistryEntity.source, models.RegistryEntity.status)
        .all()
    )
    by_source = {}
    for source, status_, count in rows:
        by_source.setdefault(source, {})[status_ or "active"] = count

    return {
        "total": db.query(func.count(models.RegistryEntity.id)).scalar() or 0,
        "last_synced_at": db.query(func.max(models.RegistryEntity.last_synced_at)).scalar(),
        "by_source": by_source,
    }


# ---------------------------------------------------------------------------
# Health.
# ---------------------------------------------------------------------------

@router.get("/health")
def admin_health(db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)):
    from sqlalchemy import text as sql_text

    db_ok = True
    try:
        db.execute(sql_text("SELECT 1"))
    except Exception:
        db_ok = False

    now = datetime.utcnow()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database_connected": db_ok,
        "uptime_seconds": now.timestamp() - bus.started_at,
        "server_started_at": datetime.utcfromtimestamp(bus.started_at),
        "live_subscribers": bus.subscriber_count(),
    }


# ---------------------------------------------------------------------------
# Live stream — Server-Sent Events.
#
# EventSource can't set an Authorization header, so the token travels
# as a query parameter here instead of the usual bearer header. It's
# validated with exactly the same JWT decode + revocation + role check
# as every other admin route, just inlined because Depends(oauth2_scheme)
# only reads the header. The token is short-lived and this is a GET a
# browser makes itself (not something an attacker can trivially read
# off the wire without already controlling the network, at which point
# the bearer-header version isn't safer either).
# ---------------------------------------------------------------------------

async def _require_admin_from_query_token(token: str, db: Session) -> models.User:
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        user_id = payload.get("sub")
        issued_at = payload.get("iat")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if user.tokens_valid_after is not None and issued_at is not None:
        if datetime.utcfromtimestamp(issued_at) <= user.tokens_valid_after:
            raise credentials_exception
    if not user.is_active or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


@router.get("/stream")
async def stream_events(token: str = Query(...), db: Session = Depends(get_db)):
    await _require_admin_from_query_token(token, db)

    queue = bus.subscribe()

    async def event_generator():
        try:
            backlog = bus.recent(30)
            for event in backlog:
                yield f"data: {json.dumps(event)}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
