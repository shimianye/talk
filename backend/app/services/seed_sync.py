"""业务种子数据的校验、指纹计算与 PostgreSQL 幂等同步。"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import hash_password
from app.models import (
    AfterSalesCase, EvaluationItem, IntentTaxonomy, Inventory, LogisticsPackage,
    Order, Price, Product, ProductVariant, Promotion, Role, Source, StoreProduct,
    SyncManifest, User, UserRole,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"
DEFAULT_PASSWORD = "password123"
SYNC_DOMAIN = "business-seed"
SYNC_VERSION = "seed-v1"
_SEED_FILES = (
    "business_data.xlsx", "evaluation_dataset.xlsx", "intent_taxonomy.xlsx",
    "phone_specs.xlsx", "sources.xlsx",
)


def parse_datetime(value: Any) -> datetime | None:
    """将 Excel 日期、日期时间或字符串统一转换为 datetime。"""
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间值: {raw}")


def load_rows(path: Path, sheet: str) -> tuple[tuple[Any, ...], list[tuple[Any, ...]]]:
    """以只读模式加载 Excel 工作表，返回表头和数据行。"""
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        rows = workbook[sheet].iter_rows(values_only=True)
        return tuple(next(rows)), [tuple(row) for row in rows]
    finally:
        workbook.close()


def rows_to_dicts(
    header: tuple[Any, ...], rows: list[tuple[Any, ...]], *,
    datetime_cols: set[str] | None = None,
) -> list[dict[str, Any]]:
    """按表头转换 Excel 行，并对指定时间列执行严格解析。"""
    date_columns = datetime_cols or set()
    return [
        {
            str(key): parse_datetime(value) if key in date_columns else value
            for key, value in zip(header, row)
        }
        for row in rows
    ]


def seed_fingerprint(data_dir: Path = DEFAULT_DATA_DIR) -> str:
    """计算全部受管 xlsx 内容与同步器版本的稳定 SHA-256。"""
    digest = hashlib.sha256(SYNC_VERSION.encode("ascii"))
    for filename in _SEED_FILES:
        digest.update(filename.encode("utf-8"))
        digest.update((data_dir / filename).read_bytes())
    return digest.hexdigest()


def validate_source_integrity(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, list[str]]:
    """校验订单时间序、外键引用和已选自然冲突键。"""
    anomalies: dict[str, list[str]] = {
        "time_order": [], "orphan_logistics": [], "orphan_after_sales": [],
        "orphan_variant": [], "duplicate_natural_key": [],
    }
    order_header, orders = load_rows(data_dir / "business_data.xlsx", "orders")
    order_idx = {str(key): index for index, key in enumerate(order_header)}
    order_ids = {row[order_idx["order_id"]] for row in orders}
    for row in orders:
        times = [parse_datetime(row[order_idx[key]]) for key in
                 ("create_time", "pay_time", "ship_time", "receive_time")]
        if any(left and right and left > right for left, right in zip(times, times[1:])):
            anomalies["time_order"].append(str(row[order_idx["order_id"]]))

    variant_header, variants = load_rows(data_dir / "phone_specs.xlsx", "specifications")
    variant_idx = {str(key): index for index, key in enumerate(variant_header)}
    variant_ids = {row[variant_idx["variant_id"]] for row in variants}
    anomalies["orphan_variant"] = [
        str(row[order_idx["order_id"]]) for row in orders
        if row[order_idx["variant_id"]] not in variant_ids
    ]

    logistics_header, logistics = load_rows(data_dir / "business_data.xlsx", "logistics")
    logistics_idx = {str(key): index for index, key in enumerate(logistics_header)}
    anomalies["orphan_logistics"] = [
        str(row[logistics_idx["order_id"]]) for row in logistics
        if row[logistics_idx["order_id"]] not in order_ids
    ]
    after_header, cases = load_rows(data_dir / "business_data.xlsx", "after_sales_cases")
    after_idx = {str(key): index for index, key in enumerate(after_header)}
    anomalies["orphan_after_sales"] = [
        str(row[after_idx["order_id"]]) for row in cases
        if row[after_idx["order_id"]] not in order_ids
    ]

    unique_columns = (
        ("phone_specs.xlsx", "variants", "variant_id"),
        ("business_data.xlsx", "store_products", "sku"),
        ("evaluation_dataset.xlsx", "evaluation", "id"),
        ("evaluation_dataset.xlsx", "evaluation", "question"),
    )
    for filename, sheet, column in unique_columns:
        header, rows = load_rows(data_dir / filename, sheet)
        index = tuple(str(key) for key in header).index(column)
        values = [row[index] for row in rows]
        if any(value is None or str(value).strip() == "" for value in values):
            anomalies["duplicate_natural_key"].append(f"{filename}/{sheet}.{column}: blank")
        elif len(values) != len(set(values)):
            anomalies["duplicate_natural_key"].append(f"{filename}/{sheet}.{column}: duplicate")
    return anomalies


async def _upsert_rows(
    session: AsyncSession, model: type, rows: list[dict[str, Any]],
    conflict_columns: tuple[str, ...], *, immutable_columns: set[str] | None = None,
) -> int:
    """使用 PostgreSQL ON CONFLICT 批量插入或更新 ORM 表。"""
    if not rows:
        return 0
    table = model.__table__
    statement = pg_insert(table).values(rows)
    immutable = set(conflict_columns) | (immutable_columns or set())
    supplied = set().union(*(row.keys() for row in rows))
    updates = {
        column.name: getattr(statement.excluded, column.name)
        for column in table.columns
        if column.name in supplied and column.name not in immutable and not column.primary_key
    }
    statement = (
        statement.on_conflict_do_update(index_elements=list(conflict_columns), set_=updates)
        if updates else statement.on_conflict_do_nothing(index_elements=list(conflict_columns))
    )
    await session.execute(statement)
    return len(rows)


def _sheet_records(
    data_dir: Path, filename: str, sheet: str, *,
    datetime_cols: set[str] | None = None,
) -> list[dict[str, Any]]:
    """加载一个种子工作表并转换为可写记录。"""
    header, rows = load_rows(data_dir / filename, sheet)
    return rows_to_dicts(header, rows, datetime_cols=datetime_cols)


async def _sync_roles_and_users(session: AsyncSession, data_dir: Path) -> dict[str, int]:
    """同步固定员工，并从订单和售后数据派生消费者及角色关系。"""
    role_rows = [
        {"name": "consumer", "description": "普通消费者"},
        {"name": "agent", "description": "人工客服"},
        {"name": "supervisor", "description": "客服主管"},
        {"name": "admin", "description": "系统管理员"},
    ]
    await _upsert_rows(session, Role, role_rows, ("name",))
    role_ids = dict((await session.execute(select(Role.name, Role.id))).all())

    order_header, orders = load_rows(data_dir / "business_data.xlsx", "orders")
    order_idx = {str(key): index for index, key in enumerate(order_header)}
    consumers = {
        str(row[order_idx["user_id"]]): str(row[order_idx["user_name"]] or row[order_idx["user_id"]])
        for row in orders if row[order_idx["user_id"]]
    }
    after_header, cases = load_rows(data_dir / "business_data.xlsx", "after_sales_cases")
    after_idx = {str(key): index for index, key in enumerate(after_header)}
    for row in cases:
        if row[after_idx["user_id"]]:
            consumers.setdefault(str(row[after_idx["user_id"]]), str(row[after_idx["user_id"]]))

    staff = (
        ("admin1", "管理员", "admin"), ("supervisor1", "主管小王", "supervisor"),
        ("agent1", "客服A", "agent"), ("agent2", "客服B", "agent"),
    )
    password = hash_password(DEFAULT_PASSWORD)
    user_rows = [
        {"user_id": uid, "username": uid, "display_name": name,
         "hashed_password": password, "is_active": True}
        for uid, name in consumers.items()
    ] + [
        {"user_id": uid, "username": uid, "display_name": name,
         "hashed_password": password, "is_active": True}
        for uid, name, _ in staff
    ]
    await _upsert_rows(session, User, user_rows, ("user_id",), immutable_columns={"hashed_password"})
    user_ids = dict((await session.execute(select(User.user_id, User.id))).all())
    links = [
        {"user_id": user_ids[uid], "role_id": role_ids["consumer"]} for uid in consumers
    ] + [
        {"user_id": user_ids[uid], "role_id": role_ids[role]} for uid, _, role in staff
    ]
    await _upsert_rows(session, UserRole, links, ("user_id", "role_id"))
    return {"roles": len(role_rows), "staff": len(staff), "consumers": len(consumers)}


async def validate_database_seed(
    session: AsyncSession, data_dir: Path = DEFAULT_DATA_DIR
) -> dict[str, int]:
    """校验关键计数、自然键唯一性和全部源业务键均已入库。"""
    models = {
        "products": Product, "product_variants": ProductVariant, "prices": Price,
        "store_products": StoreProduct, "inventory": Inventory, "orders": Order,
        "evaluation_dataset": EvaluationItem,
    }
    counts = {name: int(await session.scalar(select(func.count()).select_from(model)) or 0)
              for name, model in models.items()}
    minimums = {"products": 9, "product_variants": 31, "prices": 31,
                "store_products": 31, "inventory": 72, "orders": 50,
                "evaluation_dataset": 100}
    failures = [f"{name}={counts[name]}<{minimum}" for name, minimum in minimums.items()
                if counts[name] < minimum]
    if failures:
        raise ValueError("种子数据库后置校验失败: " + ", ".join(failures))
    for label, column in (
        ("prices.variant_id", Price.variant_id),
        ("store_products.sku", StoreProduct.sku),
        ("evaluation_dataset.question", EvaluationItem.question),
    ):
        total = int(await session.scalar(select(func.count(column))) or 0)
        distinct = int(await session.scalar(select(func.count(func.distinct(column)))) or 0)
        if total != distinct:
            raise ValueError(f"入库唯一性校验失败: {label}")

    key_checks = (
        ("products", Product.product_id, "phone_specs.xlsx", "products", "product_id"),
        ("product_variants", ProductVariant.variant_id, "phone_specs.xlsx", "specifications", "variant_id"),
        ("prices", Price.variant_id, "phone_specs.xlsx", "variants", "variant_id"),
        ("store_products", StoreProduct.sku, "business_data.xlsx", "store_products", "sku"),
        ("inventory", Inventory.inventory_id, "business_data.xlsx", "inventory", "inventory_id"),
        ("orders", Order.order_id, "business_data.xlsx", "orders", "order_id"),
        ("evaluation_dataset", EvaluationItem.id, "evaluation_dataset.xlsx", "evaluation", "id"),
    )
    for label, database_column, filename, sheet, source_column in key_checks:
        header, rows = load_rows(data_dir / filename, sheet)
        index = tuple(str(key) for key in header).index(source_column)
        expected = {row[index] for row in rows}
        actual = set((await session.execute(select(database_column))).scalars().all())
        missing = expected - actual
        if missing:
            preview = sorted(str(value) for value in missing)[:3]
            raise ValueError(f"入库业务键缺失: {label} {preview}")
    return counts


async def reset_seed_data(session: AsyncSession) -> None:
    """显式清空受管种子表；CASCADE 同时清理其运行期依赖。"""
    tables = (
        "evaluation_dataset", "intent_taxonomy", "after_sales_cases",
        "logistics_packages", "orders", "inventory", "store_products", "promotions",
        "sources", "prices", "product_variants", "products", "user_roles", "users", "roles",
    )
    await session.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    await session.execute(text("DELETE FROM sync_manifests WHERE sync_domain = :domain"),
                          {"domain": SYNC_DOMAIN})


async def sync_seed_data(
    session: AsyncSession, data_dir: Path = DEFAULT_DATA_DIR, *, reset: bool = False,
) -> dict[str, Any]:
    """在调用方事务内幂等同步全部业务种子并更新 manifest。"""
    data_dir = data_dir.resolve()
    anomalies = validate_source_integrity(data_dir)
    if any(anomalies.values()):
        raise ValueError(f"种子源数据完整性异常: {anomalies}")
    fingerprint = seed_fingerprint(data_dir)
    if reset:
        await reset_seed_data(session)
    else:
        manifest = await session.get(SyncManifest, SYNC_DOMAIN)
        if manifest and manifest.content_hash == fingerprint and manifest.sync_version == SYNC_VERSION:
            try:
                return {"skipped": True, "content_hash": fingerprint,
                        "counts": await validate_database_seed(session, data_dir)}
            except ValueError:
                pass

    counts: dict[str, Any] = {"users": await _sync_roles_and_users(session, data_dir)}
    jobs = (
        ("products", Product, _sheet_records(data_dir, "phone_specs.xlsx", "products"), ("product_id",)),
        ("product_variants", ProductVariant, _sheet_records(data_dir, "phone_specs.xlsx", "specifications"), ("variant_id",)),
        ("prices", Price, _sheet_records(data_dir, "phone_specs.xlsx", "variants"), ("variant_id",)),
        ("sources", Source, _sheet_records(data_dir, "sources.xlsx", "sources"), ("source_id",)),
        ("store_products", StoreProduct, _sheet_records(data_dir, "business_data.xlsx", "store_products"), ("sku",)),
        ("inventory", Inventory, _sheet_records(data_dir, "business_data.xlsx", "inventory"), ("inventory_id",)),
        ("promotions", Promotion, _sheet_records(data_dir, "business_data.xlsx", "promotions"), ("promo_id",)),
        ("orders", Order, _sheet_records(data_dir, "business_data.xlsx", "orders",
          datetime_cols={"create_time", "pay_time", "ship_time", "receive_time"}), ("order_id",)),
        ("logistics", LogisticsPackage, _sheet_records(data_dir, "business_data.xlsx", "logistics",
          datetime_cols={"ship_time", "last_update", "sign_time"}), ("logistics_id",)),
        ("after_sales_cases", AfterSalesCase, _sheet_records(data_dir, "business_data.xlsx", "after_sales_cases",
          datetime_cols={"create_time", "resolve_time"}), ("case_id",)),
        ("intent_taxonomy", IntentTaxonomy, _sheet_records(data_dir, "intent_taxonomy.xlsx", "intent_taxonomy"), ("intent_id",)),
        ("evaluation_dataset", EvaluationItem, _sheet_records(data_dir, "evaluation_dataset.xlsx", "evaluation"), ("id",)),
    )
    for name, model, records, conflicts in jobs:
        counts[name] = await _upsert_rows(session, model, records, conflicts)
    database_counts = await validate_database_seed(session, data_dir)
    statement = pg_insert(SyncManifest.__table__).values(
        sync_domain=SYNC_DOMAIN, content_hash=fingerprint, sync_version=SYNC_VERSION,
        statistics={"rows": counts, "database_counts": database_counts}, completed_at=func.now(),
    )
    await session.execute(statement.on_conflict_do_update(
        index_elements=["sync_domain"],
        set_={"content_hash": statement.excluded.content_hash,
              "sync_version": statement.excluded.sync_version,
              "statistics": statement.excluded.statistics, "completed_at": func.now()},
    ))
    return {"skipped": False, "content_hash": fingerprint, "counts": counts,
            "database_counts": database_counts}
