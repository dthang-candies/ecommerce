"""Request bodies. Format checks live here; business rules stay in the business layer."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..domain.enums import EventType, PaymentChannel, PaymentMethod, ShipmentStatus


class RegisterIn(BaseModel):
    email: str = Field(max_length=150)
    password: str = Field(min_length=1, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    middle_name: Optional[str] = Field(default=None, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)


class LoginIn(BaseModel):
    email: str = Field(max_length=150)
    password: str = Field(max_length=128)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class ProfileIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    middle_name: Optional[str] = Field(default=None, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)


class AddressIn(BaseModel):
    recipient: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    street: str = Field(min_length=1, max_length=150)
    district: Optional[str] = Field(default=None, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    post_code: Optional[str] = Field(default=None, max_length=15)
    is_default: bool = False


class CartAddIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=999)
    source: Optional[str] = Field(default=None, max_length=40, description="recommendation placement")
    track: bool = True


class CartUpdateIn(BaseModel):
    quantity: int = Field(ge=0, le=999)


class QuoteIn(BaseModel):
    promo_code: Optional[str] = Field(default=None, max_length=30)


class OrderIn(BaseModel):
    address_id: int
    payment_method: PaymentMethod = PaymentMethod.COD
    promo_code: Optional[str] = Field(default=None, max_length=30)
    track: bool = True


class StatusIn(BaseModel):
    status: Literal["CONFIRMED", "PACKED", "CANCELLED"]


class PayIn(BaseModel):
    channel: PaymentChannel
    token: str = Field(min_length=4, max_length=64, description="opaque token from the gateway, never a card number")


class PaymentCallbackIn(BaseModel):
    order_id: int
    transaction_id: str = Field(min_length=3, max_length=60)
    status: Literal["SUCCESS", "FAILED"]


class ShipmentCallbackIn(BaseModel):
    order_id: int
    status: ShipmentStatus


class ReviewIn(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class SupportIn(BaseModel):
    content: str = Field(min_length=5, max_length=4000)
    order_id: Optional[int] = None


class SupportReplyIn(BaseModel):
    response: str = Field(min_length=1, max_length=4000)
    resolve: bool = False


class EventIn(BaseModel):
    event_type: EventType
    product_id: Optional[int] = None
    keyword: Optional[str] = Field(default=None, max_length=150)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category_id: int
    price: float = Field(ge=0)
    brand: Optional[str] = Field(default=None, max_length=80)
    description: Optional[str] = Field(default=None, max_length=10000)
    image_url: Optional[str] = Field(default=None, max_length=255)
    attributes: Optional[dict] = None
    quantity: int = Field(default=0, ge=0)
    min_threshold: int = Field(default=5, ge=0)


class ProductUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: int
    price: float = Field(ge=0)
    brand: Optional[str] = Field(default=None, max_length=80)
    description: Optional[str] = Field(default=None, max_length=10000)
    image_url: Optional[str] = Field(default=None, max_length=255)
    attributes: Optional[dict] = None


class VisibilityIn(BaseModel):
    visible: bool


class PromotionIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    discount_type: Literal["PERCENT", "AMOUNT"]
    discount_value: float = Field(gt=0)
    min_order_value: float = Field(default=0, ge=0)
    start_at: datetime
    end_at: datetime
    active: bool = True


class StaffAccountIn(BaseModel):
    email: str = Field(max_length=150)
    password: str = Field(max_length=128)
    role: str = Field(max_length=20)


class RoleIn(BaseModel):
    role: str = Field(max_length=20)


class LockIn(BaseModel):
    locked: bool


class QuantityIn(BaseModel):
    quantity: int = Field(ge=1, le=1_000_000)


class ThresholdIn(BaseModel):
    min_threshold: int = Field(ge=0, le=1_000_000)


class RestockIn(BaseModel):
    product_id: int
    supplier_id: int
    quantity: int = Field(ge=1, le=1_000_000)


class SupplierResponseIn(BaseModel):
    accept: bool


class SupplierCallbackIn(BaseModel):
    request_id: int
    accept: bool


class CarrierSandboxIn(BaseModel):
    status: ShipmentStatus


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class ChatIn(BaseModel):
    """The conversation is kept in the browser and sent back whole; the server stores nothing."""
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=40)
