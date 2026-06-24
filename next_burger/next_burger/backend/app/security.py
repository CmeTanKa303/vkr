"""Безопасность: хеширование паролей (bcrypt) и JWT-аутентификация.

Соответствует разделу «Информационная безопасность» ВКР:
пароли хранятся только как bcrypt-хеш с солью, доступ — по JWT,
с разграничением ролей (user / admin).
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models


def _load_secret_key() -> str:
    """Ключ подписи JWT.

    Берётся из переменной окружения SECRET_KEY. Если она не задана, при первом
    запуске генерируется криптослучайный ключ и сохраняется в файл .secret_key
    (он не попадает в репозиторий — см. .gitignore). Так ключ не захардкожен в
    исходном коде, но запуск остаётся «из коробки», без ручной настройки.
    """
    env = os.environ.get("SECRET_KEY")
    if env:
        return env
    secret_file = Path(__file__).resolve().parent.parent / ".secret_key"
    if secret_file.exists():
        saved = secret_file.read_text(encoding="utf-8").strip()
        if saved:
            return saved
    key = secrets.token_urlsafe(64)
    try:
        secret_file.write_text(key, encoding="utf-8")
    except OSError:
        pass
    return key


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
# bcrypt учитывает только первые 72 байта пароля
BCRYPT_MAX_BYTES = 72
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # неделя

# auto_error=False — токен необязателен (часть эндпоинтов работает и без него)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Пароли
# ---------------------------------------------------------------------------
def _pw_bytes(password: str) -> bytes:
    # bcrypt обрабатывает максимум 72 байта — усекаем явно и единообразно,
    # чтобы хеширование и проверка вели себя одинаково в любой версии bcrypt.
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_pw_bytes(password), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Зависимости FastAPI
# ---------------------------------------------------------------------------
def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    """Возвращает пользователя по токену либо None, если токена нет/он невалиден."""
    if not token:
        return None
    user_id = _decode_token(token)
    if user_id is None:
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_current_user(
    user: Optional[models.User] = Depends(get_current_user_optional),
) -> models.User:
    """Требует авторизации."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    user: models.User = Depends(get_current_user),
) -> models.User:
    """Требует роль администратора."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администратора",
        )
    return user
