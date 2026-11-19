import hashlib
import secrets
from datetime import datetime, timedelta

from ... import config
from ...domain.extended import security
from ...domain.models import Account, Cart, Customer, PasswordReset
from ...persistence.repositories import AccountRepository, CustomerRepository, PasswordResetRepository
from ..exceptions import Conflict, Unauthorized
from ..transaction import transactional
from .validation import check_email, check_password, check_phone
from ..exceptions import BusinessError


class AuthService:
    """UC-01 Register Account, UC-26 Login/Logout (FR-01, FR-28, NFR-03)."""

    def __init__(self, session, accounts: AccountRepository, customers: CustomerRepository,
                 resets: PasswordResetRepository | None = None):
        self.session, self.accounts, self.customers = session, accounts, customers
        self.resets = resets or PasswordResetRepository(session)

    @transactional
    def register(self, email: str, password: str, first_name: str, last_name: str,
                 middle_name: str | None = None, phone: str | None = None) -> Account:
        email = check_email(email)
        check_password(password)
        if not first_name.strip() or not last_name.strip():
            raise BusinessError("Họ và tên là bắt buộc")
        if self.accounts.by_email(email) is not None:
            raise Conflict("Email đã được đăng ký")
        role = self.accounts.role_by_name("CUSTOMER")
        account = self.accounts.add(Account(email=email, password_hash=security.hash_password(password),
                                            role_id=role.id, status="ACTIVE"))
        self.customers.add(Customer(id=account.id, first_name=first_name.strip(),
                                    middle_name=(middle_name or "").strip() or None, last_name=last_name.strip(),
                                    phone=check_phone(phone), loyalty_tier="NEW", loyalty_point=0))
        self.session.add(Cart(customer_id=account.id))          # BR-02: exactly one current cart
        self.session.flush()
        self.session.refresh(account)
        return account

    def authenticate(self, email: str, password: str) -> Account:
        account = self.accounts.by_email((email or "").strip())
        # same message for unknown e-mail and wrong password: do not reveal which accounts exist
        if account is None or not account.verify_password(password or ""):
            raise Unauthorized("Email hoặc mật khẩu không đúng")
        if not account.is_active():
            raise Unauthorized("Tài khoản đã bị khóa")
        return account

    def get_active(self, account_id: int) -> Account:
        account = self.accounts.get(account_id)
        if account is None or not account.is_active():
            raise Unauthorized("Phiên đăng nhập không còn hiệu lực")
        return account

    @transactional
    def change_password(self, account_id: int, old: str, new: str) -> None:
        account = self.get_active(account_id)
        if not account.verify_password(old):
            raise BusinessError("Mật khẩu hiện tại không đúng")
        check_password(new)
        account.password_hash = security.hash_password(new)

    # ---- forgotten password
    @transactional
    def request_password_reset(self, email: str, now: datetime | None = None) -> tuple[str, str] | None:
        """Returns (e-mail, one-time token) to send, or None when there is no such active account. The caller must
        answer the same way in both cases, so the form cannot be used to find out which e-mails are registered."""
        now = now or datetime.now()
        account = self.accounts.by_email((email or "").strip())
        if account is None or not account.is_active():
            return None
        self.resets.purge_expired(now - timedelta(days=1))
        self.resets.revoke_for_account(account.id, now)                # only the newest link works
        token = secrets.token_urlsafe(32)
        self.resets.add(PasswordReset(account_id=account.id, token_hash=_token_hash(token),
                                      expires_at=now + timedelta(minutes=config.PASSWORD_RESET_MINUTES)))
        return account.email, token

    @transactional
    def reset_password(self, token: str, new: str, now: datetime | None = None) -> Account:
        now = now or datetime.now()
        check_password(new)                                            # a weak password does not use up the link
        reset = self.resets.by_hash(_token_hash(token or ""), lock=True)
        account = self.accounts.get(reset.account_id) if reset is not None and reset.is_usable(now) else None
        if account is None or not account.is_active():
            raise BusinessError("Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn. Vui lòng gửi yêu cầu mới.")
        account.password_hash = security.hash_password(new)
        self.resets.revoke_for_account(account.id, now)
        return account


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
