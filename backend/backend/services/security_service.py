import base64
import hashlib
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.fernet import Fernet, InvalidToken
from pwdlib import PasswordHash

from backend.config import settings
from backend.errors import AppError

password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expires_at, "type": "access"},
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise AppError("invalid_token", "Invalid or expired access token", 401) from exc

    user_id = payload.get("sub")
    if not user_id or payload.get("type") != "access":
        raise AppError("invalid_token", "Invalid access token", 401)
    return user_id


def _fernet() -> Fernet:
    if settings.plaid_encryption_key:
        key = settings.plaid_encryption_key.encode()
    else:
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    try:
        return Fernet(key)
    except ValueError as exc:
        raise AppError(
            "invalid_encryption_key",
            "PLAID_ENCRYPTION_KEY must be a valid Fernet key",
            500,
        ) from exc


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise AppError(
            "decryption_failed",
            "Stored Plaid credentials could not be decrypted",
            500,
        ) from exc
