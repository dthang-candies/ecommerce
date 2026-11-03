from datetime import datetime
from typing import Optional

from ..domain.enums import OrderStatus, PaymentChannel, PaymentStatus
from ..domain.models import Payment
from ..persistence.repositories import OrderRepository, PaymentRepository
from .actor import SYSTEM
from .exceptions import Conflict, Forbidden, NotFound
from .integrations import GatewayResult, SandboxPaymentGateway
from .order_service import OrderService
from .transaction import transactional


class PaymentService:
    """UC-07 Pay online. The gateway callback is idempotent: the same transaction_id is applied once."""

    def __init__(self, session, payments: PaymentRepository, orders: OrderRepository, order_service: OrderService,
                 gateway: SandboxPaymentGateway | None = None):
        self.session, self.payments, self.orders, self.order_service = session, payments, orders, order_service
        self.gateway = gateway or SandboxPaymentGateway()

    @transactional
    def handle_callback(self, order_id: int, transaction_id: str, status: PaymentStatus,
                        now: Optional[datetime] = None) -> Payment:
        known = self.payments.by_transaction(transaction_id)
        if known is not None:                                       # duplicate callback -> no effect
            return known
        payment = self.payments.by_order(order_id)
        if payment is None:
            raise NotFound("Không tìm thấy giao dịch thanh toán")
        order = self.order_service._get_locked(order_id)
        if status == PaymentStatus.SUCCESS:
            payment.mark_success(transaction_id, now or datetime.now())
            self.order_service._apply(order, OrderStatus.PENDING, SYSTEM)
        else:
            payment.mark_failed()                                   # customer may retry before timeout
        return payment

    def pay(self, order_id: int, customer_id: int, channel: PaymentChannel, token: str) -> tuple[Payment, GatewayResult]:
        """Customer pays through the (sandbox) gateway: send order id + amount, apply the answer (UC-07 steps 1-6)."""
        self.order_service.expire_unpaid()                            # an overdue order is cancelled first (A2)
        order = self.orders.get(order_id)
        if order is None or order.customer_id != customer_id:
            raise NotFound("Đơn hàng không tồn tại")
        if order.payment_method != "ONLINE":
            raise Conflict("Đơn hàng này thanh toán khi nhận hàng")
        if order.status != OrderStatus.PENDING_PAYMENT.value:
            raise Conflict("Đơn hàng không còn ở trạng thái chờ thanh toán (có thể đã hết hạn 15 phút)")
        if channel == PaymentChannel.COD:
            raise Conflict("Phương thức thanh toán không hợp lệ")
        result = self.gateway.charge(order.id, order.total_amount, channel, token)
        payment = self.handle_callback(order_id, result.transaction_id, result.status)
        if payment.method != channel.value:
            payment.method = channel.value
            self.session.commit()
        return payment, result
