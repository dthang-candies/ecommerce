from fastapi import APIRouter, Depends
from app.business.payment_service import PaymentService
from app.dependencies import get_payment_service

router = APIRouter(prefix="/payments", tags=["Payment"])


@router.post("/callback")
def callback(payload: dict, svc: PaymentService = Depends(get_payment_service)):
    raise NotImplementedError
