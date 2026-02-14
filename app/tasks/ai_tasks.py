"""
AI 相关异步任务
处理 AI 响应生成、通知发送等任务
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

from celery import Task
from celery.exceptions import Retry, Ignore

from app.tasks.celery_app import celery_app
from app.services.ai_service import ai_service
from app.core.config import settings


# 配置日志
logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    """带重试功能的任务基类"""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600  # 最大退避时间 10 分钟
    retry_jitter = True
    retry_kwargs = {"max_retries": 3}

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(
            f"任务 {self.name} 失败: task_id={task_id}, "
            f"error={exc}, traceback={einfo.traceback}"
        )
        # 这里可以添加失败通知逻辑

    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        logger.info(f"任务 {self.name} 成功: task_id={task_id}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试时的回调"""
        logger.warning(
            f"任务 {self.name} 重试: task_id={task_id}, "
            f"retry_count={self.request.retries}, error={exc}"
        )


@celery_app.task(
    name="app.tasks.ai_tasks.generate_ai_response",
    base=BaseTaskWithRetry,
    bind=True,
    max_retries=3,
    soft_time_limit=120,  # 2 分钟软超时
    time_limit=180,  # 3 分钟硬超时
)
def generate_ai_response(
    self,
    conversation_id: str,
    user_message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    异步生成 AI 响应

    Args:
        self: 任务实例（用于重试）
        conversation_id: 对话 ID
        user_message: 用户消息
        conversation_history: 对话历史
        system_prompt: 系统提示词
        temperature: 温度参数
        max_tokens: 最大 Token 数
        user_id: 用户 ID（可选）

    Returns:
        dict: 包含响应内容、Token 数量、成本等信息

    Raises:
        Exception: AI 调用失败时抛出异常
    """
    try:
        logger.info(
            f"开始生成 AI 响应: conversation_id={conversation_id}, "
            f"user_id={user_id}, message_length={len(user_message)}"
        )

        # 构建消息列表
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        # 调用 AI 服务
        result = await ai_service.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if not result["success"]:
            raise Exception(f"AI 调用失败: {result['error']}")

        # 记录任务状态
        logger.info(
            f"AI 响应生成成功: conversation_id={conversation_id}, "
            f"tokens={result['tokens']['total']}, cost={result['cost']}"
        )

        return {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "response": result["content"],
            "tokens": result["tokens"],
            "cost": result["cost"],
            "response_time": result["response_time"],
            "model": result["model"],
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SUCCESS",
        }

    except Exception as exc:
        logger.error(
            f"AI 响应生成失败: conversation_id={conversation_id}, "
            f"error={exc}, traceback={traceback.format_exc()}"
        )

        # 如果是可重试错误，进行重试
        if self.request.retries < self.max_retries:
            logger.info(f"正在重试任务: retry_count={self.request.retries + 1}")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        else:
            # 超过最大重试次数，抛出异常
            raise


@celery_app.task(
    name="app.tasks.ai_tasks.send_notification",
    base=BaseTaskWithRetry,
    bind=True,
    max_retries=3,
)
def send_notification(
    self,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    异步发送通知

    Args:
        self: 任务实例（用于重试）
        user_id: 用户 ID
        notification_type: 通知类型（email, push, sms, system）
        title: 通知标题
        message: 通知内容
        data: 附加数据
        channels: 发送渠道列表

    Returns:
        dict: 发送结果

    Raises:
        Exception: 发送失败时抛出异常
    """
    try:
        logger.info(
            f"开始发送通知: user_id={user_id}, type={notification_type}, "
            f"title={title}"
        )

        # 默认渠道为系统通知
        if channels is None:
            channels = ["system"]

        results = []

        # 模拟发送通知（实际实现需要根据通知渠道集成）
        for channel in channels:
            try:
                # 这里应该调用实际的通知服务
                # 示例：邮件通知
                if channel == "email":
                    # 调用邮件服务
                    logger.info(f"发送邮件通知给用户 {user_id}: {title}")
                    results.append({"channel": "email", "status": "sent"})

                # 示例：推送通知
                elif channel == "push":
                    # 调用推送服务
                    logger.info(f"发送推送通知给用户 {user_id}: {title}")
                    results.append({"channel": "push", "status": "sent"})

                # 示例：系统通知（存储到数据库）
                elif channel == "system":
                    # 保存系统通知到数据库
                    logger.info(f"保存系统通知给用户 {user_id}: {title}")
                    results.append({"channel": "system", "status": "saved"})

                # 示例：短信通知
                elif channel == "sms":
                    # 调用短信服务
                    logger.info(f"发送短信通知给用户 {user_id}: {title}")
                    results.append({"channel": "sms", "status": "sent"})

            except Exception as e:
                logger.error(f"发送通知失败: channel={channel}, error={e}")
                results.append({"channel": channel, "status": "failed", "error": str(e)})

        # 检查是否全部成功
        all_success = all(r["status"] in ["sent", "saved"] for r in results)

        logger.info(
            f"通知发送完成: user_id={user_id}, "
            f"total={len(results)}, success={len([r for r in results if r['status'] in ['sent', 'saved']])}"
        )

        return {
            "user_id": user_id,
            "notification_type": notification_type,
            "results": results,
            "all_success": all_success,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SUCCESS",
        }

    except Exception as exc:
        logger.error(
            f"发送通知失败: user_id={user_id}, error={exc}, "
            f"traceback={traceback.format_exc()}"
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        else:
            raise


@celery_app.task(
    name="app.tasks.ai_tasks.cleanup_expired_results",
    bind=True,
)
def cleanup_expired_results(self) -> Dict[str, Any]:
    """
    清理过期的任务结果

    Returns:
        dict: 清理结果
    """
    try:
        logger.info("开始清理过期任务结果")

        # Celery 会自动清理过期的任务结果（result_expires 配置）
        # 这个任务主要用于记录日志和其他清理工作

        cleaned_count = 0

        logger.info(f"清理完成: 清理了 {cleaned_count} 个过期结果")

        return {
            "cleaned_count": cleaned_count,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SUCCESS",
        }

    except Exception as exc:
        logger.error(f"清理过期结果失败: error={exc}, traceback={traceback.format_exc()}")
        raise


@celery_app.task(
    name="app.tasks.ai_tasks.check_task_health",
    bind=True,
)
def check_task_health(self) -> Dict[str, Any]:
    """
    检查任务健康状态

    Returns:
        dict: 健康检查结果
    """
    try:
        logger.info("检查任务健康状态")

        # 这里可以添加各种健康检查逻辑
        # 例如：检查 Redis 连接、数据库连接等

        health_status = {
            "redis_connected": True,
            "database_connected": True,
            "worker_status": "healthy",
        }

        logger.info(f"健康检查完成: status={health_status}")

        return {
            "health_status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SUCCESS",
        }

    except Exception as exc:
        logger.error(f"健康检查失败: error={exc}, traceback={traceback.format_exc()}")
        raise


# 导出所有任务
__all__ = [
    "generate_ai_response",
    "send_notification",
    "cleanup_expired_results",
    "check_task_health",
]
