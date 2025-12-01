from pydantic import BaseModel
from typing import List


class PackageShippedRequest(BaseModel):
    channel_uid: str
    order_id: str
    order_line_item_ids: List[str]  # List of item IDs being shipped together
    tracking_number: str  # Tracking number provided by shipping provider
    shipping_provider_id: str  # From Get Shipping Providers API


class ShippingUpdateRequest(BaseModel):
    channel_uid: str
    package_id: str
    tracking_number: str
    shipping_provider_id: str
