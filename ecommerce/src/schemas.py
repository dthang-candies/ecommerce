"""Pydantic schemas (request/response) – bổ sung field khi cần."""
from pydantic import BaseModel


class AddCartItemRequest(BaseModel):
    product_id: str
    quantity: int


class UpdateCartItemRequest(BaseModel):
    quantity: int


class PlaceOrderRequest(BaseModel):
    address_id: str
    payment_method: str  # "cash" | "credit"
    promo_code: str | None = None


class ChangeStatusRequest(BaseModel):
    new_status: str


class RestockRequest(BaseModel):
    product_id: str
    quantity: int
