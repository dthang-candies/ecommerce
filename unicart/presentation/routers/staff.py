"""Staff controllers: UC-13 process orders, UC-21 prepare order, UC-14 delivery status, UC-12/22 inventory & restock,
UC-23 support, UC-15/20 reports, plus partner webhooks and sandbox simulators."""
from datetime import date, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from ...business.actor import Actor
from ...business.exceptions import NotFound
from ...domain.enums import OrderStatus
from ..deps import get_services, partner_only, require_roles
from ..schemas import (
    CarrierSandboxIn, QuantityIn, RestockIn, ShipmentCallbackIn, StatusIn, SupplierCallbackIn, SupplierResponseIn,
    SupportReplyIn, ThresholdIn,
)
from ..serializers import deep_money, inventory_json, order_json, restock_json, support_json
from ..wiring import Services

router = APIRouter(prefix="/api", tags=["staff"])
Svc = Annotated[Services, Depends(get_services)]
OrderStaff = Annotated[Actor, Depends(require_roles("SERVICE", "WAREHOUSE", "SALES", "ADMIN", "MANAGER"))]
Warehouse = Annotated[Actor, Depends(require_roles("WAREHOUSE", "ADMIN"))]
StockViewer = Annotated[Actor, Depends(require_roles("WAREHOUSE", "ADMIN", "MANAGER"))]
Sales = Annotated[Actor, Depends(require_roles("SALES", "ADMIN"))]


# ---- orders
@router.get("/staff/orders")
def staff_orders(svc: Svc, _: OrderStaff, status: Optional[OrderStatus] = None, q: Optional[str] = Query(None, max_length=50),
                 page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    # the work queues (confirm / pack) are processed oldest first
    items, total = svc.orders.search(status.value if status else None, q, page, size,
                                     oldest_first=status in (OrderStatus.PENDING, OrderStatus.CONFIRMED))
    return {"total": total, "page": page, "size": size, "items": [order_json(o) for o in items]}


@router.get("/staff/orders/{order_id}")
def staff_order(order_id: int, svc: Svc, _: OrderStaff):
    return order_json(svc.orders.get_for_staff(order_id), detail=True)


@router.patch("/orders/{order_id}/status")
def change_order_status(order_id: int, body: StatusIn, svc: Svc,
                        actor: Annotated[Actor, Depends(require_roles("SERVICE", "WAREHOUSE"))]):
    """SERVICE: PENDING -> CONFIRMED / CANCELLED.  WAREHOUSE: CONFIRMED -> PACKED (creates the waybill)."""
    new = OrderStatus(body.status)
    order = svc.shipping.pack(order_id, actor) if new == OrderStatus.PACKED else svc.orders.change_status(order_id, new, actor)
    return order_json(order, detail=True)


# ---- partner webhooks (X-Partner-Secret) and sandbox simulators for the demo
@router.post("/shipping/callback", dependencies=[Depends(partner_only)])
def shipping_callback(body: ShipmentCallbackIn, svc: Svc):
    return order_json(svc.shipping.carrier_update(body.order_id, body.status), detail=True)


@router.post("/staff/sandbox/carrier/{order_id}")
def sandbox_carrier(order_id: int, body: CarrierSandboxIn, svc: Svc, _: Warehouse):
    """Stands in for the shipping provider's tracking feed during demos."""
    return order_json(svc.shipping.carrier_update(order_id, body.status), detail=True)


@router.post("/suppliers/callback", dependencies=[Depends(partner_only)])
def supplier_callback(body: SupplierCallbackIn, svc: Svc):
    return restock_json(svc.restock.supplier_respond(body.request_id, body.accept))


@router.post("/staff/sandbox/supplier/{request_id}")
def sandbox_supplier(request_id: int, body: SupplierResponseIn, svc: Svc, _: Warehouse):
    return restock_json(svc.restock.supplier_respond(request_id, body.accept))


# ---- inventory & restock
@router.get("/inventory")
def inventory_list(svc: Svc, _: StockViewer, q: Optional[str] = Query(None, max_length=50),
                   page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    items, total = svc.inventory.list(q, page, size)
    return {"total": total, "page": page, "size": size, "items": [inventory_json(i) for i in items]}


@router.get("/inventory/low-stock")
def low_stock(svc: Svc, _: StockViewer):
    return [inventory_json(i) for i in svc.inventory.low_stock_report()]


@router.get("/inventory/summary")
def inventory_summary(svc: Svc, _: StockViewer):
    return deep_money(svc.inventory.summary())


@router.get("/inventory/{product_id}/movements")
def inventory_movements(product_id: int, svc: Svc, _: StockViewer):
    return [{"id": m.id, "type": m.type, "quantity": m.quantity, "reason": m.reason, "order_id": m.order_id,
             "created_at": m.created_at.isoformat()} for m in svc.inventory.movements(product_id)]


@router.post("/inventory/{product_id}/restock")
def restock_now(product_id: int, body: QuantityIn, svc: Svc, actor: Warehouse):
    """Goods already on the shelf (manual receipt). The normal flow is a restock request to a supplier."""
    return inventory_json(svc.inventory.restock(product_id, body.quantity, actor.account_id))


@router.put("/inventory/{product_id}/threshold")
def set_threshold(product_id: int, body: ThresholdIn, svc: Svc, actor: Warehouse):
    return inventory_json(svc.inventory.set_threshold(product_id, body.min_threshold, actor.account_id))


@router.get("/suppliers")
def suppliers(svc: Svc, _: Warehouse):
    return [{"id": s.id, "name": s.name, "contact": s.contact} for s in svc.restock.suppliers_list()]


@router.get("/restock-requests")
def restock_requests(svc: Svc, _: StockViewer, status: Optional[str] = None):
    return [restock_json(r) for r in svc.restock.list(status)]


@router.post("/restock-requests", status_code=201)
def create_restock(body: RestockIn, svc: Svc, actor: Warehouse):
    return restock_json(svc.restock.create(body.product_id, body.supplier_id, body.quantity, actor.account_id))


@router.post("/restock-requests/{request_id}/receive")
def receive_restock(request_id: int, svc: Svc, actor: Warehouse):
    return restock_json(svc.restock.receive(request_id, actor.account_id))


# ---- UC-23 customer support
@router.get("/staff/support-requests")
def support_requests(svc: Svc, _: Sales, status: Optional[str] = None, page: int = Query(1, ge=1),
                     size: int = Query(20, ge=1, le=100)):
    items, total = svc.support.list(status, page, size)
    return {"total": total, "page": page, "size": size, "items": [support_json(s) for s in items]}


@router.post("/staff/support-requests/{request_id}/reply")
def support_reply(request_id: int, body: SupportReplyIn, svc: Svc, actor: Sales):
    return support_json(svc.support.reply(request_id, actor.account_id, body.response, body.resolve))


@router.post("/staff/support-requests/{request_id}/resolve")
def support_resolve(request_id: int, svc: Svc, actor: Sales):
    return support_json(svc.support.resolve(request_id, actor.account_id))


# ---- reports
def _period(start: Optional[date], end: Optional[date]) -> tuple[date, date]:
    end = end or date.today()
    return start or end - timedelta(days=29), end


@router.get("/reports/business")
def business_report(svc: Svc, _: Annotated[Actor, Depends(require_roles("MANAGER", "ADMIN"))],
                    start: Optional[date] = None, end: Optional[date] = None):
    return deep_money(svc.reports.business(*_period(start, end)))


@router.get("/reports/recommendations")
def recommendation_report(svc: Svc, _: Annotated[Actor, Depends(require_roles("MANAGER", "MARKETING", "ADMIN"))],
                          start: Optional[date] = None, end: Optional[date] = None):
    return svc.reports.recommendation_performance(*_period(start, end))
