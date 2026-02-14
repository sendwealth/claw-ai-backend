"""
WebSocket 路由
处理实时消息推送
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.api.websocket import manager
from app.api.dependencies import get_current_user, get_optional_current_user
from app.models.user import User

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT 访问令牌"),
    db: Session = Depends(get_db),
):
    """
    WebSocket 端点

    连接时需要提供有效的 JWT Token。

    参数:
        token: JWT 访问令牌

    示例:
        ws://localhost:8000/api/v1/ws?token=your_jwt_token_here
    """
    try:
        # 验证 Token 并获取用户
        current_user = await _get_user_from_token(token, db)
        if not current_user:
            await websocket.close(code=1008, reason="无效的认证凭据")
            return

        # 连接 WebSocket
        await manager.connect(current_user.id, websocket)

        try:
            # 发送欢迎消息
            await manager.send_personal_message(
                current_user.id,
                {
                    "type": "connected",
                    "message": f"欢迎, {current_user.name or current_user.email}!",
                    "user_id": current_user.id,
                }
            )

            # 持续接收消息
            while True:
                # 接收客户端消息
                data = await websocket.receive_json()

                # 处理不同类型的消息
                await _handle_websocket_message(current_user.id, data, db)

        except WebSocketDisconnect:
            manager.disconnect(current_user.id, websocket)

    except Exception as e:
        print(f"❌ WebSocket 错误: {e}")
        await websocket.close(code=1011, reason=str(e))


async def _get_user_from_token(token: str, db: Session) -> User:
    """
    从 Token 获取用户

    Args:
        token: JWT Token
        db: 数据库会话

    Returns:
        User: 用户，无效返回 None
    """
    from app.utils.security import decode_token
    from app.models.user import User

    # 解码 Token
    payload = decode_token(token)
    if not payload:
        return None

    # 提取邮箱
    email: str = payload.get("sub")
    if not email:
        return None

    # 查询用户
    user = db.query(User).filter(User.email == email).first()
    return user


async def _handle_websocket_message(user_id: int, data: dict, db: Session):
    """
    处理 WebSocket 消息

    Args:
        user_id: 用户 ID
        data: 消息数据
        db: 数据库会话
    """
    message_type = data.get("type")

    if message_type == "ping":
        # 心跳检测
        await manager.send_personal_message(
            user_id,
            {"type": "pong", "timestamp": data.get("timestamp")}
        )

    elif message_type == "chat":
        # 聊天消息
        from app.services.conversation_service import ConversationService

        conversation_id = data.get("conversation_id")
        user_message = data.get("message")

        if not conversation_id or not user_message:
            await manager.send_personal_message(
                user_id,
                {"type": "error", "message": "缺少必要参数"}
            )
            return

        # 生成 AI 响应
        service = ConversationService(db)
        result = await service.generate_ai_response(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=user_message,
        )

        if result["success"]:
            # 发送 AI 响应
            await manager.send_personal_message(
                user_id,
                {
                    "type": "chat_response",
                    "conversation_id": conversation_id,
                    "message_id": result["message_id"],
                    "content": result["content"],
                    "tokens": result["tokens"],
                    "cost": result["cost"],
                }
            )
        else:
            # 发送错误
            await manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": result.get("error", "AI 响应失败")
                }
            )

    elif message_type == "typing":
        # 输入状态
        # 可以广播给其他用户（如果实现了多用户聊天）
        pass

    else:
        # 未知消息类型
        await manager.send_personal_message(
            user_id,
            {"type": "error", "message": f"未知的消息类型: {message_type}"}
        )


@router.get("/ws/active_users")
async def get_active_users(
    current_user: User = Depends(get_current_user),
):
    """
    获取在线用户列表

    需要认证
    """
    active_users = manager.get_active_users()

    return {
        "total": len(active_users),
        "user_ids": active_users,
    }
