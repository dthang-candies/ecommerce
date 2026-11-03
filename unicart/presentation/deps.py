"""FastAPI dependencies: one DB session + service set per request, authentication and RBAC (NFR-06)."""
import hmac
import time
from collections import defaultdict, deque
from typing import Annotated, Iterator, Optional

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .. import config
from ..business.actor import Actor
from ..business.exceptions import Forbidden, Unauthorized, BusinessError
from .security import decode_token
from .wiring import Services, build_services

_bearer = HTTPBearer(auto_error=False)


def get_services(request: Request) -> Iterator[Services]:
    session = request.app.state.db.new_session()
    try:
        yield build_services(session, getattr(request.app.state, "ai", None))
    finally:
        session.close()


def optional_actor(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
                   svc: Services = Depends(get_services)) -> Optional[Actor]:
    if creds is None:
        return None
    account = svc.auth.get_active(decode_token(creds.credentials))     # a locked account loses access at once
    return Actor(role=account.role.name, account_id=account.id)


def soft_actor(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
               svc: Services = Depends(get_services)) -> Optional[Actor]:
    """Like optional_actor, but a stale or invalid token just means 'guest' (used on public pages)."""
    try:
        return optional_actor(creds, svc)
    except Unauthorized:
        return None


Soft = Annotated[Optional[Actor], Depends(soft_actor)]


def current_actor(actor: Optional[Actor] = Depends(optional_actor)) -> Actor:
    if actor is None:
        raise Unauthorized("Vui lòng đăng nhập")
    return actor


def require_roles(*roles: str):
    def dependency(actor: Actor = Depends(current_actor)) -> Actor:
        if actor.role not in roles:
            raise Forbidden("Bạn không có quyền thực hiện chức năng này")
        return actor
    return dependency


def partner_only(x_partner_secret: str = Header(default="")) -> None:
    """Webhooks of the payment gateway / carrier / supplier authenticate with a shared secret."""
    if not hmac.compare_digest(x_partner_secret.encode(), config.PARTNER_SECRET.encode()):
        raise Unauthorized("Sai khóa xác thực đối tác")


class LoginThrottle:
    """Tiny in-memory brute-force guard: max `limit` failed logins per key within `window` seconds."""

    def __init__(self, limit: int = 8, window: int = 300):
        self.limit, self.window, self.fails = limit, window, defaultdict(deque)

    def _prune(self, key: str) -> deque:
        q, now = self.fails[key], time.monotonic()
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        if len(self._prune(key)) >= self.limit:
            raise TooManyAttempts("Đăng nhập sai quá nhiều lần, vui lòng thử lại sau vài phút")

    def failed(self, key: str) -> None:
        self._prune(key).append(time.monotonic())

    def succeeded(self, key: str) -> None:
        self.fails.pop(key, None)


class TooManyAttempts(BusinessError):
    http_status, code = 429, "TOO_MANY_ATTEMPTS"


throttle = LoginThrottle()


class RateLimited(BusinessError):
    http_status, code = 429, "TOO_MANY_REQUESTS"


class SlidingWindow:
    """Per-key request budget, protects the shared free Gemini quota from one noisy client."""

    def __init__(self, limit: int, window: int = 60):
        self.limit, self.window, self.hits = limit, window, defaultdict(deque)

    def allow(self, key: str) -> bool:
        q, now = self.hits[key], time.monotonic()
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


text_budget, image_budget, voice_budget = SlidingWindow(60), SlidingWindow(10), SlidingWindow(10)
chat_budget = SlidingWindow(20)                   # chatbot questions per minute per account / client address
