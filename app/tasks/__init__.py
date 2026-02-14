"""
异步任务模块
包含 Celery 配置和所有异步任务定义
"""

from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]
