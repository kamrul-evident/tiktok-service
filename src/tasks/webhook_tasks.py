from typing import Any, Dict

from config.worker import cel_app
from tasks import process_order, process_product_creation, process_product_update
from tasks.authorization_tasks import upcoming_authorization_expiration
from tasks.message_tasks import handle_new_message


@cel_app.task(
    name="tasks.webhook.process",
    queue="tiktok_high_priority_queue",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def process_webhook_data(payload: Dict[Any, Any]):
    webhook_type = {
        1: process_order,
        7: upcoming_authorization_expiration,
        14: handle_new_message,
        15: process_product_update,
        16: process_product_creation,
        # 27: "inventory_status_change"
    }
    func = webhook_type.get(payload.get("type"))
    func.delay(payload.get("shop_id"), payload.get("data"))
    return
