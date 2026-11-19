from fastapi import APIRouter, Depends
from app.business.actor import Actor
from app.business.cart_service import CartService
from app.dependencies import get_cart_service, get_current_actor
from app.schemas import AddCartItemRequest, UpdateCartItemRequest

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("")
def view(svc: CartService = Depends(get_cart_service), actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError


@router.post("/items")
def add_item(body: AddCartItemRequest, svc: CartService = Depends(get_cart_service),
             actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError


@router.put("/items/{product_id}")
def update(product_id: str, body: UpdateCartItemRequest,
           svc: CartService = Depends(get_cart_service),
           actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError


@router.delete("/items/{product_id}")
def remove(product_id: str, svc: CartService = Depends(get_cart_service),
           actor: Actor = Depends(get_current_actor)):
    raise NotImplementedError
