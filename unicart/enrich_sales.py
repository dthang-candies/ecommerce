"""More sales history for reports, best-sellers and the recommender. Idempotent and non-destructive:

    python -m unicart.enrich_sales          # run after `python -m unicart.import_catalog`

Adds 15 customers and ~260 past orders spread over the last 90 days (more of them in recent weeks), mostly books,
laptops / other electronics and shoes. Every order is built like the ones of unicart.seed: status history, payment,
shipment, stock movements, loyalty points, reviews and interaction logs. Stock is never oversold.
A second run adds nothing (the generated payments are marked ENR-...)."""
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from .domain.extended import security
from .domain.models import Account, Address, Cart, Category, Customer, InteractionLog, Inventory, Payment, Product, Promotion, Role
from .persistence.database import Database
from .seed import SAMPLE_PASSWORD, _order

TAG, ORDERS, DAYS = "ENR", 260, 90
FOCUS = ("Books", "Electronics", "Shoes")           # categories that sell most in the generated history
# email, first name, middle name, last name, phone, street, district, city
CUSTOMERS = [
    ("giang@gmail.com", "Giang", "Thị", "Vũ", "0902000001", "45 Cầu Giấy", "Cầu Giấy", "Hà Nội"),
    ("hung@gmail.com", "Hùng", "Văn", "Đỗ", "0902000002", "102 Nguyễn Văn Cừ", "Long Biên", "Hà Nội"),
    ("khanh@gmail.com", "Khánh", "Quốc", "Bùi", "0902000003", "17 Lê Duẩn", "Hải Châu", "Đà Nẵng"),
    ("lan@gmail.com", "Lan", "Thị", "Ngô", "0902000004", "230 Nguyễn Thị Minh Khai", "Quận 3", "TP. Hồ Chí Minh"),
    ("minh@gmail.com", "Minh", "Đức", "Đặng", "0902000005", "68 Trần Hưng Đạo", "Quận 1", "TP. Hồ Chí Minh"),
    ("nga@gmail.com", "Nga", "Thị", "Dương", "0902000006", "5 Hùng Vương", "Ninh Kiều", "Cần Thơ"),
    ("phong@gmail.com", "Phong", "Thanh", "Lý", "0902000007", "88 Lạch Tray", "Ngô Quyền", "Hải Phòng"),
    ("quynh@gmail.com", "Quỳnh", "Như", "Trịnh", "0902000008", "14 Xuân Thủy", "Cầu Giấy", "Hà Nội"),
    ("son@gmail.com", "Sơn", "Hoàng", "Đinh", "0902000009", "310 Điện Biên Phủ", "Bình Thạnh", "TP. Hồ Chí Minh"),
    ("thao@gmail.com", "Thảo", "Phương", "Hồ", "0902000010", "27 Lê Lợi", "TP. Huế", "Thừa Thiên Huế"),
    ("tuan@gmail.com", "Tuấn", "Anh", "Phan", "0902000011", "9 Quang Trung", "Hà Đông", "Hà Nội"),
    ("uyen@gmail.com", "Uyên", "Thu", "Mai", "0902000012", "152 Nguyễn Văn Linh", "Thanh Khê", "Đà Nẵng"),
    ("vinh@gmail.com", "Vinh", "Quang", "Tạ", "0902000013", "41 Trần Phú", "TP. Nha Trang", "Khánh Hòa"),
    ("xuan@gmail.com", "Xuân", "Thị", "Cao", "0902000014", "76 Võ Văn Ngân", "TP. Thủ Đức", "TP. Hồ Chí Minh"),
    ("yen@gmail.com", "Yến", "Hải", "Lương", "0902000015", "23 Phạm Văn Đồng", "Bắc Từ Liêm", "Hà Nội"),
]


def _customers(s) -> int:
    role = s.scalars(select(Role).where(Role.name == "CUSTOMER")).one()
    password, added = None, 0
    for email, first, middle, last, phone, street, district, city in CUSTOMERS:
        if s.scalars(select(Account).where(Account.email == email)).first():
            continue
        password = password or security.hash_password(SAMPLE_PASSWORD)     # one slow hash is enough for sample accounts
        acc = Account(email=email, password_hash=password, role_id=role.id)
        s.add(acc)
        s.flush()
        s.add(Customer(id=acc.id, first_name=first, middle_name=middle, last_name=last, phone=phone, loyalty_tier="NEW"))
        s.flush()                                   # FKs are not mapped as relationships: keep the insert order
        s.add(Cart(customer_id=acc.id))
        s.add(Address(customer_id=acc.id, recipient=f"{last} {middle} {first}", phone=phone, street=street,
                      district=district, city=city, is_default=True))
        added += 1
    s.flush()
    return added


def _quantity(rnd, product: Product, is_book: bool) -> int:
    if product.price >= 5000000:                    # nobody buys two laptops at once
        return 1
    return rnd.choice([1, 1, 2, 3]) if is_book else rnd.choice([1, 1, 1, 2])


def _orders(s, now: datetime) -> int:
    if s.scalars(select(Payment).where(Payment.transaction_id.like(f"{TAG}-%"))).first():
        return 0
    rnd = random.Random(1113)
    focus = {c.id: c.name for c in s.scalars(select(Category).where(Category.name.in_(FOCUS)))}
    books = next((cid for cid, name in focus.items() if name == "Books"), None)
    buyers = [(c, s.scalars(select(Address).where(Address.customer_id == c.id)).first()) for c in s.scalars(select(Customer))]
    buyers = [(c, a) for c, a in buyers if a is not None]
    products = list(s.scalars(select(Product).where(Product.status == "ACTIVE")))
    if not buyers or not products:
        return 0
    taste = {c.id: rnd.choice(list(focus) or [None]) for c, _ in buyers}   # each customer favours one focus category
    promo = s.scalars(select(Promotion).where(Promotion.code == "WELCOME10")).first()
    used_promo: set[int] = set()
    made = 0
    for i in range(ORDERS):
        customer, address = rnd.choice(buyers)
        days = int(DAYS * rnd.random() ** 1.6)                              # skewed towards recent weeks: sales are growing
        created = now - timedelta(days=days, hours=rnd.randint(1, 23), minutes=rnd.randint(0, 59))
        weights = [(8 if p.category_id == taste[customer.id] else 4) if p.category_id in focus else 1 for p in products]
        picks = {}
        for p in rnd.choices(products, weights, k=rnd.choice([1, 1, 2, 2, 3])):
            left = s.get(Inventory, p.id)
            left = (left.quantity if left else 0) - (picks[p.id][1] if p.id in picks else 0)
            qty = min(_quantity(rnd, p, p.category_id == books), left)
            if qty > 0:
                picks[p.id] = (p, qty)
        if not picks:
            continue
        first_time = customer.id not in used_promo and rnd.random() < 0.3   # WELCOME10: once per customer
        order = _order(s, rnd, customer, address, picks, created, now, TAG, i, promo if first_time else None)
        if order.promotion_id:
            used_promo.add(customer.id)
        for p, _ in picks.values():                                         # the browsing trail behind the purchase
            s.add(InteractionLog(customer_id=customer.id, product_id=p.id, event_type="VIEW", created_at=created))
            s.add(InteractionLog(customer_id=customer.id, product_id=p.id, event_type="ADD_TO_CART", created_at=created))
            if order.status != "CANCELLED":
                s.add(InteractionLog(customer_id=customer.id, product_id=p.id, event_type="PURCHASE", created_at=created))
        made += 1
    s.flush()
    return made


def enrich_sales(db: Database | None = None, now: datetime | None = None) -> dict:
    db = db or Database()
    with db.new_session() as s:
        customers = _customers(s)
        orders = _orders(s, now or datetime.now())
        s.commit()
    return {"customers_added": customers, "orders_added": orders}


if __name__ == "__main__":
    print(enrich_sales())
    print(f"Sample password for the new customer accounts: {SAMPLE_PASSWORD}")
