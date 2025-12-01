import json
import logging as log
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from celery import bootsteps
from kombu import Consumer, Exchange, Queue
from sqlalchemy import tuple_
from config.database import get_db, SessionLocal
from config.worker import cel_app
from models import Channel, InventoryRequest
from utils.maps import Tiktok
from utils.helpers import get_channel_and_token
from config.app_vars import (
    INVENTORY_EXCHANGE_NAME,
    INVENTORY_QUEUE_NAME,
)

exchange = Exchange(INVENTORY_EXCHANGE_NAME)
inventory_update_queue = Queue(INVENTORY_QUEUE_NAME, exchange, routing_key="")


def update_product_stock_in_tiktok(channel, payload, product_id) -> bool:
    try:
        response = asyncio.run(
            Tiktok.update_product_inventory(
                product_id,
                channel.access_token,
                channel.shop_cipher,
                json.dumps(payload),
            )
        ).json()
        if response.get("code") == 0:
            log.info(
                f"Product stock updated successfully in TikTok for product id: {product_id}"
            )
            return True
        log.info(f"Failed to update stock in tiktok")
        return False
    except Exception as e:
        log.error(f"Error updating product stock in TikTok: {str(e)}")
        return False


def insert_inventory_update_request(
    channel_uid: str, sku: str, quantity: int, product_id: str, request_metadata: Dict
) -> bool:
    db = next(get_db())
    try:
        channel = asyncio.run(get_channel_and_token(channel_uid=channel_uid))
        status = InventoryRequest.StatusChoices.PENDING

        if not channel:
            log.warning(f"Channel {channel_uid} not found")
            return
        payload = {
            "skus": [
                {
                    "id": str(request_metadata.get("sku_id", "")),
                    "inventory": [
                        {
                            "quantity": quantity,
                            "warehouse_id": str(
                                request_metadata.get("warehouse_id", "")
                            ),
                        }
                    ],
                }
            ]
        }
        response = update_product_stock_in_tiktok(channel, payload, product_id)
        status = (
            InventoryRequest.StatusChoices.SUCCESS
            if response
            else InventoryRequest.StatusChoices.FAILED
        )

        inventory_request = InventoryRequest(
            channel_uid=channel_uid,
            sku=sku,
            quantity=quantity,
            item_id=product_id,
            status=status,
            request_metadata=request_metadata,
        )
        db.add(inventory_request)
        db.commit()
        # log.info(f"Logged {status} inventory request for {sku} - {channel_uid}")
        return True

    except Exception as e:
        log.error(
            f"Error processing inventory request for {sku} - {channel_uid}: {str(e)}"
        )
        inventory_request = InventoryRequest(
            channel_uid=channel_uid,
            sku=sku,
            quantity=quantity,
            item_id=product_id,
            status=InventoryRequest.StatusChoices.FAILED,
            request_metadata=request_metadata,
        )
        db.add(inventory_request)
        try:
            db.commit()
            log.info(f"Logged FAILED inventory request for {sku} - {channel_uid}")
        except Exception as db_e:
            db.rollback()
            log.error(f"Failed to log inventory request: {str(db_e)}")
        return True

    finally:
        db.close()


def bulk_insert_inventory_requests(data) -> bool:
    if not data:
        log.info("No data provided for bulk insert")
        return True
    items = data if isinstance(data, list) else [data]
    now = datetime.now(timezone.utc)
    two_days_ago = now - timedelta(days=2)
    with SessionLocal() as db:
        try:
            # Step 1: Get ALL existing channel_uids from Channel table (since it's small)
            all_channels = db.query(Channel.channel_uid).all()
            # Convert to a set for fast lookup
            valid_channel_uids = {c.channel_uid for c in all_channels}
            # Build unique keys for lookup
            keys = [(i["channel_uid"], i["sku"], i["product_id"]) for i in items]
            key_set = set(keys)
            # Fetch existing pending requests in bulk
            existing_requests = (
                db.query(InventoryRequest)
                .filter(
                    tuple_(
                        InventoryRequest.channel_uid,
                        InventoryRequest.sku,
                        InventoryRequest.item_id,
                    ).in_(key_set),
                    InventoryRequest.status == InventoryRequest.StatusChoices.PENDING,
                    InventoryRequest.created_at >= two_days_ago,
                )
                .all()
            )
            existing_map = {
                (req.channel_uid, req.sku, req.item_id): req
                for req in existing_requests
            }
            to_update = []
            to_create = []
            for item in items:
                # Skip invalid channel_uid
                channel_uid = item.get("channel_uid", "")
                if not channel_uid or channel_uid not in valid_channel_uids:
                    log.info(f"Skipping item with invalid channel_uid: {channel_uid}")
                    continue

                # Skip non-Tiktok channels
                channel_type = item.get("channel_type", "")
                if channel_type != "tiktok":
                    log.info(f"Skipping item with invalid channel_type: {channel_type}")
                    continue
                request_metadata = item.get("request_metadata", {})
                request_metadata.update(**item.get("product_metadata", {}))
                key = (item["channel_uid"], item["sku"], item["product_id"])

                # If pending request exists → update quantity
                if key in existing_map:
                    inv_request = existing_map[key]
                    inv_request.quantity = item.get("available_quantity", 0)
                    inv_request.updated_at = now
                    to_update.append(inv_request)
                    continue

                # Add new request to create list
                to_create.append(
                    InventoryRequest(
                        channel_uid=channel_uid,
                        sku=item.get("sku", ""),
                        item_id=item.get("product_id"),
                        quantity=item.get("available_quantity", 0),
                        status=InventoryRequest.StatusChoices.PENDING,
                        created_at=now,
                        updated_at=now,
                        request_metadata=request_metadata,
                    )
                )
            # Bulk insert new requests
            if to_create:
                db.bulk_save_objects(to_create)
                log.info(f"Bulk inserted {len(to_create)} new requests.")

            # Bulk update existing pending requests
            if to_update:
                db.bulk_save_objects(to_update)
                log.info(f"Bulk updated {len(to_update)} existing requests.")

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            db.commit()
            print(f"Error during bulk insert: {str(e)}")
            return False


class InventoryRequestProcessWorker(bootsteps.ConsumerStep):
    def get_consumers(self, channel):
        print("Getting inventory consumer")
        return [
            Consumer(
                channel,
                queues=[inventory_update_queue],
                callbacks=[self.on_message],
                accept=["json", "text/plain"],
            )
        ]

    def on_message(self, body, message):
        try:
            data = json.loads(body)
            acknowledged = True
            # log.info(f"Received message data: {data}")
            # log.info(f"Message: {message}")
            if not data:
                log.error({"error": "Empty message received"})
                acknowledged = False
            # Support both single object and list
            if "inventory_requests" in data:
                log.info("Data received as dict with List of 'inventory_requests'")
                acknowledged = bulk_insert_inventory_requests(
                    data.get("inventory_requests", [])
                )

            elif isinstance(data, dict) and data.get("channel_type", "") == "tiktok":
                log.info("data received as dict")
                # Single item for backward compatibility
                request_metadata = data.get("request_metadata", {})
                request_metadata.update(**data.get("product_metadata", {}))
                acknowledged = insert_inventory_update_request(
                    channel_uid=data["channel_uid"],
                    sku=data["sku"],
                    quantity=data["available_quantity"],
                    product_id=data["product_id"],
                    request_metadata=request_metadata,
                )
            elif isinstance(data, list):
                log.info("batch inventory data received as list")
                acknowledged = bulk_insert_inventory_requests(data)
            else:
                acknowledged = True  # Non-amazon message

            if acknowledged:
                message.ack()

        except Exception as e:
            log.error({"error": str(e)})
            message.reject()


cel_app.steps["consumer"].add(InventoryRequestProcessWorker)
