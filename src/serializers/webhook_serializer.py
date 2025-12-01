from typing import List, Literal, Optional, Union

from pydantic import BaseModel, model_validator


class OrderData(BaseModel):
    order_id: str
    order_status: Literal[
        "UNPAID",
        "ON_HOLD",
        "AWAITING_SHIPMENT",
        "AWAITING_COLLECTION",
        "CANCEL",
        "IN_TRANSIT",
        "DELIVERED",
        "COMPLETED",
    ]  # Add all possible statuses if known
    is_on_hold_order: bool
    update_time: int


class ProductData(BaseModel):
    product_id: int
    product_types: List[str]
    update_time: int


class AuthExpirationData(BaseModel):
    Message: str
    ExpirationTime: int


class InventoryDistribution(BaseModel):
    total_quantity: int
    available_quantity: int
    creator_reserved_quantity: int
    campaign_reserved_quantity: int
    committed_quantity: int


class TriggerReason(BaseModel):
    alert_type: str
    lead_days: int
    low_stock_threshold: Optional[int] = None


class InventoryData(BaseModel):
    product_id: str
    sku_id: str
    trigger_reason: TriggerReason
    current_inventory_status: str
    inventory_distribution: InventoryDistribution
    update_time: int


class MessageData(BaseModel):
    content: str
    conversation_id: str
    create_time: int
    is_visible: bool
    message_id: str
    index: str
    type: str
    sender: dict[
        str, Union[str, Literal["BUYER", "SHOP", "CUSTOMER_SERVICE", "SYSTEM", "ROBOT"]]
    ]


class Notification(BaseModel):
    type: int
    tts_notification_id: str
    shop_id: str
    timestamp: int
    data: Union[
        OrderData, InventoryData, MessageData, dict, ProductData, AuthExpirationData
    ]  # Support specific models and fallback to dict

    @model_validator(mode="before")
    def validate_data(cls, values):
        type_to_model = {
            1: OrderData,
            7: AuthExpirationData,
            14: MessageData,
            16: ProductData,
            27: InventoryData,
        }
        data = values.get("data")
        type_ = values.get("type")

        # Dynamically choose the model based on `type`
        if type_ in type_to_model:
            values["data"] = type_to_model[type_](**data)
        return values


class RemoteProductData(BaseModel):
    id: str
    sku: str
    name: str
    fba_status: bool
    image: str
    remote_product_name: str
    remote_product_description: str
