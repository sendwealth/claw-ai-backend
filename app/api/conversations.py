"""
对话相关 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
)
from app.services.conversation_service import ConversationService
from app.api.dependencies import get_current_user, get_current_active_user

router = APIRouter()


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """获取对话服务实例（依赖注入）"""
    return ConversationService(db)


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    创建新对话

    需要认证
    """
    conversation = service.create_conversation(
        user_id=current_user.id,
        conversation_data=conversation_data,
    )
    return conversation


@router.get("/", response_model=list[ConversationResponse])
async def get_conversations(
    skip: int = 0,
    limit: int = 100,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取当前用户的对话列表

    需要认证
    """
    conversations = service.get_user_conversations(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return conversations


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取对话详情（包含消息列表）

    需要认证
    """
    conversation = service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )

    messages = service.get_messages(conversation_id, current_user.id)

    return ConversationDetailResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        status=conversation.status,
        conversation_type=conversation.conversation_type,
        model=conversation.model,
        system_prompt=conversation.system_prompt,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageResponse(**msg.__dict__) for msg in messages],
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    更新对话

    需要认证
    """
    conversation = service.update_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id,
        update_data=update_data,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    删除对话

    需要认证
    """
    success = service.delete_conversation(conversation_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: int,
    message_data: MessageCreate,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    添加消息

    需要认证
    """
    # 验证对话是否存在
    conversation = service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在",
        )

    message = service.add_message(
        conversation_id=conversation_id,
        message_data=message_data,
    )
    return MessageResponse(**message.__dict__)


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取对话的消息列表

    需要认证
    """
    messages = service.get_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return MessageListResponse(
        total=len(messages),
        items=[MessageResponse(**msg.__dict__) for msg in messages],
    )


@router.post("/{conversation_id}/chat")
async def chat(
    conversation_id: int,
    user_message: str,
    service: ConversationService = Depends(get_conversation_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    发送消息并获取 AI 响应

    需要认证

    Request Body:
    {
        "message": "你好"
    }
    """
    result = await service.generate_ai_response(
        conversation_id=conversation_id,
        user_id=current_user.id,
        user_message=user_message,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "AI 响应失败"),
        )

    return {
        "content": result["content"],
        "message_id": result["message_id"],
        "tokens": result["tokens"],
        "cost": result["cost"],
    }
