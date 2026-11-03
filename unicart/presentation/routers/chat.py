"""Shopping assistant controller (chatbot): today's promotions, product help, order tracking, return guidance."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...business.chat_service import ChatReply, ChatTurn
from ...business.chat_tools import describe_promotion
from ..deps import RateLimited, Soft, chat_budget, get_services
from ..schemas import ChatIn
from ..serializers import order_json, product_json, promotion_json
from ..wiring import Services

router = APIRouter(prefix="/api/chat", tags=["chatbot"])
Svc = Annotated[Services, Depends(get_services)]


def _json(r: ChatReply) -> dict:
    return {
        "reply": r.text, "mode": r.mode, "degraded": r.degraded, "suggestions": r.suggestions,
        "products": [product_json(p, r.ratings.get(p.id, (0.0, 0))) for p in r.products],
        "promotions": [promotion_json(p) | {"description": describe_promotion(p)} for p in r.promotions],
        "orders": [order_json(o) for o in r.orders],
        "actions": r.actions,
    }


@router.post("")
def chat(body: ChatIn, request: Request, svc: Svc, actor: Soft):
    """Body = the whole conversation so far (the browser keeps it). Guests may ask about products, promotions and
    policies; order tracking and return requests need a customer login. Nothing is stored on the server."""
    key = f"acc:{actor.account_id}" if actor else f"ip:{request.client.host if request.client else '-'}"
    if not chat_budget.allow(key):
        raise RateLimited("Bạn nhắn quá nhanh, vui lòng đợi một chút rồi hỏi tiếp")
    reply = svc.chat.reply(actor, [ChatTurn(m.role, m.content) for m in body.messages])
    return _json(reply)
