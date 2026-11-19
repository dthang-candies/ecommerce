"""Staff dashboard (home page of /quan-tri): every role sees only the sections it has rights to."""
from datetime import date

from sqlalchemy import text

from conftest import ADMIN, AN, MANAGER, MARKETING, SALES, SERVICE, WAREHOUSE


def dash(client, headers):
    r = client.get("/api/staff/dashboard", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_sections_follow_the_role(client, as_):
    sections = lambda email: set(dash(client, as_(email))) - {"date"}
    assert sections(ADMIN) == {"sales", "orders", "inventory", "support", "promotions", "accounts"}
    assert sections(MANAGER) == {"sales", "orders", "inventory", "promotions"}
    assert sections(SERVICE) == {"orders"}
    assert sections(WAREHOUSE) == {"orders", "inventory"}
    assert sections(SALES) == {"orders", "support"}
    assert sections(MARKETING) == {"promotions"}


def test_customers_and_guests_are_refused(client, as_):
    assert client.get("/api/staff/dashboard", headers=as_(AN)).status_code == 403
    assert client.get("/api/staff/dashboard").status_code == 401


def test_numbers_reflect_new_activity(client, session, as_):
    before = dash(client, as_(ADMIN))
    h = as_(AN)
    client.post("/api/cart/items", json={"product_id": 1, "quantity": 2}, headers=h)
    order = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD"}, headers=h).json()
    client.post("/api/me/support-requests", json={"content": "Cho tôi hỏi về đơn hàng", "order_id": order["id"]}, headers=h)
    session.execute(text("UPDATE inventory SET quantity=0 WHERE product_id=2"))
    session.commit()
    after = dash(client, as_(ADMIN))

    assert after["date"] == str(date.today())
    assert after["sales"]["today"]["orders"] == before["sales"]["today"]["orders"] + 1
    assert after["sales"]["today"]["sales"] == before["sales"]["today"]["sales"] + order["total_amount"]
    assert len(after["sales"]["series"]) == 7 and after["sales"]["series"][-1]["date"] == str(date.today())
    assert after["sales"]["last_7_days"]["orders"] == sum(d["orders"] for d in after["sales"]["series"])
    assert after["orders"]["waiting"]["PENDING"] == before["orders"]["waiting"]["PENDING"] + 1
    assert after["orders"]["recent"][0]["id"] == order["id"]
    assert after["support"]["open"] == before["support"]["open"] + 1
    assert after["inventory"]["out_of_stock"] == before["inventory"]["out_of_stock"] + 1
    assert after["inventory"]["lowest"][0] | {"quantity": 0, "product_id": 2} == after["inventory"]["lowest"][0]


def test_account_counts(client, session, as_):
    before = dash(client, as_(ADMIN))["accounts"]
    client.post("/api/auth/register", json={"email": "moi@example.com", "password": "Abc@12345",
                                            "first_name": "Mới", "last_name": "Khách"})
    session.execute(text("UPDATE account SET status='LOCKED' WHERE email='binh@gmail.com'"))
    session.commit()
    after = dash(client, as_(ADMIN))["accounts"]
    assert after["customers"] == before["customers"] + 1 and after["new_customers"] == before["new_customers"] + 1
    assert after["staff"] == before["staff"] and after["locked"] == before["locked"] + 1
