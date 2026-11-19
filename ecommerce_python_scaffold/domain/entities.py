from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from .enums import OrderStatus, PaymentMethod, ProductStatus


@dataclass
class FullName:
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""

    def __str__(self) -> str:
        return " ".join(x for x in (self.first_name, self.middle_name, self.last_name) if x)


@dataclass
class Address:
    address_id: str
    street: str
    district: str
    city: str
    country: str
    pos_code: str


@dataclass
class Customer:
    cus_id: str
    email: str
    phone: str
    password: str
    created: Optional[date] = None
    full_name: Optional[FullName] = None
    active: bool = True
    locked: bool = False

    def is_active(self) -> bool:
        return self.active and not self.locked

    def lock(self) -> None:
        self.locked = True

    def verify_password(self, raw_password: str) -> bool:
        # TODO: thay bằng password hashing (argon2/bcrypt), tuyệt đối không lưu mật khẩu thô.
        raise NotImplementedError

    def get_full_name(self) -> str:
        return str(self.full_name or FullName())


@dataclass
class CustomerVIP:
    vip_level: str
    loyalty_point: int
    discount_rate: float


@dataclass
class CustomerNew:
    registration_date: Optional[date] = None
    welcome_discount: float = 0.0


@dataclass
class Product:
    product_id: str
    name: str
    description: str = ""
    price: float = 0.0
    stock_quantity: int = 0
    image_url: str = ""
    sku: str = ""
    status: ProductStatus = ProductStatus.ACTIVE

    def is_visible(self) -> bool:
        return self.status == ProductStatus.ACTIVE

    def in_stock(self, quantity: int = 1) -> bool:
        return quantity > 0 and self.stock_quantity >= quantity


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    publisher: str
    product_id: str


@dataclass
class Electronic:
    brand: str
    model: str
    warranty_months: int
    product_id: str


@dataclass
class Fashion:
    size: str
    color: str
    material: str
    product_id: str


@dataclass
class Shoes:
    shoes_size: float
    shoes_type: str
    product_id: str


@dataclass
class Inventory:
    quantity: int = 0
    min_threshold: int = 0


@dataclass
class CartItem:
    product_id: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Cart:
    cart_id: str
    create_date: Optional[date] = None
    items: list[CartItem] = field(default_factory=list)

    def add_item(self, item: CartItem) -> None:
        # TODO: xác định chính sách cộng dồn item trùng product_id.
        self.items.append(item)

    def update_quantity(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity phải lớn hơn 0")
        for item in self.items:
            if item.product_id == product_id:
                item.quantity = quantity
                return
        raise KeyError(product_id)

    def clear(self) -> None:
        self.items.clear()

    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items)

    def is_empty(self) -> bool:
        return not self.items


@dataclass
class OrderItem:
    product_id: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Order:
    order_id: str
    order_date: datetime
    total_amount: float
    status: OrderStatus
    cus_id: str
    ship_phone: str = ""
    ship_address: str = ""
    items: list[OrderItem] = field(default_factory=list)

    def actor_id(self) -> str:
        return self.cus_id

    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)


@dataclass
class Shipment:
    shipping_id: str
    order_id: str
    shipping_method: str = ""
    shipping_fee: float = 0.0
    tracking_number: str = ""
    shipping_status: str = "PENDING"
    delivery_date: Optional[date] = None

    def mark_in_transit(self) -> None:
        self.shipping_status = "IN_TRANSIT"

    def mark_delivered(self) -> None:
        self.shipping_status = "DELIVERED"


@dataclass
class Payment:
    payment_id: str
    payment_date: datetime
    amount: float
    status: str
    method: PaymentMethod

    def mark_success(self) -> None:
        self.status = "SUCCESS"

    def mark_fail(self) -> None:
        self.status = "FAILED"

    def is_complete(self) -> bool:
        return self.status == "SUCCESS"


@dataclass
class PayCash:
    received_amount: float


@dataclass
class PayCredit:
    transaction_id: str
    card_last_four_digits: str
    authorization_code: str
