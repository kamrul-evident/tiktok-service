from fastapi import APIRouter, Request
from serializers import PackageShippedRequest, ShippingUpdateRequest
from controllers import (
    get_shipping_providers,
    get_package_details,
    mark_package_shipped,
    update_package_shipping,
)

router = APIRouter(
    prefix="/shipping",
    tags=["shipping"],
    responses={404: {"description": "Not found"}},
)


@router.get("/shipping-providers/{delivery_option_id}", tags=["shipping"])
async def handle_get_shipping_providers(delivery_option_id: str, channel_uid: str):
    return await get_shipping_providers(delivery_option_id, channel_uid)


@router.get("/package-details/{package_id}", tags=["shipping"])
async def handle_get_package_details(package_id: str, channel_uid: str):
    return await get_package_details(package_id, channel_uid)


@router.post("/mark-package-shipped", tags=["shipping"])
async def handle_mark_package_shipped(payload: PackageShippedRequest):
    # payload = payload.model_dump()
    return await mark_package_shipped(payload)


@router.post("/update-package-shipping", tags=["shipping"])
async def handle_update_package_shipping(payload: ShippingUpdateRequest):
    return await update_package_shipping(payload)


shipping_router = router
