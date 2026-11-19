class PricingCalculator:
    def subtotal(self, items) -> float:
        return sum(item.quantity * item.unit_price for item in items)

    def discount(self, subtotal: float, promotion=None) -> float:
        # TODO: áp dụng DiscountType.PERCENT / AMOUNT theo mô hình khuyến mãi.
        raise NotImplementedError

    def shipping_fee(self, address, items) -> float:
        # TODO: xác định chính sách phí vận chuyển.
        raise NotImplementedError

    def total(self, subtotal: float, discount: float, shipping_fee: float) -> float:
        return max(0.0, subtotal - discount + shipping_fee)
