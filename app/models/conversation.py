"""
对话模型
"""

from sqlalchemy import String, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum

from app.db.base import Base


class ConversationStatus(str, enum.Enum):
    """对话状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ConversationType(str, enum.Enum):
    """对话类型"""
    CHAT = "chat"  # 普通聊天
    CONSULTING = "consulting"  # 咨询对话
    SUPPORT = "support"  # 客服支持


class Conversation(Base):
    """对话表"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    status: Mapped[str] = mapped_column(String(50), default=ConversationStatus.ACTIVE)
    conversation_type: Mapped[str] = mapped_column(String(50), default=ConversationType.CHAT)
    model: Mapped[str] = mapped_column(String(50), default="glm-4")  # 使用的 AI 模型
    system_prompt: Mapped[str | None] = mapped_column(Text)  # 系统提示词
    metadata: Mapped[dict | None] = mapped_column(default=None)  # 额外元数据

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title}, status={self.status})>"
