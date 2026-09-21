from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.errors import AppError
from backend.models import User
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.services.security_service import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("invalid_credentials", "Email or password is incorrect", 401)
    if not user.is_active:
        raise AppError("inactive_user", "User account is inactive", 403)
    return user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account",
)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = User(email=request.email, password_hash=hash_password(request.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise AppError("email_exists", "An account already uses this email", 409) from exc
    return user


@router.post("/login", response_model=TokenResponse, summary="Sign in with JSON")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = _authenticate(db, request.email, request.password)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/token", response_model=TokenResponse, summary="OAuth2 password sign-in")
def token(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = _authenticate(db, form.username, form.password)
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse, summary="Get the signed-in user")
def me(user: User = Depends(get_current_user)):
    return user
