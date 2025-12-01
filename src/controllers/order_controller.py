from http import HTTPStatus

from fastapi import Request
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError

from utils.maps import Tiktok
from utils.helpers import get_channel_and_token


async def get_order_details(req: Request):
    try:
        body = await req.body()
        channel_uid: str = req.query_params.get("channel_uid", None)
        if not channel_uid:
            return ORJSONResponse(
                content={"message": "channel_uid is required"},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        res = await Tiktok.get_order_details(
            req_params=req.query_params._dict,
            headers=req.headers,
            body=body,
        )
        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def get_single_order_details(order_id: str, channel_uid: str):
    if not channel_uid:
        return ORJSONResponse(
            content={"message": "channel_uid is required"},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    channel = await get_channel_and_token(channel_uid=channel_uid)
    if not channel:
        return ORJSONResponse(
            content={"message": "Failed to get Channel"},
            status_code=HTTPStatus.BAD_REQUEST,
        )

    try:
        res = await Tiktok.get_single_order_details(
            order_id=order_id,
            access_token=channel.access_token,
            shop_cipher=channel.shop_cipher,
        )
        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def fetch_orders(channel_uid: str = None, days_ago: int = 1):
    if not channel_uid:
        return ORJSONResponse(
            content={"message": "Channel uid is required to fetch orders"},
            status_code=HTTPStatus.BAD_REQUEST,
        )
    channel = await get_channel_and_token(channel_uid)
    if not channel:
        return ORJSONResponse(
            content={"message": "Channel not found for this uid"},
            status_code=HTTPStatus.BAD_REQUEST,
        )
    all_orders = []
    page_token = None
    while True:
        response = await Tiktok.get_orders(channel, days_ago, page_token)
        response = response.json()
        if response.get("code") != 0:
            print("Failed to get orders from tiktok server:", response)
            break
        orders = response.get("data", {}).get("orders", [])
        if not orders:
            print("No more orders found.")
            break
        all_orders.extend(orders)

        page_token = response.get("data", {}).get("next_page_token", None)
        if not page_token:
            break

    return ORJSONResponse(
        content={"orders": all_orders},
        status_code=HTTPStatus.OK,
    )
