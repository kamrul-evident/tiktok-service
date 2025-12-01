from fastapi import APIRouter, Request

from controllers import get_order_details, get_single_order_details, fetch_orders

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", tags=["orders"])
async def handle_get_order_details(req: Request):
    return await get_order_details(req)


@router.get("/{order_id}/", tags=["orders"])
async def handle_get_single_order_details(order_id: str, req: Request):
    query_params = dict(req.query_params)  # 👈 Better way to convert
    channel_uid = query_params.get("channel_uid")
    return await get_single_order_details(order_id, channel_uid)


@router.get("/fetch", tags=["orders"])
async def handle_fetch_orders(channel_uid: str = None, days_ago: int = 1):
    return await fetch_orders(channel_uid, days_ago)


order_router = router
