from __future__ import annotations

from ..domain.enums import SupportStatus
from ..domain.models import SupportRequest
from ..persistence.repositories import OrderRepository, SupportRepository
from .exceptions import BusinessError, Forbidden, InvalidTransition, NotFound
from .transaction import transactional


class SupportService:
    """UC-23 Handle Customer Request (FR-32): OPEN -> IN_PROGRESS -> RESOLVED."""

    def __init__(self, session, support: SupportRepository, orders: OrderRepository):
        self.session, self.support, self.orders = session, support, orders

    @transactional
    def create(self, customer_id: int, content: str, order_id: int | None) -> SupportRequest:
        content = content.strip()
        if len(content) < 5:
            raise BusinessError("Nội dung yêu cầu quá ngắn")
        if order_id is not None:
            order = self.orders.get(order_id)
            if order is None or order.customer_id != customer_id:
                raise NotFound("Đơn hàng không tồn tại")
        return self.support.add(SupportRequest(customer_id=customer_id, order_id=order_id, content=content,
                                               status=SupportStatus.OPEN.value))

    def mine(self, customer_id: int) -> list[SupportRequest]:
        return self.support.for_customer(customer_id)

    def list(self, status: str | None, page: int, size: int):
        return self.support.list(status, page, min(size, 100))

    def _get(self, request_id: int) -> SupportRequest:
        req = self.support.get(request_id)
        if req is None:
            raise NotFound("Yêu cầu không tồn tại")
        return req

    @transactional
    def reply(self, request_id: int, staff_id: int, response: str, resolve: bool) -> SupportRequest:
        req = self._get(request_id)
        if req.status == SupportStatus.RESOLVED.value:
            raise InvalidTransition("Yêu cầu đã được giải quyết")
        response = response.strip()
        if not response:
            raise BusinessError("Nội dung phản hồi là bắt buộc")
        req.assign(staff_id)
        req.response = response
        if resolve:
            req.resolve()
        return req

    @transactional
    def resolve(self, request_id: int, staff_id: int) -> SupportRequest:
        req = self._get(request_id)
        if req.status == SupportStatus.RESOLVED.value:
            return req
        if req.handled_by not in (None, staff_id):
            raise Forbidden("Yêu cầu đang được nhân viên khác xử lý")
        req.handled_by = staff_id
        req.resolve()
        return req
