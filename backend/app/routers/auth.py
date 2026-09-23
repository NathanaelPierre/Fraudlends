import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, security
from app.login_guard import check_login_allowed, record_failed_login, record_successful_login
from app.audit_log import log_event
from app.password_reset import request_password_reset, verify_reset_token, consume_reset_token
from app.email_verification import send_verification_email, confirm_email_verification, resend_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.UserOut)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=user_in.email,
        hashed_password=security.hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_event(db, user_id=user.id, event_type="signup")

    frontend_base_url = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    send_verification_email(db, user, frontend_base_url)

    return user


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    allowed, minutes_remaining = check_login_allowed(db, form_data.username)
    if not allowed:
        log_event(db, user_id=None, event_type="login_blocked_lockout", detail=f"email={form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in about {minutes_remaining} minute(s).",
        )

    user = db.query(models.User).filter(models.User.email == form_data.username).first()

    if user is None or not security.verify_password(form_data.password, user.hashed_password):
        record_failed_login(db, form_data.username)
        log_event(db, user_id=(user.id if user else None), event_type="login_failed", detail=f"email={form_data.username}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not user.is_active:
        log_event(db, user_id=user.id, event_type="login_blocked_suspended")
        raise HTTPException(status_code=403, detail="This account has been suspended.")

    record_successful_login(db, form_data.username)
    log_event(db, user_id=user.id, event_type="login_success")

    token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def get_current_user_info(current_user: models.User = Depends(security.get_current_user)):
    return current_user


@router.post("/password-reset/request")
def request_reset(body: schemas.PasswordResetRequestIn, db: Session = Depends(get_db)):
    frontend_base_url = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    user = db.query(models.User).filter(models.User.email == body.email).first()
    request_password_reset(db, body.email, frontend_base_url)
    if user is not None:
        log_event(db, user_id=user.id, event_type="password_reset_requested")

    return {"detail": "If an account exists with that email, a password reset link has been sent."}


@router.get("/password-reset/verify", response_model=schemas.PasswordResetTokenCheck)
def verify_reset(token: str, db: Session = Depends(get_db)):
    user = verify_reset_token(db, token)
    return {"is_valid": user is not None}


@router.post("/password-reset/confirm")
def confirm_reset(body: schemas.PasswordResetConfirmIn, db: Session = Depends(get_db)):
    user = consume_reset_token(db, body.token, body.new_password)
    if user is None:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired. Please request a new one.")

    log_event(db, user_id=user.id, event_type="password_reset_completed")
    return {"detail": "Your password has been reset. Please log in with your new password."}


@router.post("/verify-email/confirm")
def confirm_verify_email(body: schemas.EmailVerificationConfirmIn, db: Session = Depends(get_db)):
    user = confirm_email_verification(db, body.token)
    if user is None:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")

    log_event(db, user_id=user.id, event_type="email_verified")
    return {"detail": "Your email has been verified."}


@router.post("/verify-email/resend")
def resend_verify_email(body: schemas.PasswordResetRequestIn, db: Session = Depends(get_db)):
    frontend_base_url = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    resend_verification_email(db, body.email, frontend_base_url)
    return {"detail": "If an account exists with that email and isn't already verified, a new verification link has been sent."}
