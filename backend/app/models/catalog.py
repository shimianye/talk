"""商品目录相关模型：商品、SKU、价格、来源、门店商品、库存、促销。"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    """商品（机型）。"""

    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    series: Mapped[str | None] = mapped_column(String(128))
    release_date: Mapped[str | None] = mapped_column(String(16))
    official_url: Mapped[str | None] = mapped_column(String(512))
    source_date: Mapped[str | None] = mapped_column(String(16))


class ProductVariant(Base):
    """SKU 规格（参数）。对应 phone_specs.xlsx 的 specifications 表。"""

    __tablename__ = "product_variants"

    variant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.product_id", ondelete="CASCADE"), index=True, nullable=False
    )
    ram: Mapped[str | None] = mapped_column(String(64))
    storage: Mapped[str | None] = mapped_column(String(32))
    color: Mapped[str | None] = mapped_column(String(255))
    processor: Mapped[str | None] = mapped_column(String(128))
    screen_size: Mapped[str | None] = mapped_column(String(64))
    screen_type: Mapped[str | None] = mapped_column(String(255))
    refresh_rate: Mapped[str | None] = mapped_column(String(32))
    resolution: Mapped[str | None] = mapped_column(String(64))
    rear_camera: Mapped[str | None] = mapped_column(String(255))
    front_camera: Mapped[str | None] = mapped_column(String(128))
    battery: Mapped[str | None] = mapped_column(String(128))
    charging_wired: Mapped[str | None] = mapped_column(String(255))
    charging_wireless: Mapped[str | None] = mapped_column(String(255))
    network: Mapped[str | None] = mapped_column(String(64))
    wifi: Mapped[str | None] = mapped_column(String(64))
    bluetooth: Mapped[str | None] = mapped_column(String(64))
    nfc: Mapped[str | None] = mapped_column(String(64))
    dual_sim: Mapped[str | None] = mapped_column(String(255))
    weight: Mapped[str | None] = mapped_column(String(32))
    dimensions: Mapped[str | None] = mapped_column(String(64))
    waterproof: Mapped[str | None] = mapped_column(String(32))
    operating_system: Mapped[str | None] = mapped_column(String(64))


class Price(Base):
    """官方指导价。对应 phone_specs.xlsx 的 variants 表。"""

    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("product_variants.variant_id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.product_id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[str | None] = mapped_column(String(32))
    official_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    price_type: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(512))
    effective_date: Mapped[str | None] = mapped_column(String(16))


class Source(Base):
    """知识/参数来源元数据。"""

    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str | None] = mapped_column(String(64), index=True)
    source_type: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(String(512))
    page_title: Mapped[str | None] = mapped_column(String(255))
    fetch_date: Mapped[str | None] = mapped_column(String(16))
    is_official: Mapped[str | None] = mapped_column(String(8))
    applicable_version: Mapped[str | None] = mapped_column(String(64))
    source_priority: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[str | None] = mapped_column(String(64))
    data_status: Mapped[str | None] = mapped_column(String(64))
    conflict_note: Mapped[str | None] = mapped_column(Text)


class StoreProduct(Base):
    """门店在售商品（含售价、促销、成本）。对应 store_products 表。"""

    __tablename__ = "store_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("product_variants.variant_id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.product_id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str | None] = mapped_column(String(64))
    listing_status: Mapped[str | None] = mapped_column(String(32))
    original_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    promotion_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    price_type: Mapped[str | None] = mapped_column(String(32))
    promotion_id: Mapped[str | None] = mapped_column(String(64))
    price_effective_from: Mapped[str | None] = mapped_column(String(16))
    price_effective_to: Mapped[str | None] = mapped_column(String(16))
    cost_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    margin_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))
    on_shelf_date: Mapped[str | None] = mapped_column(String(16))
    category: Mapped[str | None] = mapped_column(String(64))


class Inventory(Base):
    """仓库库存。"""

    __tablename__ = "inventory"

    inventory_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    variant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("product_variants.variant_id", ondelete="CASCADE"), index=True, nullable=False
    )
    warehouse: Mapped[str | None] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    available_qty: Mapped[int] = mapped_column(Integer, default=0)
    reserved_qty: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(32))


class Promotion(Base):
    """促销活动 / 优惠券。"""

    __tablename__ = "promotions"

    promo_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    promo_type: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    discount_type: Mapped[str | None] = mapped_column(String(64))
    discount_value: Mapped[float | None] = mapped_column(Numeric(12, 2))
    min_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    applicable_products: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[str | None] = mapped_column(String(16))
    end_date: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str | None] = mapped_column(String(32))
    stackable: Mapped[str | None] = mapped_column(String(8))
