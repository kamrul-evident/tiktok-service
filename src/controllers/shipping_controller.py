from typing import Dict, Any

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError

from serializers import PackageShippedRequest, ShippingUpdateRequest
from utils.shipping import TiktokShipping
from utils.helpers import get_channel_and_token


async def get_shipping_providers(delivery_option_id: str, channel_uid: str):
    try:
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Failed to get Channel"},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        res = await TiktokShipping.get_shipping_providers(
            delivery_option_id=delivery_option_id,
            channel=channel,
        )
        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def get_package_details(package_id: str, channel_uid: str):
    try:
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Failed to get Channel"},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        res = await TiktokShipping.get_package_details(
            package_id=package_id,
            channel=channel,
        )
        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def mark_package_shipped(payload: PackageShippedRequest):
    try:
        payload_json = payload.model_dump()

        channel_uid = payload_json.get("channel_uid", None)
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Failed to get Channel"},
                status_code=HTTPStatus.BAD_REQUEST,
            )

        order_id = payload_json.get("order_id", None)

        if not order_id:
            return ORJSONResponse(
                content={"message": "order_id is required"},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        res = await TiktokShipping.mark_package_shipped(
            channel=channel, shipping_data=payload_json
        )

        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def update_package_shipping(payload: ShippingUpdateRequest):
    try:
        payload_json = payload.model_dump()

        channel_uid = payload_json.get("channel_uid", None)
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Failed to get Channel"},
                status_code=HTTPStatus.BAD_REQUEST,
            )

        res = await TiktokShipping.update_package_shipping(
            channel=channel, shipping_data=payload_json
        )

        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message
