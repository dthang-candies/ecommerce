"""Build data/catalog.json + images/products/* from the public DummyJSON sample API (https://dummyjson.com).

DummyJSON is a free API made for testing and prototyping. Product names/descriptions are translated to Vietnamese
with Gemini, prices converted to VND, thumbnails downloaded into images/products/. Dev tool, run by hand:

    python tools/fetch_catalog.py            # resumes: already translated / downloaded items are kept

The result is committed data; the application never calls DummyJSON at run time (see docs/DATA_SOURCES.md)."""
from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from unicart import config  # noqa: E402  (loads .env)
from unicart.business.extended.ai.gemini import AiUnavailable, GeminiClient  # noqa: E402

API = "https://dummyjson.com/products?limit=0"
OUT, IMG = ROOT / "data" / "catalog.json", ROOT / "images" / "products"
UA = {"User-Agent": "unicart-student-project/1.0 (educational demo)"}
USD_TO_VND = 25_000

# DummyJSON category -> (our category name, description). 'vehicle' (cars) is skipped on purpose.
CATEGORY = {
    "smartphones": "Electronics", "tablets": "Electronics", "laptops": "Electronics", "mobile-accessories": "Electronics",
    "mens-shirts": "Clothes", "tops": "Clothes", "womens-dresses": "Clothes",
    "mens-shoes": "Shoes", "womens-shoes": "Shoes",
    "kitchen-accessories": "Gia dụng",
    "beauty": "Chăm sóc cá nhân", "skin-care": "Chăm sóc cá nhân", "fragrances": "Chăm sóc cá nhân",
    "womens-bags": "Phụ kiện", "womens-jewellery": "Phụ kiện", "sunglasses": "Phụ kiện", "mens-watches": "Phụ kiện", "womens-watches": "Phụ kiện",
    "furniture": "Nội thất & trang trí", "home-decoration": "Nội thất & trang trí",
    "groceries": "Thực phẩm & đồ uống",
    "sports-accessories": "Thể thao & dã ngoại",
    "motorcycle": "Xe máy",
}

# Hand corrections of names the model left in English or garbled (source id -> Vietnamese name); applied after translation.
FIXES = {
    7: "Nước hoa Chanel Coco Noir Eau de Parfum", 10: "Nước hoa Gucci Bloom Eau de Parfum", 12: "Ghế sofa Annibale Colombo",
    13: "Bàn đầu giường gỗ anh đào châu Phi", 15: "Tủ chậu rửa mặt bằng gỗ kèm gương", 120: "Sữa dưỡng thể và dưỡng da mặt Vaseline Men",
    16: "Táo tươi", 17: "Thịt bò bít tết", 18: "Thức ăn cho mèo", 19: "Thịt gà tươi", 20: "Dầu ăn", 21: "Dưa chuột",
    22: "Thức ăn cho chó", 23: "Trứng gà", 24: "Phi-lê cá", 25: "Ớt chuông xanh", 26: "Ớt xanh cay", 27: "Mật ong nguyên chất",
    28: "Kem lạnh", 29: "Nước ép trái cây", 30: "Kiwi tươi",
}

_SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "id": {"type": "INTEGER"}, "name": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": ["id", "name", "description"]}}


def vnd(usd: float) -> int:
    v = usd * USD_TO_VND
    step = 10_000 if v >= 1_000_000 else 1_000
    return max(5_000, int(round(v / step) * step))


def vi_attributes(p: dict) -> dict:
    out = {}
    w = p.get("warrantyInformation") or ""
    if m := re.match(r"(\d+) (week|month|year)s? warranty", w, re.I):
        out["warranty"] = f"{m.group(1)} {dict(week='tuần', month='tháng', year='năm')[m.group(2).lower()]}"
    elif "lifetime" in w.lower():
        out["warranty"] = "Trọn đời"
    elif "no warranty" in w.lower():
        out["warranty"] = "Không bảo hành"
    if m := re.search(r"Ships in (.+?) business days", p.get("shippingInformation") or "", re.I):
        out["shipping"] = f"Giao trong {m.group(1)} ngày làm việc"
    r = p.get("returnPolicy") or ""
    if m := re.match(r"(\d+) days return policy", r, re.I):
        out["return_policy"] = f"Đổi trả trong {m.group(1)} ngày"
    elif "no return" in r.lower():
        out["return_policy"] = "Không đổi trả"
    return out


def translate(gemini: GeminiClient, batch: list[dict]) -> dict[int, dict]:
    prompt = ("Dịch tên và mô tả các sản phẩm sau sang tiếng Việt tự nhiên, ngắn gọn, đúng giọng một sàn thương mại điện tử. "
              "Giữ nguyên tên thương hiệu và mã model. name: tối đa 80 ký tự. description: 1-2 câu. Trả mảng JSON cùng id.\n"
              + json.dumps([{"id": p["id"], "title": p["title"], "description": p["description"], "category": p["category"]} for p in batch],
                           ensure_ascii=False))
    for attempt in range(3):
        try:
            rows = gemini.generate_json([{"text": prompt}], _SCHEMA)
            return {int(r["id"]): r for r in rows}
        except (AiUnavailable, KeyError, TypeError, ValueError) as e:
            print(f"  translate retry {attempt + 1}: {e}")
            time.sleep(3)
    return {}


def download(item: dict) -> bool:
    target = ROOT / item["image"]
    if target.exists() and target.stat().st_size > 500:
        return True
    try:
        r = httpx.get(item["_thumb"], timeout=30, headers=UA, follow_redirects=True)
    except httpx.HTTPError:
        return False
    ok = r.status_code == 200 and (r.content[:4] == b"RIFF" and r.content[8:12] == b"WEBP" or r.content[:3] == b"\xff\xd8\xff"
                                   or r.content[:8] == b"\x89PNG\r\n\x1a\n")
    if ok:
        target.write_bytes(r.content)
    return ok


def main() -> None:
    gemini = GeminiClient(config.GEMINI_API_KEY, config.GEMINI_TEXT_MODEL, config.GEMINI_FALLBACK_MODEL, config.GEMINI_EMBED_MODEL,
                          config.GEMINI_EMBED_DIM) if config.GEMINI_API_KEY else None
    if gemini is None:
        sys.exit("GEMINI_API_KEY is required to translate the catalogue to Vietnamese")
    products = [p for p in httpx.get(API, timeout=30, headers=UA).json()["products"] if p["category"] in CATEGORY]
    done = {x["source_id"]: x for x in json.loads(OUT.read_text(encoding="utf-8"))} if OUT.exists() else {}
    todo = [p for p in products if p["id"] not in done or not done[p["id"]].get("translated")]
    print(f"{len(products)} products, {len(todo)} to translate")
    IMG.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(todo), 15):
        batch = todo[i:i + 15]
        vi = translate(gemini, batch)
        for p in batch:
            t = vi.get(p["id"])
            ext = Path(p["thumbnail"].split("?")[0]).suffix or ".webp"
            done[p["id"]] = {
                "source_id": p["id"], "sku": f"DJ-{p['id']:03d}", "category": CATEGORY[p["category"]],
                "name": (t["name"] if t else p["title"]).strip()[:200], "description": (t["description"] if t else p["description"]).strip(),
                "brand": (p.get("brand") or "").strip()[:80] or None, "price": vnd(p["price"]), "stock": int(p.get("stock") or 0),
                "image": f"images/products/dj-{p['id']:03d}{ext}", "attributes": vi_attributes(p),
                "translated": bool(t), "source": "dummyjson.com", "_thumb": p["thumbnail"],
            }
        OUT.write_text(json.dumps(sorted(done.values(), key=lambda x: x["source_id"]), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  translated {min(i + 15, len(todo))}/{len(todo)}")
    for sid, name in FIXES.items():
        if sid in done:
            done[sid]["name"] = name
    items = sorted(done.values(), key=lambda x: x["source_id"])
    with ThreadPoolExecutor(6) as pool:
        ok = list(pool.map(download, items))
    for it, good in zip(items, ok):
        it["image_ok"] = good
    final = [{k: v for k, v in it.items() if k not in ("_thumb", "image_ok")} for it in items if it["image_ok"]]
    OUT.write_text(json.dumps(final, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"images ok {sum(ok)}/{len(items)}; catalog.json has {len(final)} products "
          f"({sum(1 for x in final if x['translated'])} translated)")


if __name__ == "__main__":
    main()
