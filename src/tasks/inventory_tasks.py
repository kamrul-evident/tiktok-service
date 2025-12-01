import os
import requests
import logging as log
import json
import asyncio
from collections import defaultdict

from typing import List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload
from config import cel_app
from config.app_vars import APP_KEY, APP_SECRET
from config.database import get_db, SessionLocal
from models import Channel, InventoryRequest
from utils.maps import Tiktok


# @cel_app.task(name="tasks.inventory_tasks.update_inventory_quantity_in_tiktok")
def update_inventory_quantity_in_tiktok(channel: Channel) -> None:
    with SessionLocal() as db:
        inventory_requests: List[InventoryRequest] = (
            db.query(InventoryRequest)
            .filter(
                InventoryRequest.channel_uid == channel.channel_uid,
                InventoryRequest.status == InventoryRequest.StatusChoices.PENDING,
                InventoryRequest.created_at >= (datetime.now() - timedelta(days=2)),
            )
            .order_by(InventoryRequest.created_at.asc())
            .all()
        )
        if not inventory_requests:
            log.info(f"No pending inventory requests for channel {channel.channel_uid}")
            return
        grouped_requests: Dict[str, List[InventoryRequest]] = defaultdict(list)
        for req in inventory_requests:
            grouped_requests[req.item_id].append(req)
        # Process each product in batches
        for item_id, requests in grouped_requests.items():
            try:
                skus_payload = []
                for req in requests:
                    req.status = InventoryRequest.StatusChoices.PROCESSING
                    sku_id = str(req.request_metadata.get("sku_id", ""))
                    warehouse_id = str(req.request_metadata.get("warehouse_id", ""))
                    if not sku_id or not warehouse_id:
                        log.warning(f"Skipping request {req.id} due to missing fields")
                        req.status = InventoryRequest.StatusChoices.FAILED
                        continue
                    skus_payload.append(
                        {
                            "id": sku_id,
                            "inventory": [
                                {"quantity": req.quantity, "warehouse_id": warehouse_id}
                            ],
                        }
                    )
                if not skus_payload:
                    db.commit()
                    continue

                db.commit()

                payload = {"skus": skus_payload}
                print(
                    f"Sending {len(skus_payload)} variations of the product {item_id}"
                )
                # Call TikTok API (async wrapper)
                loop = asyncio.get_event_loop()
                response = loop.run_until_complete(
                    Tiktok.update_product_inventory(
                        item_id,
                        channel.access_token,
                        channel.shop_cipher,
                        json.dumps(payload),
                    )
                ).json()

                if response.get("code") != 0:
                    log.error(f"Failed to update {item_id}: {response}")
                    for req in requests:
                        req.status = InventoryRequest.StatusChoices.FAILED
                        req.request_id = str(response.get("request_id", ""))
                else:
                    log.info(f"Batch update successful for product {item_id}")
                    for req in requests:
                        req.status = InventoryRequest.StatusChoices.SUCCESS
                        req.request_id = str(response.get("request_id", ""))

                db.commit()

            except Exception as e:
                log.error(f"Error processing {item_id}: {e}")
                for req in requests:
                    req.status = InventoryRequest.StatusChoices.FAILED
                db.commit()


@cel_app.task(name="tasks.inventory_tasks.update_inventory_stock_all_channel")
def update_inventory_stock_all_channel():
    with SessionLocal() as db:
        try:
            channels: List[Channel] = db.query(Channel).all()
            for channel in channels:
                # Check if the tokens are expired or not. If expired then get the new token
                current_timestamp = int(datetime.now().timestamp())
                if current_timestamp > channel.access_token_expiry:
                    # Need to get the new token and store it in the database
                    url: str = "https://auth.tiktok-shops.com/api/v2/token/refresh"
                    headers = {"Content-Type": "application/json"}
                    params: Dict[str, Any] = {
                        "app_key": APP_KEY,
                        "app_secret": APP_SECRET,
                        "refresh_token": channel.refresh_token,
                        "grant_type": "refresh_token",
                    }
                    response = requests.get(url, params=params, headers=headers).json()
                    if response.get("code") != 0:
                        log.error("Failed to get new refresh token")
                        return None

                    data = response.get("data", {})
                    channel.access_token = data.get("access_token", "")
                    channel.refresh_token = data.get("refresh_token", "")
                    channel.access_token_expiry = int(
                        data.get("access_token_expire_in", 0)
                    )
                    channel.refresh_token_expiry = int(
                        data.get("refresh_token_expire_in", 0)
                    )
                    db.commit()

                # Send request to TikTok for each channel
                update_inventory_quantity_in_tiktok(channel)
        except Exception as e:
            log.error(f"Error updating inventory stock for all channels: {str(e)}")
            db.rollback()
        finally:
            log.info("Inventory stock update task completed.")
