"""
Celery 应用配置
配置 Celery 与 Redis 的连接，以及任务队列的行为
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# 创建 Celery 应用实例
celery_app = Celery(
    "claw_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.ai_tasks",
        "app.tasks.knowledge_tasks",
    ]
)

# Celery 配置
celery_app.conf.update(
    # ==================== 基础配置 ====================
    timezone="Asia/Shanghai",
    enable_utc=True,

    # ==================== 任务结果配置 ====================
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0,
            "max_retries": 3,
        }
    },
    result_expires=3600,  # 任务结果保存 1 小时
    result_extended=True,  # 扩展结果信息，包含任务执行时间等

    # ==================== 任务执行配置 ====================
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    compression="gzip",  # 使用 gzip 压缩消息
    worker_prefetch_multiplier=4,  # 每个 worker 预取任务数

    # ==================== 任务重试配置 ====================
    task_acks_late=True,  # 任务执行成功后才确认
    task_reject_on_worker_lost=True,  # worker 丢失时重新入队

    # ==================== 任务路由配置 ====================
    task_routes={
        "app.tasks.ai_tasks.generate_ai_response": {
            "queue": "ai_high_priority",
            "routing_key": "ai.high",
        },
        "app.tasks.knowledge_tasks.vectorize_document": {
            "queue": "knowledge_default",
            "routing_key": "knowledge.default",
        },
        "app.tasks.knowledge_tasks.update_knowledge_base": {
            "queue": "knowledge_default",
            "routing_key": "knowledge.default",
        },
        "app.tasks.ai_tasks.send_notification": {
            "queue": "notification_default",
            "routing_key": "notification.default",
        },
    },

    # ==================== 任务优先级配置 ====================
    task_default_priority=5,
    task_default_queue="default",
    task_create_missing_queues=True,

    # ==================== 任务限流配置 ====================
    task_annotations={
        "app.tasks.ai_tasks.generate_ai_response": {
            "rate_limit": "10/m",  # 限制每分钟最多 10 个任务
        },
        "app.tasks.knowledge_tasks.vectorize_document": {
            "rate_limit": "5/m",  # 限制每分钟最多 5 个任务（文档向量化资源密集）
        },
    },

    # ==================== 任务超时配置 ====================
    task_soft_time_limit=300,  # 软超时 5 分钟
    task_time_limit=600,  # 硬超时 10 分钟

    # ==================== Worker 配置 ====================
    worker_max_tasks_per_child=100,  # 每个 worker 执行 100 个任务后重启
    worker_concurrency=4,  # 默认并发数

    # ==================== 监控和日志配置 ====================
    worker_send_task_events=True,  # 发送任务事件
    task_send_sent_event=True,  # 发送任务已发送事件
    task_track_started=True,  # 追踪任务开始状态
    task_send_result_event=True,  # 发送任务结果事件

    # ==================== 安全配置 ====================
    broker_transport_options={
        "visibility_timeout": 3600,  # 任务可见性超时
        "max_connections": 10,  # 最大连接数
    },

    # ==================== 定时任务配置 ====================
    beat_schedule={
        # 每天凌晨 2 点清理过期任务结果
        "cleanup-expired-results": {
            "task": "app.tasks.ai_tasks.cleanup_expired_results",
            "schedule": crontab(hour=2, minute=0),
        },
        # 每 30 分钟检查任务状态
        "check-task-status": {
            "task": "app.tasks.ai_tasks.check_task_health",
            "schedule": crontab(minute="*/30"),
        },
    },
)


# 导出 Celery 应用实例
__all__ = ["celery_app"]
