from fastapi import APIRouter, Depends
from app.business.inventory_service import InventoryService
from app.dependencies import get_inventory_service
from app.schemas import RestockRequest

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/low-stock")
def low_stock(threshold: int = 5, svc: InventoryService = Depends(get_inventory_service)):
    raise NotImplementedError


@router.post("/restock")
def restock(body: RestockRequest, svc: InventoryService = Depends(get_inventory_service)):
    raise NotImplementedError
