import os

RABBIT_URL = (
    "amqp://"
    + os.getenv("RABBITMQ_USER")
    + ":"
    + os.getenv("RABBITMQ_PASSWORD")
    + "@"
    + os.getenv("RABBITMQ_HOST")
    + ":"
    + os.getenv("RABBITMQ_PORT")
)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = int(os.getenv("DB_PORT"))

# Celery Beat Schedule Time in seconds
CELERY_BEAT_SCHEDULE_TIME = int(os.getenv("CELERY_BEAT_SCHEDULE_TIME", 120))

APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")

MYE_INVENTORY_AND_MAPPING_SERVICE_URL = os.environ.get("MIAMS_URL")
MYE_ORDER_SERVICE_URL = os.environ.get("MYE_ORDER_SERVICE_URL")
INTEGRATION_SERVICE = os.environ.get("INTEGRATION_SERVICE")
MIAMS_SECRET_KEY = os.environ.get("MIAMS_SECRET_KEY", None)
MOS_SECRET_KEY = os.environ.get("MOS_SECRET_KEY", None)


ORDER_EXCHANGE_NAME = os.getenv("ORDER_EXCHANGE_NAME", "order.exchange")
ORDER_QUEUE_NAME = os.getenv("ORDER_QUEUE_NAME", "order.creation")

PRODUCT_EXCHANGE_NAME = os.getenv("PRODUCT_EXCHANGE_NAME", "product.exchange")
PRODUCT_QUEUE_NAME = os.getenv("PRODUCT_QUEUE_NAME", "product.creation")

INVENTORY_EXCHANGE_NAME = os.getenv(
    "INVENTORY_EXCHANGE_NAME", "mye-exchange-stock-update-tiktok"
)
INVENTORY_QUEUE_NAME = os.getenv(
    "INVENTORY_QUEUE_NAME", "mye-queue-stock-update-tiktok"
)
