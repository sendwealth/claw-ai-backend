"""
配置管理模型
支持配置的持久化存储、历史记录和审计
"""

from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Config(Base):
    """配置表：存储所有配置项"""

    __tablename__ = "configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    # 时间戳字段继承自 Base：created_at, updated_at

    # 关系
    history_records: Mapped[list["ConfigHistory"]] = relationship(
        "ConfigHistory", back_populates="config", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_config_key_public", "key", "is_public"),
    )

    def __repr__(self):
        return f"<Config(id={self.id}, key={self.key}, is_sensitive={self.is_sensitive})>"

    def mask_value(self) -> str:
        """脱敏显示配置值"""
        if not self.is_sensitive:
            return self.value
        # 敏感信息脱敏：只显示前后各 2 个字符
        if len(self.value) <= 4:
            return "******"
        return f"{self.value[:2]}{'*' * (len(self.value) - 4)}{self.value[-2:]}"


class ConfigHistory(Base):
    """配置历史表：记录配置变更历史"""

    __tablename__ = "config_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    config_id: Mapped[int] = mapped_column(Integer, ForeignKey("configs.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # 关系
    config: Mapped["Config"] = relationship("Config", back_populates="history_records")

    # 索引
    __table_args__ = (
        Index("idx_config_history_config_id", "config_id"),
        Index("idx_config_history_key", "key"),
        Index("idx_config_history_changed_at", "changed_at"),
    )

    def __repr__(self):
        return f"<ConfigHistory(id={self.id}, key={self.key}, version={self.version})>"

    def mask_old_value(self) -> str | None:
        """脱敏显示旧值"""
        if not self.old_value:
            return None
        # 获取对应的配置项来判断是否敏感
        # 这里简单处理：如果值长度 > 8 且包含特殊字符，可能是敏感信息
        if len(self.old_value) > 8:
            return f"{self.old_value[:2]}{'*' * (len(self.old_value) - 4)}{self.old_value[-2:]}"
        return "******" if len(self.old_value) > 4 else self.old_value

    def mask_new_value(self) -> str:
        """脱敏显示新值"""
        if not self.new_value:
            return ""
        if len(self.new_value) > 8:
            return f"{self.new_value[:2]}{'*' * (len(self.new_value) - 4)}{self.new_value[-2:]}"
        return "******" if len(self.new_value) > 4 else self.new_value
