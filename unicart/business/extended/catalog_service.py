import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from ...domain.enums import MovementType, ProductStatus
from ...domain.models import Book, Category, Electronics, Fashion, Furniture, Inventory, Product
from ...persistence.repositories import CategoryRepository, InventoryRepository, ProductRepository
from ..exceptions import BusinessError, Conflict, NotFound
from ..transaction import transactional

audit = logging.getLogger("unicart.audit")


def _price(value) -> Decimal:
    try:
        price = Decimal(str(value))
    except InvalidOperation:
        raise BusinessError("Giá không hợp lệ")
    if price < 0 or price > Decimal("999999999.99"):
        raise BusinessError("Giá phải từ 0 đến 999.999.999")
    return price


# Product specialisation: category name -> subtype table, and for each column the attribute keys that feed it.
_SUBTYPES = {
    "Books": Book, "Electronics": Electronics, "Clothes": Fashion, "Shoes": Fashion, "Nội thất & trang trí": Furniture,
}
_STR, _INT, _BOOL = "str", "int", "bool"
_FIELDS = {
    Book: {"isbn": (_STR, "isbn"), "author": (_STR, "author"), "publisher": (_STR, "publisher"),
           "page_count": (_INT, "page_count", "pageCount"), "language": (_STR, "language")},
    Electronics: {"model_number": (_STR, "model_number", "modelNumber"),
                  "warranty_months": (_INT, "warranty_months", "warrantyMonths")},
    Fashion: {"size": (_STR, "size", "shoesSize"), "color": (_STR, "color"), "material": (_STR, "material")},
    Furniture: {"material": (_STR, "material"), "width_cm": (_INT, "width_cm", "widthCm"),
                "depth_cm": (_INT, "depth_cm", "depthCm"), "height_cm": (_INT, "height_cm", "heightCm"),
                "weight_kg": (_INT, "weight_kg", "weightKg"),
                "assembly_required": (_BOOL, "assembly_required", "assemblyRequired")},
}


def _warranty_months(text) -> Optional[int]:
    """'6 tháng' -> 6, '2 năm' -> 24, 'Không bảo hành' -> 0; anything else (e.g. 'Trọn đời') is unknown."""
    text = str(text or "").strip().lower()
    m = re.fullmatch(r"(\d+)\s*(tháng|năm)", text)
    if m:
        return int(m.group(1)) * (12 if m.group(2) == "năm" else 1)
    return 0 if text == "không bảo hành" else None


def _convert(kind: str, key: str, value):
    if kind == _STR:
        if isinstance(value, (dict, list)):
            raise BusinessError(f"Thuộc tính '{key}' phải là chuỗi hoặc số")
        return str(value).strip()[:255] or None
    if kind == _BOOL:
        if isinstance(value, bool):
            return value
        folded = str(value).strip().lower()
        if folded in ("true", "1", "yes", "có"):
            return True
        if folded in ("false", "0", "no", "không"):
            return False
        raise BusinessError(f"Thuộc tính '{key}' phải là true hoặc false")
    try:
        if isinstance(value, bool):
            raise ValueError
        number = Decimal(str(value).strip())
        if number != number.to_integral_value() or not 0 <= number <= 2147483647:
            raise ValueError
        return int(number)
    except (InvalidOperation, ValueError):
        raise BusinessError(f"Thuộc tính '{key}' phải là số nguyên không âm")


def sync_subtype(session, p: Product) -> None:
    """Keeps the product's subtype row (book / electronics / fashion / furniture) in step with its category, brand and
    attributes. A column keeps its value when the attributes do not mention it. Every code path that creates or edits
    a product calls this (administration, seed, catalogue import)."""
    category = session.get(Category, p.category_id)
    model = _SUBTYPES.get(category.name) if category else None
    for other in set(_SUBTYPES.values()) - {model}:        # the category changed: drop the stale subtype row
        stale = session.get(other, p.id)
        if stale is not None:
            session.delete(stale)
    if model is None:
        return
    row = session.get(model, p.id)
    if row is None:
        row = model(product_id=p.id)
        session.add(row)
    attrs = p.attributes or {}
    for column, (kind, *keys) in _FIELDS[model].items():
        key = next((k for k in keys if attrs.get(k) not in (None, "")), None)
        if key is not None:
            setattr(row, column, _convert(kind, key, attrs[key]))
    if model is Book and attrs.get("publisher") in (None, ""):
        row.publisher = p.brand or row.publisher           # books keep the publisher in product.brand
    if model is Electronics:
        row.brand = p.brand
        if all(attrs.get(k) in (None, "") for k in ("warranty_months", "warrantyMonths")):
            months = _warranty_months(attrs.get("warranty"))
            if months is not None:
                row.warranty_months = months
    session.flush()


class CatalogService:
    """UC-10 Manage Product and Category (FR-13, BR-01): data is validated centrally (P1)."""

    def __init__(self, session, products: ProductRepository, categories: CategoryRepository,
                 inventory: InventoryRepository):
        self.session, self.products, self.categories, self.inventory = session, products, categories, inventory

    # ---- categories
    def list_categories(self):
        return self.categories.list_with_counts()

    @transactional
    def create_category(self, name: str, description: Optional[str], admin_id: int) -> Category:
        name = name.strip()
        if not name:
            raise BusinessError("Tên danh mục là bắt buộc")
        if self.categories.by_name(name):
            raise Conflict("Danh mục đã tồn tại")
        c = self.categories.add(Category(name=name, description=(description or "").strip() or None))
        audit.info("admin=%s created category id=%s", admin_id, c.id)
        return c

    @transactional
    def update_category(self, category_id: int, name: str, description: Optional[str], admin_id: int) -> Category:
        c = self.categories.get(category_id)
        if c is None:
            raise NotFound("Danh mục không tồn tại")
        name = name.strip()
        other = self.categories.by_name(name)
        if not name or (other and other.id != c.id):
            raise Conflict("Tên danh mục trống hoặc đã tồn tại")
        c.name, c.description = name, (description or "").strip() or None
        audit.info("admin=%s updated category id=%s", admin_id, c.id)
        return c

    @transactional
    def delete_category(self, category_id: int, admin_id: int) -> None:
        c = self.categories.get(category_id)
        if c is None:
            raise NotFound("Danh mục không tồn tại")
        if self.categories.product_count(category_id):
            raise Conflict("Danh mục còn sản phẩm; hãy chuyển hoặc ẩn sản phẩm trước")   # BR-01
        self.categories.delete(c)
        audit.info("admin=%s deleted category id=%s", admin_id, category_id)

    # ---- products
    def admin_search(self, keyword, category_id, status, page, size):
        return self.products.search(keyword, category_id, None, None, "newest", page, min(size, 100), status=status)

    def _check(self, name, brand, category_id, attributes) -> None:
        if not name.strip():
            raise BusinessError("Tên sản phẩm là bắt buộc")
        if self.categories.get(category_id) is None:
            raise BusinessError("Danh mục không tồn tại")
        if attributes is not None and not isinstance(attributes, dict):
            raise BusinessError("Thuộc tính phải là một đối tượng JSON")

    def _sync_subtype(self, p: Product) -> None:
        sync_subtype(self.session, p)

    @transactional
    def create_product(self, sku: str, name: str, category_id: int, price, brand, description, image_url,
                       attributes, quantity: int, min_threshold: int, admin_id: int) -> Product:
        sku = sku.strip()
        if not sku:
            raise BusinessError("SKU là bắt buộc")
        self._check(name, brand, category_id, attributes)
        if self.products.by_sku(sku):
            raise Conflict("SKU đã tồn tại")
        if quantity < 0 or min_threshold < 0:
            raise BusinessError("Số lượng không được âm")
        p = self.products.add(Product(
            sku=sku, name=name.strip(), category_id=category_id, price=_price(price),
            brand=(brand or "").strip() or None, description=(description or "").strip() or None,
            image_url=(image_url or "").strip() or None, attributes=attributes, status=ProductStatus.ACTIVE.value))
        self.session.add(Inventory(product_id=p.id, quantity=quantity, min_threshold=min_threshold))
        self.session.flush()
        self._sync_subtype(p)
        if quantity:
            self.inventory.log(p.id, MovementType.IN.value, quantity, f"INITIAL by {admin_id}", None)
        self.session.refresh(p)
        audit.info("admin=%s created product id=%s sku=%s", admin_id, p.id, sku)
        return p

    @transactional
    def update_product(self, product_id: int, name: str, category_id: int, price, brand, description,
                       image_url, attributes, admin_id: int) -> Product:
        p = self.products.get(product_id)
        if p is None:
            raise NotFound("Sản phẩm không tồn tại")
        self._check(name, brand, category_id, attributes)
        p.name, p.category_id, p.price = name.strip(), category_id, _price(price)
        p.brand = (brand or "").strip() or None
        p.description = (description or "").strip() or None
        p.image_url = (image_url or "").strip() or None
        p.attributes = attributes
        self.session.flush()
        self._sync_subtype(p)
        self.session.refresh(p)
        audit.info("admin=%s updated product id=%s", admin_id, product_id)
        return p

    @transactional
    def set_visibility(self, product_id: int, visible: bool, admin_id: int) -> Product:
        p = self.products.get(product_id)
        if p is None:
            raise NotFound("Sản phẩm không tồn tại")
        p.activate() if visible else p.hide()
        audit.info("admin=%s set product=%s %s", admin_id, product_id, p.status)
        return p

    @transactional
    def delete_product(self, product_id: int, admin_id: int) -> str:
        """Returns 'DELETED' or 'HIDDEN': a product that was ordered is hidden, never deleted (BR-01)."""
        p = self.products.get(product_id)
        if p is None:
            raise NotFound("Sản phẩm không tồn tại")
        if self.products.has_orders(product_id) or self.inventory.movements(product_id, 1):
            p.hide()
            audit.info("admin=%s hid product=%s (has history)", admin_id, product_id)
            return "HIDDEN"
        self.products.delete(p)
        audit.info("admin=%s deleted product=%s", admin_id, product_id)
        return "DELETED"
