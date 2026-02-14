"""
限流监控和管理 API
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from app.core.rate_limit import RateLimiter, get_rate_limiter

router = APIRouter()


# ============ 请求/响应模型 ============


class RateLimitStatsResponse(BaseModel):
    """限流统计响应"""
    total_requests: int
    blocked_requests: int
    methods: Dict[str, Dict[str, int]]


class RateLimitMonitorResponse(BaseModel):
    """限流监控响应"""
    endpoints: Dict[str, RateLimitStatsResponse]


class WhitelistItem(BaseModel):
    """白名单项"""
    type: str  # "ip" or "user"
    value: str


class BlacklistItem(BaseModel):
    """黑名单项"""
    type: str  # "ip" or "user"
    value: str


class ResetLimitRequest(BaseModel):
    """重置限流请求"""
    type: str  # "user" or "ip"
    identifier: str


class RateLimitConfigResponse(BaseModel):
    """限流配置响应"""
    global_limit: int
    global_window: int
    user_limits: Dict[str, int]
    ip_limit: int
    api_limits: Dict[str, int]
    burst_capacity: int


# ============ 监控接口 ============


@router.get("/monitor", response_model=RateLimitMonitorResponse)
async def get_rate_limit_monitor(
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    获取限流监控数据

    返回各端点的请求统计信息，包括：
    - 总请求数
    - 被拦截的请求数
    - 各 HTTP 方法的统计
    """
    monitoring_data = await limiter.get_monitoring_data()

    # 转换为响应格式
    endpoints = {}
    for path, data in monitoring_data.items():
        endpoints[path] = RateLimitStatsResponse(
            total_requests=data.get("total_requests", 0),
            blocked_requests=data.get("blocked_requests", 0),
            methods=data.get("methods", {}),
        )

    return RateLimitMonitorResponse(endpoints=endpoints)


@router.get("/config", response_model=RateLimitConfigResponse)
async def get_rate_limit_config(
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    获取当前限流配置

    返回系统的限流配置信息，包括：
    - 全局限流配置
    - 用户限流配置（按订阅级别）
    - IP 限流配置
    - API 级别限流配置
    - 突发容量配置
    """
    config = limiter.config

    return RateLimitConfigResponse(
        global_limit=config.GLOBAL_LIMIT,
        global_window=config.GLOBAL_WINDOW,
        user_limits=config.USER_LIMITS,
        ip_limit=config.IP_LIMIT,
        api_limits=config.API_LIMITS,
        burst_capacity=config.BURST_CAPACITY,
    )


@router.get("/status")
async def get_rate_limit_status(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    获取当前请求的限流状态

    返回当前用户的限流状态，包括：
    - 各层级限流的剩余次数
    - 令牌桶容量
    - 用户订阅级别
    - 是否在白名单中
    """
    client_ip = limiter._get_client_ip(request)
    user_id = limiter._get_user_id(request)
    user_tier = limiter._get_user_tier(request)

    # 检查白名单
    is_whitelisted = (
        client_ip in limiter.config.WHITELIST_IPS or
        (user_id and user_id in limiter.config.WHITELIST_USERS)
    )

    # 检查黑名单
    is_blacklisted = (
        client_ip in limiter.config.BLACKLIST_IPS or
        (user_id and user_id in limiter.config.BLACKLIST_USERS)
    )

    # 获取各层级限流状态
    status_info = {
        "client_ip": client_ip,
        "user_id": user_id,
        "user_tier": user_tier,
        "is_whitelisted": is_whitelisted,
        "is_blacklisted": is_blacklisted,
        "limits": {},
    }

    # 全局限流
    global_key = limiter._get_redis_key("global", "all")
    from app.core.rate_limit import TokenBucket
    global_bucket = TokenBucket(
        capacity=limiter.config.GLOBAL_LIMIT * limiter.config.BURST_CAPACITY,
        refill_rate=limiter._get_refill_rate(limiter.config.GLOBAL_LIMIT, limiter.config.GLOBAL_WINDOW),
        redis_client=limiter.redis,
        key=global_key,
    )
    global_status = await global_bucket.get_status()
    status_info["limits"]["global"] = global_status

    # 用户限流
    if user_id:
        user_limit = limiter.config.USER_LIMITS.get(user_tier, limiter.config.USER_LIMITS["free"])
        user_key = limiter._get_redis_key("user", user_id)
        user_bucket = TokenBucket(
            capacity=user_limit * limiter.config.BURST_CAPACITY,
            refill_rate=limiter._get_refill_rate(user_limit, limiter.config.USER_WINDOW),
            redis_client=limiter.redis,
            key=user_key,
        )
        user_status = await user_bucket.get_status()
        status_info["limits"]["user"] = user_status

    # IP 限流
    ip_key = limiter._get_redis_key("ip", client_ip)
    ip_bucket = TokenBucket(
        capacity=limiter.config.IP_LIMIT * limiter.config.BURST_CAPACITY,
        refill_rate=limiter._get_refill_rate(limiter.config.IP_LIMIT, limiter.config.IP_WINDOW),
        redis_client=limiter.redis,
        key=ip_key,
    )
    ip_status = await ip_bucket.get_status()
    status_info["limits"]["ip"] = ip_status

    # API 限流
    path = request.url.path
    for api_path, limit in limiter.config.API_LIMITS.items():
        if path.startswith(api_path):
            api_key = limiter._get_redis_key("api", api_path)
            api_bucket = TokenBucket(
                capacity=limit * limiter.config.BURST_CAPACITY,
                refill_rate=limiter._get_refill_rate(limit, limiter.config.API_WINDOW),
                redis_client=limiter.redis,
                key=api_key,
            )
            api_status = await api_bucket.get_status()
            status_info["limits"]["api"] = {
                **api_status,
                "api_path": api_path,
            }
            break

    return status_info


# ============ 白名单管理接口 ============


@router.get("/whitelist", response_model=List[WhitelistItem])
async def get_whitelist(
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    获取白名单

    返回所有在白名单中的 IP 和用户 ID
    """
    whitelist = []

    for ip in limiter.config.WHITELIST_IPS:
        whitelist.append(WhitelistItem(type="ip", value=ip))

    for user_id in limiter.config.WHITELIST_USERS:
        whitelist.append(WhitelistItem(type="user", value=user_id))

    return whitelist


@router.post("/whitelist")
async def add_to_whitelist(
    item: WhitelistItem,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    添加到白名单

    Args:
        item: 白名单项（IP 或用户 ID）
    """
    if item.type == "ip":
        limiter.add_to_whitelist(ip=item.value)
    elif item.type == "user":
        limiter.add_to_whitelist(user_id=item.value)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="类型必须是 'ip' 或 'user'"
        )

    return {"message": f"已添加到白名单: {item.type}={item.value}"}


@router.delete("/whitelist")
async def remove_from_whitelist(
    item: WhitelistItem,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    从白名单移除

    Args:
        item: 白名单项（IP 或用户 ID）
    """
    if item.type == "ip":
        limiter.remove_from_whitelist(ip=item.value)
    elif item.type == "user":
        limiter.remove_from_whitelist(user_id=item.value)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="类型必须是 'ip' 或 'user'"
        )

    return {"message": f"已从白名单移除: {item.type}={item.value}"}


# ============ 黑名单管理接口 ============


@router.get("/blacklist", response_model=List[BlacklistItem])
async def get_blacklist(
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    获取黑名单

    返回所有在黑名单中的 IP 和用户 ID
    """
    blacklist = []

    for ip in limiter.config.BLACKLIST_IPS:
        blacklist.append(BlacklistItem(type="ip", value=ip))

    for user_id in limiter.config.BLACKLIST_USERS:
        blacklist.append(BlacklistItem(type="user", value=user_id))

    return blacklist


@router.post("/blacklist")
async def add_to_blacklist(
    item: BlacklistItem,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    添加到黑名单

    Args:
        item: 黑名单项（IP 或用户 ID）
    """
    if item.type == "ip":
        limiter.add_to_blacklist(ip=item.value)
    elif item.type == "user":
        limiter.add_to_blacklist(user_id=item.value)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="类型必须是 'ip' 或 'user'"
        )

    return {"message": f"已添加到黑名单: {item.type}={item.value}"}


@router.delete("/blacklist")
async def remove_from_blacklist(
    item: BlacklistItem,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    从黑名单移除

    Args:
        item: 黑名单项（IP 或用户 ID）
    """
    if item.type == "ip":
        limiter.remove_from_blacklist(ip=item.value)
    elif item.type == "user":
        limiter.remove_from_blacklist(user_id=item.value)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="类型必须是 'ip' 或 'user'"
        )

    return {"message": f"已从黑名单移除: {item.type}={item.value}"}


# ============ 限流重置接口 ============


@router.post("/reset")
async def reset_rate_limit(
    request: ResetLimitRequest,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    重置限流状态

    清除指定用户或 IP 的限流状态，使其可以立即恢复请求

    Args:
        request: 重置请求（类型和标识符）
    """
    if request.type == "user":
        await limiter.reset_user_limit(request.identifier)
        return {"message": f"已重置用户限流: {request.identifier}"}
    elif request.type == "ip":
        await limiter.reset_ip_limit(request.identifier)
        return {"message": f"已重置 IP 限流: {request.identifier}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="类型必须是 'user' 或 'ip'"
        )


# ============ 限流测试接口 ============


@router.get("/test")
async def test_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    测试限流接口

    用于测试限流是否正常工作。多次调用此接口会触发限流。
    """
    client_ip = limiter._get_client_ip(request)

    return {
        "message": "请求成功",
        "client_ip": client_ip,
        "timestamp": request.state.get("timestamp", None),
    }
