from datetime import datetime, timedelta
from typing import Optional

from .. import config
from ..domain.enums import MovementType, OrderStatus
from ..domain.models import Customer, CustomerOrder
from ..persistence.repositories import InventoryRepository, OrderRepository, ReviewRepository
from .actor import Actor, SYSTEM
from .exceptions import Forbidden, InvalidTransition, NotFound
from .order_status import OrderStatusPolicy
from .transaction import transactional

POINT_UNIT = 10_000          # 1 loyalty point per 10,000 VND of a delivered order


class OrderService:
    """UC-25 Track and Cancel Order, UC-13 Process Orders (BR-07, BR-08)."""

    def __init__(self, session, orders: OrderRepository, inventory: InventoryRepository,
                 policy: OrderStatusPolicy = OrderStatusPolicy, reviews: ReviewRepository | None = None):
        self.session, self.orders, self.inventory, self.policy = session, orders, inventory, policy
        self.reviews = reviews

    def list_for_customer(self, customer_id: int) -> list[CustomerOrder]:
        return self.orders.list_by_customer(customer_id)

    def get_for_customer(self, order_id: int, customer_id: int) -> CustomerOrder:
        order = self.orders.get(order_id)
        if order is None or order.customer_id != customer_id:     # do not reveal other customers' orders
            raise NotFound("Đơn hàng không tồn tại")
        return order

    def get_for_staff(self, order_id: int) -> CustomerOrder:
        order = self.orders.get(order_id)
        if order is None:
            raise NotFound("Đơn hàng không tồn tại")
        return order

    def reviewed_products(self, order_id: int) -> set[int]:
        return self.reviews.reviewed_pairs(order_id) if self.reviews else set()

    def search(self, status: Optional[str], keyword: Optional[str], page: int, size: int, oldest_first: bool = False):
        return self.orders.search(status, (keyword or "").strip() or None, max(page, 1), min(size, 100), oldest_first)

    def _get_locked(self, order_id: int) -> CustomerOrder:
        order = self.orders.get(order_id, lock=True)
        if order is None:
            raise NotFound("Đơn hàng không tồn tại")
        return order

    def _apply(self, order: CustomerOrder, new_status: OrderStatus, actor: Actor) -> None:
        current = OrderStatus(order.status)
        if not self.policy.can_transition(actor.role, current, new_status):
            raise InvalidTransition(f"{actor.role} không thể chuyển đơn từ {current.value} sang {new_status.value}")
        order.change_status(new_status, actor.account_id)
        if new_status == OrderStatus.CANCELLED:                     # give the stock back
            for it in sorted(order.items, key=lambda i: i.product_id):
                self.inventory.increase(it.product_id, it.quantity)
                self.inventory.log(it.product_id, MovementType.RETURN.value, it.quantity, "CANCEL", order.id)
        elif new_status == OrderStatus.DELIVERED:                   # loyalty points for the customer
            customer = self.session.get(Customer, order.customer_id)
            customer.add_points(int(order.total_amount // POINT_UNIT))

    @transactional
    def change_status(self, order_id: int, new_status: OrderStatus, actor: Actor) -> CustomerOrder:
        order = self._get_locked(order_id)
        self._apply(order, new_status, actor)
        return order

    @transactional
    def cancel(self, order_id: int, customer_id: int) -> CustomerOrder:
        order = self._get_locked(order_id)
        if order.customer_id != customer_id:
            raise Forbidden("Đây không phải đơn hàng của bạn")
        if not order.can_be_cancelled():
            raise InvalidTransition("Đơn hàng đã được đóng gói, không thể hủy")
        self._apply(order, OrderStatus.CANCELLED, Actor("CUSTOMER", customer_id))
        return order

    @transactional
    def expire_unpaid(self, now: Optional[datetime] = None) -> int:
        """Run by a scheduler: cancel online orders unpaid for 15 minutes (BR-04)."""
        now = now or datetime.now()
        cutoff = now - timedelta(minutes=config.UNPAID_ORDER_TIMEOUT_MINUTES)
        expired = self.orders.unpaid_before(cutoff)
        for order in expired:
            self._apply(self._get_locked(order.id), OrderStatus.CANCELLED, SYSTEM)
        return len(expired)
