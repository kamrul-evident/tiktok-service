from fastapi import APIRouter

from controllers import process_webhook_request
from serializers import Notification

router = APIRouter(
    prefix="/webhook",
    tags=["webhook"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", tags=["webhook"])
async def handle_webhook_request(payload: Notification):
    return await process_webhook_request(payload)


webhook_router = router
