from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, security
from app.crypto import encrypt_value, decrypt_value, mask_key
from app.audit_log import log_event

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-key", response_model=schemas.ApiKeyStatus)
def get_api_key_status(current_user: models.User = Depends(security.get_current_user)):
    if not current_user.xai_api_key_encrypted:
        return {"is_set": False, "masked_key": None, "last_used_at": None}
    try:
        real_key = decrypt_value(current_user.xai_api_key_encrypted)
        return {"is_set": True, "masked_key": mask_key(real_key), "last_used_at": current_user.xai_key_last_used_at}
    except ValueError:
        return {"is_set": False, "masked_key": None, "last_used_at": None}


@router.post("/api-key", response_model=schemas.ApiKeyStatus)
def save_api_key(
    key_in: schemas.ApiKeyIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    # Key verification against the real provider is intentionally
    # deferred, the AI layer (which provider, which model) hasn't been
    # decided yet. This endpoint accepts and stores the key now so the
    # rest of Settings works end-to-end; wire in a verify call here
    # once the AI provider is chosen.
    current_user.xai_api_key_encrypted = encrypt_value(key_in.api_key)
    current_user.xai_key_last_used_at = None
    db.add(current_user)
    db.commit()
    log_event(db, user_id=current_user.id, event_type="api_key_saved")
    return {"is_set": True, "masked_key": mask_key(key_in.api_key), "last_used_at": None}


@router.delete("/api-key", response_model=schemas.ApiKeyStatus)
def delete_api_key(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    current_user.xai_api_key_encrypted = None
    current_user.xai_key_last_used_at = None
    db.add(current_user)
    db.commit()
    log_event(db, user_id=current_user.id, event_type="api_key_removed")
    return {"is_set": False, "masked_key": None, "last_used_at": None}


@router.get("/audit-log", response_model=list[schemas.AuditLogEntry])
def get_audit_log(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.user_id == current_user.id)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(min(limit, 200))
        .offset(offset)
        .all()
    )


@router.post("/revoke-sessions")
def revoke_all_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    current_user.tokens_valid_after = datetime.utcnow().replace(microsecond=0)
    db.add(current_user)
    db.commit()
    log_event(db, user_id=current_user.id, event_type="sessions_revoked")
    return {"detail": "All sessions have been logged out. Please log in again."}


@router.post("/change-password")
def change_password(
    body: schemas.ChangePasswordIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if not security.verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    current_user.hashed_password = security.hash_password(body.new_password)
    current_user.tokens_valid_after = datetime.utcnow().replace(microsecond=0)
    db.add(current_user)
    db.commit()
    log_event(db, user_id=current_user.id, event_type="password_changed")
    return {"detail": "Your password has been changed. Please log in again with your new password."}


@router.post("/delete-account")
def delete_account(
    body: schemas.AccountDeleteIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if not security.verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    user_id = current_user.id
    user_email = current_user.email

    db.query(models.Check).filter(models.Check.user_id == user_id).delete()
    db.query(models.AuditLog).filter(models.AuditLog.user_id == user_id).delete()
    db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id == user_id).delete()
    db.query(models.EmailVerificationToken).filter(models.EmailVerificationToken.user_id == user_id).delete()
    db.delete(current_user)
    db.commit()

    log_event(db, user_id=None, event_type="account_deleted", detail=f"email={user_email}")
    return {"detail": "Your account and all associated data have been permanently deleted."}
