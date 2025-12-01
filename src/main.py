import logging
from http import HTTPStatus

from fastapi import Depends, FastAPI
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware

from config.database import Session, get_db
from routers import (
    auth_router,
    order_router,
    webhook_router,
    product_router,
    shipping_router,
)

logger = logging.getLogger("fastapi")
app = FastAPI(dependencies=[Depends(get_db)])

# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    db = Session()

    resp = {}
    resp["server_health"] = "MYE TikTok Service API health OK"
    resp["database_health"] = "OK" if db.is_active else "disconnected"

    return ORJSONResponse(content=resp, status_code=HTTPStatus.OK)


# app.add_middleware(Renderer)

app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(order_router)
app.include_router(product_router)
app.include_router(shipping_router)
# app.include_router(orders_router)
# app.include_router(webhook_router)
