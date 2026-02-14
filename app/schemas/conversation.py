"""
对话相关的 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.conversation import ConversationStatus, ConversationType


class ConversationBase(BaseModel):
    """对话基础模型"""
    title: Optional[str] = Field("新对话", max_length=200)
    conversation_type: Optional[ConversationType] = ConversationType.CHAT
    system_prompt: Optional[str] = None


class ConversationCreate(ConversationBase):
    """创建对话模型"""
    pass


class ConversationUpdate(BaseModel):
    """更新对话模型"""
    title: Optional[str] = None
    status: Optional[ConversationStatus] = None
    system_prompt: Optional[str] = None


class ConversationResponse(ConversationBase):
    """对话响应模型"""
    id: int
    user_id: int
    status: ConversationStatus
    model: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0  # 消息数量

    class Config:
        from_attributes = True


# ========== 消息相关 ==========

class MessageBase(BaseModel):
    """消息基础模型"""
    role: str  # user/assistant/system
    content: str


class MessageCreate(MessageBase):
    """创建消息模型"""
    conversation_id: int


class MessageResponse(MessageBase):
    """消息响应模型"""
    id: int
    conversation_id: int
    tokens: Optional[int] = None
    cost: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    """对话详情响应（包含消息列表）"""
    messages: List[MessageResponse] = []


class MessageListResponse(BaseModel):
    """消息列表响应"""
    total: int
    items: List[MessageResponse]
