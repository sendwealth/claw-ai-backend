"""
缓存装饰器
提供便捷的缓存注解，用于装饰器模式实现缓存功能
"""

import functools
import hashlib
import json
from typing import Any, Optional, List, Callable, Union
from functools import wraps

from app.services.cache_service import cache_service


def cached(
    scenario: str,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    tags: Optional[List[str]] = None,
    skip_args: Optional[List[int]] = None,
    key_builder: Optional[Callable] = None,
):
    """
    缓存装饰器

    Args:
        scenario: 缓存场景（如 user_profile, conversation_history 等）
        ttl: 过期时间（秒），None 则使用场景默认 TTL
        key_prefix: 自定义键前缀
        tags: 缓存标签列表，用于批量失效
        skip_args: 跳过的参数索引列表（不参与键生成）
        key_builder: 自定义键生成函数，接收参数列表返回缓存键

    Usage:
        @cached(scenario="user_profile", ttl=3600)
        async def get_user(user_id: int):
            return await db.get_user(user_id)

        @cached(scenario="ai_response", tags=["user:123"])
        async def generate_response(prompt: str):
            return await ai.generate(prompt)
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 构建缓存键
            cache_key = _build_cache_key(
                scenario=scenario,
                func=func,
                args=args,
                kwargs=kwargs,
                key_prefix=key_prefix,
                skip_args=skip_args,
                key_builder=key_builder,
            )

            # 获取缓存
            value = await cache_service.get(cache_key)
            if value is not None:
                return value

            # 调用原函数
            result = await func(*args, **kwargs)

            # 设置缓存
            if ttl is not None:
                _ttl = ttl
            else:
                _ttl = cache_service.CACHE_SCENARIOS.get(scenario, {}).get("ttl", 3600)

            await cache_service.set(cache_key, result, _ttl, tags)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 构建缓存键
            cache_key = _build_cache_key(
                scenario=scenario,
                func=func,
                args=args,
                kwargs=kwargs,
                key_prefix=key_prefix,
                skip_args=skip_args,
                key_builder=key_builder,
            )

            # 同步函数需要特殊处理（这里简化处理）
            # 在实际应用中，可以使用同步 Redis 客户端
            return func(*args, **kwargs)

        # 判断函数是异步还是同步
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_invalidate(scenario: str, pattern: Optional[str] = None):
    """
    缓存失效装饰器

    Args:
        scenario: 缓存场景
        pattern: 缓存键模式（支持模糊匹配）

    Usage:
        @cache_invalidate(scenario="user_profile")
        async def update_user(user_id: int, data: dict):
            await db.update_user(user_id, data)
            # 缓存会自动失效
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 先调用原函数
            result = await func(*args, **kwargs)

            # 失效相关缓存
            # 这里简化处理，实际应用中可以根据参数构建更精确的键
            # 或者使用缓存标签批量失效

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 同步版本的缓存失效
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_by_tags(tags: List[str], ttl: Optional[int] = None):
    """
    基于标签的缓存装饰器

    Args:
        tags: 缓存标签列表
        ttl: 过期时间

    Usage:
        @cache_by_tags(tags=["user:123", "conversation:456"])
        async def get_conversation(user_id: int, conv_id: int):
            return await db.get_conversation(conv_id)
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 使用函数名和参数作为键
            func_name = func.__name__
            args_key = _hash_args(args, kwargs)
            cache_key = f"{func_name}:{args_key}"

            # 尝试从缓存获取
            value = await cache_service.get(cache_key)
            if value is not None:
                return value

            # 调用原函数
            result = await func(*args, **kwargs)

            # 设置缓存（带标签）
            await cache_service.set(cache_key, result, ttl, tags)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            args_key = _hash_args(args, kwargs)
            cache_key = f"{func_name}:{args_key}"
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def rate_limit(max_requests: int, window: int = 60):
    """
    API 限流装饰器

    Args:
        max_requests: 时间窗口内最大请求数
        window: 时间窗口（秒）

    Usage:
        @rate_limit(max_requests=100, window=60)
        async def api_endpoint():
            return {"message": "Hello"}
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 尝试从请求上下文获取用户 ID
            # 这里简化处理，实际应用中应该从依赖注入获取
            user_id = "anonymous"

            # 构建限流键
            rate_limit_key = cache_service._generate_key(
                scenario="rate_limit",
                identifier=user_id,
                func.__name__,
            )

            # 获取当前计数
            current = await cache_service.get(rate_limit_key)
            if current is None:
                current = 0

            # 检查是否超限
            if current >= max_requests:
                raise Exception(f"请求频率过高，请稍后再试（{max_requests}次/{window}秒）")

            # 增加计数
            await cache_service.set(
                rate_limit_key,
                current + 1,
                ttl=window,
            )

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步版本
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _build_cache_key(
    scenario: str,
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: Optional[str] = None,
    skip_args: Optional[List[int]] = None,
    key_builder: Optional[Callable] = None,
) -> str:
    """
    构建缓存键

    Args:
        scenario: 缓存场景
        func: 被装饰的函数
        args: 位置参数
        kwargs: 关键字参数
        key_prefix: 自定义键前缀
        skip_args: 跳过的参数索引
        key_builder: 自定义键生成函数

    Returns:
        str: 缓存键
    """
    # 如果有自定义键生成函数
    if key_builder:
        return key_builder(scenario, func, args, kwargs)

    # 获取场景默认前缀
    if key_prefix is None:
        key_prefix = cache_service.CACHE_SCENARIOS.get(scenario, {}).get("prefix", "cache")

    # 过滤不需要参与键生成的参数（如 self, db session 等）
    filtered_args = []
    for i, arg in enumerate(args):
        if skip_args and i in skip_args:
            continue
        # 跳过 self 参数
        if i == 0 and hasattr(arg, '__class__') and hasattr(arg, '__dict__'):
            continue
        filtered_args.append(str(arg))

    # 过滤 kwargs 中的敏感参数
    filtered_kwargs = {
        k: str(v) for k, v in kwargs.items()
        if k not in ['db', 'session', 'service']
    }

    # 生成参数哈希
    args_str = ":".join(filtered_args)
    kwargs_str = json.dumps(filtered_kwargs, sort_keys=True)
    hash_input = f"{args_str}:{kwargs_str}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:12]

    return f"{key_prefix}:{hash_suffix}"


def _hash_args(args: tuple, kwargs: dict) -> str:
    """
    对参数进行哈希

    Args:
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        str: 哈希值
    """
    # 过滤不需要的参数
    filtered_args = [
        str(arg) for i, arg in enumerate(args)
        if i > 0  # 跳过 self
    ]

    filtered_kwargs = {
        k: str(v) for k, v in kwargs.items()
        if k not in ['db', 'session', 'service']
    }

    args_str = ":".join(filtered_args)
    kwargs_str = json.dumps(filtered_kwargs, sort_keys=True)
    hash_input = f"{args_str}:{kwargs_str}"

    return hashlib.md5(hash_input.encode()).hexdigest()[:12]


import asyncio


# 缓存预热器
class CacheWarmer:
    """缓存预热器 - 预加载热点数据"""

    def __init__(self):
        self._warmup_tasks = []

    def register_task(self, name: str, func: Callable, interval: int = None):
        """
        注册预热任务

        Args:
            name: 任务名称
            func: 预热函数
            interval: 预热间隔（秒），None 表示只执行一次
        """
        self._warmup_tasks.append({
            "name": name,
            "func": func,
            "interval": interval,
        })

    async def warmup_all(self):
        """执行所有预热任务"""
        for task in self._warmup_tasks:
            try:
                if asyncio.iscoroutinefunction(task["func"]):
                    await task["func"]()
                else:
                    task["func"]()
                print(f"缓存预热成功: {task['name']}")
            except Exception as e:
                print(f"缓存预热失败: {task['name']}, 错误: {e}")

    async def start_periodic_warmup(self):
        """启动周期性预热（后台任务）"""
        while True:
            await self.warmup_all()
            # 计算最小间隔
            intervals = [
                t["interval"] for t in self._warmup_tasks
                if t["interval"] is not None
            ]
            if intervals:
                min_interval = min(intervals)
                await asyncio.sleep(min_interval)
            else:
                break


# 全局预热器实例
cache_warmer = CacheWarmer()
