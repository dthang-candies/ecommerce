"""AI search with a deterministic fake Gemini: index sync, hybrid ranking, filters, fallback, image & voice endpoints."""
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from conftest import ADMIN, AN, login
from fake_ai import FakeGemini
from unicart.business.extended.ai.runtime import AiRuntime
from unicart.presentation.extended import deps
from unicart.presentation.app import create_app

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"0" * 100


@pytest.fixture(autouse=True)
def _fresh_budgets():
    for b in (deps.text_budget, deps.image_budget, deps.voice_budget, deps.throttle):
        b.hits.clear() if hasattr(b, "hits") else b.fails.clear()


@pytest.fixture()
def fake():
    return FakeGemini()


@pytest.fixture()
def runtime(db, fake):
    rt = AiRuntime(db, fake)
    rt.sync()
    return rt


@pytest.fixture()
def ai_client(db, runtime):
    with TestClient(create_app(db, ai=runtime)) as c:
        yield c


def names(r):
    return [p["name"] for p in r.json()["items"]]


# ------------------------------------------------------------------ index
def test_sync_embeds_only_new_or_changed_products(db, fake):
    rt = AiRuntime(db, fake)
    assert rt.sync() == {"embedded": 6, "removed": 0, "indexed": 6}
    assert rt.sync()["embedded"] == 0                                   # nothing changed: no quota spent
    with db.new_session() as s:
        s.execute(text("UPDATE product SET description='Sach lap trinh sach' WHERE id=1"))
        s.execute(text("INSERT INTO product(id,category_id,sku,name,price) VALUES (7,1,'BK-9','Sach moi',1000)"))
        s.commit()
    assert rt.sync()["embedded"] == 2
    with db.new_session() as s:
        s.execute(text("DELETE FROM product WHERE id=7"))
        s.commit()
    assert rt.sync() == {"embedded": 0, "removed": 0, "indexed": 6}      # FK ON DELETE CASCADE already dropped it
    assert AiRuntime(db, fake).load() == 6                                # vectors persisted in MySQL survive a restart


def test_disabled_without_api_key(client):
    assert client.get("/api/search/status").json()["enabled"] is False
    r = client.get("/api/search?q=Clean")
    assert r.status_code == 200 and r.json()["mode"] == "keyword" and r.json()["degraded"] is False
    assert client.post("/api/search/image", content=JPEG).status_code == 503
    assert client.post("/api/search/voice", content=WAV).status_code == 503


# ------------------------------------------------------------------ text search
def test_semantic_search_ranks_by_meaning_and_reports_mode(ai_client):
    st = ai_client.get("/api/search/status").json()
    assert st == {"enabled": True, "ready": True, "indexed": 6, "model": "fake-embedding", "syncing": False}
    r = ai_client.get("/api/search?q=Smartphone")
    assert r.status_code == 200 and r.json()["mode"] == "ai" and names(r)[0] == "Smartphone X"
    assert r.json()["items"][0]["score"] > 0.5
    assert names(ai_client.get("/api/search?q=laptop"))[0] == "Laptop Pro 14"


def test_gibberish_finds_nothing(ai_client):
    r = ai_client.get("/api/search?q=zzqx+wvkp").json()
    assert r["total"] == 0 and r["mode"] == "ai"


def test_price_phrases_become_hard_filters(ai_client):
    r = ai_client.get("/api/search?q=laptop+dưới+1+triệu").json()
    assert r["total"] == 0 and r["interpreted"]["max_price"] == 1_000_000      # laptop costs 21.5M
    r = ai_client.get("/api/search?q=laptop+dưới+30+triệu").json()
    assert r["items"][0]["name"] == "Laptop Pro 14" and r["interpreted"]["text"] == "laptop"
    only_filter = ai_client.get("/api/search?q=dưới+400k").json()
    assert only_filter["mode"] == "filters" and {p["name"] for p in only_filter["items"]} == {"Clean Code", "Ao so mi nam"}
    explicit = ai_client.get("/api/search?q=laptop&max_price=100").json()
    assert explicit["total"] == 0                                              # explicit parameters override too


def test_brand_colour_and_sort(ai_client, session):
    session.execute(text("UPDATE product SET brand='Adidas' WHERE id=5"))
    session.commit()
    ai_client.post("/api/admin/ai/reindex", headers=login(ai_client, ADMIN))
    time.sleep(0.5)
    r = ai_client.get("/api/search?q=Adidas").json()
    assert r["interpreted"]["brands"] == ["Adidas"] and r["items"][0]["name"] == "Giay chay bo"
    c = ai_client.get("/api/search?q=Ao+so+mi+nam+màu+trắng").json()
    assert c["interpreted"]["colors"] == ["white"] and c["items"][0]["name"] == "Ao so mi nam"
    cheap = ai_client.get("/api/search?q=dưới+1+triệu&sort=price_desc").json()
    assert [p["price"] for p in cheap["items"]] == sorted((p["price"] for p in cheap["items"]), reverse=True)
    assert cheap["total"] == 3


def test_sold_out_products_are_ranked_lower_not_hidden(ai_client, runtime, session):
    # two products with identical text; the first one is sold out
    session.execute(text("UPDATE product SET name='Clean Code', brand='Prentice Hall', category_id=1, "
                         "description='Robert C. Martin', attributes=NULL WHERE id=6"))
    session.execute(text("UPDATE product SET attributes=NULL WHERE id=1"))
    session.execute(text("UPDATE inventory SET quantity=0 WHERE product_id=1"))
    session.commit()
    runtime.sync()
    r = ai_client.get("/api/search?q=Clean+Code").json()
    assert [(p["id"], p["in_stock"]) for p in r["items"]] == [(6, True), (1, False)]       # findable, but behind


def test_hidden_products_never_appear(ai_client, session):
    session.execute(text("UPDATE product SET status='HIDDEN' WHERE id=2"))
    session.commit()
    assert "Laptop Pro 14" not in names(ai_client.get("/api/search?q=laptop"))


def test_typo_is_auto_corrected_and_can_be_declined(ai_client):
    r = ai_client.get("/api/search?q=laptp").json()
    assert r["corrected"] == "Laptop" and r["original"] == "laptp" and r["items"][0]["name"] == "Laptop Pro 14"
    raw = ai_client.get("/api/search?q=laptp&autocorrect=false").json()
    assert raw["corrected"] is None and raw["total"] == 0 and raw["suggestion"] == "Laptop"


def test_accent_free_typing_is_not_treated_as_a_typo(ai_client):
    r = ai_client.get("/api/search?q=giay+chay+bo").json()
    assert r["corrected"] is None and r["items"][0]["name"] == "Giay chay bo"


def test_falls_back_to_keywords_when_gemini_is_down(ai_client, fake):
    fake.fail = True
    r = ai_client.get("/api/search?q=Clean").json()
    assert r["mode"] == "keyword" and r["degraded"] is True and r["items"][0]["name"] == "Clean Code"   # NFR-12
    fake.fail = False
    assert ai_client.get("/api/search?q=Smartphone").json()["mode"] == "ai"


def test_query_embeddings_are_cached(ai_client, fake):
    for _ in range(3):
        ai_client.get("/api/search?q=Smartphone")
    assert fake.query_calls == 1


def test_text_budget_degrades_instead_of_failing(ai_client):
    deps.text_budget.limit = 2
    try:
        modes = [ai_client.get("/api/search?q=Smartphone").json() for _ in range(4)]
    finally:
        deps.text_budget.limit = 60
    assert [m["mode"] for m in modes] == ["ai", "ai", "keyword", "keyword"] and modes[3]["degraded"] is False


# ------------------------------------------------------------------ image
def test_image_search_returns_what_gemini_recognised(ai_client, session):
    before = session.execute(text("SELECT COUNT(*) FROM interaction_log")).scalar()
    r = ai_client.post("/api/search/image", content=JPEG, headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 200
    j = r.json()
    assert j["recognized"] == {"query": "laptop màu bạc", "category": "laptop", "color": "bạc", "brand": ""}
    assert j["items"][0]["name"] == "Laptop Pro 14"
    session.rollback()
    assert session.execute(text("SELECT COUNT(*) FROM interaction_log")).scalar() == before       # nothing is stored
    assert ai_client.post("/api/search/image", content=PNG).status_code == 200


def test_image_too_specific_query_falls_back_to_the_category(ai_client, fake):
    from unicart.business.extended.ai.gemini import ImageUnderstanding
    fake.image = ImageUnderstanding(query="xqzv wkpt bìa đen", category="Laptop", color="", brand="")
    r = ai_client.post("/api/search/image", content=JPEG).json()
    assert r["items"] and r["items"][0]["name"] == "Laptop Pro 14"


def test_image_validation(ai_client, fake):
    assert ai_client.post("/api/search/image", content=b"not an image at all").status_code == 415
    assert ai_client.post("/api/search/image", content=b"").status_code == 400
    assert ai_client.post("/api/search/image", content=JPEG + b"0" * (4 * 1024 * 1024)).status_code == 413
    assert ai_client.post("/api/search/image", content=WAV).status_code == 415
    fake.reject_media = True
    assert ai_client.post("/api/search/image", content=JPEG).status_code == 400
    fake.reject_media = False
    fake.fail = True
    r = ai_client.post("/api/search/image", content=JPEG)
    assert r.status_code == 503 and r.json()["error"] == "AI_UNAVAILABLE"


def test_image_endpoint_is_rate_limited(ai_client):
    codes = [ai_client.post("/api/search/image", content=JPEG).status_code for _ in range(12)]
    assert codes[:10] == [200] * 10 and codes[10:] == [429, 429]


# ------------------------------------------------------------------ voice
def test_voice_returns_a_transcript(ai_client, fake):
    r = ai_client.post("/api/search/voice", content=WAV)
    assert r.status_code == 200 and r.json() == {"text": "laptop dưới 30 triệu", "language": "vi"}
    assert ai_client.post("/api/search/voice", content=JPEG).status_code == 415
    assert ai_client.post("/api/search/voice", content=WAV + b"0" * (3 * 1024 * 1024)).status_code == 413
    from unicart.business.extended.ai.gemini import Transcript
    fake.speech = Transcript(text="", language="vi")
    assert ai_client.post("/api/search/voice", content=WAV).status_code == 400          # nothing heard
    fake.fail = True
    assert ai_client.post("/api/search/voice", content=WAV).status_code == 503


# ------------------------------------------------------------------ admin keeps the index fresh
def test_creating_a_product_schedules_a_background_reindex(ai_client, fake):
    admin = login(ai_client, ADMIN)
    assert ai_client.post("/api/admin/ai/reindex", headers=login(ai_client, AN)).status_code == 403
    body = {"sku": "NEW-1", "name": "Tai nghe moi", "category_id": 2, "price": 100000, "quantity": 5}
    assert ai_client.post("/api/admin/products", json=body, headers=admin).status_code == 201
    for _ in range(40):
        if ai_client.get("/api/search/status").json()["indexed"] == 7:
            break
        time.sleep(0.1)
    assert ai_client.get("/api/search/status").json()["indexed"] == 7
    assert names(ai_client.get("/api/search?q=Tai+nghe+moi"))[0] == "Tai nghe moi"


def test_lexical_match_uses_whole_words_not_substrings():
    from types import SimpleNamespace
    from unicart.business.extended.search_service import SearchService
    p = SimpleNamespace(name="Điện thoại Galaxy", brand="Samsung", category=SimpleNamespace(name="Electronics"), sku="MB-002")
    lex = SearchService._lexical
    assert lex(["an"], p) == 0.0                 # 'an' is inside 'Samsung' / 'Galaxy' but is not a word of it
    assert lex(["dien", "thoai"], p) == 1.0
    assert lex(["samsung", "xyz"], p) == 0.5
    assert lex(["galaxyz"], p) == 0.0


def test_sync_waits_out_the_free_tier_quota_and_keeps_partial_progress(db, fake):
    waits = []
    rt = AiRuntime(db, fake)
    rt.sleep = waits.append
    fake.quota_failures = 2                                    # two 429s, then the quota window resets
    assert rt.sync()["indexed"] == 6 and waits == [25, 45]
    # quota never recovers: the error surfaces, but vectors saved before it are loaded and searchable
    fake.quota_failures = 99
    with db.new_session() as s:
        s.execute(text("INSERT INTO product(id,category_id,sku,name,price) VALUES (8,1,'BK-8','Sach tam',1000)"))
        s.commit()
    rt2 = AiRuntime(db, fake)
    rt2.sleep = lambda _: None
    import pytest as _pytest
    from unicart.business.extended.ai.gemini import AiUnavailable
    with _pytest.raises(AiUnavailable):
        rt2.sync()
    assert len(rt2.vectors()) == 6                              # the 6 vectors already in MySQL were loaded despite the failure
