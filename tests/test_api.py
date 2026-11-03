"""Integration tests: HTTP -> router -> service -> repository -> MySQL (the 16 tests of section 4.5.8, ported to FastAPI + JWT)."""
import threading
from datetime import datetime, timedelta

from sqlalchemy import text

from unicart.business.exceptions import OutOfStock
from unicart.domain.enums import PaymentMethod
from unicart.presentation.wiring import build_services
from conftest import AN, BINH, SERVICE, WAREHOUSE


def qty(session, product_id):
    session.rollback()          # end the old REPEATABLE READ snapshot so we see what the API committed
    return session.execute(text("SELECT quantity FROM inventory WHERE product_id=:p"), {"p": product_id}).scalar()


def add_to_cart(client, h, pid, n=1):
    return client.post("/api/cart/items", json={"product_id": pid, "quantity": n}, headers=h)


def test_search_only_returns_active_products(client, session):
    session.execute(text("UPDATE product SET status='HIDDEN' WHERE id=6"))
    session.commit()
    r = client.get("/api/products?q=")
    assert r.status_code == 200 and r.json()["total"] == 5
    assert all("price" in p for p in r.json()["items"]) and all(p["id"] != 6 for p in r.json()["items"])


def test_cart_rejects_more_than_stock(client, as_):
    assert add_to_cart(client, as_(AN), 5, 3).status_code == 201          # product 5 has 3 in stock
    r = add_to_cart(client, as_(AN), 5, 1)                                # 3 + 1 > 3
    assert r.status_code == 409 and r.json()["error"] == "OUT_OF_STOCK"


def test_place_cod_order_decreases_stock_and_clears_cart(client, session, as_):
    h = as_(AN)
    add_to_cart(client, h, 1, 2)
    before = qty(session, 1)
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD"}, headers=h)
    assert r.status_code == 201
    assert r.json()["status"] == "PENDING" and r.json()["item_count"] == 2
    assert qty(session, 1) == before - 2
    assert client.get("/api/cart", headers=h).json()["items"] == []


def test_online_order_waits_for_payment(client, as_):
    h = as_(AN)
    add_to_cart(client, h, 1, 1)
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "ONLINE"}, headers=h)
    assert r.json()["status"] == "PENDING_PAYMENT"


def test_checkout_rolls_back_when_one_line_is_out_of_stock(client, session, as_):
    h = as_(AN)
    add_to_cart(client, h, 1, 1)
    add_to_cart(client, h, 5, 3)
    session.execute(text("UPDATE inventory SET quantity=1 WHERE product_id=5"))   # someone else bought it
    session.commit()
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD"}, headers=h)
    assert r.status_code == 409
    assert qty(session, 1) == 20                                   # line 1 was NOT kept
    assert session.execute(text("SELECT COUNT(*) FROM customer_order")).scalar() == 0
    assert len(client.get("/api/cart", headers=h).json()["items"]) == 2


def test_empty_cart_cannot_checkout(client, as_):
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD"}, headers=as_(AN))
    assert r.status_code == 400


def test_promotion_and_shipping_are_applied(client, as_):
    h = as_(AN)
    add_to_cart(client, h, 2, 1)
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD", "promo_code": "WELCOME10"}, headers=h)
    assert r.status_code == 201
    j = r.json()
    assert j["discount"] == 2150000 and j["shipping_fee"] == 0
    assert j["total_amount"] == j["subtotal"] - j["discount"] + j["shipping_fee"]


def test_invalid_promo_is_rejected(client, as_):
    h = as_(AN)
    add_to_cart(client, h, 1, 1)
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD", "promo_code": "NOPE"}, headers=h)
    assert r.status_code == 400


def test_only_last_units_are_sold_under_concurrency(db, session):
    """6 customers race for the 3 remaining units of product 5: exactly 3 succeed, stock never negative."""
    for i in range(10, 16):
        session.execute(text("INSERT INTO account(id,email,password_hash,role_id) VALUES (:i,:e,'x',1)"),
                        {"i": i, "e": f"c{i}@x.vn"})
        session.execute(text("INSERT INTO customer(id,first_name,last_name) VALUES (:i,'C','X')"), {"i": i})
        session.execute(text("INSERT INTO address(id,customer_id,recipient,phone,street,city) "
                             "VALUES (:i,:i,'C','090','1 A','HN')"), {"i": i})
        session.execute(text("INSERT INTO cart(id,customer_id) VALUES (:i,:i)"), {"i": i})
        session.execute(text("INSERT INTO cart_item(cart_id,product_id,quantity) VALUES (:i,5,1)"), {"i": i})
    session.commit()
    results = []

    def buy(cid):
        with db.new_session() as s:
            try:
                build_services(s).checkout.place_order(cid, cid, PaymentMethod.COD)
                results.append("ok")
            except OutOfStock:
                results.append("sold_out")

    threads = [threading.Thread(target=buy, args=(i,)) for i in range(10, 16)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 3 and results.count("sold_out") == 3
    assert qty(session, 5) == 0


def _place(client, h, method="COD"):
    add_to_cart(client, h, 1, 2)
    return client.post("/api/orders", json={"address_id": 1, "payment_method": method}, headers=h).json()


def test_customer_cancel_restores_stock(client, session, as_):
    h = as_(AN)
    o = _place(client, h)
    assert qty(session, 1) == 18
    r = client.post(f"/api/orders/{o['id']}/cancel", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert qty(session, 1) == 20


def test_customer_cannot_cancel_someone_elses_order(client, as_):
    o = _place(client, as_(AN))
    assert client.post(f"/api/orders/{o['id']}/cancel", headers=as_(BINH)).status_code == 403
    assert client.get(f"/api/orders/{o['id']}", headers=as_(BINH)).status_code == 404     # not even visible


def test_status_flow_and_invalid_transitions(client, as_):
    o = _place(client, as_(AN))
    url = f"/api/orders/{o['id']}/status"
    assert client.patch(url, json={"status": "PACKED"}, headers=as_(WAREHOUSE)).status_code == 409   # skip CONFIRMED
    assert client.patch(url, json={"status": "CONFIRMED"}, headers=as_(SERVICE)).status_code == 200
    assert client.patch(url, json={"status": "PACKED"}, headers=as_(WAREHOUSE)).status_code == 200
    assert client.post(f"/api/orders/{o['id']}/cancel", headers=as_(AN)).status_code == 409  # packed


def test_wrong_role_and_no_login(client, as_):
    assert client.get("/api/cart").status_code == 401
    assert client.patch("/api/orders/1/status", json={"status": "CONFIRMED"}, headers=as_(AN)).status_code == 403
    assert client.get("/api/cart", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_payment_callback_is_idempotent(client, session, as_):
    from unicart import config
    o = _place(client, as_(AN), "ONLINE")
    body = {"order_id": o["id"], "transaction_id": "TXN-1", "status": "SUCCESS"}
    partner = {"X-Partner-Secret": config.PARTNER_SECRET}
    assert client.post("/api/payments/callback", json=body).status_code == 401           # gateway must authenticate
    assert client.post("/api/payments/callback", json=body, headers=partner).status_code == 200
    assert client.post("/api/payments/callback", json=body, headers=partner).status_code == 200      # duplicate
    session.rollback()
    st = session.execute(text("SELECT status FROM customer_order WHERE id=:i"), {"i": o["id"]}).scalar()
    n = session.execute(text("SELECT COUNT(*) FROM order_status_history WHERE order_id=:i"),
                        {"i": o["id"]}).scalar()
    assert st == "PENDING" and n == 2                                # created + paid, not 3


def test_unpaid_online_orders_expire_and_release_stock(db, client, session, as_):
    o = _place(client, as_(AN), "ONLINE")
    with db.new_session() as s:
        n = build_services(s).orders.expire_unpaid(now=datetime.now() + timedelta(minutes=16))
    assert n == 1 and qty(session, 1) == 20
    session.rollback()
    assert session.execute(text("SELECT status FROM customer_order WHERE id=:i"), {"i": o["id"]}).scalar() == "CANCELLED"


def test_low_stock_report_for_warehouse(client, as_):
    r = client.get("/api/inventory/low-stock", headers=as_(WAREHOUSE))
    assert r.status_code == 200 and any(i["product_id"] == 5 for i in r.json())
