"""ProductController + recommendation/event endpoints: UC-02/03/04, UC-16/17 (public, Guest user allowed)."""
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from ...business.actor import Actor
from ..extended.deps import Soft, get_services, require_roles
from ..extended.schemas import EventIn
from ..serializers import category_json, product_json, recommendation_json, review_json
from ..wiring import Services

router = APIRouter(prefix="/api", tags=["catalog"])
Svc = Annotated[Services, Depends(get_services)]


def _customer_id(actor: Optional[Actor]) -> Optional[int]:
    return actor.account_id if actor and actor.role == "CUSTOMER" else None


@router.get("/categories")
def categories(svc: Svc):
    return [category_json(c, n) for c, n in svc.catalog.list_categories()]


@router.get("/products")
def search_products(svc: Svc, q: Optional[str] = Query(None, max_length=100), category_id: Optional[int] = None,
                    min_price: Optional[Decimal] = Query(None, ge=0), max_price: Optional[Decimal] = Query(None, ge=0),
                    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|name)$"),
                    page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100)):
    items, total = svc.products.search(q, category_id, min_price, max_price, sort, page, size)
    ratings = svc.products.rating_summary([p.id for p in items])
    suggestion = svc.products.suggest(q) if (q and total == 0) else None
    return {"total": total, "page": page, "size": size, "suggestion": suggestion,
            "items": [product_json(p, ratings.get(p.id, (0.0, 0))) for p in items]}


@router.get("/products/{product_id}")
def product_detail(product_id: int, svc: Svc):
    p = svc.products.get_detail(product_id)
    rating = svc.products.rating_summary([p.id]).get(p.id, (0.0, 0))
    return product_json(p, rating) | {"reviews": [review_json(r, who) for r, who in svc.products.reviews_of(p.id)]}


@router.post("/events", status_code=204)
def track_event(body: EventIn, svc: Svc, actor: Soft):
    """UC-16: the client reports views, searches and recommendation clicks/impressions (only if the user allows)."""
    svc.interactions.log(_customer_id(actor), body.event_type, body.product_id, body.keyword)


@router.get("/recommendations/home")
def recommend_home(svc: Svc, actor: Soft, personalize: bool = True, limit: int = Query(8, ge=1, le=24)):
    return [recommendation_json(r) for r in svc.recommendations.home(_customer_id(actor), personalize, limit)]


@router.get("/recommendations/product/{product_id}")
def recommend_for_product(product_id: int, svc: Svc):
    result = svc.recommendations.for_product(product_id)
    return {k: [recommendation_json(r) for r in v] for k, v in result.items()}


@router.get("/recommendations/cart")
def recommend_for_cart(svc: Svc, actor: Annotated[Actor, Depends(require_roles("CUSTOMER"))]):
    cart = svc.carts.view(actor.account_id)
    return [recommendation_json(r) for r in svc.recommendations.for_cart([i.product_id for i in cart.items])]
