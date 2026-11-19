from fastapi import APIRouter, Depends
from app.business.product_service import ProductService
from app.dependencies import get_product_service

router = APIRouter(prefix="/products", tags=["Product"])


@router.get("")
def search(keyword: str | None = None, svc: ProductService = Depends(get_product_service)):
    raise NotImplementedError


@router.get("/{product_id}")
def detail(product_id: str, svc: ProductService = Depends(get_product_service)):
    raise NotImplementedError
