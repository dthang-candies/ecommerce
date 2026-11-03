"""AI search controllers (UC-03 <<extend>>: Search Keyword / Search Image / Search Voice, FR-20..23)."""
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool

from ...business.search_service import SearchOutcome
from ..deps import RateLimited, get_services, image_budget, text_budget, voice_budget
from ..media import read_limited, sniff_audio, sniff_image
from ..serializers import product_json
from ..wiring import Services

router = APIRouter(prefix="/api/search", tags=["ai-search"])
Svc = Annotated[Services, Depends(get_services)]
MAX_IMAGE, MAX_AUDIO = 4 * 1024 * 1024, 3 * 1024 * 1024


def _client(request: Request) -> str:
    return request.client.host if request.client else "-"


def _json(svc: Services, out: SearchOutcome, page: int, size: int) -> dict:
    ratings = svc.products.rating_summary([p.id for p in out.items])
    q = out.parsed
    return {
        "total": out.total, "page": page, "size": size, "mode": out.mode, "degraded": out.degraded,
        "suggestion": out.suggestion, "corrected": out.corrected, "original": q.original,
        "interpreted": {"text": q.text, "min_price": q.min_price, "max_price": q.max_price,
                        "brands": q.brands, "colors": q.colors, "sizes": q.sizes},
        "recognized": ({"query": out.recognized.query, "category": out.recognized.category,
                        "color": out.recognized.color, "brand": out.recognized.brand} if out.recognized else None),
        "items": [product_json(p, ratings.get(p.id, (0.0, 0))) | {"score": out.scores.get(p.id)} for p in out.items],
    }


@router.get("/status")
def status(request: Request):
    """Lets the UI show the microphone / camera buttons only when the AI is really available."""
    ai = getattr(request.app.state, "ai", None)
    if ai is None:
        return {"enabled": False, "ready": False, "indexed": 0, "model": "", "syncing": False}
    s = ai.status()
    return {"enabled": s.enabled, "ready": s.ready, "indexed": s.indexed, "model": s.model, "syncing": s.syncing}


@router.get("")
def search(request: Request, svc: Svc, q: Optional[str] = Query(None, max_length=100), category_id: Optional[int] = None,
           min_price: Optional[Decimal] = Query(None, ge=0), max_price: Optional[Decimal] = Query(None, ge=0),
           sort: str = Query("relevance", pattern="^(relevance|newest|price_asc|price_desc|name)$"),
           page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100), autocorrect: bool = True):
    """Hybrid semantic + keyword search with query understanding. Over the per-client AI budget -> keyword search."""
    use_ai = text_budget.allow(_client(request))
    out = svc.search.search(q, category_id, min_price, max_price, sort, page, size, use_ai=use_ai, autocorrect=autocorrect)
    return _json(svc, out, page, size)


@router.post("/image")
async def search_by_image(request: Request, svc: Svc, page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=48)):
    """Body = raw image bytes (JPEG/PNG/WebP, <= 4 MB). The image is analysed in memory and never stored."""
    if not image_budget.allow(_client(request)):
        raise RateLimited("Bạn tìm bằng hình ảnh quá nhanh, vui lòng đợi một chút")
    data = await read_limited(request, MAX_IMAGE)
    mime = sniff_image(data)
    out = await run_in_threadpool(svc.search.search_image, data, mime, page, size)
    return _json(svc, out, page, size)


@router.post("/voice")
async def transcribe_voice(request: Request, svc: Svc):
    """Body = raw audio bytes (WAV/MP3/OGG/FLAC/AIFF, <= 3 MB). Returns the transcript; the client then searches it."""
    if not voice_budget.allow(_client(request)):
        raise RateLimited("Bạn dùng giọng nói quá nhanh, vui lòng đợi một chút")
    data = await read_limited(request, MAX_AUDIO)
    mime = sniff_audio(data)
    t = await run_in_threadpool(svc.search.transcribe, data, mime)
    return {"text": t.text, "language": t.language}
