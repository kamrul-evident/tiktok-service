import asyncio
import logging as log
from typing import Any, Dict, List
from collections import defaultdict
from sqlalchemy.orm import joinedload

from config.database import get_db
from config.worker import cel_app
from models import Channel
from publishers import publish_order_in_queue
from serializers import OrderData, preprocess_order_data
from utils.helpers import notify_new_order_v2
from utils.maps import Tiktok
from utils.shipping import TiktokShipping


order_status_map = {
    "UNPAID": "PENDING",
    "AWAITING_SHIPMENT": "OPEN_ORDER",
    "AWAITING_COLLECTION": "OPEN_ORDER",
    "IN_TRANSIT": "DISPATCHED",
    "DELIVERED": "COMPLETED",
    "FULFILLED": "COMPLETED",
    "CANCEL": "CANCELLED",
    "CLOSED": "CANCELLED",
    "RETURNED": "RETURNED",
    "REFUNDED": "CANCELLED",
    "PARTIALLY_REFUNDED": "PARTIALLY_CANCELLED",
    "PENDING": "PENDING",
}


def prepare_order_payload(
    tiktok_order: dict,
    store_id: str,
    payment_status: str = "UNPAID",
    shipping_providers: List[Dict[str, Any]] = [],
) -> dict:
    """
    Transform TikTok Shop order data into MYE-CORE-compatible payload.
    Args:
        tiktok_order: TikTok order data (single order from 'data.orders').
        store: Store object with 'id' field.
    Returns:
        MYE-CORE-compatible payload.
    """
    line_item_ids = []
    # Aggregate line items by seller_sku
    sku_data = defaultdict(lambda: {"quantity": 0, "item": None})
    for item in tiktok_order.get("line_items", []):
        sku = item.get("seller_sku", "")
        line_item_ids.append(item.get("id", ""))
        if sku:
            sku_data[sku]["quantity"] += 1
            if not sku_data[sku]["item"]:
                sku_data[sku]["item"] = item

    line_items_payload = [
        {
            "marketplace_sku": sku,
            "quantity": data["quantity"],
            "unit_price": float(data["item"].get("sale_price", "0")),
            "product_metadata": {
                "product_id": data["item"].get("product_id", ""),
                "currency": tiktok_order.get("payment", {}).get("currency", "GBP"),
                "sku_id": data["item"].get("sku_id", ""),
            },
        }
        for sku, data in sku_data.items()
        if data["item"]
    ]

    # Create district_info for address mappings
    district_info = {
        d["address_level"]: d["address_name"]
        for d in tiktok_order.get("recipient_address", {}).get("district_info", [])
    }

    return {
        "marketplace_order_id": tiktok_order.get("id", ""),
        "store_uuid": store_id,
        "marketplace": "TIKTOK",
        "buyer_name": tiktok_order.get("recipient_address", {}).get("name", ""),
        "buyer_email": tiktok_order.get("buyer_email", ""),
        "phone_number": tiktok_order.get("recipient_address", {}).get(
            "phone_number", ""
        ),
        "shipping_address": f"{tiktok_order.get('recipient_address', {}).get('address_line1', '')} {tiktok_order.get('recipient_address', {}).get('address_line2', '')}".strip(),
        "address1": tiktok_order.get("recipient_address", {}).get("address_line1", ""),
        "address2": tiktok_order.get("recipient_address", {}).get("address_line2", ""),
        "shipping_city": district_info.get("L2", ""),
        "shipping_state": district_info.get("L1", ""),
        "shipping_country": district_info.get(
            "L0", tiktok_order.get("recipient_address", {}).get("region_code", "")
        ),
        "shipping_zip": tiktok_order.get("recipient_address", {}).get(
            "postal_code", ""
        ),
        "order_status": order_status_map.get(
            tiktok_order.get("status", "PENDING"), "PENDING"
        ),
        "payment_status": payment_status,
        "currency": tiktok_order.get("payment", {}).get("currency", "GBP"),
        "total_amount": float(tiktok_order.get("payment", {}).get("total_amount", "0")),
        "order_metadata": {
            "delivery_option_id": tiktok_order.get("delivery_option_id", ""),
            "shipping_providers": shipping_providers,
            # Package IDs may be multiple
            "package_id": tiktok_order.get("packages", [{}])[0].get("id", ""),
            "region_id": "",
            "site_id": "",
            "line_item_ids": line_item_ids,
        },
        "line_items": line_items_payload,
    }


@cel_app.task(
    name="tasks.order.process",
    queue="tiktok_high_priority_queue",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def process_order(shop_id: int, data: Dict[Any, Any]):
    order_data = OrderData(**data)
    db = next(get_db())
    try:
        channel: Channel = (
            db.query(Channel).filter(Channel.shop_id == int(shop_id)).first()
        )
        if channel is None:
            log.error({"error": f"channel for shop_id {shop_id} not found"})
            return
    finally:
        db.close()

    # get order details

    loop = asyncio.get_event_loop()
    order_response = loop.run_until_complete(
        Tiktok.get_single_order_details(
            order_data.order_id,
            access_token=channel.access_token,
            shop_cipher=channel.shop_cipher,
        )
    )

    if order_response.json().get("code") != 0:
        log.info(f"failed to fetch order id {order_data.order_id}")
        return

    # preprocess order payload
    tiktok_order = order_response.json().get("data", {}).get("orders", [])

    if not tiktok_order:
        log.info("Order array is empty")
        return
    # get the delivery option id from the order response
    delivery_option_id = tiktok_order[0].get("delivery_option_id", "")
    shipping_providers = []
    if delivery_option_id:
        # log.info(f"Delivery option id: {delivery_option_id}")
        shipping_provider_response = loop.run_until_complete(
            TiktokShipping.get_shipping_providers(
                delivery_option_id=delivery_option_id,
                channel=channel,
            )
        )
        # log.info("Shipping provider response:", shipping_provider_response.json())
        if shipping_provider_response.json().get("code") != 0:
            log.error(
                f"Failed to fetch shipping providers for delivery option id {delivery_option_id}"
            )
        else:
            shipping_providers = (
                shipping_provider_response.json()
                .get("data", {})
                .get("shipping_providers", [])
            )
    # TODO: This portion sends the order in mye core service (Commenting now, uncomment when core service is ready)
    # order_payload = prepare_order_payload(
    #     tiktok_order=tiktok_order[0],
    #     store_id=channel.channel_uid,
    #     payment_status=order_data.order_status,
    #     shipping_providers=shipping_providers,
    # )
    # orders_to_publish = {"Orders": [order_payload]}
    # # push the order data in order queue
    # publish_order_in_queue(orders_to_publish)
    # Add order in MYE Order Service
    # TODO: This part is for sending order in order service
    # preprocess order payload
    order_payload_mos = preprocess_order_data(
        channel_uid=channel.channel_uid,
        order_data=order_response.json().get("data"),
        shipping_providers=shipping_providers,
    )

    # TODO: we need to remove this later when our core service is ready
    notify_new_order_v2(order_payload_mos, channel.channel_uid, channel.company_uuid)
    return
