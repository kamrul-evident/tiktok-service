import asyncio
import logging as log
from typing import Any, Dict

from sqlalchemy.orm import joinedload

from config.database import get_db
from config.worker import cel_app
from models import Channel
from serializers import AuthExpirationData


@cel_app.task(
    name="tasks.authorization.expire",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def upcoming_authorization_expiration(shop_id: str, data: Dict[Any, Any]):
    log.info(f"Shop ID: {shop_id}")
    auth_expiration_data = AuthExpirationData(**data)
    log.info(f"Auth Expiration Data: {auth_expiration_data.model_dump()}")
    return
