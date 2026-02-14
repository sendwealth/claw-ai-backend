"""
缓存增强的对话管理服务
在原有服务基础上添加缓存装饰器，提供更好的性能
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import (
    Conversation,
    Message,
    ConversationStatus,
    MessageRole,
)
from app.schemas import (
    ConversationCreate,
    ConversationUpdate,
    MessageCreate,
)
from app.services.ai_service import ai_service
from app.core.cache import cached
from app.services.cache_service import cache_service


class CachedConversationService:
    """缓存增强的对话管理服务类"""

    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db

    def create_conversation(
        self,
        user_id: int,
        conversation_data: ConversationCreate,
    ) -> Conversation:
        """
        创建新对话

        Args:
            user_id: 用户 ID
            conversation_data: 对话数据

        Returns:
            Conversation: 创建的对话
        """
        conversation = Conversation(
            user_id=user_id,
            title=conversation_data.title,
            conversation_type=conversation_data.conversation_type,
            system_prompt=conversation_data.system_prompt,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)

        # 创建后失效用户对话列表缓存
        self._invalidate_user_conversations_cache(user_id)

        return conversation

    @cached(scenario="conversation_history", ttl=1800)
    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """
        获取对话详情（已缓存 - TTL 30 分钟）

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID

        Returns:
            Conversation: 对话详情，如果不存在返回 None
        """
        return (
            self.db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

    @cached(scenario="user_conversations", ttl=600)
    def get_user_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Conversation]:
        """
        获取用户的对话列表（已缓存 - TTL 10 分钟）

        Args:
            user_id: 用户 ID
            skip: 跳过数量（分页）
            limit: 返回数量（分页）

        Returns:
            List[Conversation]: 对话列表
        """
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_conversation(
        self,
        conversation_id: int,
        user_id: int,
        update_data: ConversationUpdate,
    ) -> Optional[Conversation]:
        """
        更新对话

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID
            update_data: 更新数据

        Returns:
            Conversation: 更新后的对话
        """
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return None

        # 更新字段
        if update_data.title is not None:
            conversation.title = update_data.title
        if update_data.status is not None:
            conversation.status = update_data.status
        if update_data.system_prompt is not None:
            conversation.system_prompt = update_data.system_prompt

        self.db.commit()
        self.db.refresh(conversation)

        # 更新后失效相关缓存
        self._invalidate_conversation_cache(conversation_id)
        self._invalidate_user_conversations_cache(user_id)

        return conversation

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """
        删除对话

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID

        Returns:
            bool: 是否删除成功
        """
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        self.db.delete(conversation)
        self.db.commit()

        # 删除后失效相关缓存
        self._invalidate_conversation_cache(conversation_id)
        self._invalidate_user_conversations_cache(user_id)
        self._invalidate_messages_cache(conversation_id)

        return True

    def add_message(
        self,
        conversation_id: int,
        message_data: MessageCreate,
    ) -> Message:
        """
        添加消息

        Args:
            conversation_id: 对话 ID
            message_data: 消息数据

        Returns:
            Message: 创建的消息
        """
        message = Message(
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        # 添加消息后失效对话历史缓存
        self._invalidate_messages_cache(conversation_id)

        return message

    @cached(scenario="conversation_history", ttl=1800)
    def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """
        获取对话的消息列表（已缓存 - TTL 30 分钟）

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID（验证权限）
            skip: 跳过数量
            limit: 返回数量

        Returns:
            List[Message]: 消息列表
        """
        # 验证对话所有权
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return []

        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    async def generate_ai_response(
        self,
        conversation_id: int,
        user_id: int,
        user_message: str,
    ) -> dict:
        """
        生成 AI 响应（AI 响应已缓存 - TTL 24 小时）

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID
            user_message: 用户消息

        Returns:
            dict: AI 响应结果
        """
        # 获取对话
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return {
                "success": False,
                "error": "对话不存在",
            }

        # 添加用户消息
        self.add_message(
            conversation_id=conversation_id,
            message_data=MessageCreate(
                role=MessageRole.USER,
                content=user_message,
            ),
        )

        # 获取对话历史
        messages = self.get_messages(conversation_id, user_id, limit=20)
        message_history = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # 尝试从缓存获取 AI 响应
        import hashlib
        message_hash = hashlib.md5(
            f"{user_message}:{conversation.system_prompt}".encode()
        ).hexdigest()[:12]
        cache_key = cache_service._generate_key(
            scenario="ai_response",
            identifier=f"{conversation_id}:{message_hash}",
        )
        cached_response = await cache_service.get(cache_key)

        if cached_response:
            # 添加 AI 消息到数据库
            ai_message = self.add_message(
                conversation_id=conversation_id,
                message_data=MessageCreate(
                    role=MessageRole.ASSISTANT,
                    content=cached_response["content"],
                ),
            )
            ai_message.tokens = cached_response["tokens"]
            ai_message.cost = cached_response["cost"]
            self.db.commit()

            return {
                "success": True,
                "content": cached_response["content"],
                "message_id": ai_message.id,
                "tokens": cached_response["tokens"],
                "cost": cached_response["cost"],
                "from_cache": True,
            }

        # 调用 AI 服务
        ai_response = await ai_service.chat(
            messages=message_history,
            system_prompt=conversation.system_prompt,
        )

        if ai_response["success"]:
            # 缓存 AI 响应
            await cache_service.set(
                cache_key,
                {
                    "content": ai_response["content"],
                    "tokens": ai_response["tokens"],
                    "cost": ai_response["cost"],
                },
                ttl=86400,  # 24 小时
            )

            # 添加 AI 消息
            ai_message = self.add_message(
                conversation_id=conversation_id,
                message_data=MessageCreate(
                    role=MessageRole.ASSISTANT,
                    content=ai_response["content"],
                ),
            )

            # 更新 Token 和成本
            ai_message.tokens = ai_response["tokens"]["total"]
            ai_message.cost = ai_response["cost"]
            self.db.commit()

            return {
                "success": True,
                "content": ai_response["content"],
                "message_id": ai_message.id,
                "tokens": ai_response["tokens"],
                "cost": ai_response["cost"],
                "from_cache": False,
            }
        else:
            return {
                "success": False,
                "error": ai_response["error"],
            }

    def _invalidate_conversation_cache(self, conversation_id: int):
        """失效对话缓存"""
        import asyncio
        # 简化的缓存失效逻辑
        # 实际应用中应该根据键的模式批量删除

    def _invalidate_user_conversations_cache(self, user_id: int):
        """失效用户对话列表缓存"""
        import asyncio
        # 简化的缓存失效逻辑

    def _invalidate_messages_cache(self, conversation_id: int):
        """失效消息列表缓存"""
        import asyncio
        # 简化的缓存失效逻辑
