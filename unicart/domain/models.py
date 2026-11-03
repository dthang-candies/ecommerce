"""Domain layer: entity classes mapped to the tables of schema.sql (Chapter 4.2)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, JSON, LargeBinary, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from . import security
from .enums import (
    DiscountType, LoyaltyTier, OrderStatus, PaymentStatus, ProductStatus, RestockStatus,
    ShipmentStatus, SupportStatus,
)


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)


class Account(Base):
    __tablename__ = "account"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("role.id"))
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE")

    role: Mapped[Role] = relationship()

    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    def lock(self) -> None:
        self.status = "LOCKED"

    def unlock(self) -> None:
        self.status = "ACTIVE"

    def verify_password(self, raw: str) -> bool:
        return security.verify_password(raw, self.password_hash)


class Customer(Base):
    __tablename__ = "customer"
    id: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    middle_name: Mapped[Optional[str]] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    loyalty_tier: Mapped[str] = mapped_column(String(10), default="NEW")
    loyalty_point: Mapped[int] = mapped_column(Integer, default=0)

    addresses: Mapped[list["Address"]] = relationship(back_populates="customer")

    def full_name(self) -> str:                      # replaces class FullName of the analysis model
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)

    def add_points(self, points: int) -> None:
        self.loyalty_point += points
        if self.loyalty_point >= 1000:
            self.loyalty_tier = LoyaltyTier.VIP.value
        elif self.loyalty_point >= 200:
            self.loyalty_tier = LoyaltyTier.REGULAR.value

    def default_address(self):
        return next((a for a in self.addresses if a.is_default), self.addresses[0] if self.addresses else None)


class Address(Base):
    __tablename__ = "address"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer.id"))
    recipient: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    street: Mapped[str] = mapped_column(String(150))
    district: Mapped[Optional[str]] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(60), default="Viet Nam")
    post_code: Mapped[Optional[str]] = mapped_column(String(15))
    is_default: Mapped[bool] = mapped_column(default=False)

    customer: Mapped[Customer] = relationship(back_populates="addresses")

    def one_line(self) -> str:
        return ", ".join(p for p in [self.street, self.district, self.city, self.country] if p)


class Category(Base):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))


class Product(Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("category.id"))
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(String(80))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    image_url: Mapped[Optional[str]] = mapped_column(String(255))
    attributes: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped[Category] = relationship()
    inventory: Mapped[Optional["Inventory"]] = relationship(back_populates="product", uselist=False,
                                                           cascade="all, delete-orphan")   # composition (4.3)

    def is_visible(self) -> bool:                    # BR-01
        return self.status == "ACTIVE"

    def in_stock(self, quantity: int = 1) -> bool:
        return self.inventory is not None and self.inventory.can_fulfill(quantity)

    def hide(self) -> None:
        self.status = ProductStatus.HIDDEN.value

    def activate(self) -> None:
        self.status = ProductStatus.ACTIVE.value


class Inventory(Base):
    __tablename__ = "inventory"
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_threshold: Mapped[int] = mapped_column(Integer, default=5)

    product: Mapped[Product] = relationship(back_populates="inventory")

    def is_low(self) -> bool:                        # BR-11
        return self.quantity <= self.min_threshold

    def can_fulfill(self, quantity: int) -> bool:
        return self.quantity >= quantity


class StockMovement(Base):
    __tablename__ = "stock_movement"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"))
    type: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(String(100))
    order_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("customer_order.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Promotion(Base):
    __tablename__ = "promotion"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    discount_type: Mapped[str] = mapped_column(String(10))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    min_order_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(default=True)

    def is_valid(self, subtotal: Decimal, now: datetime) -> bool:   # BR-05
        return self.active and self.start_at <= now <= self.end_at and subtotal >= self.min_order_value

    def compute_discount(self, subtotal: Decimal) -> Decimal:
        if self.discount_type == DiscountType.PERCENT.value:
            value = (subtotal * self.discount_value / 100).quantize(Decimal("0.01"))
        else:
            value = self.discount_value
        return min(value, subtotal)


class Cart(Base):
    __tablename__ = "cart"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer.id"), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")

    def add_item(self, product: Product, quantity: int) -> None:
        for it in self.items:
            if it.product_id == product.id:
                it.quantity += quantity
                return
        self.items.append(CartItem(product_id=product.id, product=product, quantity=quantity))

    def update_quantity(self, product_id: int, quantity: int) -> None:
        for it in self.items:
            if it.product_id == product_id:
                if quantity <= 0:
                    self.items.remove(it)
                else:
                    it.quantity = quantity
                return

    def remove_item(self, product_id: int) -> None:
        self.items[:] = [it for it in self.items if it.product_id != product_id]

    def clear(self) -> None:
        self.items.clear()

    def subtotal(self) -> Decimal:
        return sum((it.sub_total() for it in self.items), Decimal("0"))

    def is_empty(self) -> bool:
        return not self.items


class CartItem(Base):
    __tablename__ = "cart_item"
    cart_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cart.id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)

    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

    def sub_total(self) -> Decimal:                  # derived value, not stored (3NF)
        return self.product.price * self.quantity


class CustomerOrder(Base):
    __tablename__ = "customer_order"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer.id"))
    promotion_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("promotion.id"))
    ship_recipient: Mapped[str] = mapped_column(String(100))
    ship_phone: Mapped[str] = mapped_column(String(20))
    ship_address: Mapped[str] = mapped_column(String(300))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    history: Mapped[list["OrderStatusHistory"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payment: Mapped[Optional["Payment"]] = relationship(back_populates="order", uselist=False)
    shipment: Mapped[Optional["Shipment"]] = relationship(back_populates="order", uselist=False)

    def can_be_cancelled(self) -> bool:              # BR-08: before the parcel is handed to the carrier
        return self.status in (OrderStatus.PENDING_PAYMENT.value, OrderStatus.PENDING.value,
                               OrderStatus.CONFIRMED.value)

    def change_status(self, new_status: OrderStatus, actor_id: Optional[int]) -> None:
        """Record the transition; whether the actor is allowed is decided by OrderStatusPolicy."""
        self.history.append(OrderStatusHistory(from_status=self.status, to_status=new_status.value,
                                               changed_by=actor_id))
        self.status = new_status.value

    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)


class OrderItem(Base):
    __tablename__ = "order_item"
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer_order.id"), primary_key=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[CustomerOrder] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

    def sub_total(self) -> Decimal:
        return self.unit_price * self.quantity


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer_order.id"))
    from_status: Mapped[Optional[str]] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("account.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped[CustomerOrder] = relationship(back_populates="history")


class Payment(Base):
    __tablename__ = "payment"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer_order.id"), unique=True)
    method: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(10), default="PENDING")
    transaction_id: Mapped[Optional[str]] = mapped_column(String(60), unique=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    order: Mapped[CustomerOrder] = relationship(back_populates="payment")

    def mark_success(self, transaction_id: str, at: datetime) -> None:
        self.status = PaymentStatus.SUCCESS.value
        self.transaction_id = transaction_id
        self.paid_at = at

    def mark_failed(self) -> None:
        self.status = PaymentStatus.FAILED.value

    def is_completed(self) -> bool:
        return self.status == PaymentStatus.SUCCESS.value


class Shipment(Base):
    __tablename__ = "shipment"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer_order.id"), unique=True)
    carrier: Mapped[Optional[str]] = mapped_column(String(60))
    tracking_number: Mapped[Optional[str]] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(15), default="CREATED")
    delivery_date: Mapped[Optional[date]] = mapped_column(Date)

    order: Mapped[CustomerOrder] = relationship(back_populates="shipment")

    def mark_in_transit(self) -> None:
        self.status = ShipmentStatus.IN_TRANSIT.value

    def mark_delivered(self, on: date) -> None:
        self.status = ShipmentStatus.DELIVERED.value
        self.delivery_date = on


class Review(Base):
    __tablename__ = "review"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer.id"))
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"))
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer_order.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def is_valid_rating(self) -> bool:               # BR-09
        return 1 <= self.rating <= 5


class SupportRequest(Base):
    __tablename__ = "support_request"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customer.id"))
    order_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("customer_order.id"))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="OPEN")
    handled_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("account.id"))
    response: Mapped[Optional[str]] = mapped_column(Text)          # staff reply (UC-23)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def assign(self, account_id: int) -> None:
        self.handled_by = account_id
        self.status = SupportStatus.IN_PROGRESS.value

    def resolve(self) -> None:
        self.status = SupportStatus.RESOLVED.value


class Supplier(Base):
    __tablename__ = "supplier"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[Optional[str]] = mapped_column(String(150))


class RestockRequest(Base):
    __tablename__ = "restock_request"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id"))
    supplier_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("supplier.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="REQUESTED")
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("account.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def confirm(self) -> None:
        self.status = RestockStatus.CONFIRMED.value

    def receive(self) -> None:
        self.status = RestockStatus.RECEIVED.value


class InteractionLog(Base):
    __tablename__ = "interaction_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("customer.id"))
    product_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("product.id"))
    event_type: Mapped[str] = mapped_column(String(15))
    keyword: Mapped[Optional[str]] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProductEmbedding(Base):
    """Vector of a product's searchable text for AI semantic search (ProductEmbedding of section 3.6.2)."""
    __tablename__ = "product_embedding"
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    model: Mapped[str] = mapped_column(String(60))
    dim: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(32))            # re-embed only when the text changed
    vector: Mapped[bytes] = mapped_column(LargeBinary(65535))        # float32 little-endian
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
