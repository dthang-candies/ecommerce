"""Tests of the full-product features: auth, profile, payment, shipping, review, admin, support, restock, reports, AI."""
from sqlalchemy import text

from conftest import ADMIN, AN, BINH, MANAGER, MARKETING, SALES, SERVICE, WAREHOUSE, login, SAMPLE_PASSWORD


def cart_add(client, h, pid, n=1, **extra):
    return client.post("/api/cart/items", json={"product_id": pid, "quantity": n, **extra}, headers=h)


def place(client, h, method="COD", pid=1, n=1, promo=None):
    cart_add(client, h, pid, n)
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": method, "promo_code": promo}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def to_delivered(client, as_, order_id):
    assert client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=as_(SERVICE)).status_code == 200
    assert client.patch(f"/api/orders/{order_id}/status", json={"status": "PACKED"}, headers=as_(WAREHOUSE)).status_code == 200
    for st in ("IN_TRANSIT", "DELIVERED"):
        r = client.post(f"/api/staff/sandbox/carrier/{order_id}", json={"status": st}, headers=as_(WAREHOUSE))
        assert r.status_code == 200, r.text


# ------------------------------------------------------------------ accounts (UC-01, UC-26, UC-24)
def test_register_login_and_profile(client):
    r = client.post("/api/auth/register", json={"email": "New@Mail.com", "password": "Passw0rdX", "first_name": "Mai",
                                                "last_name": "Lê", "phone": "0912345678"})
    assert r.status_code == 201 and r.json()["user"]["email"] == "new@mail.com" and r.json()["user"]["role"] == "CUSTOMER"
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=h).json()["profile"]["full_name"] == "Mai Lê"
    assert client.get("/api/cart", headers=h).json()["items"] == []
    dup = client.post("/api/auth/register", json={"email": "new@mail.com", "password": "Passw0rdX", "first_name": "A", "last_name": "B"})
    assert dup.status_code == 409


def test_register_validation(client):
    bad = client.post("/api/auth/register", json={"email": "nope", "password": "Passw0rdX", "first_name": "A", "last_name": "B"})
    assert bad.status_code == 400
    weak = client.post("/api/auth/register", json={"email": "a@b.vn", "password": "short", "first_name": "A", "last_name": "B"})
    assert weak.status_code == 400
    missing = client.post("/api/auth/register", json={"email": "a@b.vn"})
    assert missing.status_code == 422 and missing.json()["error"] == "VALIDATION_ERROR"


def test_login_errors_do_not_reveal_accounts_and_are_throttled(client):
    unknown = client.post("/api/auth/login", json={"email": "ghost@x.vn", "password": "Whatever1"})
    wrong = client.post("/api/auth/login", json={"email": AN, "password": "Wrong1234"})
    assert unknown.status_code == wrong.status_code == 401 and unknown.json()["message"] == wrong.json()["message"]
    for _ in range(10):
        r = client.post("/api/auth/login", json={"email": "spam@x.vn", "password": "Wrong1234"})
    assert r.status_code == 429


def test_locked_account_loses_access_immediately(client, as_):
    admin, h = as_(ADMIN), as_(AN)
    assert client.get("/api/cart", headers=h).status_code == 200
    assert client.patch("/api/admin/accounts/4/lock", json={"locked": True}, headers=admin).status_code == 200
    assert client.get("/api/cart", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"email": AN, "password": SAMPLE_PASSWORD}).status_code == 401
    assert client.patch("/api/admin/accounts/4/lock", json={"locked": False}, headers=admin).status_code == 200
    assert client.get("/api/cart", headers=h).status_code == 200


def test_admin_manages_staff_accounts_with_rbac(client, as_):
    admin = as_(ADMIN)
    r = client.post("/api/admin/accounts", json={"email": "staff2@abc.vn", "password": "Passw0rdX", "role": "SERVICE"}, headers=admin)
    assert r.status_code == 201 and r.json()["role"] == "SERVICE"
    assert client.post("/api/admin/accounts", json={"email": "x@abc.vn", "password": "Passw0rdX", "role": "CUSTOMER"}, headers=admin).status_code == 400
    assert client.patch(f"/api/admin/accounts/{r.json()['id']}/role", json={"role": "SALES"}, headers=admin).json()["role"] == "SALES"
    assert client.patch("/api/admin/accounts/1/lock", json={"locked": True}, headers=admin).status_code == 403   # not yourself
    assert client.get("/api/admin/accounts", headers=as_(SERVICE)).status_code == 403
    assert login(client, "staff2@abc.vn", "Passw0rdX")


def test_profile_and_address_book(client, as_):
    h = as_(AN)
    p = client.put("/api/me/profile", json={"first_name": "An", "last_name": "Nguyen", "phone": "0988888888"}, headers=h)
    assert p.status_code == 200 and p.json()["phone"] == "0988888888"
    a = client.post("/api/me/addresses", json={"recipient": "An", "phone": "0988888888", "street": "1 Lê Lợi",
                                               "city": "Hà Nội", "is_default": True}, headers=h)
    assert a.status_code == 201
    lst = client.get("/api/me/addresses", headers=h).json()
    assert len(lst) == 2 and sum(x["is_default"] for x in lst) == 1 and lst[0]["id"] == a.json()["id"]
    assert client.delete(f"/api/me/addresses/{a.json()['id']}", headers=h).status_code == 204
    left = client.get("/api/me/addresses", headers=h).json()
    assert len(left) == 1 and left[0]["is_default"]
    assert client.delete("/api/me/addresses/999", headers=h).status_code == 404


# ------------------------------------------------------------------ catalogue (UC-02..04)
def test_search_filter_sort_paginate_and_accent_insensitive(client):
    r = client.get("/api/products?sort=price_desc&size=2&page=1").json()
    assert r["total"] == 6 and [p["id"] for p in r["items"]][:1] == [2]
    assert [p["price"] for p in r["items"]] == sorted((p["price"] for p in r["items"]), reverse=True)
    assert client.get("/api/products?category_id=1").json()["total"] == 2
    assert client.get("/api/products?min_price=1000000&max_price=10000000").json()["total"] == 2
    assert client.get("/api/products?q=clean").json()["total"] == 1
    assert client.get("/api/products?min_price=abc").status_code == 422


def test_did_you_mean_for_typos(client):
    r = client.get("/api/products?q=Smartphne").json()
    assert r["total"] == 0 and r["suggestion"] == "Smartphone"
    assert client.get("/api/products?q=zzzzqqqq").json()["suggestion"] is None


def test_product_detail_shows_stock_and_hides_inactive(client, session):
    d = client.get("/api/products/5").json()
    assert d["in_stock"] and d["quantity"] == 3 and d["category"]["name"] == "Shoes" and d["reviews"] == []
    session.execute(text("UPDATE product SET status='HIDDEN' WHERE id=5"))
    session.commit()
    assert client.get("/api/products/5").status_code == 404


# ------------------------------------------------------------------ checkout quote, payment (UC-06/07)
def test_quote_validates_cart_and_computes_total(client, session, as_):
    h = as_(AN)
    assert client.post("/api/checkout/quote", json={}, headers=h).json()["can_checkout"] is False
    cart_add(client, h, 1, 1)
    q = client.post("/api/checkout/quote", json={"promo_code": "welcome10"}, headers=h).json()
    assert q["subtotal"] == 350000 and q["discount"] == 35000 and q["shipping_fee"] == 30000 and q["total"] == 345000
    assert q["promo_code"] == "WELCOME10" and q["can_checkout"]
    bad = client.post("/api/checkout/quote", json={"promo_code": "NOPE"}, headers=h).json()
    assert bad["promo_error"] and bad["discount"] == 0
    session.execute(text("UPDATE inventory SET quantity=0 WHERE product_id=1"))
    session.commit()
    blocked = client.post("/api/checkout/quote", json={}, headers=h).json()
    assert blocked["can_checkout"] is False and blocked["issues"]


def test_online_payment_success_failure_and_expiry(client, session, as_):
    h = as_(AN)
    o = place(client, h, "ONLINE")
    bad = client.post(f"/api/payments/orders/{o['id']}/pay", json={"channel": "CARD", "token": "tok_4000_0000"}, headers=h)
    assert bad.status_code == 200 and bad.json()["success"] is False and bad.json()["order"]["status"] == "PENDING_PAYMENT"
    ok = client.post(f"/api/payments/orders/{o['id']}/pay", json={"channel": "WALLET", "token": "tok_wallet_1"}, headers=h).json()
    assert ok["success"] and ok["order"]["status"] == "PENDING" and ok["payment"]["method"] == "WALLET"
    assert ok["payment"]["transaction_id"].startswith("TXN-")
    again = client.post(f"/api/payments/orders/{o['id']}/pay", json={"channel": "CARD", "token": "tok_4242_4242"}, headers=h)
    assert again.status_code == 409                                    # already paid
    cod = place(client, h, "COD", pid=4)
    assert client.post(f"/api/payments/orders/{cod['id']}/pay", json={"channel": "CARD", "token": "tok_4242_4242"}, headers=h).status_code == 409
    other = client.post(f"/api/payments/orders/{o['id']}/pay", json={"channel": "CARD", "token": "tok_4242_4242"}, headers=as_(BINH))
    assert other.status_code == 404


def test_overdue_online_order_cannot_be_paid(client, session, as_):
    h = as_(AN)
    o = place(client, h, "ONLINE")
    session.execute(text("UPDATE customer_order SET created_at = NOW() - INTERVAL 20 MINUTE WHERE id=:i"), {"i": o["id"]})
    session.commit()
    r = client.post(f"/api/payments/orders/{o['id']}/pay", json={"channel": "CARD", "token": "tok_4242_4242"}, headers=h)
    assert r.status_code == 409
    assert client.get(f"/api/orders/{o['id']}", headers=h).json()["status"] == "CANCELLED"


# ------------------------------------------------------------------ shipping, delivery, reviews (UC-14, UC-21, UC-09)
def test_full_fulfilment_flow_points_cod_and_review_rules(client, session, as_):
    h = as_(AN)
    o = place(client, h, "COD", pid=2, n=1)                           # 21,500,000 -> 2,150 points
    oid = o["id"]
    assert client.post(f"/api/orders/{oid}/reviews", json={"product_id": 2, "rating": 5}, headers=h).status_code == 400   # not delivered
    client.patch(f"/api/orders/{oid}/status", json={"status": "CONFIRMED"}, headers=as_(SERVICE))
    packed = client.patch(f"/api/orders/{oid}/status", json={"status": "PACKED"}, headers=as_(WAREHOUSE)).json()
    assert packed["shipment"]["tracking_number"].startswith("UCX") and packed["shipment"]["status"] == "CREATED"
    assert client.post(f"/api/staff/sandbox/carrier/{oid}", json={"status": "DELIVERED"}, headers=as_(WAREHOUSE)).status_code == 409  # skip transit
    t = client.post(f"/api/staff/sandbox/carrier/{oid}", json={"status": "IN_TRANSIT"}, headers=as_(WAREHOUSE)).json()
    assert t["status"] == "SHIPPING"
    d = client.post(f"/api/staff/sandbox/carrier/{oid}", json={"status": "DELIVERED"}, headers=as_(WAREHOUSE)).json()
    assert d["status"] == "DELIVERED" and d["payment"]["status"] == "SUCCESS" and d["shipment"]["delivery_date"]
    assert client.post(f"/api/staff/sandbox/carrier/{oid}", json={"status": "DELIVERED"}, headers=as_(WAREHOUSE)).status_code == 200   # idempotent
    assert client.get("/api/me/profile", headers=h).json()["loyalty_point"] == 2150
    detail = client.get(f"/api/orders/{oid}", headers=h).json()
    assert [x["to_status"] for x in detail["history"]] == ["PENDING", "CONFIRMED", "PACKED", "SHIPPING", "DELIVERED"]
    # reviews: delivered only, own order, product in order, once per product, 1..5
    assert client.post(f"/api/orders/{oid}/reviews", json={"product_id": 1, "rating": 5}, headers=h).status_code == 400
    assert client.post(f"/api/orders/{oid}/reviews", json={"product_id": 2, "rating": 6}, headers=h).status_code == 422
    assert client.post(f"/api/orders/{oid}/reviews", json={"product_id": 2, "rating": 4}, headers=as_(BINH)).status_code == 403
    assert client.post(f"/api/orders/{oid}/reviews", json={"product_id": 2, "rating": 4, "comment": "Tốt"}, headers=h).status_code == 201
    assert client.post(f"/api/orders/{oid}/reviews", json={"product_id": 2, "rating": 5}, headers=h).status_code == 409
    shown = client.get("/api/products/2").json()
    assert shown["rating"] == {"average": 4.0, "count": 1} and shown["reviews"][0]["author"] == "An Van Nguyen"
    assert client.get(f"/api/orders/{oid}", headers=h).json()["items"][0]["reviewed"] is True


def test_failed_delivery_cancels_order_and_returns_stock(client, session, as_):
    h = as_(AN)
    o = place(client, h, "COD", pid=1, n=2)
    client.patch(f"/api/orders/{o['id']}/status", json={"status": "CONFIRMED"}, headers=as_(SERVICE))
    client.patch(f"/api/orders/{o['id']}/status", json={"status": "PACKED"}, headers=as_(WAREHOUSE))
    client.post(f"/api/staff/sandbox/carrier/{o['id']}", json={"status": "IN_TRANSIT"}, headers=as_(WAREHOUSE))
    r = client.post(f"/api/staff/sandbox/carrier/{o['id']}", json={"status": "FAILED"}, headers=as_(WAREHOUSE))
    assert r.json()["status"] == "CANCELLED"
    session.rollback()
    assert session.execute(text("SELECT quantity FROM inventory WHERE product_id=1")).scalar() == 20


def test_shipping_webhook_requires_partner_secret(client, as_):
    from unicart import config
    h = as_(AN)
    o = place(client, h)
    to_packed = [client.patch(f"/api/orders/{o['id']}/status", json={"status": s}, headers=as_(u)) for s, u in
                 (("CONFIRMED", SERVICE), ("PACKED", WAREHOUSE))]
    assert all(r.status_code == 200 for r in to_packed)
    body = {"order_id": o["id"], "status": "IN_TRANSIT"}
    assert client.post("/api/shipping/callback", json=body).status_code == 401
    assert client.post("/api/shipping/callback", json=body, headers={"X-Partner-Secret": "wrong"}).status_code == 401
    ok = client.post("/api/shipping/callback", json=body, headers={"X-Partner-Secret": config.PARTNER_SECRET})
    assert ok.status_code == 200 and ok.json()["status"] == "SHIPPING"


def test_staff_order_queues(client, as_):
    h = as_(AN)
    o = place(client, h)
    q = client.get("/api/staff/orders?status=PENDING", headers=as_(SERVICE)).json()
    assert q["total"] == 1 and q["items"][0]["id"] == o["id"]
    assert client.get("/api/staff/orders", headers=h).status_code == 403
    assert client.get(f"/api/staff/orders/{o['id']}", headers=as_(SALES)).json()["history"]
    assert client.get("/api/staff/orders?status=BOGUS", headers=as_(SERVICE)).status_code == 422


# ------------------------------------------------------------------ admin (UC-10, UC-11)
def test_admin_product_lifecycle_and_bar_01(client, session, as_):
    admin = as_(ADMIN)
    cat = client.post("/api/admin/categories", json={"name": "Gia dụng", "description": "Nhà bếp"}, headers=admin)
    assert cat.status_code == 201
    assert client.post("/api/admin/categories", json={"name": "Gia dụng"}, headers=admin).status_code == 409
    body = {"sku": "HM-900", "name": "Nồi cơm điện", "category_id": cat.json()["id"], "price": 1590000, "brand": "Sharp",
            "attributes": {"capacity": "1.8L"}, "quantity": 7, "min_threshold": 2}
    p = client.post("/api/admin/products", json=body, headers=admin)
    assert p.status_code == 201 and p.json()["quantity"] == 7 and p.json()["status"] == "ACTIVE"
    pid = p.json()["id"]
    assert client.post("/api/admin/products", json=body, headers=admin).status_code == 409           # duplicate SKU
    assert client.post("/api/admin/products", json=body | {"sku": "X", "price": -1}, headers=admin).status_code == 422
    assert client.post("/api/admin/products", json=body | {"sku": "Y", "category_id": 999}, headers=admin).status_code == 400
    up = client.put(f"/api/admin/products/{pid}", json={k: v for k, v in body.items() if k not in ("sku", "quantity", "min_threshold")} | {"price": 1490000}, headers=admin)
    assert up.json()["price"] == 1490000
    assert client.post(f"/api/admin/products/{pid}/visibility", json={"visible": False}, headers=admin).json()["status"] == "HIDDEN"
    assert client.get(f"/api/products/{pid}").status_code == 404                                      # BR-01
    assert client.get("/api/admin/products?status=HIDDEN", headers=admin).json()["total"] == 1
    assert client.delete("/api/admin/categories/%d" % cat.json()["id"], headers=admin).status_code == 409   # not empty
    # a product that was ordered is hidden, never deleted
    place(client, as_(AN), pid=1)
    assert client.delete("/api/admin/products/1", headers=admin).json()["result"] == "HIDDEN"
    assert client.get("/api/admin/products?q=Clean", headers=admin).json()["items"][0]["status"] == "HIDDEN"
    # a product with stock history is hidden; a brand-new one with no history is really deleted
    assert client.delete(f"/api/admin/products/{pid}", headers=admin).json()["result"] == "HIDDEN"
    fresh = client.post("/api/admin/products", json=body | {"sku": "FRESH", "quantity": 0}, headers=admin).json()
    assert client.delete(f"/api/admin/products/{fresh['id']}", headers=admin).json()["result"] == "DELETED"
    assert client.get("/api/admin/products?q=FRESH", headers=admin).json()["total"] == 0
    assert client.post("/api/admin/products", json=body | {"sku": "Z1"}, headers=as_(SERVICE)).status_code == 403


def test_promotions_crud_and_validation(client, as_):
    admin = as_(ADMIN)
    base = {"code": "sale50k", "discount_type": "AMOUNT", "discount_value": 50000, "min_order_value": 100000,
            "start_at": "2026-01-01T00:00:00", "end_at": "2026-12-31T23:59:59"}
    p = client.post("/api/admin/promotions", json=base, headers=admin)
    assert p.status_code == 201 and p.json()["code"] == "SALE50K"
    assert client.post("/api/admin/promotions", json=base, headers=admin).status_code == 409
    assert client.post("/api/admin/promotions", json=base | {"code": "BAD", "discount_type": "PERCENT", "discount_value": 150}, headers=admin).status_code == 400
    assert client.post("/api/admin/promotions", json=base | {"code": "BAD2", "end_at": "2025-01-01T00:00:00"}, headers=admin).status_code == 400
    assert len(client.get("/api/admin/promotions", headers=as_(MARKETING)).json()) == 2
    assert client.post("/api/admin/promotions", json=base | {"code": "M"}, headers=as_(MARKETING)).status_code == 403
    h = as_(AN)
    cart_add(client, h, 1, 1)
    q = client.post("/api/checkout/quote", json={"promo_code": "SALE50K"}, headers=h).json()
    assert q["discount"] == 50000
    assert client.delete(f"/api/admin/promotions/{p.json()['id']}", headers=admin).json()["result"] == "DELETED"


# ------------------------------------------------------------------ support (UC-23)
def test_support_request_flow(client, as_):
    h = as_(AN)
    o = place(client, h)
    r = client.post("/api/me/support-requests", json={"content": "Tôi muốn đổi địa chỉ nhận hàng", "order_id": o["id"]}, headers=h)
    assert r.status_code == 201 and r.json()["status"] == "OPEN"
    assert client.post("/api/me/support-requests", json={"content": "hello there", "order_id": 999}, headers=h).status_code == 404
    rid = r.json()["id"]
    q = client.get("/api/staff/support-requests?status=OPEN", headers=as_(SALES)).json()
    assert q["total"] == 1
    assert client.get("/api/staff/support-requests", headers=h).status_code == 403
    rep = client.post(f"/api/staff/support-requests/{rid}/reply", json={"response": "Đã cập nhật địa chỉ cho bạn"}, headers=as_(SALES)).json()
    assert rep["status"] == "IN_PROGRESS" and rep["response"]
    done = client.post(f"/api/staff/support-requests/{rid}/resolve", headers=as_(SALES)).json()
    assert done["status"] == "RESOLVED"
    mine = client.get("/api/me/support-requests", headers=h).json()
    assert mine[0]["status"] == "RESOLVED" and mine[0]["response"].startswith("Đã")
    assert client.post(f"/api/staff/support-requests/{rid}/reply", json={"response": "again"}, headers=as_(SALES)).status_code == 409


# ------------------------------------------------------------------ inventory & restock (UC-12, UC-22, BR-11)
def test_restock_request_flow_increases_stock_only_when_received(client, session, as_):
    w = as_(WAREHOUSE)
    low = [i["product_id"] for i in client.get("/api/inventory/low-stock", headers=w).json()]
    assert 5 in low
    sup = client.get("/api/suppliers", headers=w).json()[0]["id"]
    req = client.post("/api/restock-requests", json={"product_id": 5, "supplier_id": sup, "quantity": 40}, headers=w)
    assert req.status_code == 201 and req.json()["status"] == "REQUESTED"
    rid = req.json()["id"]
    assert client.post("/api/restock-requests", json={"product_id": 5, "supplier_id": sup, "quantity": 5}, headers=w).status_code == 409
    assert client.post(f"/api/restock-requests/{rid}/receive", headers=w).status_code == 409           # not confirmed yet
    assert client.post(f"/api/staff/sandbox/supplier/{rid}", json={"accept": True}, headers=w).json()["status"] == "CONFIRMED"
    session.rollback()
    assert session.execute(text("SELECT quantity FROM inventory WHERE product_id=5")).scalar() == 3    # still unchanged
    assert client.post(f"/api/restock-requests/{rid}/receive", headers=w).json()["status"] == "RECEIVED"
    session.rollback()
    assert session.execute(text("SELECT quantity FROM inventory WHERE product_id=5")).scalar() == 43
    assert client.get("/api/inventory/5/movements", headers=w).json()[0]["type"] == "IN"
    assert client.post(f"/api/restock-requests/{rid}/receive", headers=w).status_code == 409           # only once
    assert client.get("/api/inventory/summary", headers=as_(MANAGER)).json()["skus"] == 6
    assert client.post("/api/restock-requests", json={"product_id": 5, "supplier_id": sup, "quantity": 1}, headers=as_(MANAGER)).status_code == 403


# ------------------------------------------------------------------ reports (UC-15, UC-20)
def test_business_report_and_access_control(client, as_):
    h = as_(AN)
    o1, o2 = place(client, h, pid=1, n=2), place(client, h, pid=2, n=1)
    to_delivered(client, as_, o1["id"])
    client.post(f"/api/orders/{o2['id']}/cancel", headers=h)
    r = client.get("/api/reports/business", headers=as_(MANAGER))
    assert r.status_code == 200
    j = r.json()
    assert j["kpis"]["total_orders"] == 2 and j["kpis"]["committed_orders"] == 1 and j["kpis"]["units_sold"] == 2
    assert j["kpis"]["cancel_rate"] == 50.0 and j["kpis"]["delivered_revenue"] == 700000
    assert j["kpis"]["committed_sales"] == 700000 and j["kpis"]["average_order_value"] == 700000
    assert j["by_status"]["DELIVERED"] == 1 and j["by_status"]["CANCELLED"] == 1
    assert j["top_products"][0]["product_id"] == 1 and len(j["series"]) == 30
    assert client.get("/api/reports/business", headers=as_(MARKETING)).status_code == 403
    assert client.get("/api/reports/business?start=2026-02-01&end=2026-01-01", headers=as_(MANAGER)).status_code == 400
    assert client.get("/api/reports/business", headers=h).status_code == 403


# ------------------------------------------------------------------ AI subset (UC-16, UC-17, UC-20)
def test_recommendations_never_show_hidden_or_out_of_stock(client, session, as_):
    session.execute(text("UPDATE inventory SET quantity=0 WHERE product_id=3"))
    session.execute(text("UPDATE product SET status='HIDDEN' WHERE id=4"))
    session.commit()
    ids = [p["id"] for p in client.get("/api/recommendations/home?limit=10").json()]
    assert ids and 3 not in ids and 4 not in ids
    sim = client.get("/api/recommendations/product/2").json()
    assert all(p["id"] not in (3, 4) for p in sim["similar"] + sim["bought_together"])
    assert all(p["id"] != 2 for p in sim["similar"])


def test_personalised_home_prefers_viewed_categories_and_respects_opt_out(client, as_):
    h = as_(AN)
    for _ in range(3):
        client.post("/api/events", json={"event_type": "VIEW", "product_id": 1}, headers=h)    # books
        client.post("/api/events", json={"event_type": "VIEW", "product_id": 6}, headers=h)
    mine = client.get("/api/recommendations/home?limit=2", headers=h).json()
    assert {p["id"] for p in mine} == {1, 6} and mine[0]["reason"] == "Dành cho bạn"
    anon = client.get("/api/recommendations/home?limit=6&personalize=false", headers=h).json()
    assert all(p["reason"] != "Dành cho bạn" for p in anon)


def test_events_and_cart_recommendations(client, session, as_):
    h = as_(AN)
    assert client.post("/api/events", json={"event_type": "SEARCH", "keyword": "áo khoác"}).status_code == 204   # guest
    assert client.post("/api/events", json={"event_type": "PURCHASE", "product_id": 1}, headers=h).status_code == 400     # server-only event
    assert client.post("/api/events", json={"event_type": "VIEW", "product_id": 99999}, headers=h).status_code == 204
    assert client.post("/api/events", json={"event_type": "NOPE"}, headers=h).status_code == 422
    cart_add(client, h, 2, 1)
    rec = client.get("/api/recommendations/cart", headers=h).json()
    assert rec and all(p["id"] != 2 for p in rec)


def test_recommendation_performance_report(client, session, as_):
    h = as_(AN)
    for _ in range(4):
        client.post("/api/events", json={"event_type": "REC_IMPRESSION", "keyword": "home"}, headers=h)
    client.post("/api/events", json={"event_type": "CLICK_REC", "product_id": 1, "keyword": "home"}, headers=h)
    assert cart_add(client, h, 1, 1, source="home").status_code == 201
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD"}, headers=h)
    assert r.status_code == 201
    rep = client.get("/api/reports/recommendations", headers=as_(MARKETING)).json()
    home = next(p for p in rep["placements"] if p["placement"] == "home")
    assert home["impressions"] == 4 and home["clicks"] == 1 and home["add_to_cart"] == 1 and home["purchases"] == 1
    assert home["ctr"] == 25.0 and home["add_to_cart_rate"] == 100.0 and home["conversion_rate"] == 25.0
    assert client.get("/api/reports/recommendations", headers=h).status_code == 403


def test_tracking_can_be_switched_off(client, session, as_):
    h = as_(AN)
    assert cart_add(client, h, 1, 1, source="home", track=False).status_code == 201
    session.rollback()
    assert session.execute(text("SELECT COUNT(*) FROM interaction_log")).scalar() == 0
