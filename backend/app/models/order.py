"""订单、物流与售后模型。"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    """订单。时间字段满足 create ≤ pay ≤ ship ≤ receive 约束。"""

    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 对外订单号。
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), index=True, nullable=False
    )
    user_name: Mapped[str | None] = mapped_column(String(64))
    variant_id: Mapped[str | None] = mapped_column(String(64))
    product_name: Mapped[str | None] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # 下单时商品单价。
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # 优惠前商品总额。
    coupon_discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 优惠券减免金额。
    final_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # 用户实付金额。
    payment_method: Mapped[str | None] = mapped_column(String(64))
    order_status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # 待支付、已发货、已完成等状态。
    create_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pay_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ship_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    receive_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    address: Mapped[str | None] = mapped_column(Text)


class OrderItem(Base):
    """订单明细（从订单行拆分，支持一单多商品）。"""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orders.order_id", ondelete="CASCADE"), index=True, nullable=False
    )
    variant_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("product_variants.variant_id")
    )
    product_name: Mapped[str | None] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # 明细单价乘数量。


class LogisticsPackage(Base):
    """物流包裹。对应 logistics 表。"""

    __tablename__ = "logistics_packages"

    logistics_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orders.order_id", ondelete="CASCADE"), index=True, nullable=False
    )
    package_id: Mapped[str | None] = mapped_column(String(128))
    package_count: Mapped[int | None] = mapped_column(Integer)
    is_split_shipment: Mapped[str | None] = mapped_column(String(8))
    carrier: Mapped[str | None] = mapped_column(String(64))
    tracking_number: Mapped[str | None] = mapped_column(String(64))  # 承运商运单号。
    current_status: Mapped[str | None] = mapped_column(String(64))
    current_location: Mapped[str | None] = mapped_column(String(128))
    estimated_delivery: Mapped[str | None] = mapped_column(String(16))
    ship_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sign_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LogisticsEvent(Base):
    """物流轨迹事件（运行期/演示数据）。"""

    __tablename__ = "logistics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    logistics_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(64))
    location: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)


class AfterSalesCase(Base):
    """售后工单。对应 after_sales_cases 表。"""

    __tablename__ = "after_sales_cases"

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orders.order_id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    case_type: Mapped[str | None] = mapped_column(String(32))
    sub_type: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(32), index=True)
    create_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolve_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    compensation_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)  # 审批后的补偿金额，单位元。
    handler: Mapped[str | None] = mapped_column(String(64))
