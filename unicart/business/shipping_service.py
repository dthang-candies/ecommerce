from datetime import date, datetime

from ..domain.enums import OrderStatus, PaymentStatus, ShipmentStatus
from ..domain.models import CustomerOrder, Shipment
from ..persistence.repositories import OrderRepository, ShipmentRepository
from .actor import Actor
from .exceptions import BusinessError, InvalidTransition, NotFound
from .integrations import SandboxCarrier
from .order_service import OrderService
from .transaction import transactional


class ShippingService:
    """UC-21 Prepare Order (pack + hand over) and UC-14 Update Delivery Status (carrier callbacks), FR-16, FR-30."""

    def __init__(self, session, orders: OrderRepository, shipments: ShipmentRepository,
                 order_service: OrderService, carrier: SandboxCarrier | None = None):
        self.session, self.orders, self.shipments = session, orders, shipments
        self.order_service, self.carrier = order_service, carrier or SandboxCarrier()

    @transactional
    def pack(self, order_id: int, actor: Actor) -> CustomerOrder:
        """Warehouse marks a CONFIRMED order as packed; a waybill is created with the carrier."""
        order = self.order_service._get_locked(order_id)
        self.order_service._apply(order, OrderStatus.PACKED, actor)
        if self.shipments.by_order(order.id) is None:
            self.shipments.add(Shipment(order_id=order.id, carrier=self.carrier.name,
                                        tracking_number=self.carrier.create_waybill(order.id),
                                        status=ShipmentStatus.CREATED.value))
        self.session.refresh(order)
        return order

    @transactional
    def carrier_update(self, order_id: int, status: ShipmentStatus, now: datetime | None = None) -> CustomerOrder:
        """Webhook of the shipping provider. Repeated callbacks with the same status are ignored."""
        shipper = Actor("SHIPPING")
        order = self.order_service._get_locked(order_id)
        shipment = self.shipments.by_order(order_id)
        if shipment is None:
            raise NotFound("Đơn hàng chưa có vận đơn")
        if shipment.status == status.value:
            return order
        if status == ShipmentStatus.IN_TRANSIT:
            self.order_service._apply(order, OrderStatus.SHIPPING, shipper)
            shipment.mark_in_transit()
        elif status == ShipmentStatus.DELIVERED:
            self.order_service._apply(order, OrderStatus.DELIVERED, shipper)
            shipment.mark_delivered((now or datetime.now()).date())
            payment = order.payment
            if payment is not None and not payment.is_completed():          # COD: cash collected on delivery
                payment.status = PaymentStatus.SUCCESS.value
                payment.paid_at = now or datetime.now()
        elif status == ShipmentStatus.FAILED:
            self.order_service._apply(order, OrderStatus.CANCELLED, shipper)   # returns stock
            shipment.status = ShipmentStatus.FAILED.value
        else:
            raise BusinessError("Trạng thái vận chuyển không hợp lệ")
        return order

    def tracking(self, order_id: int) -> Shipment | None:
        return self.shipments.by_order(order_id)
