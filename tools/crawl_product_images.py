"""Crawl real product photos from the internet to replace SVG placeholders and fill missing images.
Updates images/products/, MySQL database, data/sample_images.json, and data/catalog_extra.json.
"""
import json
import logging
import re
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from unicart.config import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("crawl_images")

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "images" / "products"
IMG_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_IMAGES_FILE = ROOT / "data" / "sample_images.json"
EXTRA_CATALOG_FILE = ROOT / "data" / "catalog_extra.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

client = httpx.Client(headers=HEADERS, timeout=15, follow_redirects=True)


def get_image_ext(content: bytes, content_type: str = "") -> str:
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"\x89PNG"):
        return ".png"
    if content.startswith(b"RIFF") and b"WEBP" in content[:16]:
        return ".webp"
    if "jpeg" in content_type.lower() or "jpg" in content_type.lower():
        return ".jpg"
    if "png" in content_type.lower():
        return ".png"
    if "webp" in content_type.lower():
        return ".webp"
    return ".jpg"


def search_openlibrary(isbn: str = "", title: str = "", author: str = "") -> str | None:
    # 1. Search by ISBN first if present
    if isbn:
        clean_isbn = re.sub(r"[^0-9X]", "", isbn.upper())
        if clean_isbn:
            test_url = f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg"
            try:
                r = client.get(test_url)
                # OpenLibrary returns a 1x1 blank gif or < 1000 bytes if not found
                if r.status_code == 200 and len(r.content) > 2000:
                    return test_url
            except Exception:
                pass

    # 2. Search by title / author
    query = f"{title} {author}".strip()
    if not query:
        return None
    try:
        url = "https://openlibrary.org/search.json"
        r = client.get(url, params={"q": query, "limit": 3})
        if r.status_code == 200:
            for doc in r.json().get("docs", []):
                cover_i = doc.get("cover_i")
                if cover_i:
                    cov_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
                    cr = client.get(cov_url)
                    if cr.status_code == 200 and len(cr.content) > 2000:
                        return cov_url
    except Exception as e:
        log.warning(f"OpenLibrary error for {query}: {e}")
    return None


def search_tiki(query: str) -> str | None:
    clean_q = re.sub(r"[\(\)\[\]]", " ", query).strip()
    try:
        r = client.get("https://tiki.vn/api/v2/products", params={"limit": 5, "q": clean_q})
        if r.status_code == 200:
            for item in r.json().get("data", []):
                thumb = item.get("thumbnail_url")
                if thumb and "http" in thumb:
                    # Upgrade to higher resolution
                    large = thumb.replace("/cache/280x280/", "/cache/750x750/").replace("/cache/w280/", "/cache/w750/")
                    return large
    except Exception as e:
        log.warning(f"Tiki error for {clean_q}: {e}")
    return None


def search_baidu(query: str) -> str | None:
    clean_q = re.sub(r"[\(\)\[\]]", " ", query).strip()
    try:
        r = client.get(
            "https://image.baidu.com/search/acjson",
            params={"tn": "resultjson_com", "ipn": "rj", "word": clean_q, "pn": 0, "rn": 5},
        )
        if r.status_code == 200:
            for item in r.json().get("data", []):
                u = item.get("thumbURL") or item.get("middleURL") or item.get("hoverURL")
                if u and u.startswith("http"):
                    return u
    except Exception as e:
        log.warning(f"Baidu error for {clean_q}: {e}")
    return None


def search_wikipedia(query: str, lang: str = "vi") -> str | None:
    try:
        r = client.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 2,
                "prop": "pageimages",
                "piprop": "thumbnail|original",
                "pithumbsize": 600,
                "format": "json",
            },
        )
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for _, p in pages.items():
                thumb = p.get("thumbnail", {}).get("source")
                orig = p.get("original", {}).get("source")
                img = thumb or orig
                if img and not img.endswith(".svg"):
                    return img
    except Exception as e:
        log.warning(f"Wikipedia error for {query}: {e}")
    return None


def find_image_url(sku: str, name: str, brand: str | None, category: str | None, isbn: str | None, author: str | None) -> str | None:
    # Build candidate queries
    is_book = category == "Books" or sku.startswith("BK-")
    
    if is_book:
        # Try OpenLibrary first
        url = search_openlibrary(isbn=isbn or "", title=name, author=author or "")
        if url:
            return url
        # Try Tiki with book title & author
        q = f"{name} {author or ''}".strip()
        url = search_tiki(q) or search_tiki(name)
        if url:
            return url
        # Try Vietnamese Wikipedia for classic books
        url = search_wikipedia(name, lang="vi")
        if url:
            return url
        # Fallback to Baidu
        return search_baidu(f"Sách {name}")

    # For non-book products
    # 1. Search Tiki with full name + brand
    q_full = f"{name} {brand or ''}".strip()
    url = search_tiki(q_full) or search_tiki(name)
    if url:
        return url

    # 2. Search Baidu
    url = search_baidu(q_full) or search_baidu(name)
    if url:
        return url

    # 3. Search Wikipedia
    url = search_wikipedia(q_full, lang="vi") or search_wikipedia(name, lang="en")
    return url


def download_image(url: str, dest_stem: str) -> tuple[Path, str] | None:
    try:
        r = client.get(url)
        if r.status_code == 200 and len(r.content) > 3000:
            ext = get_image_ext(r.content, r.headers.get("content-type", ""))
            dest_path = IMG_DIR / f"{dest_stem}{ext}"
            dest_path.write_bytes(r.content)
            return dest_path, ext
    except Exception as e:
        log.warning(f"Failed to download {url}: {e}")
    return None


def run_crawler():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = text("""
            SELECT p.id, p.sku, p.name, p.brand, c.name as category, 
                   b.isbn, b.author, p.image_url
            FROM product p
            LEFT JOIN category c ON p.category_id = c.id
            LEFT JOIN book b ON p.id = b.product_id
            WHERE p.image_url LIKE '%.svg' OR p.image_url IS NULL OR p.image_url = ''
            ORDER BY p.id
        """)
        products = conn.execute(query).fetchall()

    log.info(f"Found {len(products)} products that need real images.")

    # Load existing sample_images.json
    sample_images = {}
    if SAMPLE_IMAGES_FILE.exists():
        sample_images = json.loads(SAMPLE_IMAGES_FILE.read_text(encoding="utf-8"))

    # Load existing catalog_extra.json
    extra_catalog = []
    if EXTRA_CATALOG_FILE.exists():
        extra_catalog = json.loads(EXTRA_CATALOG_FILE.read_text(encoding="utf-8"))
    extra_by_sku = {item["sku"]: item for item in extra_catalog}

    success_count = 0
    failed_items = []

    db_updates = []

    for idx, p in enumerate(products, 1):
        pid, sku, name, brand, category, isbn, author, old_img = p
        dest_stem = f"old-{sku.lower()}" if not sku.startswith("DJ-") and (sku.startswith("BK-00") or sku in sample_images or old_img and "old-" in old_img or sku in ("EL-004", "EL-005", "CL-003", "CL-004", "CL-006", "SH-003", "HM-001", "HM-002", "HM-003", "PC-002", "PC-003", "AC-003")) else f"x-{sku.lower()}"

        log.info(f"[{idx}/{len(products)}] Finding image for {sku} ({category}): {name}...")

        img_url = find_image_url(sku, name, brand, category, isbn, author)
        downloaded = None
        if img_url:
            downloaded = download_image(img_url, dest_stem)

        if not downloaded:
            # Fallback search attempts
            log.info(f"  Retrying fallback for {sku}...")
            alt_query = name.replace("Laptop", "").replace("Điện thoại", "").replace("Máy tính bảng", "").replace("Tai nghe", "").replace("Giày", "").strip()
            img_url = search_tiki(alt_query) or search_baidu(alt_query) or search_baidu(f"{brand} {alt_query}")
            if img_url:
                downloaded = download_image(img_url, dest_stem)

        if downloaded:
            dest_path, ext = downloaded
            rel_path = f"images/products/{dest_path.name}"
            web_url = f"/{rel_path}"
            log.info(f"  -> SUCCESS: saved to {rel_path} ({dest_path.stat().st_size} bytes)")

            # Record DB update
            db_updates.append((web_url, sku))

            # Update sample_images if it was an old sample item
            if dest_stem.startswith("old-"):
                sample_images[sku] = rel_path

            # Update catalog_extra if it exists there
            if sku in extra_by_sku:
                extra_by_sku[sku]["image"] = rel_path

            success_count += 1
        else:
            log.error(f"  -> FAILED to find image for {sku}: {name}")
            failed_items.append((sku, name))

        time.sleep(0.3)  # Gentle rate limit

    log.info(f"Done crawling! Succeeded: {success_count}/{len(products)}. Failed: {len(failed_items)}")

    # Update MySQL Database
    if db_updates:
        log.info(f"Updating {len(db_updates)} products in MySQL database...")
        with engine.begin() as conn:
            for web_url, sku in db_updates:
                conn.execute(
                    text("UPDATE product SET image_url = :image_url WHERE sku = :sku"),
                    {"image_url": web_url, "sku": sku},
                )
        log.info("Database updated successfully!")

    # Save data/sample_images.json
    SAMPLE_IMAGES_FILE.write_text(
        json.dumps(dict(sorted(sample_images.items())), ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    log.info("Updated data/sample_images.json")

    # Save data/catalog_extra.json
    if extra_catalog:
        EXTRA_CATALOG_FILE.write_text(
            json.dumps(extra_catalog, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        log.info("Updated data/catalog_extra.json")


if __name__ == "__main__":
    run_crawler()

