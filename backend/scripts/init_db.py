"""初始化数据库：创建 pgvector 扩展 + 建表 + 导入种子数据。

用法（需先启动 PostgreSQL，例如 `docker compose up -d postgres`）：
    cd backend
    python scripts/init_db.py

说明：本脚本是「快速引导」路径，用 Base.metadata.create_all 建表；
Alembic 已配置可用于后续 schema 变更迁移（`alembic revision --autogenerate`）。
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# When invoked as ``python scripts/init_db.py`` Python places ``scripts/``
# (rather than the project root) on sys.path. Add the backend root so the
# ``app`` package resolves consistently both locally and inside the API image.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import openpyxl
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.models  # noqa: F401  触发全部模型注册
from app.config import settings
from app.core.rag.embedding import get_embedding_provider
from app.core.rag.ingest import ingest_kb_docs
from app.core.security.password import hash_password
from app.db.base import Base
from app.models.catalog import (
    Inventory,
    Price,
    Product,
    ProductVariant,
    Promotion,
    Source,
    StoreProduct,
)
from app.models.knowledge import EvaluationItem, IntentTaxonomy
from app.models.order import AfterSalesCase, LogisticsPackage, Order
from app.models.user import Role, User

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed"
KB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "kb-docs"

# 种子默认密码（演示用，生产务必更换）
DEFAULT_PASSWORD = "password123"


def parse_dt(v):
    """将字符串解析为 datetime，兼容日期/日期时间/空值。"""
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def load_rows(path: Path, sheet: str):
    """以只读模式加载 Excel 工作表，返回表头和数据行。"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    data = list(rows)
    wb.close()
    return header, data


def rows_to_dicts(header, rows, drop_cols=None, dt_cols=None):
    """按表头将 Excel 行转换为字典，并处理忽略列和时间列。"""
    drop_cols = set(drop_cols or [])
    dt_cols = set(dt_cols or [])
    out = []
    for r in rows:
        d = {}
        for h, v in zip(header, r):
            if h in drop_cols:
                continue
            d[h] = parse_dt(v) if h in dt_cols else v
        out.append(d)
    return out


async def import_sheet(session, path, sheet, model, drop_cols=None, dt_cols=None):
    """将指定工作表批量实例化为 ORM 对象，返回导入行数。"""
    header, rows = load_rows(path, sheet)
    dicts = rows_to_dicts(header, rows, drop_cols, dt_cols)
    session.add_all([model(**d) for d in dicts])
    await session.flush()
    return len(dicts)


async def seed_roles_users(session: AsyncSession) -> dict:
    """写入角色 + 用户（含从订单提取的消费者账号）。"""
    role_names = {
        "consumer": "普通消费者",
        "agent": "人工客服",
        "supervisor": "客服主管",
        "admin": "系统管理员",
    }
    roles = {}
    for name, desc in role_names.items():
        r = Role(name=name, description=desc)
        session.add(r)
        roles[name] = r
    await session.flush()

    # 演示员工账号
    staff = [
        ("admin1", "管理员", "admin"),
        ("supervisor1", "主管小王", "supervisor"),
        ("agent1", "客服A", "agent"),
        ("agent2", "客服B", "agent"),
    ]
    for uid, name, role_name in staff:
        u = User(
            user_id=uid,
            username=uid,
            display_name=name,
            hashed_password=hash_password(DEFAULT_PASSWORD),
            roles=[roles[role_name]],
        )
        session.add(u)

    # 从订单表提取消费者账号
    header, rows = load_rows(DATA_DIR / "business_data.xlsx", "orders")
    idx = {h: i for i, h in enumerate(header)}
    consumers: dict[str, str] = {}
    for r in rows:
        uid = r[idx["user_id"]]
        name = r[idx["user_name"]] if idx["user_name"] < len(r) else None
        if uid and uid not in consumers:
            consumers[uid] = name or uid
    for uid, name in consumers.items():
        session.add(
            User(
                user_id=uid,
                username=uid,
                display_name=name,
                hashed_password=hash_password(DEFAULT_PASSWORD),
                roles=[roles["consumer"]],
            )
        )
    await session.flush()
    return {"roles": len(roles), "staff": len(staff), "consumers": len(consumers)}


async def validate_seed_integrity() -> dict:
    """导入前校验：订单时间序 + 外键引用完整性。返回异常统计。"""
    anomalies = {"time_order": [], "orphan_logistics": [], "orphan_after_sales": [], "orphan_variant": []}

    oh, orders = load_rows(DATA_DIR / "business_data.xlsx", "orders")
    oi = {h: i for i, h in enumerate(oh)}
    order_ids = {r[oi["order_id"]] for r in orders}

    # 订单时间序：create ≤ pay ≤ ship ≤ receive
    for r in orders:
        times = [parse_dt(r[oi[k]]) for k in ("create_time", "pay_time", "ship_time", "receive_time")]
        for a, b in zip(times, times[1:]):
            if a and b and a > b:
                anomalies["time_order"].append(r[oi["order_id"]])
                break

    vh, variants = load_rows(DATA_DIR / "phone_specs.xlsx", "specifications")
    vi = {h: i for i, h in enumerate(vh)}
    variant_ids = {r[vi["variant_id"]] for r in variants}

    anomalies["orphan_variant"] = [
        r[oi["order_id"]] for r in orders if r[oi["variant_id"]] not in variant_ids
    ]

    lh, logistics = load_rows(DATA_DIR / "business_data.xlsx", "logistics")
    li = {h: i for i, h in enumerate(lh)}
    anomalies["orphan_logistics"] = [
        r[li["order_id"]] for r in logistics if r[li["order_id"]] not in order_ids
    ]

    ah, cases = load_rows(DATA_DIR / "business_data.xlsx", "after_sales_cases")
    ai = {h: i for i, h in enumerate(ah)}
    anomalies["orphan_after_sales"] = [
        r[ai["order_id"]] for r in cases if r[ai["order_id"]] not in order_ids
    ]
    return anomalies


async def main() -> None:
    """创建扩展和表，校验并导入业务种子数据，最后构建 RAG 索引。"""
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("[1/4] pgvector 扩展就绪")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("[2/5] 数据表已创建（23 张，含外键约束）")

    anomalies = await validate_seed_integrity()
    total_anomalies = sum(len(v) for v in anomalies.values())
    if total_anomalies:
        print("      ⚠️ 数据完整性异常:", anomalies)
    else:
        print("      ✓ 种子数据完整性校验通过（时间序 + 外键引用）")

    async with session_factory() as session:
        counts = await seed_roles_users(session)

        order_dt = {"create_time", "pay_time", "ship_time", "receive_time"}
        logistics_dt = {"ship_time", "last_update", "sign_time"}
        aftersales_dt = {"create_time", "resolve_time"}

        results = {}
        results["products"] = await import_sheet(
            session, DATA_DIR / "phone_specs.xlsx", "products", Product
        )
        results["product_variants"] = await import_sheet(
            session, DATA_DIR / "phone_specs.xlsx", "specifications", ProductVariant
        )
        results["prices"] = await import_sheet(
            session, DATA_DIR / "phone_specs.xlsx", "variants", Price
        )
        results["sources"] = await import_sheet(
            session, DATA_DIR / "sources.xlsx", "sources", Source
        )
        results["store_products"] = await import_sheet(
            session, DATA_DIR / "business_data.xlsx", "store_products", StoreProduct
        )
        results["inventory"] = await import_sheet(
            session, DATA_DIR / "business_data.xlsx", "inventory", Inventory
        )
        results["promotions"] = await import_sheet(
            session, DATA_DIR / "business_data.xlsx", "promotions", Promotion
        )
        results["orders"] = await import_sheet(
            session, DATA_DIR / "business_data.xlsx", "orders", Order, dt_cols=order_dt
        )
        results["logistics"] = await import_sheet(
            session,
            DATA_DIR / "business_data.xlsx",
            "logistics",
            LogisticsPackage,
            dt_cols=logistics_dt,
        )
        results["after_sales_cases"] = await import_sheet(
            session,
            DATA_DIR / "business_data.xlsx",
            "after_sales_cases",
            AfterSalesCase,
            dt_cols=aftersales_dt,
        )
        results["intent_taxonomy"] = await import_sheet(
            session, DATA_DIR / "intent_taxonomy.xlsx", "intent_taxonomy", IntentTaxonomy
        )
        results["evaluation_dataset"] = await import_sheet(
            session,
            DATA_DIR / "evaluation_dataset.xlsx",
            "evaluation",
            EvaluationItem,
            drop_cols={"id"},
        )

        await session.commit()

        print("[3/5] 种子数据导入完成")
        print("      用户/角色:", counts)
        for k, v in results.items():
            print(f"      {k}: {v} 行")

        # 知识库入库（RAG）
        embedding = get_embedding_provider()
        kb_stats = await ingest_kb_docs(session, KB_DIR, embedding)
        await session.commit()
        print("[4/5] 知识库入库完成:", kb_stats)

    await engine.dispose()
    print("[5/5] 数据库初始化完成 ✅")


if __name__ == "__main__":
    asyncio.run(main())
