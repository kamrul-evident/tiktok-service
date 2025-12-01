import time

import asyncio
import logging as log
from typing import Any, Dict, List
import requests

from config.worker import cel_app
from config.app_vars import MYE_INVENTORY_AND_MAPPING_SERVICE_URL, MIAMS_SECRET_KEY
from serializers import ProductData, RemoteProductData
from models import Channel
from utils.maps import Tiktok
from utils.helpers import get_channel_token_by_shop_id, get_channel_and_token

from publishers import publish_product_in_queue


def prepare_product_data(
    store_id: str, company_uid: str, product: Dict[str, Any], sku_info: Dict[str, Any]
):
    payload = {
        "id": str(product.get("id")),
        "sku": sku_info.get("seller_sku", ""),
        "store_uuid": store_id,
        "company_uuid": company_uid,
        "name": product["title"],
        "price": sku_info.get("price", {}).get("sale_price", 0),
        "quantity": sku_info.get("inventory", [{}])[0].get("quantity", 0),
        "fba_status": False,  # TODO: Change later
        "image_url": product.get("main_images", [{}])[0].get(
            "urls", ["https://test.jpg"]
        )[0],
        # "fulfillment_method": "FBA",  # TODO: Change later
        "product_metadata": {
            "sku_id": sku_info.get("id", ""),
            "currency": sku_info.get("price", {}).get("currency", "GBP"),
            "warehouse_id": sku_info.get("inventory", [{}])[0].get("warehouse_id", ""),
        },
    }

    return payload


def send_product_to_miams(channel_uid: str, company_uid: str, product: Dict[str, Any]):
    # TODO This is a temporary solution, we need to remove this later when our core service is ready
    # We need to send the product data to the queue
    payload = {
        "channel_uid": channel_uid,
        "company_uid": company_uid,
    }
    product_data = []
    for sku in product.get("skus", []):
        seller_sku = sku.get("seller_sku", "")
        if not seller_sku:
            print(f"SKU is not available", sku)
            continue
        product_data.append(
            {
                "id": str(product.get("id", "")),
                "sku": seller_sku,
                "name": product.get("title", ""),
                "fba_status": False,
                "image": product.get("main_images", [{}])[0].get(
                    "urls", ["http://test.jpg"]
                )[0],
                "remote_product_name": product.get("title", ""),
                "remote_product_description": "Test Description",  # we are sending test description becuase description may be too large.
                "product_metadata": {
                    "sku_id": sku.get("id", ""),
                    "currency": sku.get("price", {}).get("currency", "GBP"),
                    "warehouse_id": sku.get("inventory", [{}])[0].get(
                        "warehouse_id", ""
                    ),
                },
            }
        )
    if not product_data or product_data == []:
        print("No Product to send in MIAMS")
        return True
    payload["data"] = product_data
    print(f"Sending {len(product_data)} to MIAMS")
    # Send the request to the remote product add endpoint
    remote_product_add_url = (
        MYE_INVENTORY_AND_MAPPING_SERVICE_URL
        + "/api/v1/mapping/product/remote-product/add/"
    )

    headers = {"Content-Type": "application/json", "secret-key": MIAMS_SECRET_KEY}
    # Send the request
    response = requests.post(remote_product_add_url, json=payload, headers=headers)

    # Log response based on task type (creation or update)
    if int(response.status_code) != 201:
        log.info(f"Failed to add remote product. Error code {response.status_code}")
        print("response: ", response.json())
        return False

    log.info(f"Products send to miams successfully {response.json()}")
    return True


def send_product_request(
    product_data: Dict[str, Any], channel: Channel, task_type: str
) -> None:
    # TODO: this portion is to send product in queue(Core service Compatible)
    # products = []
    # for sku in product_data.get("skus", []):
    #     product_payload = prepare_product_data(
    #         store_id=channel.channel_uid,
    #         company_uid=channel.company_uuid,
    #         product=product_data,
    #         sku_info=sku,
    #     )
    #     products.append(product_payload)
    # payload = {"Products": products}
    # # Add the product data to the queue
    # result = publish_product_in_queue(payload)
    # if result:
    #     log.info(f"Product {task_type} request added in queue successfully")
    # else:
    #     log.info(f"Product {task_type} request failed to add in queue")

    # Send the request to the miams service
    # TODO: When the core service is ready then uncommect above code and comment this line.
    result = send_product_to_miams(
        channel.channel_uid, channel.company_uuid, product_data
    )
    if result:
        log.info(f"Product {task_type} request added in MIAMS successfully")
    else:
        log.info(f"Product {task_type} request failed to add in MIAMS")


@cel_app.task(
    name="tasks.product.sync",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def process_product_creation(shop_id: str, data: Dict[Any, Any]):
    product_data = ProductData(**data)
    # Get channel and token from the database
    channel = get_channel_token_by_shop_id(shop_id=shop_id)
    if not channel:
        log.error(f"Failed to get channel for shop id: {shop_id}")
        return None
    # Run the async function synchronously
    loop = asyncio.get_event_loop()
    product = loop.run_until_complete(
        Tiktok.get_single_product_details(
            product_id=product_data.product_id,
            access_token=channel.access_token,
            shop_cipher=channel.shop_cipher,
        )
    )

    product_json = product.json()

    if product_json.get("code") != 0:
        log.info(f"failed to fetch product id {product_data.product_id}")
        return
    # Send the create request to add in queue
    send_product_request(product_json["data"], channel, "create")


@cel_app.task(
    name="tasks.product.update",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def process_product_update(shop_id: str, data: Dict[Any, Any]):
    product_id: str = str(data.get("product_id", ""))
    required_fields_for_products: List[str] = [
        "title",
        "description",
        "sku",
        "main_images",
        "price",
        "quantity",
    ]
    changed_fields: List[str] = data.get("changed_fields", [])
    # Check if update is necessary
    if not any(field in changed_fields for field in required_fields_for_products):
        log.info("No update needed for the product.")
        return

    log.info("product need to be updated")
    # Get channel and token from the database
    channel = get_channel_token_by_shop_id(shop_id=shop_id)
    if not channel:
        log.error(f"Failed to get channel for shop id: {shop_id}")
        return None

    # Run the async function synchronously
    loop = asyncio.get_event_loop()
    product = loop.run_until_complete(
        Tiktok.get_single_product_details(
            product_id=product_id,
            access_token=channel.access_token,
            shop_cipher=channel.shop_cipher,
        )
    )
    product_json = product.json()
    if product_json.get("code") != 0:
        log.info(f"failed to fetch product id {product_id}")
        return
    # send the product update request to queue
    send_product_request(product_json["data"], channel, "update")


@cel_app.task(
    name="tasks.product.fetch_all_products",
    retry_kwargs={"max_retries": 3, "countdown": 5},
    ack_late=True,
)
def process_all_products(channel_uid: str):
    next_page_token = ""
    total_products = 0
    loop = asyncio.get_event_loop()
    channel = loop.run_until_complete(get_channel_and_token(channel_uid=channel_uid))

    if not channel:
        log.info(f"Channel not found for: {channel_uid}")
        return

    while True:
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(
            Tiktok.get_products(
                channel.access_token,
                channel.shop_cipher,
                page_token=next_page_token,
            )
        )
        response = response.json()
        if response.get("code") != 0:
            log.error(f"Failed to fetch products: {response}")
            break
        products = response.get("data", {}).get("products", [])

        next_page_token = response.get("data", {}).get("next_page_token", "")
        has_more = bool(next_page_token)
        for product in products:
            total_products += 1
            send_product_request(product, channel, "create")

        if not has_more:
            break

        # Avoid rate-limiting
        # time.sleep(1)

    log.info(f"Total products processed: {total_products}")
