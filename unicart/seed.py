"""Development / demo data. Idempotent and non-destructive: never deletes or overwrites existing rows.

    python -m unicart.seed            # hash sample passwords + add the demo catalogue, staff and order history

Every account uses the sample password below."""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from .domain.extended import security
from .domain.models import (
    Account, Address, Cart, Category, Customer, CustomerOrder, InteractionLog, Inventory, OrderItem,
    OrderStatusHistory, Payment, Product, Review, Role, Shipment, StockMovement,
)
from .persistence.database import Database

SAMPLE_PASSWORD = "Abc@12345"

CATEGORIES = [(5, "Gia dụng", "Đồ dùng nhà bếp, gia đình"), (6, "Chăm sóc cá nhân", "Mỹ phẩm, chăm sóc da và tóc"),
              (7, "Phụ kiện", "Balo, ví, đồng hồ, kính")]

# sku, category_id, name, brand, price, description, attributes, stock
PRODUCTS = [
    ("LT-002", 2, "Laptop Gaming Z15", "ASUS", 28900000, "Laptop gaming mạnh mẽ, màn hình 144Hz.", {"cpu": "Ryzen 7", "ram": "16GB", "storage": "1TB"}, 12),
    ("MB-002", 2, "Điện thoại Galaxy A55", "Samsung", 9490000, "Màn hình Super AMOLED, pin 5000mAh.", {"screenSize": 6.6, "storage": "256GB", "warrantyMonths": 12}, 30),
    ("EL-003", 2, "Tai nghe Bluetooth chống ồn", "Sony", 2490000, "Chống ồn chủ động, pin 30 giờ.", {"warrantyMonths": 12}, 25),
    ("EL-004", 2, "Chuột không dây Silent", "Logitech", 390000, "Click êm, kết nối đa thiết bị.", {"warrantyMonths": 12}, 60),
    ("EL-005", 2, "Màn hình 27 inch 4K", "Dell", 8990000, "Tấm nền IPS, phủ 99% sRGB.", {"screenSize": 27, "warrantyMonths": 36}, 8),
    ("EL-006", 2, "Sạc dự phòng 20000mAh", "Anker", 790000, "Sạc nhanh 22.5W, 2 cổng ra.", {"warrantyMonths": 18}, 3),
    ("CL-002", 3, "Áo thun nam cổ tròn", "Routine", 199000, "Cotton 100%, thoáng mát.", {"size": "L", "color": "black", "material": "cotton"}, 80),
    ("CL-003", 3, "Áo khoác gió unisex", "Uniqlo", 690000, "Chống nước nhẹ, gấp gọn.", {"size": "M", "color": "navy", "material": "polyester"}, 40),
    ("CL-004", 3, "Quần jeans slim fit", "Levi's", 1190000, "Denim co giãn, form slim.", {"size": "32", "color": "blue", "material": "denim"}, 35),
    ("CL-005", 3, "Váy midi hoa nhí", "Zara", 590000, "Chất voan nhẹ, phong cách vintage.", {"size": "S", "color": "floral"}, 20),
    ("CL-006", 3, "Áo len cổ lọ mùa đông", "H&M", 450000, "Len mềm ấm áp, mặc mùa đông.", {"size": "M", "color": "cream", "material": "wool"}, 0),
    ("SH-002", 4, "Giày sneaker trắng", "Adidas", 1890000, "Đế êm, dễ phối đồ.", {"shoesSize": 41, "shoesType": "sneaker"}, 22),
    ("SH-003", 4, "Dép sandal quai ngang", "Biti's", 320000, "Nhẹ, chống trượt.", {"shoesSize": 40, "shoesType": "sandal"}, 50),
    ("BK-003", 1, "Đắc nhân tâm", "First News", 86000, "Sách kỹ năng sống kinh điển.", {"author": "Dale Carnegie"}, 100),
    ("BK-004", 1, "Nhà giả kim", "Nhã Nam", 79000, "Tiểu thuyết nổi tiếng của Paulo Coelho.", {"author": "Paulo Coelho"}, 70),
    ("BK-005", 1, "Clean Architecture", "Pearson", 520000, "Kiến trúc phần mềm sạch.", {"author": "Robert C. Martin"}, 15),
    ("HM-001", 5, "Nồi chiên không dầu 5L", "Philips", 2190000, "Chiên nướng ít dầu, 7 chế độ.", {"warrantyMonths": 24}, 18),
    ("HM-002", 5, "Máy hút bụi cầm tay", "Xiaomi", 3290000, "Lực hút mạnh, pin 60 phút.", {"warrantyMonths": 12}, 10),
    ("HM-003", 5, "Bộ chăn ga gối cotton", "Everon", 1290000, "Cotton 100%, mềm mại.", {"material": "cotton"}, 26),
    ("HM-004", 5, "Bình giữ nhiệt 500ml", "Lock&Lock", 290000, "Giữ nóng 12 giờ, giữ lạnh 24 giờ.", {"capacity": "500ml"}, 90),
    ("PC-001", 6, "Sữa rửa mặt dịu nhẹ", "Cetaphil", 180000, "Làm sạch dịu nhẹ cho da nhạy cảm.", {"volume": "250ml"}, 120),
    ("PC-002", 6, "Kem chống nắng SPF50", "La Roche-Posay", 420000, "Bảo vệ da khỏi tia UVA/UVB.", {"volume": "50ml"}, 45),
    ("PC-003", 6, "Máy sấy tóc ion", "Panasonic", 890000, "Công suất 1800W, giảm xơ rối.", {"warrantyMonths": 12}, 4),
    ("AC-001", 7, "Ba lô laptop chống nước", "Mikkor", 590000, "Ngăn laptop 15.6 inch, chống nước.", {"color": "grey"}, 55),
    ("AC-002", 7, "Đồng hồ thông minh Fit", "Garmin", 3490000, "Theo dõi sức khỏe và GPS.", {"warrantyMonths": 12}, 14),
    ("AC-003", 7, "Ví da nam", "Bufalo", 350000, "Da bò thật, nhiều ngăn.", {"material": "leather"}, 40),
    ("AC-004", 7, "Kính râm phân cực", "Ray-Ban", 2100000, "Chống tia UV400.", {"color": "black"}, 16),
]
HIDDEN_PRODUCT = ("OLD-001", 2, "Điện thoại cũ (ngừng kinh doanh)", "Legacy", 1500000, "Sản phẩm đã ngừng bán.", {}, 0)

STAFF = [("sales@abc.vn", "SALES"), ("marketing@abc.vn", "MARKETING"), ("manager@abc.vn", "MANAGER")]
CUSTOMERS = [("chi@gmail.com", "Chi", "Lê", "0901000003"), ("dung@gmail.com", "Dũng", "Phạm", "0901000004"),
             ("em@gmail.com", "Em", "Hoàng", "0901000005")]
COMMENTS = ["Sản phẩm đúng mô tả, giao nhanh.", "Chất lượng tốt, đóng gói cẩn thận.", "Rất hài lòng, sẽ mua lại.",
            "Tạm ổn so với giá tiền.", "Dùng ổn định, đáng tiền."]


def seed_passwords(db: Database | None = None) -> int:
    db = db or Database()
    with db.new_session() as s:
        n = 0
        for acc in s.scalars(select(Account)):
            if not security.is_hashed(acc.password_hash):
                acc.password_hash = security.hash_password(SAMPLE_PASSWORD)
                n += 1
        s.commit()
    return n


def _accounts(s) -> dict[str, int]:
    roles = {r.name: r.id for r in s.scalars(select(Role))}
    ids: dict[str, int] = {}
    for email, role in STAFF:
        acc = s.scalars(select(Account).where(Account.email == email)).first()
        if acc is None:
            acc = Account(email=email, password_hash=security.hash_password(SAMPLE_PASSWORD), role_id=roles[role])
            s.add(acc)
            s.flush()
        ids[email] = acc.id
    for email, first, last, phone in CUSTOMERS:
        acc = s.scalars(select(Account).where(Account.email == email)).first()
        if acc is None:
            acc = Account(email=email, password_hash=security.hash_password(SAMPLE_PASSWORD), role_id=roles["CUSTOMER"])
            s.add(acc)
            s.flush()
            s.add(Customer(id=acc.id, first_name=first, last_name=last, phone=phone, loyalty_tier="NEW"))
            s.flush()                                   # FKs are not mapped as relationships: keep the insert order
            s.add(Cart(customer_id=acc.id))
            s.add(Address(customer_id=acc.id, recipient=f"{last} {first}", phone=phone, street="25 Nguyễn Trãi",
                          district="Thanh Xuân", city="Hà Nội", is_default=True))
        ids[email] = acc.id
    binh = s.scalars(select(Account).where(Account.email == "binh@gmail.com")).first()
    if binh and not s.scalars(select(Address).where(Address.customer_id == binh.id)).first():
        s.add(Address(customer_id=binh.id, recipient="Trần Bình", phone="0901000002", street="8 Lê Lợi",
                      district="Hà Đông", city="Hà Nội", is_default=True))
    s.flush()
    return ids


def _catalogue(s) -> int:
    for cid, name, desc in CATEGORIES:
        if s.get(Category, cid) is None and not s.scalars(select(Category).where(Category.name == name)).first():
            s.add(Category(id=cid, name=name, description=desc))
    s.flush()
    added = 0
    for sku, cat, name, brand, price, desc, attrs, qty in PRODUCTS + [HIDDEN_PRODUCT]:
        if s.scalars(select(Product).where(Product.sku == sku)).first():
            continue
        p = Product(sku=sku, category_id=cat, name=name, brand=brand, price=Decimal(price), description=desc,
                    attributes=attrs, status="HIDDEN" if sku == HIDDEN_PRODUCT[0] else "ACTIVE")
        s.add(p)
        s.flush()
        s.add(Inventory(product_id=p.id, quantity=qty, min_threshold=5))
        if qty:
            s.add(StockMovement(product_id=p.id, type="IN", quantity=qty, reason="SEED"))
        added += 1
    s.flush()
    return added


def _history(s) -> int:
    """~45 orders over the last 30 days so reports, best-sellers and the recommender have data."""
    if s.scalar(select(func.count()).select_from(CustomerOrder)):
        return 0
    rnd = random.Random(2026)
    customers = [c for c in s.scalars(select(Customer))]
    products = [p for p in s.scalars(select(Product).where(Product.status == "ACTIVE"))]
    weights = [3 if p.category_id in (2, 3) else 1 for p in products]
    now, made = datetime.now(), 0
    for i in range(45):
        customer = rnd.choice(customers)
        address = s.scalars(select(Address).where(Address.customer_id == customer.id)).first()
        if address is None:
            continue
        created = now - timedelta(days=rnd.randint(1, 29), hours=rnd.randint(0, 20), minutes=rnd.randint(0, 59))
        age_days = (now - created).days
        picks = {}
        for p in rnd.choices(products, weights, k=rnd.randint(1, 3)):
            picks[p.id] = (p, rnd.randint(1, 2))
        subtotal = sum(p.price * q for p, q in picks.values())
        shipping = Decimal(0) if subtotal >= 500000 else Decimal(30000)
        online = rnd.random() < 0.45
        roll = rnd.random()
        if age_days >= 8:
            status = "CANCELLED" if roll < 0.1 else "DELIVERED"
        else:
            status = ("CANCELLED" if roll < 0.08 else "DELIVERED" if roll < 0.35 else "SHIPPING" if roll < 0.5 else
                      "PACKED" if roll < 0.62 else "CONFIRMED" if roll < 0.8 else "PENDING")
        order = CustomerOrder(customer_id=customer.id, ship_recipient=address.recipient, ship_phone=address.phone,
                              ship_address=address.one_line(), subtotal=subtotal, discount=Decimal(0),
                              shipping_fee=shipping, total_amount=subtotal + shipping,
                              payment_method="ONLINE" if online else "COD", status=status, created_at=created)
        for p, q in picks.values():
            order.items.append(OrderItem(product_id=p.id, quantity=q, unit_price=p.price))
        path = ["PENDING", "CONFIRMED", "PACKED", "SHIPPING", "DELIVERED"]
        flow = (["PENDING_PAYMENT"] if online else []) + path[:path.index(status) + 1] if status != "CANCELLED" \
            else ([("PENDING_PAYMENT" if online else "PENDING"), "CANCELLED"])
        prev, t = None, created
        for st in flow:
            order.history.append(OrderStatusHistory(from_status=prev, to_status=st, changed_at=t))
            prev, t = st, t + timedelta(hours=rnd.randint(1, 10))
        paid = online and status != "CANCELLED"
        order.payment = Payment(method="CARD" if online else "COD", amount=order.total_amount,
                                status="SUCCESS" if paid or status == "DELIVERED" else "PENDING",
                                transaction_id=f"SEED-{i:04d}" if paid else None, paid_at=created if paid else None)
        if status in ("PACKED", "SHIPPING", "DELIVERED"):
            order.shipment = Shipment(carrier="UniExpress", tracking_number=f"UCXSEED{i:04d}",
                                      status={"PACKED": "CREATED", "SHIPPING": "IN_TRANSIT"}.get(status, "DELIVERED"),
                                      delivery_date=created.date() + timedelta(days=3) if status == "DELIVERED" else None)
        s.add(order)
        s.flush()
        if status != "CANCELLED":
            for p, q in picks.values():
                inv = s.get(Inventory, p.id)
                inv.quantity = max(inv.quantity - q, 0)
                s.add(StockMovement(product_id=p.id, type="OUT", quantity=q, reason="ORDER", order_id=order.id,
                                    created_at=created))
        if status == "DELIVERED":
            customer.add_points(int(order.total_amount // 10000))
            for p, q in picks.values():
                if rnd.random() < 0.5:
                    s.add(Review(customer_id=customer.id, product_id=p.id, order_id=order.id,
                                 rating=rnd.choice([3, 4, 4, 5, 5, 5]), comment=rnd.choice(COMMENTS),
                                 created_at=created + timedelta(days=4)))
        made += 1
    s.flush()
    # synthetic recommendation telemetry so the AI report (FR-18) is not empty
    for _ in range(300):
        placement = rnd.choice(["home", "home", "product", "cart"])
        when = now - timedelta(days=rnd.randint(0, 29), hours=rnd.randint(0, 23))
        s.add(InteractionLog(event_type="REC_IMPRESSION", keyword=placement, created_at=when))
        if rnd.random() < 0.18:
            pid = rnd.choice(products).id
            cust = rnd.choice(customers).id
            s.add(InteractionLog(customer_id=cust, product_id=pid, event_type="CLICK_REC", keyword=placement, created_at=when))
            if rnd.random() < 0.4:
                s.add(InteractionLog(customer_id=cust, product_id=pid, event_type="ADD_TO_CART",
                                     keyword=f"rec:{placement}", created_at=when))
                if rnd.random() < 0.45:
                    s.add(InteractionLog(customer_id=cust, product_id=pid, event_type="PURCHASE",
                                         keyword=f"rec:{placement}", created_at=when))
    for c in customers:                       # browsing history for the personalised "Dành cho bạn" block
        for p in rnd.sample(products, 6):
            s.add(InteractionLog(customer_id=c.id, product_id=p.id, event_type="VIEW",
                                 created_at=now - timedelta(days=rnd.randint(0, 10))))
    return made


def seed_demo(db: Database | None = None) -> dict:
    db = db or Database()
    with db.new_session() as s:
        _accounts(s)
        products = _catalogue(s)
        orders = _history(s)
        s.commit()
    return {"products_added": products, "orders_added": orders}


if __name__ == "__main__":
    print(f"{seed_passwords()} account(s) re-hashed")
    print(seed_demo())
    seed_passwords()                          # the demo accounts created above already use the sample password
    print(f"Sample password for every account: {SAMPLE_PASSWORD}")
