"""Calculate Order Total (include of UC-06): BR-05, BR-06."""
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Optional

from .. import config
from ..domain.models import Promotion


class PricingCalculator:
    @staticmethod
    def subtotal(lines: Iterable[tuple[Decimal, int]]) -> Decimal:
        return sum((price * qty for price, qty in lines), Decimal("0"))

    @staticmethod
    def discount(promo: Optional[Promotion], subtotal: Decimal, now: datetime) -> Decimal:
        if promo is None or not promo.is_valid(subtotal, now):
            return Decimal("0")
        return promo.compute_discount(subtotal)

    @staticmethod
    def shipping_fee(subtotal: Decimal) -> Decimal:
        if subtotal >= config.FREE_SHIPPING_THRESHOLD:
            return Decimal("0")
        return Decimal(config.FLAT_SHIPPING_FEE)

    @classmethod
    def total(cls, subtotal: Decimal, discount: Decimal, shipping: Decimal) -> Decimal:
        return subtotal - discount + shipping
