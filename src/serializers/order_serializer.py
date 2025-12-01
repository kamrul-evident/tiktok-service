from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


@dataclass
class ShippingAddress:
    firstName: str = ""
    lastName: str = ""
    address1: str = ""
    address2: str = ""
    city: str = ""
    state: str = ""
    postCode: str = ""
    country: str = ""
    phone: str = ""
    reference_id: Optional[str] = None


@dataclass
class OrderItem:
    sku: str
    quantity: int
    price: float
    positionItemId: List[str] = field(default_factory=list)


@dataclass
class Order:
    order_id: str
    channel_uid: str
    market_place: str = "TIKTOK"
    payment_status: str = ""
    order_status: str = ""
    seller_info: str = ""
    purchase_date: str = ""
    shipping_address: ShippingAddress = field(default_factory=ShippingAddress)
    payment_method: str = ""
    buyer_name: str = ""
    buyer_email: str = ""
    currency: Optional[str] = None
    total_price: float = 0.00
    isDispatched: bool = False
    items: List[OrderItem] = field(default_factory=list)
    order_meta: Optional[Dict[str, Any]] = None

    @property
    def order_status(self):
        return self._order_status

    @order_status.setter
    def order_status(self, value: str):
        if value in ["AWAITING_SHIPMENT", "AWAITING_COLLECTION"]:
            self._order_status = "OPEN_ORDER"
        elif value == "IN_TRANSIT":
            self._order_status = "DISPATCHED"
        elif value == "CANCEL":
            self._order_status = "CANCELLED"
        elif value in ["UNPAID"]:
            self._order_status = "PENDING"
        else:
            self._order_status = value


class LineItem(BaseModel):
    product_id: str
    product_name: str
    seller_sku: str
    sale_price: Optional[str] = None
    seller_discount: Optional[str] = None
    original_price: Optional[str] = None
    currency: str
    id: Optional[str] = None
    tracking_number: Optional[str] = None
    platform_discount: Optional[str] = None
    display_status: Optional[str] = None
    is_gift: Optional[bool] = None
    package_id: Optional[str] = None
    package_status: Optional[str] = None


class PaymentInfo(BaseModel):
    total_amount: str
    currency: str
    original_shipping_fee: str
    original_total_product_price: str
    sub_total: Optional[str] = None
    shipping_fee: Optional[str] = None
    platform_discount: Optional[str] = None
    seller_discount: Optional[str] = None
    shipping_fee_platform_discount: Optional[str] = None
    shipping_fee_seller_discount: Optional[str] = None
    tax: Optional[str] = None


class DistrictInfo(BaseModel):
    address_level: Optional[str] = None
    address_level_name: Optional[str] = None
    address_name: Optional[str] = None


class RecipientAddress(BaseModel):
    address_detail: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    address_line4: Optional[str] = None
    district_info: List[DistrictInfo]
    first_name: Optional[str] = None
    full_address: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    postal_code: Optional[str] = None
    region_code: Optional[str] = None


class OrderDetails(BaseModel):
    id: str
    buyer_email: Optional[str] = None
    buyer_message: Optional[str] = None
    create_time: Optional[int] = None
    delivery_option_id: Optional[str] = None
    delivery_option_name: Optional[str] = None
    delivery_time: Optional[int] = None
    delivery_type: Optional[str] = None
    fulfillment_type: Optional[str] = None
    is_cod: Optional[bool] = None
    is_on_hold_order: Optional[bool] = None
    is_replacement_order: Optional[bool] = None
    is_sample_order: Optional[bool] = None
    line_items: Optional[List[LineItem]] = None
    paid_time: Optional[int] = None
    payment: Optional[PaymentInfo] = None
    payment_method_name: Optional[str] = None
    recipient_address: Optional[RecipientAddress] = None
    status: str
    shipping_provider: Optional[str] = None
    shipping_provider_id: Optional[str] = None
    tracking_number: Optional[str] = None
    update_time: Optional[int] = None


class OrderList(BaseModel):
    orders: List[OrderDetails]


def preprocess_order_data(channel_uid, order_data: Dict[Any, Any], shipping_providers):

    order_list = OrderList(**order_data)

    data = order_list.orders[0]

    # extract item data
    line_items = {}
    line_item_ids = []
    for item in data.line_items:
        line_item_ids.append(item.id)
        if line_items.get(item.seller_sku) is not None:
            line_items[item.seller_sku]["quantity"] += 1
        else:
            line_items.update(
                {item.seller_sku: {"quantity": 1, "price": float(item.sale_price)}}
            )

    shipping_address = ShippingAddress(
        firstName=data.recipient_address.first_name,
        lastName=data.recipient_address.last_name,
        address1=data.recipient_address.address_line1,
        address2=data.recipient_address.address_line2,
        state=getattr(data.recipient_address, "state", ""),
        phone=data.recipient_address.phone_number or "",
        city=getattr(data.recipient_address, "city", ""),
        postCode=data.recipient_address.postal_code or "",
        country=data.recipient_address.region_code or "",
    )

    items = [
        OrderItem(sku=key, quantity=value.get("quantity"), price=value.get("price"))
        for key, value in line_items.items()
    ]

    order_data = Order(
        order_id=data.id,
        channel_uid=channel_uid,
        payment_status="PAID" if data.paid_time is not None else "Pending",
        purchase_date=datetime.fromtimestamp(data.paid_time).isoformat(),
        order_status=data.status,
        shipping_address=shipping_address,
        items=items,
        payment_method=data.payment_method_name,
        currency=data.line_items[0].currency,
        total_price=float(data.payment.total_amount),
        order_meta={
            "delivery_option_id": data.delivery_option_id,
            # Package IDs may be multiple
            "package_id": data.line_items[0].package_id,
            "region_id": "",
            "site_id": "",
            "line_item_ids": line_item_ids,
            "shipping_providers": shipping_providers,
        },
    )

    return asdict(order_data)
