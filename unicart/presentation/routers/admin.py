"""Administration controllers: UC-10 products & categories, UC-11 promotions, UC-24 accounts and roles."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, Response

from ...business.actor import Actor
from ..extended.deps import get_services, require_roles
from ..extended.schemas import (
    CategoryIn, LockIn, ProductIn, ProductUpdateIn, PromotionIn, RoleIn, StaffAccountIn, VisibilityIn,
)
from ..serializers import account_json, category_json, product_json, promotion_json
from ..wiring import Services

router = APIRouter(prefix="/api/admin", tags=["admin"])
Svc = Annotated[Services, Depends(get_services)]
Admin = Annotated[Actor, Depends(require_roles("ADMIN"))]
PromoViewer = Annotated[Actor, Depends(require_roles("ADMIN", "MARKETING", "MANAGER"))]


# ---- UC-10 categories and products
@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, svc: Svc, admin: Admin):
    return category_json(svc.catalog.create_category(body.name, body.description, admin.account_id))


@router.put("/categories/{category_id}")
def update_category(category_id: int, body: CategoryIn, svc: Svc, admin: Admin):
    return category_json(svc.catalog.update_category(category_id, body.name, body.description, admin.account_id))


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, svc: Svc, admin: Admin):
    svc.catalog.delete_category(category_id, admin.account_id)
    return Response(status_code=204)


@router.get("/products")
def admin_products(svc: Svc, _: Admin, q: Optional[str] = Query(None, max_length=100), category_id: Optional[int] = None,
                   status: Optional[str] = Query(None, pattern="^(ACTIVE|HIDDEN)$"),
                   page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
    items, total = svc.catalog.admin_search(q, category_id, status, page, size)
    return {"total": total, "page": page, "size": size, "items": [product_json(p, admin=True) for p in items]}


def _reindex(request: Request) -> None:
    """Product text changed: refresh its AI vector in the background (only changed products are re-embedded)."""
    ai = getattr(request.app.state, "ai", None)
    if ai is not None:
        ai.schedule_sync()


@router.post("/ai/reindex", status_code=202)
def reindex(request: Request, _: Admin):
    _reindex(request)
    return {"scheduled": True}


@router.post("/products", status_code=201)
def create_product(request: Request, body: ProductIn, svc: Svc, admin: Admin):
    p = svc.catalog.create_product(body.sku, body.name, body.category_id, body.price, body.brand, body.description,
                                   body.image_url, body.attributes, body.quantity, body.min_threshold, admin.account_id)
    _reindex(request)
    return product_json(p, admin=True)


@router.put("/products/{product_id}")
def update_product(request: Request, product_id: int, body: ProductUpdateIn, svc: Svc, admin: Admin):
    p = svc.catalog.update_product(product_id, body.name, body.category_id, body.price, body.brand, body.description,
                                   body.image_url, body.attributes, admin.account_id)
    _reindex(request)
    return product_json(p, admin=True)


@router.post("/products/{product_id}/visibility")
def set_visibility(product_id: int, body: VisibilityIn, svc: Svc, admin: Admin):
    return product_json(svc.catalog.set_visibility(product_id, body.visible, admin.account_id), admin=True)


@router.delete("/products/{product_id}")
def delete_product(request: Request, product_id: int, svc: Svc, admin: Admin):
    """Physical delete only if the product never appeared in an order; otherwise it is hidden (BR-01)."""
    result = svc.catalog.delete_product(product_id, admin.account_id)
    _reindex(request)
    return {"result": result}


# ---- UC-11 promotions
@router.get("/promotions")
def list_promotions(svc: Svc, _: PromoViewer):
    return [promotion_json(p, svc.promotions.usage(p.id)) for p in svc.promotions.list()]


@router.post("/promotions", status_code=201)
def create_promotion(body: PromotionIn, svc: Svc, admin: Admin):
    data = body.model_dump()
    return promotion_json(svc.promotions.create(admin.account_id, **data))


@router.put("/promotions/{promotion_id}")
def update_promotion(promotion_id: int, body: PromotionIn, svc: Svc, admin: Admin):
    return promotion_json(svc.promotions.update(admin.account_id, promotion_id, **body.model_dump()))


@router.delete("/promotions/{promotion_id}")
def delete_promotion(promotion_id: int, svc: Svc, admin: Admin):
    return {"result": svc.promotions.delete(admin.account_id, promotion_id)}


# ---- UC-24 accounts and roles
@router.get("/roles")
def roles(svc: Svc, _: Admin):
    return [{"id": r.id, "name": r.name} for r in svc.accounts.roles()]


@router.get("/accounts")
def accounts(svc: Svc, _: Admin, role: Optional[str] = None, q: Optional[str] = Query(None, max_length=100)):
    return [account_json(a) for a in svc.accounts.list(role, q)]


@router.post("/accounts", status_code=201)
def create_account(body: StaffAccountIn, svc: Svc, admin: Admin):
    return account_json(svc.accounts.create_staff(body.email, body.password, body.role, admin.account_id))


@router.patch("/accounts/{account_id}/role")
def set_role(account_id: int, body: RoleIn, svc: Svc, admin: Admin):
    return account_json(svc.accounts.set_role(account_id, body.role, admin.account_id))


@router.patch("/accounts/{account_id}/lock")
def set_lock(account_id: int, body: LockIn, svc: Svc, admin: Admin):
    return account_json(svc.accounts.set_locked(account_id, body.locked, admin.account_id))
