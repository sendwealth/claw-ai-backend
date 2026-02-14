"""
缓存管理 API
提供缓存监控、管理和操作接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.services.cache_service import get_cache_service, CacheService
from app.api.dependencies import get_current_active_user


router = APIRouter(prefix="/cache", tags=["缓存管理"])


# ========== 响应模型 ==========


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    hits: int
    misses: int
    sets: int
    deletes: int
    errors: int
    hit_rate: float
    memory_cache_size: int
    redis_connected: bool


class CacheConfigResponse(BaseModel):
    """缓存配置响应"""
    scenario: str
    ttl: int
    prefix: str


class CacheOperationResponse(BaseModel):
    """缓存操作响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class CacheKeysResponse(BaseModel):
    """缓存键列表响应"""
    total: int
    keys: List[str]
    scenario: Optional[str] = None


# ========== 缓存监控接口 ==========


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取缓存统计信息

    返回缓存命中、未命中、设置、删除等统计数据
    """
    stats = cache.get_stats()
    return CacheStatsResponse(**stats)


@router.get("/scenarios", response_model=List[CacheConfigResponse])
async def get_cache_scenarios(
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取所有缓存场景配置

    返回各个缓存场景的 TTL 和前缀配置
    """
    scenarios = []
    for name, config in cache.CACHE_SCENARIOS.items():
        scenarios.append(
            CacheConfigResponse(
                scenario=name,
                ttl=config["ttl"],
                prefix=config["prefix"],
            )
        )
    return scenarios


@router.get("/keys", response_model=CacheKeysResponse)
async def get_cache_keys(
    scenario: Optional[str] = Query(None, description="缓存场景，过滤特定场景的键"),
    prefix: Optional[str] = Query(None, description="键前缀"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大键数"),
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取缓存键列表

    支持按场景或前缀过滤
    """
    try:
        # 构建匹配模式
        if scenario:
            if scenario not in cache.CACHE_SCENARIOS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"未知的缓存场景: {scenario}",
                )
            pattern = cache.CACHE_SCENARIOS[scenario]["prefix"]
        elif prefix:
            pattern = prefix
        else:
            pattern = "*"

        keys = []
        if cache._connected and cache._async_redis_client:
            async for key in cache._async_redis_client.scan_iter(match=f"{pattern}*", count=limit):
                keys.append(key)
                if len(keys) >= limit:
                    break

        # 加上内存缓存的键
        from app.services.cache_service import _memory_cache
        for key in _memory_cache.keys():
            if pattern == "*" or key.startswith(pattern):
                if key not in keys:
                    keys.append(key)

        return CacheKeysResponse(
            total=len(keys),
            keys=keys,
            scenario=scenario,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取缓存键失败: {str(e)}",
        )


@router.get("/keys/{key}")
async def get_cache_value(
    key: str,
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    获取指定键的缓存值
    """
    try:
        value = await cache.get(key)
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="缓存键不存在",
            )
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取缓存值失败: {str(e)}",
        )


# ========== 缓存操作接口 ==========


@router.delete("/stats/reset", response_model=CacheOperationResponse)
async def reset_cache_stats(
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    重置缓存统计信息
    """
    try:
        cache.reset_stats()
        return CacheOperationResponse(
            success=True,
            message="缓存统计已重置",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置统计失败: {str(e)}",
        )


@router.delete("/keys/{key}", response_model=CacheOperationResponse)
async def delete_cache_key(
    key: str,
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    删除指定缓存键
    """
    try:
        success = await cache.delete(key)
        if success:
            return CacheOperationResponse(
                success=True,
                message=f"缓存键 {key} 已删除",
            )
        else:
            return CacheOperationResponse(
                success=False,
                message=f"删除缓存键 {key} 失败",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除缓存键失败: {str(e)}",
        )


@router.post("/invalidate/by-tags", response_model=CacheOperationResponse)
async def invalidate_by_tags(
    tags: List[str],
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    根据标签批量失效缓存

    Request Body:
    {
        "tags": ["user:123", "conversation:456"]
    }
    """
    try:
        count = await cache.delete_by_tags(tags)
        return CacheOperationResponse(
            success=True,
            message=f"已失效 {count} 个缓存",
            data={"invalidated_count": count},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量失效缓存失败: {str(e)}",
        )


@router.post("/invalidate/by-scenario", response_model=CacheOperationResponse)
async def invalidate_by_scenario(
    scenario: str,
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    根据场景失效缓存

    Request Body:
    {
        "scenario": "user_profile"
    }
    """
    try:
        if scenario not in cache.CACHE_SCENARIOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"未知的缓存场景: {scenario}",
            )

        # 获取该场景的所有键
        pattern = cache.CACHE_SCENARIOS[scenario]["prefix"]
        keys = []
        if cache._connected and cache._async_redis_client:
            async for key in cache._async_redis_client.scan_iter(match=f"{pattern}:*"):
                keys.append(key)

        # 批量删除
        if keys:
            from app.services.cache_service import _memory_cache, _memory_lock
            import asyncio

            # 删除内存缓存
            async with _memory_lock:
                for key in keys:
                    if key in _memory_cache:
                        del _memory_cache[key]

            # 删除 Redis 缓存
            await cache._async_redis_client.delete(*keys)

        return CacheOperationResponse(
            success=True,
            message=f"已失效场景 {scenario} 的 {len(keys)} 个缓存",
            data={"invalidated_count": len(keys)},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"失效场景缓存失败: {str(e)}",
        )


@router.delete("/all", response_model=CacheOperationResponse)
async def clear_all_cache(
    confirm: bool = Query(False, description="确认清空所有缓存（需要设置为 true）"),
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    清空所有缓存（危险操作！）

    需要确认参数 confirm=true
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要确认参数 confirm=true 才能清空所有缓存",
            )

        success = await cache.clear_all()
        if success:
            return CacheOperationResponse(
                success=True,
                message="所有缓存已清空",
            )
        else:
            return CacheOperationResponse(
                success=False,
                message="清空缓存失败",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空缓存失败: {str(e)}",
        )


@router.post("/warmup", response_model=CacheOperationResponse)
async def trigger_cache_warmup(
    scenario: Optional[str] = Query(None, description="预热的场景，None 表示预热所有场景"),
    cache: CacheService = Depends(get_cache_service),
    current_user: get_current_active_user = Depends(get_current_active_user),
):
    """
    触发缓存预热

    执行预定义的预热任务，预加载热点数据
    """
    try:
        from app.core.cache import cache_warmer

        # 如果指定了场景，只预热该场景
        # 这里简化处理，实际应用中应该根据场景执行不同的预热任务
        await cache_warmer.warmup_all()

        return CacheOperationResponse(
            success=True,
            message="缓存预热已完成",
            data={"warmed_scenarios": list(cache.CACHE_SCENARIOS.keys())},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"缓存预热失败: {str(e)}",
        )


# ========== 缓存健康检查 ==========


@router.get("/health")
async def cache_health_check(
    cache: CacheService = Depends(get_cache_service),
):
    """
    缓存健康检查

    检查 Redis 连接状态和缓存系统是否正常工作
    """
    try:
        # 检查内存缓存
        from app.services.cache_service import _memory_cache

        # 检查 Redis 连接
        redis_status = "connected" if cache._connected else "disconnected"

        # 尝试简单的读写操作
        test_key = "health_check_test"
        test_value = {"test": True, "timestamp": __import__("time").time()}

        # 写入测试
        write_success = await cache.set(test_key, test_value, ttl=60)

        # 读取测试
        read_success = False
        read_value = None
        if write_success:
            read_value = await cache.get(test_key)
            read_success = read_value is not None

        # 清理测试键
        await cache.delete(test_key)

        return {
            "status": "healthy" if (write_success and read_success) else "degraded",
            "memory_cache": {
                "status": "active",
                "size": len(_memory_cache),
            },
            "redis": {
                "status": redis_status,
                "write_test": write_success,
                "read_test": read_success,
            },
            "overall": write_success and read_success,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "memory_cache": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "overall": False,
        }
