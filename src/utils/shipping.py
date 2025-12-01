from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from http import HTTPStatus
from fastapi.responses import ORJSONResponse
from fastapi.exceptions import HTTPException

import requests
import json

from config.app_vars import APP_KEY, APP_SECRET
from utils.helpers import calculate_signature, get_channel_and_token


class TiktokShipping:

    @staticmethod
    async def get_shipping_providers(delivery_option_id: str, channel):
        params = {
            "app_key": APP_KEY,
            "shop_cipher": channel.shop_cipher,
        }
        headers = {
            "x-tts-access-token": channel.access_token,
            "Content-Type": "application/json",
        }
        url: str = (
            f"https://open-api.tiktokglobalshop.com/logistics/202309/delivery_options/{delivery_option_id}/shipping_providers"
        )

        timestamp = int(datetime.now(timezone.utc).timestamp())
        signature = await calculate_signature(
            url=url,
            params=params,
            headers=headers,
            body=None,
            secret=APP_SECRET,
            timestamp=timestamp,
        )

        params.update({"sign": signature, "timestamp": timestamp})
        response = requests.get(url=url, params=params, headers=headers)

        return response

    @staticmethod
    async def get_package_details(package_id: str, channel):
        params = {
            "app_key": APP_KEY,
            "shop_cipher": channel.shop_cipher,
        }
        headers = {
            "x-tts-access-token": channel.access_token,
            "Content-Type": "application/json",
        }
        url: str = (
            f"https://open-api.tiktokglobalshop.com/fulfillment/202309/packages/{package_id}"
        )
        timestamp = int(datetime.now(timezone.utc).timestamp())
        signature = await calculate_signature(
            url=url,
            params=params,
            headers=headers,
            body=None,
            secret=APP_SECRET,
            timestamp=timestamp,
        )
        params.update({"sign": signature, "timestamp": timestamp})
        response = requests.get(url=url, params=params, headers=headers)

        return response

    @staticmethod
    async def mark_package_shipped(channel, shipping_data: Dict[str, Any]):
        order_id: str = shipping_data.get("order_id", "")

        payload: Dict[str, Any] = {
            "order_line_item_ids": shipping_data.get("order_line_item_ids", []),
            "shipping_provider_id": shipping_data.get("shipping_provider_id", ""),
            "tracking_number": shipping_data.get("tracking_number", ""),
        }
        payload = json.dumps(payload)

        params = {
            "app_key": APP_KEY,
            "shop_cipher": channel.shop_cipher,
        }
        headers = {
            "x-tts-access-token": channel.access_token,
            "Content-Type": "application/json",
        }
        url: str = (
            f"https://open-api.tiktokglobalshop.com/fulfillment/202309/orders/{order_id}/packages"
        )
        timestamp = int(datetime.now(timezone.utc).timestamp())
        signature = await calculate_signature(
            url=url,
            params=params,
            headers=headers,
            body=payload,
            secret=APP_SECRET,
            timestamp=timestamp,
        )

        params.update({"sign": signature, "timestamp": timestamp})
        response = requests.post(url=url, params=params, headers=headers, data=payload)

        return response

    @staticmethod
    async def update_package_shipping(channel, shipping_data: Dict[str, Any]):
        package_id: str = shipping_data.get("package_id", "")
        payload: Dict[str, Any] = {
            "shipping_provider_id": shipping_data.get("shipping_provider_id", ""),
            "tracking_number": shipping_data.get("tracking_number", ""),
        }

        payload = json.dumps(payload)

        params = {
            "app_key": APP_KEY,
            "shop_cipher": channel.shop_cipher,
        }
        headers = {
            "x-tts-access-token": channel.access_token,
            "Content-Type": "application/json",
        }
        url: str = (
            f"https://open-api.tiktokglobalshop.com/fulfillment/202309/packages/{package_id}/shipping_info/update"
        )
        timestamp = int(datetime.now(timezone.utc).timestamp())
        signature = await calculate_signature(
            url=url,
            params=params,
            headers=headers,
            body=payload,
            secret=APP_SECRET,
            timestamp=timestamp,
        )

        params.update({"sign": signature, "timestamp": timestamp})

        response = requests.post(url=url, params=params, headers=headers, data=payload)

        return response
