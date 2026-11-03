"""create_app: wires the FastAPI application (routers = controllers of section 4.4), error handling,
the 15-minute unpaid-order sweeper (BR-04) and, when built, the React front-end."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import config
from ..business.exceptions import BusinessError
from ..ai.runtime import AiRuntime
from ..persistence.database import Database
from .routers import admin, auth, catalog, chat, customer, search, staff
from .wiring import build_services

log = logging.getLogger("unicart")
ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"
IMAGES_DIR = ROOT / "images"


def sweep_expired(db: Database) -> int:
    """Cancel online orders unpaid for 15 minutes and give the stock back (BR-04)."""
    with db.new_session() as session:
        return build_services(session).orders.expire_unpaid()


def create_app(db: Database | None = None, run_scheduler: bool = False, ai: AiRuntime | None = None) -> FastAPI:
    database = db or Database()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if run_scheduler and ai is not None and ai.enabled:
            ai.load()                                                  # vectors saved in MySQL: search is ready at once
            ai.schedule_sync()                                         # embed only new / changed products
        if run_scheduler:
            async def loop():
                while True:
                    try:
                        count = await asyncio.to_thread(sweep_expired, database)
                        if count:
                            log.info("expired %s unpaid order(s)", count)
                    except Exception:                                  # keep the sweeper alive
                        log.exception("expiry sweep failed")
                    await asyncio.sleep(config.EXPIRY_SWEEP_SECONDS)
            task = asyncio.create_task(loop())
        yield
        if task:
            task.cancel()

    app = FastAPI(title="UniCart API", version="1.0.0", lifespan=lifespan)
    app.state.db = database
    app.state.ai = ai
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=False,
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(BusinessError)
    async def business_error(_: Request, e: BusinessError):
        return JSONResponse({"error": e.code, "message": e.message}, status_code=e.http_status)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(_: Request, e: RequestValidationError):
        fields = {".".join(str(p) for p in err["loc"][1:]): err["msg"] for err in e.errors()}
        detail = "; ".join(f"{k}: {v}" if k else v for k, v in fields.items())
        return JSONResponse({"error": "VALIDATION_ERROR", "message": f"Dữ liệu không hợp lệ ({detail})",
                             "fields": fields}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("unhandled error", exc_info=e)
        return JSONResponse({"error": "INTERNAL_ERROR", "message": "Lỗi hệ thống, vui lòng thử lại sau"},
                            status_code=500)

    @app.get("/api/health", tags=["system"])
    def health():
        return {"status": "ok"}

    for module in (auth, catalog, search, chat, customer, staff, admin):
        app.include_router(module.router)

    if IMAGES_DIR.is_dir():                                             # product photos: /images/products/<file>
        app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

    if FRONTEND_DIST.exists():                                          # production: serve the built SPA
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                return JSONResponse({"error": "NOT_FOUND", "message": "Không tìm thấy"}, status_code=404)
            target = (FRONTEND_DIST / path).resolve()
            if path and target.is_file() and FRONTEND_DIST.resolve() in target.parents:
                return FileResponse(target)
            return FileResponse(FRONTEND_DIST / "index.html")
    return app
