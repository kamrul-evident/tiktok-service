from http import HTTPStatus

from fastapi import Request
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from models import Channel
from serializers import AuthRequest
from utils.maps import Tiktok
from utils.helpers import get_channel_and_token, create_channel_in_mis


async def get_authorized_shops(req: Request):
    try:
        body = await req.body()

        channel_uid = req.query_params._dict.get("channel_uid", None)
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

        res = await Tiktok.get_authorized_shops(access_token=channel.access_token)
        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def get_active_shops(req: Request):
    try:
        body = await req.body()
        query_params = req.query_params._dict
        channel_uid: str = query_params.get("channel_uid", None)

        if not channel_uid:
            return ORJSONResponse(
                content={"message": "Channel uid is required to get active shops"},
                status_code=400,
            )
        channel = await get_channel_and_token(channel_uid=channel_uid)

        if not channel:
            return ORJSONResponse(
                content={"message": "Channel Not found for this uid"},
                status_code=400,
            )
        res = await Tiktok.get_active_shops(
            req_params=req.query_params._dict,
            headers=req.headers,
            body=body,
            access_token=channel.access_token,
        )
        return ORJSONResponse(content=res.json())

    except ValidationError as e:
        error_message = f"Validation failed: {e}"
        print(error_message)
        return error_message


async def integrate_channel(payload: AuthRequest, db: Session):
    try:
        # Get access and refresh tokens
        (
            access_token,
            refresh_token,
            access_token_expires_in,
            refresh_token_expires_in,
            err,
        ) = await Tiktok.get_access_token(auth_code=payload.auth_code)

        if err:
            return ORJSONResponse(
                content={"message": err}, status_code=HTTPStatus.BAD_REQUEST
            )
        # Get shop details
        shop_resp = await Tiktok.get_authorized_shops(access_token=access_token)
        shop_data = shop_resp.json()

        if shop_data.get("code") != 0:
            return ORJSONResponse(
                content={"errors": [{"message": "Failed to retrieve shop details"}]},
                status_code=HTTPStatus.BAD_REQUEST,
            )

        shops = shop_data.get("data", {}).get("shops", [{}])
        shop_id = shops[0].get("id", None)
        shop_cipher = shops[0].get("cipher", None)

        if not shop_id or not shop_cipher:
            return ORJSONResponse(
                content={"errors": [{"message": "Failed to retrieve shop details"}]},
                status_code=HTTPStatus.BAD_REQUEST,
            )

        # Check for existing channel
        channel = db.query(Channel).filter_by(shop_cipher=shop_cipher).first()

        if channel:
            # Update existing channel tokens
            channel.access_token = access_token
            channel.refresh_token = refresh_token
            channel.access_token_expiry = access_token_expires_in
            channel.refresh_token_expiry = refresh_token_expires_in
            db.commit()
            message = "Channel updated successfully"
        else:
            # Create new channel
            channel = Channel(
                company_uuid=payload.company_uid,
                name=payload.name,
                country=payload.country,
                shop_id=int(shop_id),
                shop_cipher=shop_cipher,
                access_token=access_token,
                refresh_token=refresh_token,
                access_token_expiry=access_token_expires_in,
                refresh_token_expiry=refresh_token_expires_in,
            )
            db.add(channel)
            db.commit()
            # Optionally call MIS integration here
            # create_channel_in_mis(new_channel)
            message = "Channel added successfully"

        # Manually serialize channel and token info
        channel_data = {
            "channel_uid": channel.channel_uid,
            "company_uuid": channel.company_uuid,
            "name": channel.name,
            "country": channel.country,
            "channel_metadata": {
                "shop_id": channel.shop_id,
                "shop_cipher": channel.shop_cipher,
                "access_token": channel.access_token,
                "refresh_token": channel.refresh_token,
                "access_token_expiry": channel.access_token_expiry,
                "refresh_token_expiry": channel.refresh_token_expiry,
            },
        }

        return ORJSONResponse(
            content={"message": message, "channel": channel_data},
            status_code=HTTPStatus.OK,
        )

    except ValidationError as e:
        return ORJSONResponse(
            content={"message": f"Validation failed: {str(e)}"},
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
