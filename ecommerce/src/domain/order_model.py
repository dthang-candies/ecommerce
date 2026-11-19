"""OrderModel: CustomerOrder, OrderItem, OrderStatusHistory, Payment (+PayCash/PayCredit), Shipping."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from .product_model import Product


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPING = "shipping"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class OrderItem:
    product: Product
    quantity: int
    unit_price: float
    sub_total: float

    def subtotal(self) -> Decimal:
        raise NotImplementedError


@dataclass
class OrderStatusHistory:
    order_id: str
    old_status: str
    new_status: str
    changed_at: datetime


@dataclass
class Payment:
    payment_id: str
    payment_date: date
    amount: float
    status: str

    def mark_success(self, transaction_id: int, at: datetime) -> None:
        raise NotImplementedError

    def mark_fail(self) -> None:
        raise NotImplementedError

    def is_complete(self) -> bool:
        raise NotImplementedError


@dataclass
class PayCash(Payment):
    received_amount: float = 0.0


@dataclass
class PayCredit(Payment):
    transaction_id: str = ""
    card_last_four_digits: str = ""
    authorization_code: str = ""


@dataclass
class Shipping:
    shipping_id: str
    shipping_method: str
    shipping_fee: float
    tracking_number: str
    shipping_status: str
    delivery_date: date | None = None

    def mark_in_transit(self) -> None:
        raise NotImplementedError

    def mark_delivered(self, on: date) -> None:
        raise NotImplementedError


@dataclass
class CustomerOrder:
    order_id: str
    order_date: date
    total_amount: float
    status: str
    customer_id: str
    order_items: list[OrderItem] = field(default_factory=list)  # 1..*
    payment: Payment | None = None
    shipping: Shipping | None = None  # 0..1
    history: list[OrderStatusHistory] = field(default_factory=list)


Order = CustomerOrder  # alias theo sơ đồ lớp
