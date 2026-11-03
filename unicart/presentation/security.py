"""JWT access tokens (presentation concern: the business layer only knows accounts and roles)."""
from datetime import datetime, timedelta, timezone

import jwt

from .. import config
from ..business.exceptions import Unauthorized


def create_token(account_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(account_id), "role": role, "iat": now,
               "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES)}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> int:
    try:
        return int(jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise Unauthorized("Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
