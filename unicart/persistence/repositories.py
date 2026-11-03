"""Data-access layer: one repository per aggregate. Only this layer talks to the database."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, case, delete, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from ..domain.models import (
    Account, Address, Cart, CartItem, Category, Customer, CustomerOrder, InteractionLog, Inventory,
    OrderItem, OrderStatusHistory, Payment, Product, ProductEmbedding, Promotion, RestockRequest, Review, Role, Shipment,
    StockMovement, Supplier, SupportRequest,
)

# Orders that count as "committed sales": paid online orders and COD orders that are still alive.
COMMITTED = ("PENDING", "CONFIRMED", "PACKED", "SHIPPING", "DELIVERED")


def _like(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# ----------------------------------------------------------------------------- accounts
class AccountRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, account_id: int) -> Optional[Account]:
        return self.s.get(Account, account_id)

    def by_email(self, email: str) -> Optional[Account]:
        return self.s.scalars(select(Account).where(func.lower(Account.email) == email.lower())).first()

    def role_by_name(self, name: str) -> Optional[Role]:
        return self.s.scalars(select(Role).where(Role.name == name)).first()

    def roles(self) -> list[Role]:
        return list(self.s.scalars(select(Role).order_by(Role.id)))

    def add(self, account: Account) -> Account:
        self.s.add(account)
        self.s.flush()
        return account

    def list(self, role: Optional[str] = None, keyword: Optional[str] = None) -> list[Account]:
        q = select(Account).options(joinedload(Account.role)).order_by(Account.id)
        if role:
            q = q.join(Role).where(Role.name == role)
        if keyword:
            q = q.where(Account.email.like(_like(keyword)))
        return list(self.s.scalars(q).unique())


class CustomerRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, customer_id: int) -> Optional[Customer]:
        return self.s.get(Customer, customer_id)

    def add(self, customer: Customer) -> Customer:
        self.s.add(customer)
        self.s.flush()
        return customer


class AddressRepository:
    def __init__(self, s: Session):
        self.s = s

    def get_for_customer(self, address_id: int, customer_id: int) -> Optional[Address]:
        a = self.s.get(Address, address_id)
        return a if a and a.customer_id == customer_id else None

    def list_for_customer(self, customer_id: int) -> list[Address]:
        return list(self.s.scalars(select(Address).where(Address.customer_id == customer_id)
                                   .order_by(Address.is_default.desc(), Address.id)))

    def add(self, address: Address) -> Address:
        self.s.add(address)
        self.s.flush()
        return address

    def delete(self, address: Address) -> None:
        self.s.delete(address)

    def clear_default(self, customer_id: int) -> None:
        self.s.execute(update(Address).where(Address.customer_id == customer_id).values(is_default=False))


# ----------------------------------------------------------------------------- catalogue
class CategoryRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, category_id: int) -> Optional[Category]:
        return self.s.get(Category, category_id)

    def by_name(self, name: str) -> Optional[Category]:
        return self.s.scalars(select(Category).where(Category.name == name)).first()

    def list_with_counts(self) -> list[tuple[Category, int]]:
        q = (select(Category, func.count(Product.id))
             .outerjoin(Product, and_(Product.category_id == Category.id, Product.status == "ACTIVE"))
             .group_by(Category.id).order_by(Category.id))
        return [(c, n) for c, n in self.s.execute(q)]

    def product_count(self, category_id: int) -> int:
        return self.s.scalar(select(func.count()).select_from(Product).where(Product.category_id == category_id))

    def add(self, category: Category) -> Category:
        self.s.add(category)
        self.s.flush()
        return category

    def delete(self, category: Category) -> None:
        self.s.delete(category)


class ProductRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, product_id: int) -> Optional[Product]:
        return self.s.get(Product, product_id)

    def by_sku(self, sku: str) -> Optional[Product]:
        return self.s.scalars(select(Product).where(Product.sku == sku)).first()

    def add(self, product: Product) -> Product:
        self.s.add(product)
        self.s.flush()
        return product

    def has_orders(self, product_id: int) -> bool:
        return self.s.scalar(select(func.count()).select_from(OrderItem)
                             .where(OrderItem.product_id == product_id)) > 0

    def delete(self, product: Product) -> None:
        self.s.delete(product)

    def search(self, keyword=None, category_id=None, min_price=None, max_price=None,
               sort="newest", page=1, size=20, status: Optional[str] = "ACTIVE", in_stock_only: bool = False):
        q = select(Product)
        if status:                                  # None = every status (administration)
            q = q.where(Product.status == status)
        if keyword:
            for token in keyword.split():          # every word must match name, brand or SKU (collation is accent-insensitive)
                like = _like(token)
                q = q.where(or_(Product.name.like(like), Product.brand.like(like), Product.sku.like(like)))
        if category_id:
            q = q.where(Product.category_id == category_id)
        if min_price is not None:
            q = q.where(Product.price >= min_price)
        if max_price is not None:
            q = q.where(Product.price <= max_price)
        if in_stock_only:
            q = q.join(Inventory, Inventory.product_id == Product.id).where(Inventory.quantity > 0)
        total = self.s.scalar(select(func.count()).select_from(q.subquery()))
        order = {"price_asc": Product.price.asc(), "price_desc": Product.price.desc(),
                 "name": Product.name.asc()}.get(sort, Product.id.desc())
        q = (q.options(joinedload(Product.inventory), joinedload(Product.category))
             .order_by(order, Product.id.desc()).limit(size).offset((max(page, 1) - 1) * size))
        return list(self.s.scalars(q).unique()), total

    def searchable_terms(self) -> list[str]:
        """Names and brands of visible products, used for 'did you mean' suggestions (FR-20)."""
        rows = self.s.execute(select(Product.name, Product.brand).where(Product.status == "ACTIVE")).all()
        terms: set[str] = set()
        for name, brand in rows:
            terms.add(name)
            if brand:
                terms.add(brand)
        return sorted(terms)

    def all_active(self, limit: int = 2000) -> list[Product]:
        """Every visible product with stock and category (stock is shown, sold-out items are ranked lower)."""
        q = (select(Product).where(Product.status == "ACTIVE")
             .options(joinedload(Product.inventory), joinedload(Product.category))
             .order_by(Product.id.desc()).limit(limit))
        return list(self.s.scalars(q).unique())

    def brands(self) -> list[str]:
        return sorted({b for (b,) in self.s.execute(select(Product.brand).where(Product.status == "ACTIVE",
                                                                                Product.brand.is_not(None)).distinct())})

    def candidates(self, limit: int = 500) -> list[Product]:
        """Visible, in-stock products (FR-25) with their stock, newest first."""
        q = (select(Product).join(Inventory, Inventory.product_id == Product.id)
             .where(Product.status == "ACTIVE", Inventory.quantity > 0)
             .options(joinedload(Product.inventory), joinedload(Product.category))
             .order_by(Product.id.desc()).limit(limit))
        return list(self.s.scalars(q).unique())

    def by_ids(self, ids: list[int]) -> list[Product]:
        if not ids:
            return []
        q = (select(Product).where(Product.id.in_(ids))
             .options(joinedload(Product.inventory), joinedload(Product.category)))
        return list(self.s.scalars(q).unique())

    def best_sellers(self, limit: int = 50) -> list[tuple[int, int]]:
        q = (select(OrderItem.product_id, func.sum(OrderItem.quantity).label("sold"))
             .join(CustomerOrder, CustomerOrder.id == OrderItem.order_id)
             .where(CustomerOrder.status.in_(COMMITTED))
             .group_by(OrderItem.product_id).order_by(func.sum(OrderItem.quantity).desc()).limit(limit))
        return [(pid, int(n)) for pid, n in self.s.execute(q)]

    def co_purchased(self, product_ids: list[int], limit: int = 50) -> list[tuple[int, int]]:
        if not product_ids:
            return []
        a, b = OrderItem.__table__.alias("a"), OrderItem.__table__.alias("b")
        q = (select(b.c.product_id, func.count().label("n"))
             .select_from(a.join(b, and_(a.c.order_id == b.c.order_id, a.c.product_id != b.c.product_id))
                          .join(CustomerOrder, CustomerOrder.id == a.c.order_id))
             .where(a.c.product_id.in_(product_ids), CustomerOrder.status.in_(COMMITTED))
             .group_by(b.c.product_id).order_by(func.count().desc()).limit(limit))
        return [(pid, int(n)) for pid, n in self.s.execute(q)]


class InventoryRepository:
    def __init__(self, s: Session):
        self.s = s

    def try_decrease(self, product_id: int, qty: int) -> bool:
        """Atomic conditional update: no overselling even with concurrent orders (NFR-15)."""
        res = self.s.execute(
            update(Inventory)
            .where(Inventory.product_id == product_id, Inventory.quantity >= qty)
            .values(quantity=Inventory.quantity - qty)
        )
        return res.rowcount == 1

    def increase(self, product_id: int, qty: int) -> None:
        self.s.execute(update(Inventory).where(Inventory.product_id == product_id)
                       .values(quantity=Inventory.quantity + qty))

    def get(self, product_id: int) -> Optional[Inventory]:
        return self.s.get(Inventory, product_id)

    def log(self, product_id: int, type_: str, qty: int, reason: str, order_id: Optional[int]) -> None:
        self.s.add(StockMovement(product_id=product_id, type=type_, quantity=qty, reason=reason, order_id=order_id))

    def low_stock(self) -> list[Inventory]:
        q = (select(Inventory).where(Inventory.quantity <= Inventory.min_threshold)
             .options(joinedload(Inventory.product)).order_by(Inventory.quantity, Inventory.product_id))
        return list(self.s.scalars(q).unique())

    def list_all(self, keyword: Optional[str] = None, page: int = 1, size: int = 20):
        q = select(Inventory).join(Product, Product.id == Inventory.product_id)
        if keyword:
            q = q.where(or_(Product.name.like(_like(keyword)), Product.sku.like(_like(keyword))))
        total = self.s.scalar(select(func.count()).select_from(q.subquery()))
        q = q.options(joinedload(Inventory.product)).order_by(Inventory.product_id).limit(size).offset((page - 1) * size)
        return list(self.s.scalars(q).unique()), total

    def movements(self, product_id: int, limit: int = 50) -> list[StockMovement]:
        return list(self.s.scalars(select(StockMovement).where(StockMovement.product_id == product_id)
                                   .order_by(StockMovement.id.desc()).limit(limit)))

    def summary(self) -> dict:
        row = self.s.execute(
            select(func.count(), func.coalesce(func.sum(Inventory.quantity), 0),
                   func.coalesce(func.sum(Inventory.quantity * Product.price), 0),
                   func.coalesce(func.sum(case((Inventory.quantity == 0, 1), else_=0)), 0),
                   func.coalesce(func.sum(case((Inventory.quantity <= Inventory.min_threshold, 1), else_=0)), 0))
            .join(Product, Product.id == Inventory.product_id).where(Product.status == "ACTIVE")).one()
        return {"skus": int(row[0]), "units": int(row[1]), "value": row[2],
                "out_of_stock": int(row[3]), "low_stock": int(row[4])}


class PromotionRepository:
    def __init__(self, s: Session):
        self.s = s

    def find_by_code(self, code: str) -> Optional[Promotion]:
        return self.s.scalars(select(Promotion).where(Promotion.code == code)).first()

    def get(self, promotion_id: int) -> Optional[Promotion]:
        return self.s.get(Promotion, promotion_id)

    def list(self) -> list[Promotion]:
        return list(self.s.scalars(select(Promotion).order_by(Promotion.id.desc())))

    def add(self, promo: Promotion) -> Promotion:
        self.s.add(promo)
        self.s.flush()
        return promo

    def active_at(self, now) -> "list[Promotion]":   # quoted: the method named list() shadows the builtin here
        """Codes a shopper can use right now (switched on and inside their validity period)."""
        q = (select(Promotion).where(Promotion.active.is_(True), Promotion.start_at <= now, Promotion.end_at >= now)
             .order_by(Promotion.end_at, Promotion.id))
        return list(self.s.scalars(q))

    def used_count(self, promotion_id: int) -> int:
        return self.s.scalar(select(func.count()).select_from(CustomerOrder)
                             .where(CustomerOrder.promotion_id == promotion_id))

    def delete(self, promo: Promotion) -> None:
        self.s.delete(promo)


# ----------------------------------------------------------------------------- cart
class CartRepository:
    def __init__(self, s: Session):
        self.s = s

    def get_by_customer(self, customer_id: int) -> Optional[Cart]:
        q = (select(Cart).where(Cart.customer_id == customer_id)
             .options(joinedload(Cart.items).joinedload(CartItem.product).joinedload(Product.inventory)))
        return self.s.scalars(q).unique().first()


# ----------------------------------------------------------------------------- orders
_ORDER_LOAD = (selectinload(CustomerOrder.items).joinedload(OrderItem.product),
               joinedload(CustomerOrder.payment), joinedload(CustomerOrder.shipment))


class OrderRepository:
    def __init__(self, s: Session):
        self.s = s

    def add(self, order: CustomerOrder) -> CustomerOrder:
        self.s.add(order)
        self.s.flush()
        return order

    def get(self, order_id: int, lock: bool = False) -> Optional[CustomerOrder]:
        q = select(CustomerOrder).where(CustomerOrder.id == order_id)
        if lock:
            q = q.with_for_update()
        return self.s.scalars(q).first()

    def list_by_customer(self, customer_id: int) -> list[CustomerOrder]:
        q = (select(CustomerOrder).where(CustomerOrder.customer_id == customer_id)
             .options(*_ORDER_LOAD).order_by(CustomerOrder.id.desc()))
        return list(self.s.scalars(q).unique())

    def list_by_status(self, status: str) -> list[CustomerOrder]:
        return list(self.s.scalars(select(CustomerOrder).where(CustomerOrder.status == status)
                                   .order_by(CustomerOrder.id)))

    def search(self, status: Optional[str] = None, keyword: Optional[str] = None, page: int = 1, size: int = 20,
               oldest_first: bool = False):
        q = select(CustomerOrder)
        if status:
            q = q.where(CustomerOrder.status == status)
        if keyword:
            q = q.where(or_(CustomerOrder.ship_recipient.like(_like(keyword)),
                            CustomerOrder.ship_phone.like(_like(keyword)),
                            CustomerOrder.id == (int(keyword) if keyword.isdigit() else -1)))
        total = self.s.scalar(select(func.count()).select_from(q.subquery()))
        q = (q.options(*_ORDER_LOAD).order_by(CustomerOrder.id if oldest_first else CustomerOrder.id.desc())
             .limit(size).offset((page - 1) * size))
        return list(self.s.scalars(q).unique()), total

    def unpaid_before(self, cutoff: datetime) -> list[CustomerOrder]:
        q = select(CustomerOrder).where(CustomerOrder.status == "PENDING_PAYMENT",
                                        CustomerOrder.created_at < cutoff)
        return list(self.s.scalars(q))

    def add_history(self, order: CustomerOrder, from_status, to_status, actor_id) -> None:
        order.history.append(OrderStatusHistory(from_status=from_status, to_status=to_status, changed_by=actor_id))

    def has_purchased(self, customer_id: int, product_id: int) -> bool:
        q = (select(func.count()).select_from(OrderItem).join(CustomerOrder, CustomerOrder.id == OrderItem.order_id)
             .where(CustomerOrder.customer_id == customer_id, OrderItem.product_id == product_id,
                    CustomerOrder.status.in_(COMMITTED)))
        return self.s.scalar(q) > 0

    def purchased_product_ids(self, customer_id: int) -> list[int]:
        q = (select(OrderItem.product_id).join(CustomerOrder, CustomerOrder.id == OrderItem.order_id)
             .where(CustomerOrder.customer_id == customer_id, CustomerOrder.status.in_(COMMITTED)).distinct())
        return list(self.s.scalars(q))


class PaymentRepository:
    def __init__(self, s: Session):
        self.s = s

    def by_order(self, order_id: int) -> Optional[Payment]:
        return self.s.scalars(select(Payment).where(Payment.order_id == order_id)).first()

    def by_transaction(self, transaction_id: str) -> Optional[Payment]:
        return self.s.scalars(select(Payment).where(Payment.transaction_id == transaction_id)).first()


class ShipmentRepository:
    def __init__(self, s: Session):
        self.s = s

    def by_order(self, order_id: int) -> Optional[Shipment]:
        return self.s.scalars(select(Shipment).where(Shipment.order_id == order_id)).first()

    def add(self, shipment: Shipment) -> Shipment:
        self.s.add(shipment)
        self.s.flush()
        return shipment


# ----------------------------------------------------------------------------- reviews, support, restock
class ReviewRepository:
    def __init__(self, s: Session):
        self.s = s

    def exists(self, order_id: int, product_id: int) -> bool:
        return self.s.scalar(select(func.count()).select_from(Review)
                             .where(Review.order_id == order_id, Review.product_id == product_id)) > 0

    def add(self, review: Review) -> Review:
        self.s.add(review)
        self.s.flush()
        return review

    def for_product(self, product_id: int, limit: int = 20) -> list[tuple[Review, str]]:
        q = (select(Review, Customer).join(Customer, Customer.id == Review.customer_id)
             .where(Review.product_id == product_id).order_by(Review.id.desc()).limit(limit))
        return [(r, c.full_name()) for r, c in self.s.execute(q)]

    def summary(self, product_ids: list[int]) -> dict[int, tuple[float, int]]:
        if not product_ids:
            return {}
        q = (select(Review.product_id, func.avg(Review.rating), func.count())
             .where(Review.product_id.in_(product_ids)).group_by(Review.product_id))
        return {pid: (float(avg), int(n)) for pid, avg, n in self.s.execute(q)}

    def reviewed_pairs(self, order_id: int) -> set[int]:
        return set(self.s.scalars(select(Review.product_id).where(Review.order_id == order_id)))


class SupportRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, request_id: int) -> Optional[SupportRequest]:
        return self.s.get(SupportRequest, request_id)

    def add(self, req: SupportRequest) -> SupportRequest:
        self.s.add(req)
        self.s.flush()
        return req

    def for_customer(self, customer_id: int) -> list[SupportRequest]:
        return list(self.s.scalars(select(SupportRequest).where(SupportRequest.customer_id == customer_id)
                                   .order_by(SupportRequest.id.desc())))

    def list(self, status: Optional[str] = None, page: int = 1, size: int = 20):
        q = select(SupportRequest)
        if status:
            q = q.where(SupportRequest.status == status)
        total = self.s.scalar(select(func.count()).select_from(q.subquery()))
        q = q.order_by(SupportRequest.id.desc()).limit(size).offset((page - 1) * size)
        return list(self.s.scalars(q)), total


class SupplierRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, supplier_id: int) -> Optional[Supplier]:
        return self.s.get(Supplier, supplier_id)

    def list(self) -> list[Supplier]:
        return list(self.s.scalars(select(Supplier).order_by(Supplier.id)))


class RestockRepository:
    def __init__(self, s: Session):
        self.s = s

    def get(self, request_id: int, lock: bool = False) -> Optional[RestockRequest]:
        q = select(RestockRequest).where(RestockRequest.id == request_id)
        if lock:
            q = q.with_for_update()
        return self.s.scalars(q).first()

    def add(self, req: RestockRequest) -> RestockRequest:
        self.s.add(req)
        self.s.flush()
        return req

    def list(self, status: Optional[str] = None) -> list[RestockRequest]:
        q = select(RestockRequest).order_by(RestockRequest.id.desc())
        if status:
            q = q.where(RestockRequest.status == status)
        return list(self.s.scalars(q))

    def open_for_product(self, product_id: int) -> bool:
        return self.s.scalar(select(func.count()).select_from(RestockRequest).where(
            RestockRequest.product_id == product_id,
            RestockRequest.status.in_(("REQUESTED", "CONFIRMED")))) > 0


# ----------------------------------------------------------------------------- AI & reports
class InteractionRepository:
    def __init__(self, s: Session):
        self.s = s

    def add(self, log: InteractionLog) -> None:
        self.s.add(log)

    def recent_for_customer(self, customer_id: int, limit: int = 200) -> list[InteractionLog]:
        q = (select(InteractionLog).where(InteractionLog.customer_id == customer_id,
                                          InteractionLog.product_id.is_not(None),
                                          InteractionLog.event_type.in_(("VIEW", "ADD_TO_CART", "PURCHASE", "CLICK_REC")))
             .order_by(InteractionLog.id.desc()).limit(limit))
        return list(self.s.scalars(q))

    def rec_sourced_recently(self, customer_id: int, product_id: int, since: datetime) -> Optional[str]:
        """Placement of the last recommendation click / add-to-cart that led to this product (for attribution)."""
        q = (select(InteractionLog.keyword).where(
            InteractionLog.customer_id == customer_id, InteractionLog.product_id == product_id,
            InteractionLog.created_at >= since,
            or_(InteractionLog.event_type == "CLICK_REC",
                and_(InteractionLog.event_type == "ADD_TO_CART", InteractionLog.keyword.like("rec:%"))))
             .order_by(InteractionLog.id.desc()).limit(1))
        value = self.s.scalar(q)
        if value is None:
            return None
        return value if value.startswith("rec:") else f"rec:{value}"

    def counts(self, start: datetime, end: datetime) -> list[tuple[str, Optional[str], int]]:
        q = (select(InteractionLog.event_type, InteractionLog.keyword, func.count())
             .where(InteractionLog.created_at >= start, InteractionLog.created_at < end)
             .group_by(InteractionLog.event_type, InteractionLog.keyword))
        return [(e, k, int(n)) for e, k, n in self.s.execute(q)]


class ReportRepository:
    def __init__(self, s: Session):
        self.s = s

    def sales_by_day(self, start: datetime, end: datetime):
        day = func.date(CustomerOrder.created_at)
        q = (select(day, func.count(), func.coalesce(func.sum(CustomerOrder.total_amount), 0))
             .where(CustomerOrder.created_at >= start, CustomerOrder.created_at < end,
                    CustomerOrder.status.in_(COMMITTED))
             .group_by(day).order_by(day))
        return [(d, int(n), amount) for d, n, amount in self.s.execute(q)]

    def orders_by_status(self, start: datetime, end: datetime) -> dict[str, int]:
        q = (select(CustomerOrder.status, func.count())
             .where(CustomerOrder.created_at >= start, CustomerOrder.created_at < end)
             .group_by(CustomerOrder.status))
        return {s: int(n) for s, n in self.s.execute(q)}

    def delivered_revenue(self, start: datetime, end: datetime) -> Decimal:
        return self.s.scalar(select(func.coalesce(func.sum(CustomerOrder.total_amount), 0)).where(
            CustomerOrder.created_at >= start, CustomerOrder.created_at < end,
            CustomerOrder.status == "DELIVERED"))

    def top_products(self, start: datetime, end: datetime, limit: int = 10):
        q = (select(Product.id, Product.name, Product.sku, func.sum(OrderItem.quantity),
                    func.sum(OrderItem.quantity * OrderItem.unit_price))
             .join(OrderItem, OrderItem.product_id == Product.id)
             .join(CustomerOrder, CustomerOrder.id == OrderItem.order_id)
             .where(CustomerOrder.created_at >= start, CustomerOrder.created_at < end,
                    CustomerOrder.status.in_(COMMITTED))
             .group_by(Product.id, Product.name, Product.sku)
             .order_by(func.sum(OrderItem.quantity).desc()).limit(limit))
        return [(pid, name, sku, int(qty), rev) for pid, name, sku, qty, rev in self.s.execute(q)]

    def units_sold(self, start: datetime, end: datetime) -> int:
        q = (select(func.coalesce(func.sum(OrderItem.quantity), 0))
             .join(CustomerOrder, CustomerOrder.id == OrderItem.order_id)
             .where(CustomerOrder.created_at >= start, CustomerOrder.created_at < end,
                    CustomerOrder.status.in_(COMMITTED)))
        return int(self.s.scalar(q))


class EmbeddingRepository:
    def __init__(self, s: Session):
        self.s = s

    def all(self) -> dict[int, ProductEmbedding]:
        return {e.product_id: e for e in self.s.scalars(select(ProductEmbedding))}

    def upsert(self, product_id: int, model: str, dim: int, content_hash: str, vector: bytes) -> None:
        row = self.s.get(ProductEmbedding, product_id)
        if row is None:
            self.s.add(ProductEmbedding(product_id=product_id, model=model, dim=dim, content_hash=content_hash, vector=vector))
        else:
            row.model, row.dim, row.content_hash, row.vector = model, dim, content_hash, vector

    def delete_except(self, product_ids: set[int]) -> int:
        q = delete(ProductEmbedding)
        if product_ids:
            q = q.where(ProductEmbedding.product_id.not_in(product_ids))
        return self.s.execute(q).rowcount
