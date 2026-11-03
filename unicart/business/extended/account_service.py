from __future__ import annotations

import logging

from ...domain.extended import security
from ...domain.models import Account, Role
from ...persistence.repositories import AccountRepository
from ..exceptions import BusinessError, Conflict, Forbidden, NotFound
from ..transaction import transactional
from .validation import check_email, check_password

audit = logging.getLogger("unicart.audit")
STAFF_ROLES = ("ADMIN", "SERVICE", "SALES", "WAREHOUSE", "MARKETING", "MANAGER")


class AccountService:
    """UC-24 Manage Accounts and Roles (FR-33, BR-10: exactly one role per account)."""

    def __init__(self, session, accounts: AccountRepository):
        self.session, self.accounts = session, accounts

    def list(self, role: str | None = None, keyword: str | None = None) -> list[Account]:
        return self.accounts.list(role, keyword)

    def roles(self) -> list[Role]:
        return self.accounts.roles()

    def _get(self, account_id: int) -> Account:
        account = self.accounts.get(account_id)
        if account is None:
            raise NotFound("Tài khoản không tồn tại")
        return account

    @transactional
    def create_staff(self, email: str, password: str, role_name: str, admin_id: int) -> Account:
        email = check_email(email)
        check_password(password)
        if role_name not in STAFF_ROLES:
            raise BusinessError("Vai trò nhân viên không hợp lệ")
        if self.accounts.by_email(email):
            raise Conflict("Email đã tồn tại")
        role = self.accounts.role_by_name(role_name)
        account = self.accounts.add(Account(email=email, password_hash=security.hash_password(password),
                                            role_id=role.id, status="ACTIVE"))
        self.session.refresh(account)
        audit.info("admin=%s created staff account id=%s role=%s", admin_id, account.id, role_name)
        return account

    @transactional
    def set_role(self, account_id: int, role_name: str, admin_id: int) -> Account:
        account = self._get(account_id)
        if account.role.name == "CUSTOMER" or role_name not in STAFF_ROLES:
            raise BusinessError("Chỉ có thể gán vai trò nhân viên cho tài khoản nhân viên")
        if account.id == admin_id:
            raise Forbidden("Không thể tự đổi vai trò của chính mình")
        account.role_id = self.accounts.role_by_name(role_name).id
        self.session.flush()
        self.session.refresh(account)
        audit.info("admin=%s set role of account=%s to %s", admin_id, account_id, role_name)
        return account

    @transactional
    def set_locked(self, account_id: int, locked: bool, admin_id: int) -> Account:
        account = self._get(account_id)
        if account.id == admin_id:
            raise Forbidden("Không thể tự khóa tài khoản của chính mình")
        account.lock() if locked else account.unlock()
        audit.info("admin=%s %s account=%s", admin_id, "locked" if locked else "unlocked", account_id)
        return account
