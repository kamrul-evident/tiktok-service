from typing import Dict, Any
import logging as log
import json
from kombu import Connection, Exchange, Queue, Producer
from config.app_vars import RABBIT_URL, PRODUCT_EXCHANGE_NAME, PRODUCT_QUEUE_NAME

# Product Queue Names
PRODUCT_CREATION_ROUTING_KEY = "order.creation"

# Define exchanges
product_exchange = Exchange(PRODUCT_EXCHANGE_NAME, type="direct", durable=True)
product_dl_exchange = Exchange(
    PRODUCT_EXCHANGE_NAME, type="direct", durable=True
)  # Dead-letter exchange

# Define queue with dead-letter configuration
product_queue = Queue(
    PRODUCT_QUEUE_NAME,
    exchange=product_exchange,
    routing_key=PRODUCT_CREATION_ROUTING_KEY,
    durable=True,
    queue_arguments={
        "x-dead-letter-exchange": PRODUCT_EXCHANGE_NAME,
        "x-dead-letter-routing-key": "product.creation.deadletter",
    },
)


def publish_product_in_queue(payload: Dict[str, Any]) -> bool:
    """Publish product data to RabbitMQ"""
    try:
        with Connection(RABBIT_URL) as conn:
            # Create producer
            producer = Producer(
                conn,
                exchange=product_exchange,
                routing_key=PRODUCT_CREATION_ROUTING_KEY,
            )

            # Publish message
            producer.publish(
                json.dumps(payload),
                retry=True,
                declare=[product_exchange, product_queue],
                content_type="application/json",
                delivery_mode=2,  # Persistent delivery
            )
            log.info("Product data published to RabbitMQ")
            return True
    except Exception as e:
        log.error(f"Failed to publish product to RabbitMQ: {str(e)}", exc_info=True)
        return False
