from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.business import errors
from app.presentation import (cart_controller, inventory_controller, order_controller,
                              payment_controller, product_controller)

app = FastAPI(title="ABC Online Shop")

for module in (product_controller, cart_controller, order_controller,
               payment_controller, inventory_controller):
    app.include_router(module.router)


@app.exception_handler(errors.NotFound)
async def not_found_handler(request: Request, exc: errors.NotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(errors.OutOfStock)
@app.exception_handler(errors.InvalidTransaction)
async def bad_request_handler(request: Request, exc: errors.BusinessError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(errors.Forbidden)
async def forbidden_handler(request: Request, exc: errors.Forbidden):
    return JSONResponse(status_code=403, content={"detail": str(exc)})
