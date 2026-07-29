"""Password hashing (bcrypt) + JWT sign/verify."""
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def _to_bytes(password: str) -> bytes:
    # bcrypt giới hạn 72 byte — cắt cho an toàn (giống hành vi passlib trước đây).
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(seconds=settings.jwt_access_ttl),
    }
    return jwt.encode(payload, settings.jwt_access_secret, algorithm=settings.jwt_alg)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": _now(),
        "exp": _now() + timedelta(seconds=settings.jwt_refresh_ttl),
    }
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm=settings.jwt_alg)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_access_secret, algorithms=[settings.jwt_alg])
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_refresh_secret, algorithms=[settings.jwt_alg])
    except JWTError:
        return None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
