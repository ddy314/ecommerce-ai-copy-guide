"""用户模型 - 支持普通用户和商家管理员双身份"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    """用户表 - 统一存储普通用户和商家管理员"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, comment="登录账号")
    password_hash: Mapped[str] = mapped_column(String(256), comment="密码哈希")
    password_plain: Mapped[str] = mapped_column(String(100), nullable=True, comment="明文密码（仅管理查看）")
    nickname: Mapped[str] = mapped_column(String(100), nullable=True, comment="昵称")
    role: Mapped[str] = mapped_column(String(20), default="user", comment="角色: user/merchant")
    avatar: Mapped[str] = mapped_column(String(500), nullable=True, comment="头像URL")
    phone: Mapped[str] = mapped_column(String(20), nullable=True, comment="手机号")
    email: Mapped[str] = mapped_column(String(200), nullable=True, comment="邮箱")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    display_id: Mapped[str] = mapped_column(String(64), nullable=True, unique=True, comment="展示ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname or self.username,
            "role": self.role,
            "avatar": self.avatar,
            "phone": self.phone,
            "email": self.email,
            "is_active": self.is_active,
            "display_id": self.display_id or "",
            "password": self.password_plain or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserAddress(Base):
    """用户收货地址"""
    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, comment="用户ID")
    name: Mapped[str] = mapped_column(String(100), comment="收货人姓名")
    phone: Mapped[str] = mapped_column(String(20), comment="联系电话")
    province: Mapped[str] = mapped_column(String(50), comment="省")
    city: Mapped[str] = mapped_column(String(50), comment="市")
    district: Mapped[str] = mapped_column(String(50), comment="区")
    detail: Mapped[str] = mapped_column(String(500), comment="详细地址")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认地址")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "recipient": self.name,
            "phone": self.phone,
            "province": self.province,
            "city": self.city,
            "district": self.district,
            "detail": self.detail,
            "is_default": self.is_default,
            "full_address": f"{self.province}{self.city}{self.district}{self.detail}",
        }


class UserFavorite(Base):
    """用户收藏"""
    __tablename__ = "user_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, comment="用户ID")
    product_id: Mapped[int] = mapped_column(Integer, comment="商品ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class BrowseHistory(Base):
    """浏览记录"""
    __tablename__ = "browse_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, comment="用户ID")
    product_id: Mapped[int] = mapped_column(Integer, comment="商品ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
