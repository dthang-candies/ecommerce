"""CartModel: Cart, CartItem."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .product_model import Product


@dataclass
class CartItem:
    product: Product
    quantity: int
    unit_price: int

    def subtotal(self) -> int:
        raise NotImplementedError


@dataclass
class Cart:
    cart_id: str
    create_date: date
    total_amount: float
    customer_id: str | None = None
    cart_items: list[CartItem] = field(default_factory=list)  # 0..*

    def add_item(self, product: Product, quantity: int) -> None:
        raise NotImplementedError

    def update_quantity(self, product_id: int, quantity: int) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def subtotal(self) -> Decimal:
        raise NotImplementedError

    def is_empty(self) -> bool:
        raise NotImplementedError
