from celery import Celery
from celery.signals import task_received
from kombu import Queue

from config.app_vars import RABBIT_URL, CELERY_BEAT_SCHEDULE_TIME

cel_app = Celery("tiktok-tasks", broker=RABBIT_URL, include=["tasks", "consumers"])

cel_app.conf.task_queues = [
    Queue(
        "tiktok_high_priority_queue",
        exchange="tiktok_high_priority_queue_exchange",
        routing_key="tiktok_high_priority_queue",
    ),
    Queue("tiktok-queue", exchange="tiktok_queue_exchange", routing_key="tiktok_queue"),
]

cel_app.conf.task_default_queue = "tiktok-queue"
cel_app.autodiscover_tasks()


# cel_app.conf.beat_schedule = {
#     "update-product-inveontory-stock": {
#         "task": "tasks.inventory_tasks.update_inventory_stock_all_channel",
#         "schedule": CELERY_BEAT_SCHEDULE_TIME,
#         "args": (),
#         "options": {"queue": "tiktok-queue"},
#     }
# }


# cel_app.conf.beat_schedule={
#     'retrive-order-every-in-min':{
#         "task":"tasks.orders.get_active_channel_order",
#         "schedule": ORDER_FETCH_IN_MIN*60,
#         "args":(),
#         'options': {'queue': 'woocommerce_high_priority_queue'},
#     },
#     'retrive-product-every-in-hours':{
#         "task":"tasks.product.get_active_channel_products",
#         "schedule": PRODUCT_FETCH_IN_HOUR*60*60,
#         "args":(),
#         'options': {'queue': 'woocommerce-queue'},
#     }
# }
@task_received.connect
def on_task_received(sender=None, request=None, **kwargs):
    print("==============================================")
    print(f"Task received from {request.name}")
    print("==============================================")
