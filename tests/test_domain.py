"""Unit tests of domain methods (no database needed)."""
from datetime import datetime
from decimal import Decimal

from unicart.domain.enums import OrderStatus
from unicart.domain.models import Cart, CartItem, Customer, CustomerOrder, Inventory, Product, Promotion
from unicart.business.order_status import OrderStatusPolicy
from unicart.business.pricing import PricingCalculator


def test_full_name_skips_empty_middle_name():
    c = Customer(first_name="Binh", middle_name=None, last_name="Tran")
    assert c.full_name() == "Binh Tran"


def test_inventory_low_and_fulfill():
    inv = Inventory(product_id=1, quantity=3, min_threshold=5)
    assert inv.is_low() and inv.can_fulfill(3) and not inv.can_fulfill(4)


def test_cart_subtotal_and_add_merges_same_product():
    p = Product(id=1, price=Decimal("100000"))
    cart = Cart(items=[])
    cart.add_item(p, 1)
    cart.add_item(p, 2)
    assert len(cart.items) == 1 and cart.subtotal() == Decimal("300000")


def test_promotion_percent_and_min_order():
    promo = Promotion(code="X", discount_type="PERCENT", discount_value=Decimal("10"),
                      min_order_value=Decimal("200000"), start_at=datetime(2020, 1, 1),
                      end_at=datetime(2099, 1, 1), active=True)
    now = datetime(2026, 1, 1)
    assert PricingCalculator.discount(promo, Decimal("500000"), now) == Decimal("50000.00")
    assert PricingCalculator.discount(promo, Decimal("100000"), now) == Decimal("0")


def test_shipping_fee_rule():
    assert PricingCalculator.shipping_fee(Decimal("100000")) == Decimal("30000")
    assert PricingCalculator.shipping_fee(Decimal("500000")) == Decimal("0")


def test_cancel_rule_and_history():
    o = CustomerOrder(status="PACKED", items=[], history=[])
    assert not o.can_be_cancelled()
    o.status = "PENDING"
    assert o.can_be_cancelled()
    o.change_status(OrderStatus.CONFIRMED, 2)
    assert o.status == "CONFIRMED" and o.history[0].from_status == "PENDING"


def test_status_policy_by_actor():
    S = OrderStatus
    assert OrderStatusPolicy.can_transition("WAREHOUSE", S.CONFIRMED, S.PACKED)
    assert not OrderStatusPolicy.can_transition("WAREHOUSE", S.PENDING, S.PACKED)
    assert not OrderStatusPolicy.can_transition("CUSTOMER", S.SHIPPING, S.CANCELLED)
