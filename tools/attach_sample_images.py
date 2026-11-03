"""Photos for the original sample products (schema.sql / seed.py). Dev tool, run by hand:  python tools/attach_sample_images.py

- Products with a same-kind item in the DummyJSON sample API reuse a *different photo* of that item (images/products/old-<sku>.*).
  The photo may show another brand: it is a stand-in for a demo store, see docs/DATA_SOURCES.md.
- Books get a generated SVG cover (title, author, publisher) - no photo exists for them in the sample data.
- Products with no suitable image are left alone and keep the category icon.
Writes data/sample_images.json (sku -> image path); `python -m unicart.import_catalog` applies it to MySQL."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

ROOT = Path(__file__).resolve().parent.parent
IMG, OUT = ROOT / "images" / "products", ROOT / "data" / "sample_images.json"
UA = {"User-Agent": "unicart-student-project/1.0 (educational demo)"}

# sku -> (DummyJSON product id, index into its images[]) ; the item kind is what matters, not the brand
PHOTOS = {
    "LT-001": (82, 1), "LT-002": (79, 1), "MB-001": (128, 1), "MB-002": (133, 1), "OLD-001": (124, 1),
    "EL-003": (101, 1), "EL-006": (105, 1), "CL-001": (85, 1), "CL-002": (84, 1), "CL-005": (180, 1),
    "SH-001": (90, 1), "SH-002": (91, 1), "AC-001": (175, 1), "AC-002": (106, 1),
    "AC-004": (155, 1), "HM-004": (49, 1), "PC-001": (119, 1),
}
BOOKS = {  # sku -> (title, author, publisher, cover colour, accent)
    "BK-001": ("Clean Code", "Robert C. Martin", "Prentice Hall", "#1e3a5f", "#f2b705"),
    "BK-002": ("Database System Concepts", "Silberschatz, Korth, Sudarshan", "McGraw-Hill", "#7a1f2b", "#f4e3c1"),
    "BK-003": ("Đắc nhân tâm", "Dale Carnegie", "First News", "#2f6b4f", "#fff4d6"),
    "BK-004": ("Nhà giả kim", "Paulo Coelho", "Nhã Nam", "#b5651d", "#fff1d0"),
    "BK-005": ("Clean Architecture", "Robert C. Martin", "Pearson", "#2d2d3a", "#4fc3f7"),
}


def cover_svg(title: str, author: str, publisher: str, bg: str, accent: str) -> str:
    lines = textwrap.wrap(title, 14) or [title]
    size = 64 if len(lines) <= 2 else 52
    y0 = 300 - (len(lines) - 1) * size // 2
    tspans = "".join(f'<tspan x="300" y="{y0 + i * (size + 10)}">{escape(t)}</tspan>' for i, t in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" role="img" aria-label="{escape(title)}">
<rect width="600" height="800" fill="{bg}"/><rect x="0" y="0" width="36" height="800" fill="#00000033"/>
<rect x="90" y="120" width="420" height="6" fill="{accent}"/><rect x="90" y="470" width="420" height="6" fill="{accent}"/>
<text font-family="Georgia, 'Times New Roman', serif" font-weight="700" font-size="{size}" fill="#ffffff" text-anchor="middle">{tspans}</text>
<text x="300" y="540" font-family="Georgia, 'Times New Roman', serif" font-size="30" fill="{accent}" text-anchor="middle">{escape(author)}</text>
<text x="300" y="730" font-family="Helvetica, Arial, sans-serif" font-size="24" letter-spacing="4" fill="#ffffffcc" text-anchor="middle">{escape(publisher.upper())}</text>
</svg>
'''


def main() -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = json.loads(OUT.read_text()) if OUT.exists() else {}
    for sku, (pid, idx) in PHOTOS.items():
        if sku in mapping and (ROOT / mapping[sku]).is_file():
            continue
        data = httpx.get(f"https://dummyjson.com/products/{pid}", timeout=30, headers=UA).json()
        url = data["images"][idx if idx < len(data["images"]) else 0]
        r = httpx.get(url, timeout=30, headers=UA, follow_redirects=True)
        ext = Path(url.split("?")[0]).suffix.lower() or ".webp"
        ok = r.status_code == 200 and (r.content[8:12] == b"WEBP" or r.content[:3] == b"\xff\xd8\xff" or r.content[:4] == b"\x89PNG")
        if not ok:
            print("skip", sku, r.status_code)
            continue
        path = IMG / f"old-{sku.lower()}{ext}"
        path.write_bytes(r.content)
        mapping[sku] = f"images/products/{path.name}"
        print("photo", sku, "<-", data["title"])
    for sku, spec in BOOKS.items():
        path = IMG / f"old-{sku.lower()}.svg"
        path.write_text(cover_svg(*spec), encoding="utf-8")
        mapping[sku] = f"images/products/{path.name}"
    OUT.write_text(json.dumps(dict(sorted(mapping.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(mapping)} sample products now have an image")


if __name__ == "__main__":
    main()
