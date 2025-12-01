from fastapi import APIRouter, Depends, Request

from config.database import get_db
from controllers import get_active_shops, get_authorized_shops, integrate_channel
from serializers import AuthRequest

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


@router.get("/get-authorized-shops", tags=["auth"])
async def handle_get_authorized_shops(req: Request):
    return await get_authorized_shops(req)


@router.get("/get-active-shops", tags=["auth"])
async def handle_get_active_shops(req: Request):
    return await get_active_shops(req)


@router.post("/integrate-channel/", tags=["auth"])
async def handle_channel_integration(payload: AuthRequest, db=Depends(get_db)):
    return await integrate_channel(payload, db)


auth_router = router
