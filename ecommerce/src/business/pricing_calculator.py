from decimal import Decimal


class PricingCalculator:
    def subtotal(self, items) -> Decimal:
        raise NotImplementedError

    def discount(self, subtotal: Decimal, customer=None, promo_code: str | None = None) -> Decimal:
        raise NotImplementedError

    def shipping_fee(self, address, method: str) -> Decimal:
        raise NotImplementedError

    def total(self, items, customer=None, address=None, method: str = "standard",
              promo_code: str | None = None) -> Decimal:
        raise NotImplementedError
