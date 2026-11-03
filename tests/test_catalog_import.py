"""Catalogue import (data/catalog.json -> MySQL) and the product photos in images/products/."""
import json
from pathlib import Path

from sqlalchemy import text

from unicart.import_catalog import attach_sample_images, import_catalog

ROOT = Path(__file__).resolve().parent.parent
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"0" * 600


def write_catalog(tmp_path, items):
    (tmp_path / "images" / "products").mkdir(parents=True)
    for it in items:
        if it.pop("_has_image", True):
            (tmp_path / it["image"]).write_bytes(WEBP)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


def item(n, category="Thể thao & dã ngoại", **kw):
    return {"sku": f"T-{n}", "category": category, "name": f"Sản phẩm {n}", "description": "Mô tả", "brand": None, "price": 100000 + n,
            "stock": 7, "source": "test", "image": f"images/products/t-{n}.webp", "attributes": {"warranty": "1 năm", "return_policy": "Đổi trả trong 7 ngày"}, **kw}


def test_import_is_idempotent_and_never_overwrites(db, session, tmp_path):
    path = write_catalog(tmp_path, [item(1), item(2, _has_image=False), item(3, "Thực phẩm & đồ uống"), item(4, "Electronics", stock=0)])
    r = import_catalog(db, path, tmp_path)
    assert r == {"products_added": 4, "images_attached_to_existing": 0, "missing_images": 1, "texts_updated": 0, "in_file": 4}
    session.rollback()
    rows = {r[0]: r for r in session.execute(text("SELECT sku, image_url, quantity, c.name FROM product p JOIN inventory i ON i.product_id=p.id "
                                                    "JOIN category c ON c.id=p.category_id WHERE sku LIKE 'T-%'"))}
    assert rows["T-1"][1] == "/images/products/t-1.webp" and rows["T-1"][2] == 7
    assert rows["T-2"][1] is None                                          # no photo on disk -> no broken link
    assert rows["T-4"][2] == 0 and rows["T-4"][3] == "Electronics"         # existing category reused
    assert session.execute(text("SELECT id FROM category WHERE name='Thể thao & dã ngoại'")).scalar() == 10   # stable id for the UI icon
    assert session.execute(text("SELECT COUNT(*) FROM stock_movement WHERE reason='IMPORT'")).scalar() == 3    # stock 0 has no movement
    assert session.execute(text("SELECT attributes FROM product WHERE sku='T-3'")).scalar() == '{"return_policy": "Đổi trả trong 7 ngày"}'  # no warranty on food
    # run again: nothing new, an edited product stays as the admin left it, a missing photo can be filled in later
    session.execute(text("UPDATE product SET name='Tên do admin sửa' WHERE sku='T-1'"))
    session.commit()
    (tmp_path / "images/products/t-2.webp").write_bytes(WEBP)
    again = import_catalog(db, path, tmp_path)
    assert again["products_added"] == 0 and again["images_attached_to_existing"] == 1
    session.rollback()
    assert session.execute(text("SELECT name FROM product WHERE sku='T-1'")).scalar() == "Tên do admin sửa"
    assert session.execute(text("SELECT COUNT(*) FROM product WHERE sku LIKE 'T-%'")).scalar() == 4


def test_shipped_catalog_file_is_consistent():
    items = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    assert len(items) >= 150
    assert len({i["sku"] for i in items}) == len(items)
    assert len({i["name"] for i in items}) == len(items)
    for i in items:
        assert 0 < len(i["name"]) <= 200 and i["description"] and i["price"] >= 1000 and i["stock"] >= 0
        head = (ROOT / i["image"]).read_bytes()[:12]
        assert head[:4] == b"RIFF" and head[8:12] == b"WEBP" or head[:3] == b"\xff\xd8\xff" or head[:4] == b"\x89PNG", i["image"]
    assert len({i["category"] for i in items}) >= 8                         # diverse on purpose
    food = [i["name"] for i in items if i["category"] == "Thực phẩm & đồ uống"]
    assert food and all(any(ord(c) > 127 for c in n) for n in food), [n for n in food if n.isascii()]   # no untranslated English names


def test_images_are_served_and_cannot_escape_the_folder(client):
    r = client.get("/images/products/dj-001.webp")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp" and r.content[8:12] == b"WEBP"
    assert client.get("/images/products/nope.webp").status_code == 404
    for url in ("/images/../.env", "/images/%2e%2e/.env", "/images/..%2f.env", "/images/products/../../.env", "/.env"):
        r = client.get(url)
        assert b"DATABASE_URL" not in r.content and b"PASSWORD" not in r.content, url      # never the secrets file
    assert client.get("/images/%2e%2e/.env").status_code in (400, 404)                    # the static mount itself refuses


def test_update_text_only_touches_rows_created_by_the_import(db, session, tmp_path):
    items = [item(1, source="dummyjson.com"), item(2, source="dummyjson.com")]
    path = write_catalog(tmp_path, items)
    import_catalog(db, path, tmp_path)
    session.execute(text("INSERT INTO product(category_id,sku,name,price) VALUES (1,'MANUAL-1','Tên admin tự đặt',1000)"))
    session.commit()
    fixed = json.loads(path.read_text(encoding="utf-8"))
    fixed[0]["name"] = "Tên đã sửa"
    path.write_text(json.dumps(fixed), encoding="utf-8")
    assert import_catalog(db, path, tmp_path)["texts_updated"] == 0                      # off by default
    assert import_catalog(db, path, tmp_path, update_text=True)["texts_updated"] == 1
    session.rollback()
    assert session.execute(text("SELECT name FROM product WHERE sku='T-1'")).scalar() == "Tên đã sửa"
    assert session.execute(text("SELECT name FROM product WHERE sku='MANUAL-1'")).scalar() == "Tên admin tự đặt"


def test_shipped_sample_images_exist_and_are_valid():
    mapping = json.loads((ROOT / "data" / "sample_images.json").read_text(encoding="utf-8"))
    assert len(mapping) >= 20
    for sku, image in mapping.items():
        head = (ROOT / image).read_bytes()[:12]
        assert head[:4] == b"RIFF" or head[:3] == b"\xff\xd8\xff" or head[:4] == b"\x89PNG" or head.lstrip()[:4] in (b"<svg", b"<?xm"), (sku, image)
    assert {"BK-001", "LT-001", "MB-002"} <= set(mapping)
    svg = (ROOT / mapping["BK-003"]).read_text(encoding="utf-8")
    assert "Đắc nhân tâm" in svg and "<script" not in svg and "onload" not in svg       # a book cover can never run code


def test_attach_sample_images_only_fills_missing(db, session, tmp_path):
    (tmp_path / "images" / "products").mkdir(parents=True)
    (tmp_path / "images/products/a.webp").write_bytes(WEBP)
    (tmp_path / "images/products/b.webp").write_bytes(WEBP)
    session.execute(text("UPDATE product SET image_url='/images/custom/mine.jpg' WHERE sku='LT-001'"))     # admin already set one
    session.commit()
    mapping = tmp_path / "m.json"
    mapping.write_text(json.dumps({"BK-001": "images/products/a.webp", "LT-001": "images/products/b.webp",
                                   "MB-001": "images/products/missing.webp", "NOPE-1": "images/products/a.webp"}))
    assert attach_sample_images(db, mapping, tmp_path) == {"sample_images_attached": 1, "skipped": 3}
    session.rollback()
    urls = dict(session.execute(text("SELECT sku, image_url FROM product WHERE sku IN ('BK-001','LT-001','MB-001')")).all())
    assert urls == {"BK-001": "/images/products/a.webp", "LT-001": "/images/custom/mine.jpg", "MB-001": None}
