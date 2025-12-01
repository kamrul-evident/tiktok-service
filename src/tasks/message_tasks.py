import logging as log
from typing import Any, Dict

from config.worker import cel_app


@cel_app.task(
    name="tasks.message.new_message",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def handle_new_message(shop_id: str, data: Dict[Any, Any]):
    # new message webhook task will be handle here.
    log.info(f"Shop ID: {shop_id}")
    log.info(f"Data from message webhook: {data}")
    return
