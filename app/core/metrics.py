"""
CLAW.AI - Prometheus 监控指标模块
用于 FastAPI 应用的指标采集
"""

import time
from functools import wraps
from typing import Callable, Optional, Dict, Any
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Request, Response
from fastapi.responses import Response as FastAPIResponse
import logging

logger = logging.getLogger(__name__)


# ====================
# 核心指标定义
# ====================

# HTTP 请求总数
http_requests_total = Counter(
    'claw_ai_http_requests_total',
    'HTTP 请求总数',
    ['method', 'endpoint', 'status']
)

# HTTP 请求持续时间（直方图）
http_request_duration_seconds = Histogram(
    'claw_ai_http_request_duration_seconds',
    'HTTP 请求持续时间',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
)

# 活跃连接数
http_active_connections = Gauge(
    'claw_ai_http_active_connections',
    '当前活跃 HTTP 连接数'
)

# 响应体大小
http_response_size_bytes = Histogram(
    'claw_ai_http_response_size_bytes',
    'HTTP 响应体大小',
    ['method', 'endpoint'],
    buckets=(100, 1000, 10000, 100000, 1000000, 10000000)
)

# 业务指标 - 对话总数
conversations_total = Counter(
    'claw_ai_conversations_total',
    '对话总数',
    ['status']
)

# 业务指标 - 消息总数
messages_total = Counter(
    'claw_ai_messages_total',
    '消息总数',
    ['role']
)

# 业务指标 - AI 响应时间
ai_response_duration_seconds = Histogram(
    'claw_ai_ai_response_duration_seconds',
    'AI 响应时间',
    ['model'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, float('inf'))
)

# 业务指标 - 向量数据库操作时间
vector_db_operation_duration_seconds = Histogram(
    'claw_ai_vector_db_operation_duration_seconds',
    '向量数据库操作时间',
    ['operation'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, float('inf'))
)

# 数据库连接池状态
db_pool_connections = Gauge(
    'claw_ai_db_pool_connections',
    '数据库连接池状态',
    ['state']  # state: idle, active
)

# Redis 操作时间
redis_operation_duration_seconds = Histogram(
    'claw_ai_redis_operation_duration_seconds',
    'Redis 操作时间',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, float('inf'))
)

# 应用信息
app_info = Info(
    'claw_ai_app_info',
    '应用信息'
)

# ====================
# 中间件
# ====================

class PrometheusMiddleware:
    """Prometheus 监控中间件"""

    def __init__(self, app):
        self.app = app
        self.registry = CollectorRegistry()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # 增加活跃连接数
        http_active_connections.inc()

        # 记录开始时间
        start_time = time.time()

        # 拦截响应
        status_code = 200
        response_size = 0

        async def send_wrapper(message):
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                if "body" in message and message["body"]:
                    response_size += len(message["body"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            status_code = 500
            logger.error(f"Request error: {e}")
            raise
        finally:
            # 记录持续时间
            duration = time.time() - start_time
            method = request.method
            path = self._get_path(request)

            # 更新指标
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)

            http_response_size_bytes.labels(
                method=method,
                endpoint=path
            ).observe(response_size)

            # 减少活跃连接数
            http_active_connections.dec()

    def _get_path(self, request: Request) -> str:
        """获取请求路径，去除动态参数"""
        path = request.url.path
        # 移除路径中的数字 ID
        import re
        path = re.sub(r'/\d+', '/{id}', path)
        # 移除 UUID
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{uuid}',
            path
        )
        return path


# ====================
# 装饰器
# ====================

def track_ai_response(model: str = "default"):
    """追踪 AI 响应时间的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                ai_response_duration_seconds.labels(model=model).observe(time.time() - start_time)
                return result
            except Exception as e:
                ai_response_duration_seconds.labels(model=model).observe(time.time() - start_time)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                ai_response_duration_seconds.labels(model=model).observe(time.time() - start_time)
                return result
            except Exception as e:
                ai_response_duration_seconds.labels(model=model).observe(time.time() - start_time)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_vector_db_operation(operation: str = "query"):
    """追踪向量数据库操作时间的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                vector_db_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                return result
            except Exception as e:
                vector_db_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                vector_db_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                return result
            except Exception as e:
                vector_db_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_redis_operation(operation: str = "get"):
    """追踪 Redis 操作时间的装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                redis_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                return result
            except Exception as e:
                redis_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                redis_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                return result
            except Exception as e:
                redis_operation_duration_seconds.labels(operation=operation).observe(time.time() - start_time)
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ====================
# 辅助函数
# ====================

def init_app_metrics(app_name: str, app_version: str):
    """初始化应用信息指标"""
    app_info.info({
        'name': app_name,
        'version': app_version,
    })


def track_conversation(status: str = "created"):
    """追踪对话事件"""
    conversations_total.labels(status=status).inc()


def track_message(role: str = "user"):
    """追踪消息事件"""
    messages_total.labels(role=role).inc()


def update_db_pool_stats(active: int, idle: int):
    """更新数据库连接池统计"""
    db_pool_connections.labels(state='active').set(active)
    db_pool_connections.labels(state='idle').set(idle)


# ====================
# FastAPI 端点
# ====================

async def metrics_endpoint():
    """Prometheus 指标端点"""
    metrics_data = generate_latest()
    return FastAPIResponse(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )


# ====================
# 使用示例
# ====================

if __name__ == "__main__":
    # 示例：如何在 FastAPI 中使用
    print("Prometheus metrics module loaded successfully")
    print("Available metrics:")
    print("- claw_ai_http_requests_total")
    print("- claw_ai_http_request_duration_seconds")
    print("- claw_ai_http_active_connections")
    print("- claw_ai_conversations_total")
    print("- claw_ai_messages_total")
    print("- claw_ai_ai_response_duration_seconds")
    print("- claw_ai_vector_db_operation_duration_seconds")
    print("- claw_ai_redis_operation_duration_seconds")
