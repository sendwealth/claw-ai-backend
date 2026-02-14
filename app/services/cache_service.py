"""
缓存服务
提供多级缓存（内存 + Redis）和缓存管理功能
"""

import json
import hashlib
import time
from typing import Any, Optional, List, Dict, Union, Callable
from functools import wraps
from datetime import timedelta
import asyncio

import redis
from redis.asyncio import Redis as AsyncRedis
from redis.connection import ConnectionPool

from app.core.config import settings


# 内存缓存存储（一级缓存）
_memory_cache: Dict[str, Dict[str, Any]] = {}
_memory_lock = asyncio.Lock()

# 缓存统计
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "sets": 0,
    "deletes": 0,
    "errors": 0,
}


class CacheService:
    """缓存服务类 - 支持多级缓存和缓存标签"""

    # 缓存场景配置
    CACHE_SCENARIOS = {
        "user_profile": {
            "ttl": 3600,  # 1小时
            "prefix": "user:profile",
        },
        "user_conversations": {
            "ttl": 600,  # 10分钟
            "prefix": "user:conversations",
        },
        "conversation_history": {
            "ttl": 1800,  # 30分钟
            "prefix": "conversation:history",
        },
        "document_content": {
            "ttl": 3600,  # 1小时
            "prefix": "doc:content",
        },
        "ai_response": {
            "ttl": 86400,  # 24小时
            "prefix": "ai:response",
        },
        "rate_limit": {
            "ttl": 60,  # 1分钟
            "prefix": "rate:limit",
        },
    }

    def __init__(self):
        """初始化缓存服务"""
        self._redis_pool = None
        self._redis_client = None
        self._async_redis_pool = None
        self._async_redis_client = None
        self._connected = False

    async def connect(self):
        """连接到 Redis"""
        try:
            # 同步 Redis 客户端
            self._redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)

            # 异步 Redis 客户端
            self._async_redis_pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            self._async_redis_client = AsyncRedis(connection_pool=self._async_redis_pool)

            # 测试连接
            await self._async_redis_client.ping()
            self._connected = True
            return True
        except Exception as e:
            print(f"Redis 连接失败: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """断开 Redis 连接"""
        if self._async_redis_client:
            await self._async_redis_client.close()
        if self._redis_client:
            self._redis_client.close()

    def _generate_key(self, scenario: str, identifier: str, *args) -> str:
        """
        生成缓存键

        Args:
            scenario: 缓存场景
            identifier: 标识符
            *args: 额外的参数

        Returns:
            str: 缓存键
        """
        if scenario not in self.CACHE_SCENARIOS:
            raise ValueError(f"未知的缓存场景: {scenario}")

        prefix = self.CACHE_SCENARIOS[scenario]["prefix"]

        # 如果有额外参数，使用 hash 简化
        if args:
            hash_input = f"{identifier}:{args}"
            hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
            return f"{prefix}:{identifier}:{hash_suffix}"

        return f"{prefix}:{identifier}"

    async def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据（多级缓存）

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在返回 None
        """
        try:
            # 1. 先从内存缓存获取（一级缓存）
            async with _memory_lock:
                if key in _memory_cache:
                    entry = _memory_cache[key]
                    # 检查是否过期
                    if entry["expires_at"] > time.time():
                        _cache_stats["hits"] += 1
                        return entry["value"]
                    else:
                        # 内存缓存过期，删除
                        del _memory_cache[key]

            # 2. 从 Redis 获取（二级缓存）
            if self._connected and self._async_redis_client:
                value = await self._async_redis_client.get(key)
                if value is not None:
                    try:
                        parsed_value = json.loads(value)
                        # 回填到内存缓存
                        ttl = await self._async_redis_client.ttl(key)
                        await self._set_memory_cache(key, parsed_value, ttl)
                        _cache_stats["hits"] += 1
                        return parsed_value
                    except json.JSONDecodeError:
                        _cache_stats["hits"] += 1
                        return value

            _cache_stats["misses"] += 1
            return None
        except Exception as e:
            _cache_stats["errors"] += 1
            print(f"缓存获取错误: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        设置缓存（多级缓存）

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 表示不设置
            tags: 缓存标签列表

        Returns:
            bool: 是否设置成功
        """
        try:
            # 序列化值
            serialized_value = json.dumps(value, ensure_ascii=False)

            # 1. 设置内存缓存（一级缓存）
            if ttl is None:
                ttl = 3600  # 默认 1 小时
            await self._set_memory_cache(key, value, ttl)

            # 2. 设置 Redis 缓存（二级缓存）
            if self._connected and self._async_redis_client:
                await self._async_redis_client.setex(key, ttl, serialized_value)

                # 设置缓存标签
                if tags:
                    for tag in tags:
                        tag_key = f"tag:{tag}"
                        await self._async_redis_client.sadd(tag_key, key)
                        await self._async_redis_client.expire(tag_key, ttl + 60)

            _cache_stats["sets"] += 1
            return True
        except Exception as e:
            _cache_stats["errors"] += 1
            print(f"缓存设置错误: {e}")
            return False

    async def _set_memory_cache(self, key: str, value: Any, ttl: int):
        """设置内存缓存"""
        async with _memory_lock:
            _memory_cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        try:
            # 删除内存缓存
            async with _memory_lock:
                if key in _memory_cache:
                    del _memory_cache[key]

            # 删除 Redis 缓存
            if self._connected and self._async_redis_client:
                await self._async_redis_client.delete(key)

            _cache_stats["deletes"] += 1
            return True
        except Exception as e:
            _cache_stats["errors"] += 1
            print(f"缓存删除错误: {e}")
            return False

    async def delete_by_tags(self, tags: List[str]) -> int:
        """
        根据标签批量删除缓存

        Args:
            tags: 标签列表

        Returns:
            int: 删除的缓存数量
        """
        if not self._connected or not self._async_redis_client:
            return 0

        try:
            keys_to_delete = set()

            # 收集所有标签关联的键
            for tag in tags:
                tag_key = f"tag:{tag}"
                keys = await self._async_redis_client.smembers(tag_key)
                keys_to_delete.update(keys)
                # 删除标签集合
                await self._async_redis_client.delete(tag_key)

            # 批量删除缓存
            if keys_to_delete:
                # 从内存缓存删除
                async with _memory_lock:
                    for key in keys_to_delete:
                        if key in _memory_cache:
                            del _memory_cache[key]

                # 从 Redis 删除
                await self._async_redis_client.delete(*keys_to_delete)

                _cache_stats["deletes"] += len(keys_to_delete)
                return len(keys_to_delete)

            return 0
        except Exception as e:
            _cache_stats["errors"] += 1
            print(f"批量删除缓存错误: {e}")
            return 0

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Any:
        """
        获取缓存，如果不存在则调用工厂函数生成并缓存

        Args:
            key: 缓存键
            factory: 工厂函数，用于生成缓存值
            ttl: 过期时间
            tags: 缓存标签

        Returns:
            缓存值
        """
        value = await self.get(key)
        if value is not None:
            return value

        # 调用工厂函数
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        # 设置缓存
        await self.set(key, value, ttl, tags)
        return value

    async def clear_all(self) -> bool:
        """
        清空所有缓存

        Returns:
            bool: 是否清空成功
        """
        try:
            # 清空内存缓存
            async with _memory_lock:
                _memory_cache.clear()

            # 清空 Redis 缓存
            if self._connected and self._async_redis_client:
                pattern = f"{settings.REDIS_URL.split('/')[-1]}:*"
                keys = []
                async for key in self._async_redis_client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self._async_redis_client.delete(*keys)

            return True
        except Exception as e:
            _cache_stats["errors"] += 1
            print(f"清空缓存错误: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict: 统计信息
        """
        total_requests = _cache_stats["hits"] + _cache_stats["misses"]
        hit_rate = (
            _cache_stats["hits"] / total_requests * 100
            if total_requests > 0
            else 0
        )

        return {
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "sets": _cache_stats["sets"],
            "deletes": _cache_stats["deletes"],
            "errors": _cache_stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "memory_cache_size": len(_memory_cache),
            "redis_connected": self._connected,
        }

    def reset_stats(self):
        """重置缓存统计"""
        global _cache_stats
        _cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }


# 全局缓存服务实例
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """
    依赖注入：获取缓存服务实例

    Returns:
        CacheService: 缓存服务实例
    """
    if not cache_service._connected:
        await cache_service.connect()
    return cache_service
