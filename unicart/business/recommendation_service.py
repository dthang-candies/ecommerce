"""AI Phase 2 subset: Hybrid recommender (formula 3.2) with cold-start fallbacks, never showing hidden or
out-of-stock products (FR-24, FR-25). score(u,i) = alpha*CF + (1-alpha)*CB, alpha grows with the user's history."""
from collections import Counter, defaultdict
from dataclasses import dataclass

from ..domain.models import Product
from ..persistence.repositories import InteractionRepository, OrderRepository, ProductRepository

WEIGHT = {"VIEW": 1.0, "CLICK_REC": 1.0, "ADD_TO_CART": 3.0, "PURCHASE": 5.0}


@dataclass
class Recommendation:
    product: Product
    reason: str


def _norm(values: dict[int, float]) -> dict[int, float]:
    top = max(values.values(), default=0)
    return {k: v / top for k, v in values.items()} if top else {}


class RecommendationService:
    def __init__(self, session, products: ProductRepository, interactions: InteractionRepository,
                 orders: OrderRepository):
        self.session, self.products, self.interactions, self.orders = session, products, interactions, orders

    def _popularity(self) -> dict[int, float]:
        return _norm({pid: float(n) for pid, n in self.products.best_sellers(100)})

    def home(self, customer_id: int | None, personalize: bool = True, limit: int = 8,
             exclude: set[int] | None = None) -> list[Recommendation]:
        exclude = exclude or set()
        candidates = [p for p in self.products.candidates() if p.id not in exclude]
        popularity = self._popularity()
        history = self.interactions.recent_for_customer(customer_id) if (customer_id and personalize) else []
        by_id = {p.id: p for p in candidates}

        category_w, brand_w, seeds = defaultdict(float), defaultdict(float), Counter()
        for log in history:
            p = by_id.get(log.product_id) or self.products.get(log.product_id)
            if p is None:
                continue
            w = WEIGHT.get(log.event_type, 0.0)
            category_w[p.category_id] += w
            if p.brand:
                brand_w[p.brand] += w
            if log.event_type in ("PURCHASE", "ADD_TO_CART"):
                seeds[log.product_id] += 1
        top_c, top_b = max(category_w.values(), default=0), max(brand_w.values(), default=0)
        cf = _norm({pid: float(n) for pid, n in self.products.co_purchased(list(seeds))}) if seeds else {}
        alpha = min(0.8, len(history) / 25)                      # new customers: alpha ~ 0 (cold start)

        scored = []
        for i, p in enumerate(candidates):
            recency = 0.05 * (1 - i / max(len(candidates), 1))   # candidates are newest first
            if history:
                cb = ((category_w[p.category_id] / top_c if top_c else 0)
                      + 0.5 * (brand_w[p.brand] / top_b if top_b and p.brand else 0)) / 1.5
                score = alpha * cf.get(p.id, 0) + (1 - alpha) * cb + 0.15 * popularity.get(p.id, 0) + recency
                reason = "Dành cho bạn"
            else:
                score = popularity.get(p.id, 0) + recency
                reason = "Bán chạy" if popularity.get(p.id) else "Sản phẩm mới"
            scored.append((score, p, reason))
        scored.sort(key=lambda t: -t[0])
        return [Recommendation(p, r) for _, p, r in scored[:limit]]

    def for_product(self, product_id: int, limit: int = 8) -> dict[str, list[Recommendation]]:
        base = self.products.get(product_id)
        candidates = [p for p in self.products.candidates() if p.id != product_id]
        if base is None:
            return {"similar": [], "bought_together": []}
        scored = []
        for p in candidates:
            score = (1.0 if p.category_id == base.category_id else 0.0) + (0.5 if p.brand and p.brand == base.brand else 0.0)
            if base.price:
                score += 0.5 * max(0.0, 1 - abs(float(p.price - base.price)) / float(base.price))
            if p.category_id == base.category_id:
                scored.append((score, p))
        scored.sort(key=lambda t: -t[0])
        together = self.products.by_ids([pid for pid, _ in self.products.co_purchased([product_id], 6)])
        in_stock = {p.id for p in candidates}
        return {"similar": [Recommendation(p, "Sản phẩm tương tự") for _, p in scored[:limit]],
                "bought_together": [Recommendation(p, "Thường được mua cùng nhau") for p in together
                                    if p.id in in_stock][:4]}

    def for_cart(self, cart_product_ids: list[int], limit: int = 6) -> list[Recommendation]:
        if not cart_product_ids:
            return []
        in_cart = set(cart_product_ids)
        candidates = {p.id: p for p in self.products.candidates() if p.id not in in_cart}
        out: list[Recommendation] = []
        for pid, _ in self.products.co_purchased(cart_product_ids, 20):          # cross-selling
            if pid in candidates:
                out.append(Recommendation(candidates.pop(pid), "Mua kèm"))
        for cart_product in self.products.by_ids(cart_product_ids):                # up-selling
            better = [p for p in candidates.values()
                      if p.category_id == cart_product.category_id and cart_product.price < p.price <= cart_product.price * 2]
            better.sort(key=lambda p: p.price)
            if better:
                out.append(Recommendation(better[0], "Phiên bản cao cấp hơn"))
                candidates.pop(better[0].id)
        popularity = self._popularity()
        rest = sorted(candidates.values(), key=lambda p: -popularity.get(p.id, 0))
        out += [Recommendation(p, "Có thể bạn cần") for p in rest]
        return out[:limit]
