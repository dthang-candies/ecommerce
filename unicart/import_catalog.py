"""Import data/catalog.json (built by tools/fetch_catalog.py) into MySQL. Idempotent and non-destructive:

    python -m unicart.import_catalog

New SKUs are inserted with stock; existing SKUs are never overwritten (only a missing image_url is filled in).
`--update-text` also refreshes name/description of the rows this import created (sku DJ-...), e.g. after correcting translations.
Also attaches photos to the original sample products (data/sample_images.json).
Product photos live in images/products/ and are served at /images/products/<file>."""
import json
from pathlib import Path

from sqlalchemy import select

from . import config
from .domain.models import Category, Inventory, Product, StockMovement
from .persistence.database import Database

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.json"
SAMPLE_IMAGES = ROOT / "data" / "sample_images.json"
# Stable ids for the categories this import creates (the front-end picks their icons by id).
NEW_CATEGORIES = {"Nội thất & trang trí": (8, "Đồ nội thất, trang trí nhà cửa"), "Thực phẩm & đồ uống": (9, "Thực phẩm, đồ uống, đồ khô"),
                  "Thể thao & dã ngoại": (10, "Dụng cụ thể thao, dã ngoại"), "Xe máy": (11, "Xe máy và phụ tùng")}
NO_WARRANTY = {"Thực phẩm & đồ uống", "Chăm sóc cá nhân"}      # the sample data gives groceries a "warranty": meaningless


def _category(s, name: str) -> Category:
    cat = s.scalars(select(Category).where(Category.name == name)).first()
    if cat is None:
        cid, desc = NEW_CATEGORIES.get(name, (None, None))
        cat = Category(name=name, description=desc)
        if cid and s.get(Category, cid) is None:
            cat.id = cid
        s.add(cat)
        s.flush()
    return cat


def import_catalog(db: Database | None = None, path: Path = CATALOG, images_root: Path = ROOT, update_text: bool = False) -> dict:
    db = db or Database()
    items = json.loads(path.read_text(encoding="utf-8"))
    added = updated = missing_images = retexted = 0
    with db.new_session() as s:
        categories: dict[str, Category] = {}
        for it in items:
            cat = categories.get(it["category"]) or categories.setdefault(it["category"], _category(s, it["category"]))
            image = "/" + it["image"] if (images_root / it["image"]).is_file() else None
            missing_images += image is None
            product = s.scalars(select(Product).where(Product.sku == it["sku"])).first()
            if product is not None:
                if product.image_url is None and image:
                    product.image_url, updated = image, updated + 1
                if update_text and it["source"] == "dummyjson.com" and (product.name, product.description) != (it["name"], it["description"]):
                    product.name, product.description, retexted = it["name"], it["description"], retexted + 1   # only rows this import created
                continue
            attrs = {k: v for k, v in it["attributes"].items() if not (k == "warranty" and it["category"] in NO_WARRANTY)}
            product = Product(sku=it["sku"], category_id=cat.id, name=it["name"], brand=it.get("brand"), description=it["description"],
                              price=it["price"], image_url=image, attributes=attrs or None, status="ACTIVE")
            s.add(product)
            s.flush()
            s.add(Inventory(product_id=product.id, quantity=it["stock"], min_threshold=5))
            if it["stock"]:
                s.add(StockMovement(product_id=product.id, type="IN", quantity=it["stock"], reason="IMPORT"))
            added += 1
        s.commit()
    return {"products_added": added, "images_attached_to_existing": updated, "missing_images": missing_images, "texts_updated": retexted, "in_file": len(items)}


def attach_sample_images(db: Database | None = None, path: Path = SAMPLE_IMAGES, images_root: Path = ROOT) -> dict:
    """Photos for the original sample products (built by tools/attach_sample_images.py). Only fills a missing image_url."""
    db = db or Database()
    mapping = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    attached = skipped = 0
    with db.new_session() as s:
        for sku, image in mapping.items():
            product = s.scalars(select(Product).where(Product.sku == sku)).first()
            if product is None or product.image_url is not None or not (images_root / image).is_file():
                skipped += 1
                continue
            product.image_url, attached = "/" + image, attached + 1
        s.commit()
    return {"sample_images_attached": attached, "skipped": skipped}


if __name__ == "__main__":
    import sys
    print(import_catalog(update_text="--update-text" in sys.argv))
    print(attach_sample_images())
    print("Restart the server (or POST /api/admin/ai/reindex) so the new products get AI search vectors.")
