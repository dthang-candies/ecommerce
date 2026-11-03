import difflib
import unicodedata

from ..domain.models import Product
from ..persistence.repositories import ProductRepository, ReviewRepository
from .exceptions import NotFound


def fold(text: str) -> str:
    """Lower-case and strip Vietnamese diacritics: 'Áo khoác' -> 'ao khoac'."""
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()


class ProductService:
    """UC-02/03/04 Browse, search, view detail (BR-01: only ACTIVE products are visible; FR-20 spelling help)."""

    def __init__(self, session, products: ProductRepository, reviews: ReviewRepository | None = None):
        self.session, self.products, self.reviews = session, products, reviews

    def search(self, keyword=None, category_id=None, min_price=None, max_price=None,
               sort="newest", page=1, size=20) -> tuple[list[Product], int]:
        keyword = (keyword or "").strip() or None
        return self.products.search(keyword, category_id, min_price, max_price, sort,
                                    max(page or 1, 1), max(1, min(size or 20, 100)))

    def suggest(self, keyword: str) -> str | None:
        """'Did you mean': closest product name/brand/word when a query finds nothing (typo tolerance)."""
        key = fold(keyword.strip())
        if not key:
            return None
        terms = self.products.searchable_terms()
        folded = {fold(t): t for t in terms}
        for word in {w for t in terms for w in t.split()}:
            folded.setdefault(fold(word), word)
        match = difflib.get_close_matches(key, list(folded), n=1, cutoff=0.6)
        if match:
            return folded[match[0]]
        words = [difflib.get_close_matches(w, list(folded), n=1, cutoff=0.7) for w in key.split()]
        if words and all(words):
            return " ".join(folded[w[0]] for w in words)
        return None

    def get_detail(self, product_id: int) -> Product:
        p = self.products.get(product_id)
        if p is None or not p.is_visible():
            raise NotFound("Sản phẩm không tồn tại")
        return p

    def rating_summary(self, product_ids: list[int]) -> dict[int, tuple[float, int]]:
        return self.reviews.summary(product_ids) if self.reviews else {}

    def reviews_of(self, product_id: int):
        return self.reviews.for_product(product_id) if self.reviews else []
