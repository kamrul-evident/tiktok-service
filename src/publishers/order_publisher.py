from typing import Dict, Any
import logging as log
import json
from kombu import Connection, Exchange, Queue, Producer
from config.app_vars import RABBIT_URL, ORDER_EXCHANGE_NAME, ORDER_QUEUE_NAME

# Order Queue Names
ORDER_CREATION_DL_QUEUE = "order.creation.deadletter"
ORDER_CREATION_ROUTING_KEY = "order.creation"

# Define exchanges
order_exchange = Exchange(ORDER_EXCHANGE_NAME, type="direct", durable=True)
order_dl_exchange = Exchange(
    ORDER_EXCHANGE_NAME, type="direct", durable=True
)  # Dead-letter exchange

# Define queue with dead-letter configuration
order_queue = Queue(
    ORDER_QUEUE_NAME,
    exchange=order_exchange,
    routing_key=ORDER_CREATION_ROUTING_KEY,
    durable=True,
    queue_arguments={
        "x-dead-letter-exchange": ORDER_EXCHANGE_NAME,
        "x-dead-letter-routing-key": ORDER_CREATION_DL_QUEUE,
    },
)


def publish_order_in_queue(payload: Dict[str, Any]) -> bool:
    """Publish order data to RabbitMQ"""
    try:
        with Connection(RABBIT_URL) as conn:
            producer = Producer(
                conn,
                exchange=order_exchange,
                routing_key=ORDER_CREATION_ROUTING_KEY,
            )
            producer.publish(
                json.dumps(payload),
                content_type="application/json",
                delivery_mode=2,  # persistent
                declare=[order_exchange, order_queue],  # auto-declare if not already
                retry=True,
            )
            log.info("Order data published to RabbitMQ")
            return True
    except Exception as e:
        log.error(f"Failed to publish order to RabbitMQ: {str(e)}", exc_info=True)
        return False
