"""CustomerModel: Role, Account, Customer (+VIP/New), Address, FullName."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass
class FullName:
    first_name: str
    middle_name: str
    last_name: str


@dataclass
class Address:
    address_id: str
    street: str
    district: str
    city: str
    country: str
    pos_code: str


@dataclass
class Role:
    role_id: str
    name: str


@dataclass
class Account:
    account_id: int
    role: Role


@dataclass
class Customer:
    cus_id: str
    email: str
    phone: str
    password: str
    created: date
    full_name_info: FullName | None = None
    addresses: list[Address] = field(default_factory=list)  # 0..*

    def is_active(self) -> bool:
        raise NotImplementedError

    def lock(self) -> None:
        raise NotImplementedError

    def verify_password(self, raw_password: str) -> bool:
        raise NotImplementedError

    def full_name(self) -> str:
        raise NotImplementedError


@dataclass
class CustomerVIP(Customer):
    vip_level: int = 0
    loyalty_point: int = 0
    discount_rate: str = "0"


@dataclass
class CustomerNew(Customer):
    registration_date: date | None = None
    welcome_discount: float = 0.0
