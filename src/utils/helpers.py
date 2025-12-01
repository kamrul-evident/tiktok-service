import hashlib
import hmac
import json
import logging as log
from urllib.parse import parse_qs, urlencode, urlparse
from sqlalchemy.orm import joinedload
import requests
import datetime
from typing import Dict, Any
import asyncio

from config.app_vars import (
    INTEGRATION_SERVICE,
    MYE_ORDER_SERVICE_URL,
    APP_KEY,
    APP_SECRET,
    MOS_SECRET_KEY,
)
from config.database import get_db, SessionLocal
from models import Channel


async def calculate_signature(
    url: str, params: dict, headers: dict, secret: str, body: bytes = None, **kwargs
):
    """
    Calculate the signature based on query parameters, request path, and body.

    :param req: A dictionary representing the request with keys 'url', 'headers', and 'body'.
                - 'url' should contain the full URL of the request.
                - 'headers' should be a dictionary of HTTP headers.
                - 'body' should be a byte stream or a string of the request body.
    :param secret: The app secret key used for signing.
    :return: The calculated signature as a hexadecimal string.
    """
    # Parse query parameters from the URL
    url_parts = urlparse(url)
    query_string = urlencode(params, doseq=True)
    queries = parse_qs(query_string)

    for k, v in kwargs.items():
        queries[k] = [str(v)]

    # Extract all query parameters excluding 'sign' and 'access_token'
    keys = [k for k in queries if k not in {"sign", "access_token"}]

    # Reorder the parameters' keys in alphabetical order
    keys.sort()

    # Concatenate all the parameters in the format of {key}{value}
    input_data = ""
    for key in keys:
        input_data += key + "".join(
            queries[key]
        )  # Join query values as a single string

    # Append the request path
    input_data = url_parts.path + input_data

    # Check if Content-Type is not multipart/form-data and append body if needed
    content_type = headers.get("Content-Type", "")
    if not content_type.startswith("multipart/form-data"):
        if isinstance(body, bytes):
            body = body.decode("utf-8")

        if body is not None:
            input_data += body

    # Wrap the generated string with the App secret
    input_data = secret + input_data + secret
    # Generate the HMAC-SHA256 signature
    return generate_sha256(input_data, secret)


def generate_sha256(input_data, secret):
    """
    Generate HMAC-SHA256 signature for the given input and secret.

    :param input_data: The data to be signed.
    :param secret: The secret key used for signing.
    :return: The generated signature in hexadecimal.
    """
    h = hmac.new(secret.encode("utf-8"), input_data.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


def notify_new_order_v2(open_order, channel_uid, company_uid, dispatched_order=[]):

    try:
        print("------------Order Is sending to order service--------------  ")
        order_service_url = MYE_ORDER_SERVICE_URL + "/api/v1/orders/add-v3/"
        # print(order_service_url)
        order_dict = {
            "channel_uid": channel_uid,
            "company_uid": company_uid,
            "data": [open_order],
            "missing_orders": dispatched_order,
        }

        print(f"The Payload that are sending to order service {order_dict}")
        headers = {"Content-Type": "application/json", "secret-key": MOS_SECRET_KEY}
        req = requests.post(order_service_url, json=order_dict, headers=headers)
        if int(req.status_code) != 200:
            log.error(
                "Failed to send order in order service {}".format(req.status_code)
            )
            print("respone from order service", req.content)
            return

        print(f"Order Service Response: {req.status_code}")
        log.info(f"Order service respose: {req.content}")

    except Exception as e:
        log.error(f"Error Sending to Order Service {str(e)}")


# Function to get the channel and token based on channel uuid
async def get_channel_and_token(channel_uid: str):
    with SessionLocal() as db:
        try:
            channel: Channel = (
                db.query(Channel).filter(Channel.channel_uid == channel_uid).first()
            )

            if not channel:
                return None  # No matching channel found
            if not channel.access_token or not channel.refresh_token:
                log.info(f"Channel has no tokens")
                return None
            # Check if the tokes are expired or not. If expired then get the new token
            current_timestamp = int(datetime.datetime.now().timestamp())
            if current_timestamp > channel.access_token_expiry:
                # need to get the new token and store it in the database
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
                channel.access_token_expiry = int(data.get("access_token_expire_in", 0))
                channel.refresh_token_expiry = int(
                    data.get("refresh_token_expire_in", 0)
                )
                db.commit()

            # ✅ Force-load all fields so they stay after session closes
            _ = channel.channel_uid
            _ = channel.company_uuid
            _ = channel.name
            _ = channel.country
            _ = channel.shop_id
            _ = channel.shop_cipher
            _ = channel.created_at
            _ = channel.updated_at
            _ = channel.access_token
            _ = channel.refresh_token
            _ = channel.access_token_expiry
            _ = channel.refresh_token_expiry

            # ✅ Detach instance from session → safe to use in Celery
            db.expunge(channel)

            return channel

        except Exception as e:
            log.error(f"Error fetching channel and token: {e}")
            return None


def get_channel_token_by_shop_id(shop_id: str):
    with SessionLocal() as db:
        try:
            # Fetch the Channel based on shop_id, along with the associated tokens
            channel: Channel = (
                db.query(Channel).filter(Channel.shop_id == int(shop_id)).first()
            )

            # If no matching channel is found, return None
            if not channel:
                return None

            if not channel.access_token or not channel.refresh_token:
                log.info("Channel has no tokens. Please add access and refresh Token.")
                return None

            # Check if the tokens are expired and need refreshing
            current_timestamp = int(datetime.datetime.now().timestamp())
            if current_timestamp > channel.access_token_expiry:
                # Tokens are expired, so we need to refresh them
                url = "https://auth.tiktok-shops.com/api/v2/token/refresh"
                headers = {"Content-Type": "application/json"}
                params: Dict[str, Any] = {
                    "app_key": APP_KEY,
                    "app_secret": APP_SECRET,
                    "refresh_token": channel.refresh_token,
                    "grant_type": "refresh_token",
                }

                # Make the request to refresh the access token
                response = requests.get(url, params=params, headers=headers).json()

                # If the response code is not 0, it means the refresh token is invalid or there was an issue
                if response.get("code") != 0:
                    log.error(
                        f"Failed to refresh token for shop_id {shop_id}. Response: {response}"
                    )
                    return None

                # Parse the response and update the channel's tokens
                data = response.get("data", {})
                channel.access_token = data.get("access_token", "")
                channel.refresh_token = data.get("refresh_token", "")
                channel.access_token_expiry = int(data.get("access_token_expire_in", 0))
                channel.refresh_token_expiry = int(
                    data.get("refresh_token_expire_in", 0)
                )

                # Commit the changes to the database
                db.commit()

            # Return the channel with the valid (or refresh) token
            # ✅ Force-load all fields so they stay after session closes
            _ = channel.channel_uid
            _ = channel.company_uuid
            _ = channel.name
            _ = channel.country
            _ = channel.shop_id
            _ = channel.shop_cipher
            _ = channel.created_at
            _ = channel.updated_at
            _ = channel.access_token
            _ = channel.refresh_token
            _ = channel.access_token_expiry
            _ = channel.refresh_token_expiry

            # ✅ Detach instance from session → safe to use in Celery
            db.expunge(channel)

            return channel
        except Exception as e:
            log.error(f"Error fetching channel by shop_id {shop_id}: {e}")
            return None


async def create_channel_in_mis(channel: Channel):
    """Helper function to create channel in integration service"""
    # Need to check the function after new endpoint integrated in integration service
    url: str = INTEGRATION_SERVICE + "/api/v1/channel/add-channel/tiktok/"
    headers = {
        "Content-Type": "application/json",
        "secret-key": "6433220e-5f0b-4238-bb11-046f589e9149",  # require for calling integraion service from local only
    }
    payload = {
        "name": channel.name,
        "channel_uid": channel.channel_uid,
        "company_uid": channel.company_uuid,
        "channel_type": "tiktok",
        "channel_max_stock": 20,
        "country": channel.country,
        "channel_metadata": {
            "shop_id": channel.shop_id,
            "shop_cipher": channel.shop_cipher,
        },
    }
    payload = json.dumps(payload)
    log.info("Channel data is sending into integration service")
    # Run the async function synchronously
    loop = asyncio.get_event_loop()
    response = loop.run_until_complete(
        requests.post(url, json=payload, headers=headers)
    ).json()
    if response.get("status_code") != 201:
        log.error("Failed to create channel in integration service")
        return None
    log.info("Channel created successfully in integration service")
    return True
