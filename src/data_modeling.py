from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class SaleTerm:
    id: str
    name: str
    value_id: str | None
    value_name: str | None


@dataclass
class Picture:
    id: str
    url: str
    secure_url: str
    size: str
    max_size: str
    quality: str


@dataclass
class Description:
    id: str


@dataclass
class FreeShippingRule:
    default: bool
    free_mode: str
    free_shipping_flag: bool
    value: Decimal | None


@dataclass
class FreeMethod:
    id: int
    rule: FreeShippingRule


@dataclass
class AddressLocation:
    id: str
    name: str


@dataclass
class SearchLocation:
    neighborhood: AddressLocation
    city: AddressLocation
    state: AddressLocation


@dataclass
class SellerAddress:
    city: AddressLocation
    state: AddressLocation
    country: AddressLocation
    search_location: SearchLocation
    id: int


@dataclass
class Shipping:
    mode: str
    free_methods: list[FreeMethod]
    tags: list[str]
    dimensions: str | None
    local_pick_up: bool
    free_shipping: bool
    logistic_type: str
    store_pick_up: bool


@dataclass
class Attribute:
    id: str
    name: str
    value_id: str | None
    value_name: str | None
    attribute_group_id: str | None = None
    attribute_group_name: str | None = None
    value_type: str | None = None


@dataclass
class VariationAttribute:
    id: str
    name: str
    value_id: str | None
    value_name: str | None
    value_type: str


@dataclass
class Variation:
    id: int
    price: Decimal
    attribute_combinations: list[VariationAttribute]
    available_quantity: int
    sale_terms: list[SaleTerm]
    picture_ids: list[str]
    catalog_product_id: str | None
    sold_quantity: int | None = None


@dataclass
class Item:
    id: str
    site_id: str
    title: str
    seller_id: int
    category_id: str
    price: Decimal
    base_price: Decimal
    currency_id: str
    initial_quantity: int
    available_quantity: int
    buying_mode: str
    listing_type_id: str
    start_time: str
    condition: str
    permalink: str
    thumbnail_id: str
    thumbnail: str
    pictures: list[Picture]
    descriptions: list[Description]
    sale_terms: list[SaleTerm]
    accepts_mercadopago: bool
    non_mercado_pago_payment_methods: list[Any]
    shipping: Shipping
    international_delivery_mode: str
    seller_address: SellerAddress
    location: dict[str, Any]
    coverage_areas: list[Any]
    attributes: list[Attribute]
    listing_source: str
    variations: list[Variation]
    status: str
    sub_status: list[str]
    tags: list[str]
    warranty: str
    domain_id: str
    deal_ids: list[str]
    automatic_relist: bool
    date_created: str
    last_updated: str
    catalog_listing: bool
    official_store_id: int | None = None
    original_price: Decimal | None = None
    sold_quantity: int | None = None
    historical_start_time: str | None = None
    stop_time: str | None = None
    video_id: str | None = None
    seller_contact: dict[str, Any] | None = None
    catalog_product_id: str | None = None
    parent_item_id: str | None = None
    total_listing_fee: Decimal | None = None
    health: Decimal | None = None
    channels: list[str] | None = None
    bundle: Any | None = None


@dataclass
class Credentials:
    client_id: str | None
    secret_key: str | None
    access_token: str | None
    refresh_token: str | None
    access_token_expiration_date: str | None
    refresh_token_expiration_date: str | None
