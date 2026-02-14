"""
使用 Celery 异步任务处理对话的示例
展示如何将同步 AI 调用改为异步任务处理
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Conversation, Message, MessageRole
from app.tasks.ai_tasks import generate_ai_response
from app.services.conversation_service import ConversationService


class AsyncConversationService:
    """异步对话服务 - 使用 Celery 处理耗时任务"""

    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db

    async def send_message_async(
        self,
        conversation_id: str,
        user_message: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        发送消息（异步处理）

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息
            user_id: 用户 ID

        Returns:
            dict: 包含任务 ID 的响应，用于后续查询结果
        """
        # 1. 保存用户消息到数据库
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_message,
        )
        self.db.add(message)
        self.db.commit()

        # 2. 获取对话历史（用于上下文）
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise ValueError(f"对话不存在: {conversation_id}")

        # 获取最近的对话历史
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).limit(10).all()

        conversation_history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages[:-1]  # 排除当前用户消息
        ]

        # 3. 提交异步任务生成 AI 响应
        task = generate_ai_response.apply_async(
            kwargs={
                "conversation_id": conversation_id,
                "user_message": user_message,
                "conversation_history": conversation_history,
                "user_id": user_id,
            },
            queue="ai_high_priority",
            priority=8,
        )

        # 4. 返回任务信息
        return {
            "message_id": message.id,
            "task_id": task.id,
            "status": "PENDING",
            "message": "消息已发送，AI 响应正在生成中...",
        }

    async def get_async_result(
        self,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        获取异步任务结果

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务结果
        """
        from app.tasks.celery_app import celery_app

        # 获取任务结果
        result = celery_app.AsyncResult(task_id)

        if result.status == "PENDING":
            return {
                "task_id": task_id,
                "status": "PENDING",
                "message": "任务等待处理中...",
            }

        elif result.status == "STARTED":
            return {
                "task_id": task_id,
                "status": "STARTED",
                "message": "任务执行中...",
            }

        elif result.status == "SUCCESS":
            # 任务成功，保存 AI 响应到数据库
            task_result = result.result

            if isinstance(task_result, dict) and "response" in task_result:
                message = Message(
                    conversation_id=task_result["conversation_id"],
                    role=MessageRole.ASSISTANT,
                    content=task_result["response"],
                    tokens=task_result.get("tokens", {}).get("total"),
                    cost=task_result.get("cost"),
                )
                self.db.add(message)
                self.db.commit()

                return {
                    "task_id": task_id,
                    "status": "SUCCESS",
                    "message_id": message.id,
                    "response": task_result["response"],
                    "tokens": task_result.get("tokens"),
                    "cost": task_result.get("cost"),
                }

        elif result.status == "FAILURE":
            # 任务失败
            return {
                "task_id": task_id,
                "status": "FAILURE",
                "error": str(result.result) if result.result else "未知错误",
                "traceback": result.traceback,
            }

        elif result.status == "RETRY":
            return {
                "task_id": task_id,
                "status": "RETRY",
                "message": f"任务重试中（第 {result.info.get('retries', 0)} 次）",
            }

        return {
            "task_id": task_id,
            "status": result.status,
        }


# ==================== 使用示例 ====================

"""
在 API 端点中使用异步对话服务：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db

router = APIRouter()

@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
):
    # 使用异步服务
    async_service = AsyncConversationService(db)
    result = await async_service.send_message_async(
        conversation_id=conversation_id,
        user_message=message_data.content,
        user_id=message_data.user_id,
    )

    return result

@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    db: Session = Depends(get_db),
):
    # 获取任务结果
    async_service = AsyncConversationService(db)
    result = await async_service.get_async_result(task_id)

    return result
```
"""


# ==================== 前端集成示例 ====================

"""
前端使用异步对话的示例：

```javascript
// 1. 发送消息
async function sendMessage(conversationId, message) {
    const response = await fetch(
        `/api/v1/conversations/${conversationId}/messages`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: message }),
        }
    );

    const result = await response.json();
    const taskId = result.task_id;

    // 2. 轮询查询任务结果
    return pollTaskResult(taskId);
}

// 2. 轮询查询任务结果
async function pollTaskResult(taskId, maxAttempts = 30, interval = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
        const response = await fetch(`/api/v1/tasks/${taskId}/result`);
        const result = await response.json();

        if (result.status === 'SUCCESS') {
            return result;
        } else if (result.status === 'FAILURE') {
            throw new Error(result.error || '任务执行失败');
        }

        // 等待后重试
        await new Promise(resolve => setTimeout(resolve, interval));
    }

    throw new Error('任务执行超时');
}

// 3. 使用示例
try {
    const result = await sendMessage('conv_123', '你好');
    console.log('AI 响应:', result.response);
} catch (error) {
    console.error('错误:', error.message);
}
```
"""


# ==================== WebSocket 集成示例 ====================

"""
使用 WebSocket 实现实时通知：

```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str):
    await websocket.accept()

    async_service = AsyncConversationService(db)

    try:
        while True:
            # 查询任务状态
            result = await async_service.get_async_result(task_id)

            # 发送更新
            await websocket.send_json(result)

            # 如果任务完成或失败，关闭连接
            if result["status"] in ["SUCCESS", "FAILURE"]:
                break

            # 等待 1 秒后再次查询
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print(f"WebSocket 断开: task_id={task_id}")
```
"""
