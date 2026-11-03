"""Small input rules shared by several services (server-side validation, Chapter 2 NFRs)."""
import re

from ..exceptions import BusinessError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^[0-9+][0-9 .\-]{7,18}$")


def check_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not _EMAIL.match(email) or len(email) > 150:
        raise BusinessError("Email không hợp lệ")
    return email


def check_password(password: str) -> str:
    if len(password or "") < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise BusinessError("Mật khẩu tối thiểu 8 ký tự, gồm cả chữ và số")
    return password


def check_phone(phone: str | None, required: bool = False) -> str | None:
    phone = (phone or "").strip()
    if not phone:
        if required:
            raise BusinessError("Số điện thoại là bắt buộc")
        return None
    if not _PHONE.match(phone):
        raise BusinessError("Số điện thoại không hợp lệ")
    return phone
