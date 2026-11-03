"""Order life cycle (BR-07, BR-08) = Table 'Order status transitions' of Chapter 2."""
from ..domain.enums import OrderStatus

S = OrderStatus

# actor -> set of (from, to) it may perform  (FR-34, NFR-06)
ALLOWED = {
    "CUSTOMER":  {(S.PENDING_PAYMENT, S.CANCELLED), (S.PENDING, S.CANCELLED), (S.CONFIRMED, S.CANCELLED)},
    "SERVICE":   {(S.PENDING, S.CONFIRMED), (S.PENDING, S.CANCELLED), (S.CONFIRMED, S.CANCELLED)},
    "WAREHOUSE": {(S.CONFIRMED, S.PACKED)},
    "SHIPPING":  {(S.PACKED, S.SHIPPING), (S.SHIPPING, S.DELIVERED), (S.SHIPPING, S.CANCELLED)},
    "SYSTEM":    {(S.PENDING_PAYMENT, S.PENDING), (S.PENDING_PAYMENT, S.CANCELLED)},
}


class OrderStatusPolicy:
    """Who may move an order from one status to another."""

    @staticmethod
    def can_transition(actor: str, current: OrderStatus, target: OrderStatus) -> bool:
        return (current, target) in ALLOWED.get(actor, set())
