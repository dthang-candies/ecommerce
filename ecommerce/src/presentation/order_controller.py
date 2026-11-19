from fastapi import APIRouter, Depends
from app.business.actor import Actor
from app.business.checkout_service import CheckoutService
from app.business.order_service import OrderService
from app.dependencies import get_checkout_service, get_current_actor, get_order_service
from app.schemas import ChangeStatusRequest, PlaceOrderRequest

router = APIRouter(prefix="/orders", tags=["Order"])


@router.post("")
def place(body: PlaceOrderRequest, svc: CheckoutService = Depends(get_checkout_service),
          actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError


@router.get("/mine")
def mine(svc: OrderService = Depends(get_order_service),
         actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError


@router.patch("/{order_id}/status")
def change_status(order_id: str, body: ChangeStatusRequest,
                  svc: OrderService = Depends(get_order_service),
                  actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError


@router.post("/{order_id}/cancel")
def cancel(order_id: str, svc: OrderService = Depends(get_order_service),
           actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError
