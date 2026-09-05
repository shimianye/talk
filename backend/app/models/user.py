"""用户与角色模型（RBAC）。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Role(Base):
    """角色：consumer / agent / supervisor / admin。"""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 数据库内部角色主键。
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # 稳定角色代码。
    description: Mapped[str | None] = mapped_column(String(255))  # 面向管理端的中文说明。

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles", back_populates="roles"
    )


class User(Base, TimestampMixin):
    """系统用户（消费者 / 客服 / 主管 / 管理员）。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 数据库内部自增主键。
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # 业务用户 ID。
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 登录账号。
    display_name: Mapped[str | None] = mapped_column(String(64))  # 前端展示名称。
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt 哈希，禁止保存明文。
    email: Mapped[str | None] = mapped_column(String(128))  # 可选联系邮箱。
    phone: Mapped[str | None] = mapped_column(String(32))  # 可选手机号，输出前需脱敏。
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 是否允许登录。

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles", back_populates="users"
    )


class UserRole(Base):
    """用户-角色关联表。"""

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(  # 指向 users.id，而非业务字符串 user_id。
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(  # 指向 roles.id。
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
