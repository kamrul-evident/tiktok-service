from http import HTTPStatus

from fastapi import Request
from fastapi.responses import ORJSONResponse

from utils.maps import Tiktok
from utils.helpers import get_channel_and_token
from tasks.product_tasks import process_all_products
from tasks.inventory_tasks import update_inventory_stock_all_channel


async def fetch_products(channel_uid: str):
    try:
        process_all_products.delay(channel_uid=channel_uid)
        return {"message": "Products are being fetched in the background"}

    except Exception as e:
        return {"message": "Failed to fetch products", "error": str(e)}


async def get_product_details(product_id: str, req: Request):
    query_params = req.query_params._dict
    channel_uid = query_params.get("channel_uid", None)
    if not channel_uid:
        return ORJSONResponse(
            content={"message": "Channel uid is required"},
            status_code=HTTPStatus.BAD_REQUEST,
        )
    try:
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Channel Not Found"},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        # Fetch product details from TikTok
        res = await Tiktok.get_single_product_details(
            product_id=product_id,
            access_token=channel.access_token,
            shop_cipher=channel.shop_cipher,
        )
        return ORJSONResponse(content=res.json())

    except Exception as e:
        return ORJSONResponse(
            content={"message": f"An error occurred {str(e)}"},
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


async def update_product_inventory(product_id: str, req: Request):
    query_params = req.query_params._dict
    channel_uid = query_params.get("channel_uid", None)
    if not channel_uid:
        return ORJSONResponse(
            content={"message": "Channel uid is required"},
            status_code=HTTPStatus.BAD_REQUEST,
        )
    try:
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Failed to get Channel"},
                status_code=HTTPStatus.BAD_REQUEST,
            )

        req_body = await req.body()

        res = await Tiktok.update_product_inventory(
            product_id, channel.access_token, channel.shop_cipher, req_body
        )
        if res.json().get("code") != 0:
            return ORJSONResponse(
                content={"message": "Failed to update inventory", "data": res.json()},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        return ORJSONResponse(content=res.json())

    except Exception as e:
        return ORJSONResponse(
            content={"message": f"An error occurred {str(e)}"},
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


async def get_products_from_tiktok(channel_uid: str = None):
    if not channel_uid:
        return ORJSONResponse(
            content={"message": "Channel uid is required"},
            status_code=HTTPStatus.BAD_REQUEST,
        )
    try:
        channel = await get_channel_and_token(channel_uid=channel_uid)
        if not channel:
            return ORJSONResponse(
                content={"message": "Failed to get Channel"},
                status_code=HTTPStatus.BAD_REQUEST,
            )
        response = await Tiktok.get_products(channel.access_token, channel.shop_cipher)

        next_page_token = ""
        all_products = []
        while True:
            response = await Tiktok.get_products(
                channel.access_token, channel.shop_cipher, next_page_token
            )
            response = response.json()
            if response.get("code") != 0:
                break

            next_page_token = response.get("data", {}).get("next_page_token", "")
            has_more = bool(next_page_token)
            for product in response.get("data", {}).get("products", []):
                for sku in product.get("skus", []):
                    all_products.append(
                        {
                            "id": product.get("id", ""),
                            "sku": sku.get("seller_sku", ""),
                            "sku_id": sku.get("id"),
                            "warehouse_id": sku.get("inventory", [{}])[0].get(
                                "warehouse_id", ""
                            ),
                            "quantity": sku.get("inventory", [{}])[0].get(
                                "quantity", 0
                            ),
                            "price": sku.get("price", {}).get(
                                "tax_exclusive_price", 0.0
                            ),
                        }
                    )
            if not has_more:
                break

        return ORJSONResponse(
            content={
                "success": True,
                "message": "Products fetched from tiktok",
                "data": all_products,
            },
            status_code=HTTPStatus.OK,
        )

    except Exception as e:
        return ORJSONResponse(
            content={"message": f"An error occurred {str(e)}"},
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


async def update_inventory_all_channel():
    update_inventory_stock_all_channel.delay()
    return ORJSONResponse(
        content={"message": "Background inventory update started!"},
        status_code=HTTPStatus.OK,
    )
