from fastapi import APIRouter, Depends, Request, Query

from config.database import get_db
from controllers import (
    get_product_details,
    update_product_inventory,
    fetch_products,
    get_products_from_tiktok,
    update_inventory_all_channel,
)
from serializers import AuthRequest

router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={404: {"description": "Not found"}},
)


@router.get("/fetch-all", tags=["products"])
async def handle_fetch_products(
    channel_uid: str = Query(..., Description="Channel UID")
):
    return await fetch_products(channel_uid)


@router.get("/all", tags=["products"])
async def get_products(channel_uid: str = None):
    return await get_products_from_tiktok(channel_uid)


@router.get("/inventory-update/multiple", tags=["products"])
async def inventory_update_schedule():
    return await update_inventory_all_channel()


@router.get("/{product_id}", tags=["products"])
async def handle_get_product_details(product_id: str, req: Request):
    return await get_product_details(product_id, req)


@router.post("/{product_id}/inventory/update", tags=["products"])
async def handle_update_product_inventory(product_id: str, req: Request):
    return await update_product_inventory(product_id, req)


product_router = router
