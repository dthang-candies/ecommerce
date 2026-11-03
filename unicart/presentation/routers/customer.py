"""Customer-facing controllers: UC-05 cart, UC-06 checkout, UC-07 payment, UC-08 profile, UC-09 review,
UC-25 track/cancel order, support requests."""
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from ...business.actor import Actor
from ...domain.enums import PaymentStatus
from ..extended.deps import get_services, partner_only, require_roles
from ..extended.schemas import (
    AddressIn, CartAddIn, CartUpdateIn, OrderIn, PayIn, PaymentCallbackIn, ProfileIn, QuoteIn, ReviewIn, SupportIn,
)
from ..serializers import (
    address_json, cart_json, customer_json, order_json, payment_json, quote_json, support_json,
)
from ..wiring import Services

router = APIRouter(prefix="/api", tags=["customer"])
Svc = Annotated[Services, Depends(get_services)]
Customer = Annotated[Actor, Depends(require_roles("CUSTOMER"))]


# ---- UC-08 profile & address book
@router.get("/me/profile")
def get_profile(svc: Svc, me: Customer):
    return customer_json(svc.customers.profile(me.account_id), svc.auth.get_active(me.account_id))


@router.put("/me/profile")
def update_profile(body: ProfileIn, svc: Svc, me: Customer):
    c = svc.customers.update_profile(me.account_id, body.first_name, body.last_name, body.middle_name, body.phone)
    return customer_json(c, svc.auth.get_active(me.account_id))


@router.get("/me/addresses")
def list_addresses(svc: Svc, me: Customer):
    return [address_json(a) for a in svc.customers.list_addresses(me.account_id)]


@router.post("/me/addresses", status_code=201)
def add_address(body: AddressIn, svc: Svc, me: Customer):
    return address_json(svc.customers.add_address(me.account_id, **body.model_dump()))


@router.put("/me/addresses/{address_id}")
def update_address(address_id: int, body: AddressIn, svc: Svc, me: Customer):
    return address_json(svc.customers.update_address(me.account_id, address_id, **body.model_dump()))


@router.delete("/me/addresses/{address_id}", status_code=204)
def delete_address(address_id: int, svc: Svc, me: Customer):
    svc.customers.delete_address(me.account_id, address_id)
    return Response(status_code=204)


# ---- UC-05 cart
@router.get("/cart")
def view_cart(svc: Svc, me: Customer):
    return cart_json(svc.carts.view(me.account_id))


@router.post("/cart/items", status_code=201)
def add_to_cart(body: CartAddIn, svc: Svc, me: Customer):
    return cart_json(svc.carts.add_item(me.account_id, body.product_id, body.quantity, body.source, body.track))


@router.patch("/cart/items/{product_id}")
def update_cart_item(product_id: int, body: CartUpdateIn, svc: Svc, me: Customer):
    return cart_json(svc.carts.update_quantity(me.account_id, product_id, body.quantity))


@router.delete("/cart/items/{product_id}")
def remove_cart_item(product_id: int, svc: Svc, me: Customer):
    return cart_json(svc.carts.remove_item(me.account_id, product_id))


# ---- UC-06 checkout
@router.post("/checkout/quote")
def checkout_quote(body: QuoteIn, svc: Svc, me: Customer):
    return quote_json(svc.checkout.quote(me.account_id, body.promo_code))


@router.post("/orders", status_code=201)
def place_order(body: OrderIn, svc: Svc, me: Customer):
    order = svc.checkout.place_order(me.account_id, body.address_id, body.payment_method, body.promo_code,
                                     track=body.track)
    return order_json(order, detail=True)


# ---- UC-25 track and cancel
@router.get("/orders")
def my_orders(svc: Svc, me: Customer):
    return [order_json(o) for o in svc.orders.list_for_customer(me.account_id)]


@router.get("/orders/{order_id}")
def my_order(order_id: int, svc: Svc, me: Customer):
    order = svc.orders.get_for_customer(order_id, me.account_id)
    return order_json(order, detail=True, reviewed=svc.orders.reviewed_products(order_id))


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, svc: Svc, me: Customer):
    return order_json(svc.orders.cancel(order_id, me.account_id), detail=True)


# ---- UC-09 review
@router.post("/orders/{order_id}/reviews", status_code=201)
def review_product(order_id: int, body: ReviewIn, svc: Svc, me: Customer):
    r = svc.reviews.create(me.account_id, order_id, body.product_id, body.rating, body.comment)
    return {"id": r.id, "rating": r.rating, "product_id": r.product_id}


# ---- UC-07 payment (sandbox gateway) and the gateway's webhook
@router.post("/payments/orders/{order_id}/pay")
def pay_order(order_id: int, body: PayIn, svc: Svc, me: Customer):
    payment, result = svc.payments.pay(order_id, me.account_id, body.channel, body.token)
    order = svc.orders.get_for_customer(order_id, me.account_id)
    return {"success": result.status == PaymentStatus.SUCCESS, "message": result.message,
            "payment": payment_json(payment), "order": order_json(order, detail=True)}


@router.post("/payments/callback", dependencies=[Depends(partner_only)])
def payment_callback(body: PaymentCallbackIn, svc: Svc):
    """Called by the payment gateway (X-Partner-Secret required). Duplicates are ignored (UC-07 A3)."""
    p = svc.payments.handle_callback(body.order_id, body.transaction_id, PaymentStatus(body.status))
    return {"order_id": p.order_id, "status": p.status, "transaction_id": p.transaction_id}


# ---- support requests
@router.get("/me/support-requests")
def my_support_requests(svc: Svc, me: Customer):
    return [support_json(s) for s in svc.support.mine(me.account_id)]


@router.post("/me/support-requests", status_code=201)
def create_support_request(body: SupportIn, svc: Svc, me: Customer):
    return support_json(svc.support.create(me.account_id, body.content, body.order_id))
