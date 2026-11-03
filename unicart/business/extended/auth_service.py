from ...domain.extended import security
from ...domain.models import Account, Cart, Customer
from ...persistence.repositories import AccountRepository, CustomerRepository
from ..exceptions import Conflict, Unauthorized
from ..transaction import transactional
from .validation import check_email, check_password, check_phone
from ..exceptions import BusinessError


class AuthService:
    """UC-01 Register Account, UC-26 Login/Logout (FR-01, FR-28, NFR-03)."""

    def __init__(self, session, accounts: AccountRepository, customers: CustomerRepository):
        self.session, self.accounts, self.customers = session, accounts, customers

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
