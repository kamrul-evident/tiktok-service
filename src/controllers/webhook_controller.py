from serializers.webhook_serializer import Notification
from tasks import process_webhook_data


async def process_webhook_request(payload: Notification):
    print("webhook payload:", payload)
    process_webhook_data.delay(payload.model_dump())
    return {"message": "Webhook request received successfully"}
