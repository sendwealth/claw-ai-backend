"""
消息模型
"""

from sqlalchemy import String, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.base import Base


class MessageRole(str, enum.Enum):
    """消息角色"""
    USER = "user"  # 用户消息
    ASSISTANT = "assistant"  # AI 消息
    SYSTEM = "system"  # 系统消息


class Message(Base):
    """消息表"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 消息内容
    tokens: Mapped[int | None] = mapped_column(default=None)  # Token 数量
    cost: Mapped[float | None] = mapped_column(default=None)  # 成本（单位：元）

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, content={self.content[:50]...})>"
