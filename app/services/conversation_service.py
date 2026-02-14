"""
对话管理服务
处理对话和消息的 CRUD 操作
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


class ConversationService:
    """对话管理服务类"""

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
        return conversation

    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        """
        获取对话详情

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

    def get_user_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Conversation]:
        """
        获取用户的对话列表

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
        return message

    def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """
        获取对话的消息列表

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
        生成 AI 响应

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

        # 调用 AI 服务
        ai_response = await ai_service.chat(
            messages=message_history,
            system_prompt=conversation.system_prompt,
        )

        if ai_response["success"]:
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
                "tokens": ai_message["tokens"],
                "cost": ai_message["cost"],
            }
        else:
            return {
                "success": False,
                "error": ai_response["error"],
            }
