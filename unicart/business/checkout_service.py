from datetime import datetime
from decimal import Decimal
from typing import Optional

from datetime import timedelta

from ..domain.enums import EventType, MovementType, OrderStatus, PaymentMethod
from ..domain.models import CustomerOrder, InteractionLog, OrderItem, OrderStatusHistory, Payment
from ..persistence.repositories import (
    AddressRepository, CartRepository, InteractionRepository, InventoryRepository, OrderRepository,
    PromotionRepository,
)
from .exceptions import BusinessError, NotFound, OutOfStock
from .pricing import PricingCalculator
from .transaction import transactional


class CheckoutService:
    """UC-05 Place order. One transaction: reserve stock -> price -> save order -> clear cart.
    If any line is out of stock the whole transaction is rolled back (BR-02, BR-03)."""

    def __init__(self, session, carts: CartRepository, addresses: AddressRepository,
                 promotions: PromotionRepository, inventory: InventoryRepository,
                 orders: OrderRepository, pricing: PricingCalculator = PricingCalculator,
                 interactions: InteractionRepository | None = None):
        self.session, self.carts, self.addresses = session, carts, addresses
        self.promotions, self.inventory, self.orders, self.pricing = promotions, inventory, orders, pricing
        self.interactions = interactions

    def quote(self, customer_id: int, promo_code: Optional[str] = None, now: Optional[datetime] = None) -> dict:
        """Validate Shopping Cart + Calculate Order Total (the two <<include>> of UC-06). Changes nothing."""
        now = now or datetime.now()
        cart = self.carts.get_by_customer(customer_id)
        lines, issues = [], []
        if cart is not None:
            for it in sorted(cart.items, key=lambda i: i.product_id):
                p = it.product
                available = p.inventory.quantity if p.inventory else 0
                problem = None
                if not p.is_visible():
                    problem = "Sản phẩm không còn được bán"
                elif available < it.quantity:
                    problem = "Hết hàng" if available == 0 else f"Chỉ còn {available} sản phẩm"
                lines.append({"product": p, "quantity": it.quantity, "unit_price": p.price,
                              "sub_total": it.sub_total(), "problem": problem})
                if problem:
                    issues.append(f"{p.name}: {problem}")
        subtotal = sum((l["sub_total"] for l in lines), Decimal("0"))
        promo, promo_error = None, None
        if promo_code and promo_code.strip():
            promo = self.promotions.find_by_code(promo_code.strip().upper())
            if promo is None:
                promo_error = "Mã giảm giá không tồn tại"
            elif not promo.is_valid(subtotal, now):
                promo_error = "Mã giảm giá đã hết hạn hoặc chưa đạt giá trị đơn tối thiểu"
            if promo_error:
                promo = None
        discount = self.pricing.discount(promo, subtotal, now) if lines else Decimal("0")
        shipping = self.pricing.shipping_fee(subtotal) if lines else Decimal("0")
        return {"lines": lines, "subtotal": subtotal, "discount": discount, "shipping_fee": shipping,
                "total": self.pricing.total(subtotal, discount, shipping) if lines else Decimal("0"),
                "promo_code": promo.code if promo else None, "promo_error": promo_error, "issues": issues,
                "can_checkout": bool(lines) and not issues}

    @transactional
    def place_order(self, customer_id: int, address_id: int, method: PaymentMethod,
                    promo_code: Optional[str] = None, now: Optional[datetime] = None,
                    track: bool = True) -> CustomerOrder:
        now = now or datetime.now()
        cart = self.carts.get_by_customer(customer_id)
        if cart is None or cart.is_empty():
            raise BusinessError("Giỏ hàng đang trống")
        address = self.addresses.get_for_customer(address_id, customer_id)
        if address is None:
            raise NotFound("Không tìm thấy địa chỉ giao hàng")
        promo = None
        if promo_code:
            promo = self.promotions.find_by_code(promo_code)

        lines = sorted(cart.items, key=lambda i: i.product_id)      # fixed order avoids deadlocks
        for it in lines:
            if not it.product.is_visible():
                raise BusinessError(f"{it.product.name} không còn được bán")
            if not self.inventory.try_decrease(it.product_id, it.quantity):
                raise OutOfStock(f"{it.product.name}: không đủ hàng trong kho")

        subtotal = cart.subtotal()
        if promo_code and (promo is None or not promo.is_valid(subtotal, now)):
            raise BusinessError("Mã giảm giá không hợp lệ hoặc chưa đạt giá trị đơn tối thiểu")
        discount = self.pricing.discount(promo, subtotal, now)
        shipping = self.pricing.shipping_fee(subtotal)
        initial = OrderStatus.PENDING_PAYMENT if method == PaymentMethod.ONLINE else OrderStatus.PENDING

        order = CustomerOrder(
            customer_id=customer_id, promotion_id=promo.id if promo and discount else None,
            ship_recipient=address.recipient, ship_phone=address.phone, ship_address=address.one_line(),
            subtotal=subtotal, discount=discount, shipping_fee=shipping,
            total_amount=self.pricing.total(subtotal, discount, shipping),
            payment_method=method.value, status=initial.value,
        )
        for it in lines:                                            # price snapshot (BR-03)
            order.items.append(OrderItem(product_id=it.product_id, quantity=it.quantity,
                                         unit_price=it.product.price))
        order.history.append(OrderStatusHistory(from_status=None, to_status=initial.value, changed_by=customer_id))
        order.payment = Payment(method="CARD" if method == PaymentMethod.ONLINE else "COD",
                                amount=order.total_amount)
        self.orders.add(order)
        for it in lines:
            self.inventory.log(it.product_id, MovementType.OUT.value, it.quantity, "ORDER", order.id)
        if track and self.interactions is not None:                 # FR-19 + attribution for FR-18
            since = now - timedelta(days=7)
            for it in lines:
                source = self.interactions.rec_sourced_recently(customer_id, it.product_id, since)
                self.interactions.add(InteractionLog(customer_id=customer_id, product_id=it.product_id,
                                                     event_type=EventType.PURCHASE.value, keyword=source))
        cart.clear()
        return order
