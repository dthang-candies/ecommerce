"""Shopping assistant: promotions of today, product help, order tracking, return guidance.

Both engines are covered: the rule engine (no Gemini key, or Gemini down) and the Gemini function-calling loop, driven by a
scripted fake model. The security properties are tested explicitly: a customer can never reach someone else's order, the
model never sees address/phone, and the bot never writes anything itself."""
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from conftest import AN, BINH, SERVICE, WAREHOUSE
from fake_ai import FakeGemini
from unicart import config
from unicart.business.extended.ai.runtime import AiRuntime
from unicart.presentation.extended import deps
from unicart.presentation.app import create_app


@pytest.fixture(autouse=True)
def _fresh_budgets():
    for b in (deps.chat_budget, deps.text_budget):
        b.hits.clear()


@pytest.fixture()
def fake():
    return FakeGemini()


@pytest.fixture()
def ai_client(db, fake):
    rt = AiRuntime(db, fake)
    rt.sync()
    with TestClient(create_app(db, ai=rt)) as c:
        yield c


def say(client, *texts, headers=None, roles=None):
    """Post a conversation; `texts` alternate user / assistant starting with the user unless `roles` is given."""
    roles = roles or ["user" if i % 2 == 0 else "assistant" for i in range(len(texts))]
    return client.post("/api/chat", json={"messages": [{"role": r, "content": t} for r, t in zip(roles, texts)]},
                       headers=headers or {})


LONG = "Bạn ơi cho mình hỏi một chút nhé, mình đang phân vân mãi từ nãy giờ nên hỏi: "   # > 12 words: not a quick question, so the model is used


def call(name, **args):
    return [{"functionCall": {"name": name, "args": args}}]


def add_promo(db, code, start=-1, end=30, active=True, minimum=0, kind="PERCENT", value=10):
    now = datetime.now()
    with db.new_session() as s:
        s.execute(text("INSERT INTO promotion(code,discount_type,discount_value,min_order_value,start_at,end_at,active) "
                       "VALUES (:c,:k,:v,:m,:s,:e,:a)"),
                  {"c": code, "k": kind, "v": value, "m": minimum, "s": now + timedelta(days=start),
                   "e": now + timedelta(days=end), "a": active})
        s.commit()


def place(client, h, pid=1, n=1):
    client.post("/api/cart/items", json={"product_id": pid, "quantity": n}, headers=h)
    r = client.post("/api/orders", json={"address_id": 1, "payment_method": "COD"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def deliver(client, as_, order_id):
    assert client.patch(f"/api/orders/{order_id}/status", json={"status": "CONFIRMED"}, headers=as_(SERVICE)).status_code == 200
    assert client.patch(f"/api/orders/{order_id}/status", json={"status": "PACKED"}, headers=as_(WAREHOUSE)).status_code == 200
    for st in ("IN_TRANSIT", "DELIVERED"):
        assert client.post(f"/api/staff/sandbox/carrier/{order_id}", json={"status": st}, headers=as_(WAREHOUSE)).status_code == 200


def codes(r):
    return [p["code"] for p in r.json()["promotions"]]


# ------------------------------------------------------------------ request validation
def test_validation(client, as_):
    assert client.post("/api/chat", json={"messages": []}).status_code == 422
    assert client.post("/api/chat", json={"messages": [{"role": "system", "content": "x"}]}).status_code == 422
    assert say(client, "chào", "Xin chào bạn", roles=["user", "assistant"]).status_code == 400      # must end on the shopper
    assert say(client, "   ").status_code == 400
    ok = say(client, "bạn đang làm gì", "x" * 50, "chào", roles=["assistant", "user", "user"])        # leading bot turn is dropped
    assert ok.status_code == 200
    assert say(client, "a" * 2001).status_code == 422                                                # oversize message rejected


def test_rate_limit_per_client(client):
    for _ in range(20):
        assert say(client, "chào").status_code == 200
    r = say(client, "chào")
    assert r.status_code == 429 and r.json()["error"] == "TOO_MANY_REQUESTS"


# ------------------------------------------------------------------ rule engine (no Gemini key)
def test_todays_promotions_lists_only_valid_codes(client, db):
    add_promo(db, "SALE50K", kind="AMOUNT", value=50000, minimum=300000)
    add_promo(db, "OLD", start=-60, end=-1)                  # expired
    add_promo(db, "SOON", start=2, end=9)                    # not started
    add_promo(db, "OFF", active=False)                       # switched off by admin
    r = say(client, "Hôm nay có sản phẩm nào giảm giá không?")
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "rules" and body["degraded"] is False
    assert sorted(codes(r)) == ["SALE50K", "WELCOME10"]
    assert "SALE50K" in body["reply"] and "OLD" not in body["reply"] and "SOON" not in body["reply"]
    assert "chưa có giá giảm riêng" in body["reply"]         # never pretends products are individually discounted
    sale = next(p for p in body["promotions"] if p["code"] == "SALE50K")
    assert "50.000đ" in sale["description"] and "300.000đ" in sale["description"]


def test_no_promotions_today(client, db):
    with db.new_session() as s:
        s.execute(text("UPDATE promotion SET active=FALSE"))
        s.commit()
    r = say(client, "có khuyến mãi gì không")
    assert r.json()["promotions"] == [] and "chưa có mã giảm giá" in r.json()["reply"]


def test_policy_answers_use_real_config(client):
    ship = say(client, "Phí ship bao nhiêu?").json()["reply"]
    assert "30.000đ" in ship and "500.000đ" in ship
    pay = say(client, "thanh toán thế nào").json()["reply"]
    assert "15 phút" in pay
    assert "Mình là trợ lý" in say(client, "xin chào").json()["reply"]


def test_product_search_returns_cards_from_the_database(client):
    r = say(client, "laptop dưới 25 triệu")
    items = r.json()["products"]
    assert [p["name"] for p in items] == ["Laptop Pro 14"] and items[0]["price"] == 21500000
    nothing = say(client, "xe ô tô điện").json()
    assert nothing["products"] == [] and "chưa tìm thấy" in nothing["reply"]


def test_guest_cannot_track_orders(client, as_):
    place(client, as_(AN))
    r = say(client, "đơn hàng của tôi đến đâu rồi")
    assert r.json()["orders"] == [] and "đăng nhập" in r.json()["reply"]
    assert say(client, "kiểm tra đơn #1").json()["orders"] == []


def test_customer_tracks_own_orders(client, as_):
    h = as_(AN)
    order = place(client, h)
    listing = say(client, "đơn hàng của tôi đến đâu rồi", headers=h).json()
    assert [o["id"] for o in listing["orders"]] == [order["id"]]
    one = say(client, f"đơn #{order['id']} đang ở đâu", headers=h).json()
    assert "Chờ xác nhận" in one["reply"] or "Chờ thanh toán" in one["reply"]
    assert "”, tổng 380.000đ." in one["reply"]                                    # 350k + 30k shipping; punctuation kept, only thousands dots
    follow = say(client, "Tôi muốn kiểm tra đơn hàng", "Bạn cho mình mã đơn nhé", f"{order['id']}", headers=h).json()
    assert [o["id"] for o in follow["orders"]] == [order["id"]]                  # a bare number continues the previous question


def test_customer_cannot_see_another_customers_order(client, as_):
    order = place(client, as_(AN))
    r = say(client, f"đơn #{order['id']} của tôi đâu", headers=as_(BINH)).json()
    assert r["orders"] == [] and "không tìm thấy" in r["reply"].lower()
    missing = say(client, "đơn #99999", headers=as_(BINH)).json()
    assert missing["reply"] == r["reply"]                                        # identical answer: ids cannot be enumerated


def test_staff_account_is_not_treated_as_customer(client, as_):
    place(client, as_(AN))
    r = say(client, "đơn hàng của tôi", headers=as_(SERVICE)).json()
    assert r["orders"] == [] and "đăng nhập" in r["reply"]


def test_return_flow_for_delivered_order_proposes_but_never_creates(client, as_, db):
    h = as_(AN)
    order = place(client, h)
    deliver(client, as_, order["id"])
    r = say(client, f"Tôi muốn đổi trả đơn #{order['id']}", headers=h).json()
    assert "đủ điều kiện" in r["reply"]
    (action,) = r["actions"]
    assert action["type"] == "create_support_request" and action["order_id"] == order["id"]
    assert client.get("/api/me/support-requests", headers=h).json() == []              # only proposed, nothing stored
    sent = client.post("/api/me/support-requests", json={"content": action["content"] + "sai size", "order_id": action["order_id"]},
                       headers=h)                                                      # the customer's confirm button
    assert sent.status_code == 201 and len(client.get("/api/me/support-requests", headers=h).json()) == 1


def test_return_refused_for_undelivered_and_expired_orders(client, as_, db):
    h = as_(AN)
    pending = place(client, h)
    r = say(client, f"đổi trả đơn #{pending['id']}", headers=h).json()
    assert r["actions"] == [] and "chưa được giao" in r["reply"]

    delivered = place(client, h, pid=3)
    deliver(client, as_, delivered["id"])
    old = datetime.now() - timedelta(days=config.RETURN_WINDOW_DAYS + 3)
    with db.new_session() as s:
        s.execute(text("UPDATE order_status_history SET changed_at=:t WHERE order_id=:o AND to_status='DELIVERED'"),
                  {"t": old, "o": delivered["id"]})
        s.commit()
    r = say(client, f"trả hàng đơn #{delivered['id']}", headers=h).json()
    assert r["actions"] == [] and "quá thời hạn" in r["reply"]


def test_return_without_login_explains_policy_only(client):
    r = say(client, "Làm sao để đổi trả hàng?").json()
    assert "7 ngày" in r["reply"] and "đăng nhập" in r["reply"] and r["actions"] == []


def test_cancel_question_points_to_the_order_page(client, as_):
    h = as_(AN)
    order = place(client, h)
    r = say(client, f"huỷ đơn #{order['id']} giúp mình", headers=h).json()
    assert "hủy được" in r["reply"] or "vẫn hủy" in r["reply"]
    assert client.get(f"/api/orders/{order['id']}", headers=h).json()["status"] != "CANCELLED"   # the bot never cancels


# ------------------------------------------------------------------ Gemini function-calling path
def test_gemini_calls_tool_then_answers(ai_client, fake, db):
    add_promo(db, "FLASH5", value=5)
    fake.chat_script = [call("list_active_promotions"), [{"text": "Hôm nay có mã **FLASH5** và WELCOME10 nhé!"}]]
    r = say(ai_client, LONG + "hôm nay shop có chương trình ưu đãi gì không")
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "ai" and body["degraded"] is False
    assert body["reply"] == "Hôm nay có mã FLASH5 và WELCOME10 nhé!"             # markdown stripped
    assert sorted(codes(r)) == ["FLASH5", "WELCOME10"]
    assert len(fake.chat_calls) == 2
    sent_back = fake.chat_calls[1]["contents"][-1]["parts"][0]["functionResponse"]
    assert sent_back["name"] == "list_active_promotions"
    assert "FLASH5" in json.dumps(sent_back, ensure_ascii=False)
    assert "chưa đăng nhập" in fake.chat_calls[0]["system"].lower() or "CHƯA" in fake.chat_calls[0]["system"]


def test_gemini_product_search_cards_and_prices_come_from_db(ai_client, fake):
    fake.chat_script = [call("search_products", query="laptop", max_price=30000000, in_stock_only=True),
                        [{"text": "Mình gợi ý Laptop Pro 14 nhé."}]]
    body = say(ai_client, "tư vấn laptop cho sinh viên").json()
    assert [p["name"] for p in body["products"]] == ["Laptop Pro 14"] and body["products"][0]["price"] == 21500000


def test_gemini_never_gets_personal_data_and_cannot_cross_accounts(ai_client, fake, as_):
    an, binh = as_(AN), as_(BINH)
    order = place(ai_client, an)
    fake.chat_script = [call("get_order_status", order_id=order["id"]), [{"text": "Đơn của bạn đang chờ xác nhận."}]]
    mine = say(ai_client, LONG + "đơn hàng mình mới đặt đang ở đâu rồi", headers=an).json()
    assert [o["id"] for o in mine["orders"]] == [order["id"]]
    wire = json.dumps(fake.chat_calls, ensure_ascii=False)
    for secret in ("Tran Phu", "0901000001", "Nguyen Van An", "Ha Dong"):
        assert secret not in wire                                                  # recipient, phone, address never reach the model

    fake.chat_calls.clear()
    fake.chat_script = [call("get_order_status", order_id=order["id"]), [{"text": "Không thấy đơn đó."}]]
    theirs = say(ai_client, LONG + f"cho mình xem đơn số {order['id']} với", headers=binh).json()
    assert theirs["orders"] == []
    answer = fake.chat_calls[1]["contents"][-1]["parts"][0]["functionResponse"]["response"]["result"]
    assert "error" in answer and "items" not in answer


def test_gemini_tools_need_login_and_survive_garbage(ai_client, fake):
    fake.chat_script = [
        [{"functionCall": {"name": "get_my_orders", "args": {}}},
         {"functionCall": {"name": "drop_all_tables", "args": {"x": 1}}},
         {"functionCall": {"name": "get_order_status", "args": {"order_id": "abc"}}},
         {"functionCall": {"name": "get_product_details", "args": "not-a-dict"}},
         {"functionCall": {"name": "search_products", "args": {"query": ""}}}],
        [{"text": "Bạn cần đăng nhập để xem đơn hàng."}]]
    r = say(ai_client, LONG + "các đơn của tôi đang thế nào")
    assert r.status_code == 200 and r.json()["orders"] == []
    results = [p["functionResponse"]["response"]["result"] for p in fake.chat_calls[1]["contents"][-1]["parts"]]
    assert len(results) == 5 and all("error" in x for x in results)             # every call answered, none crashed


def test_gemini_proposal_is_only_a_proposal(ai_client, fake, as_, db):
    h = as_(AN)
    order = place(ai_client, h)
    fake.chat_script = [call("propose_support_request", content="Tôi muốn đổi size áo của đơn này", order_id=order["id"]),
                        [{"text": "Mình đã soạn sẵn yêu cầu, bạn kiểm tra rồi bấm Gửi nhé."}]]
    body = say(ai_client, LONG + "soạn giúp mình yêu cầu đổi size cho áo vừa nhận", headers=h).json()
    assert body["actions"] == [{"type": "create_support_request", "content": "Tôi muốn đổi size áo của đơn này", "order_id": order["id"]}]
    with db.new_session() as s:
        assert s.scalar(text("SELECT COUNT(*) FROM support_request")) == 0
    fake.chat_script = [call("propose_support_request", content="đổi size", order_id=999), [{"text": "ok"}]]
    assert say(ai_client, LONG + "soạn giúp mình yêu cầu đổi size cho áo vừa nhận", headers=h).json()["actions"] == []        # unknown / foreign order id: no proposal


def test_gemini_thought_signatures_are_echoed_back(ai_client, fake):
    model_turn = [{"functionCall": {"name": "get_shop_policy", "args": {"topic": "shipping"}}, "thoughtSignature": "sig-123"}]
    fake.chat_script = [model_turn, [{"text": "internal", "thought": True}, {"text": "Phí ship 30.000đ, miễn phí từ 500.000đ."}]]
    body = say(ai_client, LONG + "phí vận chuyển đơn nhỏ là bao nhiêu").json()
    assert body["reply"] == "Phí ship 30.000đ, miễn phí từ 500.000đ."            # 'thought' parts are not shown
    assert fake.chat_calls[1]["contents"][-2] == {"role": "model", "parts": model_turn}


def test_history_is_sent_to_the_model(ai_client, fake):
    say(ai_client, "tôi cần giày", "Bạn thích màu gì?", "màu đen")
    contents = fake.chat_calls[0]["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"] and contents[2]["parts"][0]["text"] == "màu đen"


# ------------------------------------------------------------------ degradation (NFR-12)
def test_gemini_outage_falls_back_to_rules(ai_client, fake):
    fake.fail = True
    r = say(ai_client, LONG + "hôm nay có mã giảm giá nào không")
    assert r.status_code == 200 and r.json()["mode"] == "rules" and r.json()["degraded"] is True
    assert codes(r) == ["WELCOME10"]


def test_endless_tool_loop_is_cut_off(ai_client, fake):
    fake.chat_script = [call("list_active_promotions")] * 10
    r = say(ai_client, LONG + "khuyến mãi")
    assert r.json()["mode"] == "rules" and r.json()["degraded"] is True
    assert len(fake.chat_calls) == 4                                              # MAX_ROUNDS, not infinite


def test_slow_model_and_no_rule_match_says_so_instead_of_no_products(ai_client, fake):
    fake.fail = True
    r = say(ai_client, LONG + "quà sinh nhật cho bạn thích chạy bộ tầm một triệu").json()
    assert r["degraded"] is True and r["products"] == []
    assert "AI đang bận" in r["reply"] and "chưa tìm thấy sản phẩm" not in r["reply"]


def test_empty_model_answer_falls_back(ai_client, fake):
    fake.chat_script = [[{"text": "   "}]]
    body = say(ai_client, LONG + "phí ship").json()
    assert body["mode"] == "rules" and body["degraded"] is True


# ------------------------------------------------------------------ latency design: quick questions skip the model
def test_quick_questions_never_wait_for_the_model(ai_client, fake):
    fake.fail = True                                                  # even a dead model cannot slow or degrade them
    for q in ("Hôm nay có mã giảm giá nào?", "Phí vận chuyển thế nào?", "Chính sách đổi trả",
              "Hôm nay có sản phẩm nào giảm giá không?"):
        r = say(ai_client, q).json()
        assert r["mode"] == "rules" and r["degraded"] is False and r["reply"]
    assert fake.chat_calls == []                                      # no quota spent on FAQs


def test_open_ended_questions_use_the_model(ai_client, fake):
    fake.chat_script = [[{"text": "Mình gợi ý Laptop Pro 14."}]]
    r = say(ai_client, "tư vấn giúp mình một chiếc laptop để học lập trình").json()
    assert r["mode"] == "ai" and len(fake.chat_calls) == 1


def test_bare_order_number_after_a_question_is_a_quick_follow_up(ai_client, fake, as_):
    h = as_(AN)
    order = place(ai_client, h)
    r = say(ai_client, "Tôi muốn kiểm tra đơn hàng", "Bạn cho mình mã đơn nhé", str(order["id"]), headers=h).json()
    assert r["mode"] == "rules" and [o["id"] for o in r["orders"]] == [order["id"]] and fake.chat_calls == []


def test_model_calls_are_time_boxed(ai_client, fake):
    fake.chat_script = [[{"text": "ok"}]]
    say(ai_client, LONG + "tư vấn giúp mình chọn giày chạy bộ")
    assert 1.0 <= fake.chat_calls[0]["timeout"] <= config.CHAT_CALL_TIMEOUT


def test_overall_deadline_falls_back_to_rules(ai_client, fake, monkeypatch):
    monkeypatch.setattr(config, "CHAT_TIMEOUT", 0.0)                  # no time budget left before the first call
    r = say(ai_client, LONG + "hôm nay có mã giảm giá nào không").json()
    assert r["mode"] == "rules" and r["degraded"] is True and fake.chat_calls == []


# ------------------------------------------------------------------ Gemini client: model fallback policy of chat_turn
def test_chat_turn_does_not_retry_a_second_model_after_a_timeout():
    from unicart.business.extended.ai.gemini import AiUnavailable, GeminiClient
    client = GeminiClient("k", "primary", "secondary", "emb", 8)
    seen = []

    def fake_post(path, body, timeout):
        seen.append((path, timeout))
        raise AiUnavailable("timeout")
    client._post = fake_post
    with pytest.raises(AiUnavailable):
        client.chat_turn("sys", [{"role": "user", "parts": [{"text": "hi"}]}], [], timeout=20)
    assert len(seen) == 1 and seen[0][1] == 20                                    # one wait only, with the chat time limit


def test_chat_turn_tries_the_fallback_model_on_server_errors():
    from unicart.business.extended.ai.gemini import AiUnavailable, GeminiClient
    client = GeminiClient("k", "primary", "secondary", "emb", 8)
    models = []

    def fake_post(path, body, timeout):
        models.append(path.split("/")[-1].split(":")[0])
        if len(models) == 1:
            raise AiUnavailable("http 503")
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
    client._post = fake_post
    assert client.chat_turn("sys", [], []) == [{"text": "ok"}] and models == ["primary", "secondary"]
