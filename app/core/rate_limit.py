"""
API 限流核心模块
使用令牌桶算法实现多层级限流
"""

import time
import json
import asyncio
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from datetime import timedelta

import redis
from fastapi import Request, HTTPException, status, Response
from fastapi.dependencies.utils import get_typed_signature

from app.core.config import settings


# 限流配置类
class RateLimitConfig:
    """限流配置"""

    # 全局限流配置
    GLOBAL_LIMIT = 10000  # 请求/分钟
    GLOBAL_WINDOW = 60  # 秒

    # 用户限流配置（根据订阅级别）
    USER_LIMITS = {
        "free": 100,      # 免费版：100 req/min
        "professional": 500,  # 专业版：500 req/min
        "enterprise": 2000,   # 企业版：2000 req/min
    }
    USER_WINDOW = 60  # 秒

    # IP 限流配置
    IP_LIMIT = 200  # 请求/分钟
    IP_WINDOW = 60  # 秒

    # API 级别限流配置
    API_LIMITS = {
        "/api/v1/conversations": 60,
        "/api/v1/messages": 120,
        "/api/v1/knowledge": 30,
    }
    API_WINDOW = 60  # 秒

    # 令牌桶配置
    BURST_CAPACITY = 2  # 突发容量倍数
    DEFAULT_CAPACITY = 100  # 默认令牌桶容量

    # 白名单（IP 和用户 ID）
    WHITELIST_IPS = set()
    WHITELIST_USERS = set()

    # 黑名单（IP 和用户 ID）
    BLACKLIST_IPS = set()
    BLACKLIST_USERS = set()

    # 监控配置
    ENABLE_MONITORING = True
    ALERT_THRESHOLD = 0.9  # 限流告警阈值（使用率 90%）


class TokenBucket:
    """令牌桶算法实现"""

    def __init__(
        self,
        capacity: int,
        refill_rate: float,  # 每秒填充的令牌数
        redis_client: redis.Redis,
        key: str,
    ):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.redis = redis_client
        self.key = key

    async def consume(self, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        消费令牌

        Returns:
            Tuple[bool, Dict]: (是否成功, {剩余令牌, 重试时间, 令牌容量})
        """
        current_time = time.time()

        try:
            # 使用 Lua 脚本保证原子性
            lua_script = """
            local key = KEYS[1]
            local current_time = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local capacity = tonumber(ARGV[3])
            local tokens_requested = tonumber(ARGV[4])

            -- 获取当前令牌数和最后更新时间
            local data = redis.call('HMGET', key, 'tokens', 'last_update')
            local current_tokens = tonumber(data[1])
            local last_update = tonumber(data[2])

            -- 如果不存在或已过期，初始化
            if current_tokens == nil then
                current_tokens = capacity
                last_update = current_time
            end

            -- 计算需要添加的令牌数
            local elapsed = current_time - last_update
            local tokens_to_add = elapsed * refill_rate
            current_tokens = math.min(capacity, current_tokens + tokens_to_add)

            -- 检查是否有足够的令牌
            if current_tokens >= tokens_requested then
                current_tokens = current_tokens - tokens_requested
                redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', current_time)
                redis.call('EXPIRE', key, 300)  -- 5分钟过期
                return {1, current_tokens, 0}
            else
                -- 计算需要等待的时间
                local tokens_needed = tokens_requested - current_tokens
                local wait_time = tokens_needed / refill_rate
                redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', current_time)
                redis.call('EXPIRE', key, 300)
                return {0, current_tokens, wait_time}
            end
            """

            result = await asyncio.to_thread(
                self.redis.eval,
                lua_script,
                1,
                self.key,
                current_time,
                self.refill_rate,
                self.capacity,
                tokens
            )

            allowed = bool(result[0])
            remaining = float(result[1])
            retry_after = float(result[2])

            return allowed, {
                "remaining": max(0, remaining),
                "retry_after": retry_after,
                "capacity": self.capacity,
            }

        except Exception as e:
            # Redis 出错时，降级处理：允许请求通过
            print(f"Rate limit error: {e}")
            return True, {
                "remaining": self.capacity,
                "retry_after": 0,
                "capacity": self.capacity,
            }

    async def get_status(self) -> Dict[str, Any]:
        """获取当前令牌桶状态"""
        try:
            data = await asyncio.to_thread(
                self.redis.hgetall,
                self.key
            )
            if not data:
                return {
                    "tokens": self.capacity,
                    "capacity": self.capacity,
                    "last_update": time.time(),
                }

            return {
                "tokens": float(data.get(b"tokens", self.capacity)),
                "capacity": self.capacity,
                "last_update": float(data.get(b"last_update", time.time())),
            }
        except Exception as e:
            print(f"Get bucket status error: {e}")
            return {
                "tokens": self.capacity,
                "capacity": self.capacity,
                "last_update": time.time(),
            }


class RateLimiter:
    """限流器 - 支持多层级限流"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.from_url(settings.REDIS_URL)
        self.config = RateLimitConfig()
        self._monitoring_data = {}

    def _get_redis_key(self, level: str, identifier: str) -> str:
        """生成 Redis 键"""
        return f"rate_limit:{level}:{identifier}"

    def _get_refill_rate(self, limit: int, window: int) -> float:
        """计算填充速率（令牌/秒）"""
        return limit / window

    async def check_whitelist(self, request: Request) -> bool:
        """检查是否在白名单中"""
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        if client_ip in self.config.WHITELIST_IPS:
            return True
        if user_id in self.config.WHITELIST_USERS:
            return True

        return False

    async def check_blacklist(self, request: Request) -> bool:
        """检查是否在黑名单中"""
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        if client_ip in self.config.BLACKLIST_IPS:
            return True
        if user_id in self.config.BLACKLIST_USERS:
            return True

        return False

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        # 检查代理头
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """获取用户 ID（从 token 或 session 中）"""
        # 这里需要根据实际的认证机制来获取
        # 可以从 request.state.user 或其他地方获取
        if hasattr(request.state, "user") and request.state.user:
            return str(request.state.user.id)

        # 尝试从 Authorization header 解析
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # 这里可以解析 JWT token 获取 user_id
            # 简化实现，实际应该验证 token
            pass

        return None

    def _get_user_tier(self, request: Request) -> str:
        """获取用户的订阅级别"""
        user_id = self._get_user_id(request)
        # 这里应该从数据库或缓存中获取用户的订阅级别
        # 简化实现，默认为免费版
        return "free"

    async def check_global_limit(self) -> Tuple[bool, Dict[str, Any]]:
        """检查全局限流"""
        key = self._get_redis_key("global", "all")
        bucket = TokenBucket(
            capacity=self.config.GLOBAL_LIMIT * self.config.BURST_CAPACITY,
            refill_rate=self._get_refill_rate(self.config.GLOBAL_LIMIT, self.config.GLOBAL_WINDOW),
            redis_client=self.redis,
            key=key,
        )

        allowed, info = await bucket.consume()
        return allowed, info

    async def check_user_limit(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """检查用户限流"""
        user_id = self._get_user_id(request)

        if not user_id:
            # 未认证用户，使用 IP 限流
            return await self.check_ip_limit(request)

        tier = self._get_user_tier(request)
        limit = self.config.USER_LIMITS.get(tier, self.config.USER_LIMITS["free"])

        key = self._get_redis_key("user", user_id)
        bucket = TokenBucket(
            capacity=limit * self.config.BURST_CAPACITY,
            refill_rate=self._get_refill_rate(limit, self.config.USER_WINDOW),
            redis_client=self.redis,
            key=key,
        )

        allowed, info = await bucket.consume()
        info["user_tier"] = tier
        return allowed, info

    async def check_ip_limit(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """检查 IP 限流"""
        client_ip = self._get_client_ip(request)

        key = self._get_redis_key("ip", client_ip)
        bucket = TokenBucket(
            capacity=self.config.IP_LIMIT * self.config.BURST_CAPACITY,
            refill_rate=self._get_refill_rate(self.config.IP_LIMIT, self.config.IP_WINDOW),
            redis_client=self.redis,
            key=key,
        )

        allowed, info = await bucket.consume()
        info["client_ip"] = client_ip
        return allowed, info

    async def check_api_limit(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """检查 API 级别限流"""
        path = request.url.path

        # 查找匹配的限流规则
        matched_limit = None
        for api_path, limit in self.config.API_LIMITS.items():
            if path.startswith(api_path):
                matched_limit = limit
                break

        if not matched_limit:
            # 没有特定的限流规则，允许通过
            return True, {"remaining": float("inf"), "retry_after": 0, "capacity": float("inf")}

        key = self._get_redis_key("api", path)
        bucket = TokenBucket(
            capacity=matched_limit * self.config.BURST_CAPACITY,
            refill_rate=self._get_refill_rate(matched_limit, self.config.API_WINDOW),
            redis_client=self.redis,
            key=key,
        )

        allowed, info = await bucket.consume()
        info["api_path"] = path
        return allowed, info

    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """
        检查所有限流层级

        Returns:
            Tuple[bool, Dict]: (是否允许通过, 详细信息)
        """
        # 检查黑名单
        if await self.check_blacklist(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您的 IP 或账户已被封禁",
            )

        # 检查白名单
        if await self.check_whitelist(request):
            return True, {"whitelisted": True}

        # 并行检查所有限流层级
        global_allowed, global_info = await self.check_global_limit()
        user_allowed, user_info = await self.check_user_limit(request)
        ip_allowed, ip_info = await self.check_ip_limit(request)
        api_allowed, api_info = await self.check_api_limit(request)

        # 汇总结果
        allowed = all([global_allowed, user_allowed, ip_allowed, api_allowed])

        info = {
            "global": global_info,
            "user": user_info,
            "ip": ip_info,
            "api": api_info,
        }

        # 找出最严格的限制（重试时间最长的）
        retry_after = max(
            global_info.get("retry_after", 0),
            user_info.get("retry_after", 0),
            ip_info.get("retry_after", 0),
            api_info.get("retry_after", 0),
        )

        # 找出剩余令牌最少的限制
        remaining = min(
            global_info.get("remaining", float("inf")),
            user_info.get("remaining", float("inf")),
            ip_info.get("remaining", float("inf")),
            api_info.get("remaining", float("inf")),
        )

        info["retry_after"] = retry_after
        info["remaining"] = remaining

        # 记录监控数据
        if self.config.ENABLE_MONITORING:
            await self._record_monitoring_data(request, info)

        return allowed, info

    async def _record_monitoring_data(self, request: Request, info: Dict[str, Any]):
        """记录监控数据"""
        path = request.url.path
        method = request.method

        if path not in self._monitoring_data:
            self._monitoring_data[path] = {
                "total_requests": 0,
                "blocked_requests": 0,
                "methods": {},
            }

        self._monitoring_data[path]["total_requests"] += 1

        if method not in self._monitoring_data[path]["methods"]:
            self._monitoring_data[path]["methods"][method] = {
                "total": 0,
                "blocked": 0,
            }

        self._monitoring_data[path]["methods"][method]["total"] += 1

        # 计算使用率，触发告警
        for level, level_info in info.items():
            if level in ["global", "user", "ip", "api"]:
                remaining = level_info.get("remaining", 0)
                capacity = level_info.get("capacity", 1)
                usage_rate = 1 - (remaining / capacity)

                if usage_rate >= self.config.ALERT_THRESHOLD:
                    await self._trigger_alert(request, level, usage_rate)

    async def _trigger_alert(self, request: Request, level: str, usage_rate: float):
        """触发限流告警"""
        # 这里可以集成到实际的告警系统（如 Sentry、Slack 等）
        print(
            f"⚠️ Rate Limit Alert: {level} usage at {usage_rate:.1%} "
            f"for {request.url.path}"
        )

    async def get_monitoring_data(self) -> Dict[str, Any]:
        """获取监控数据"""
        return self._monitoring_data

    async def reset_user_limit(self, user_id: str):
        """重置用户的限流状态"""
        key = self._get_redis_key("user", user_id)
        await asyncio.to_thread(self.redis.delete, key)

    async def reset_ip_limit(self, ip: str):
        """重置 IP 的限流状态"""
        key = self._get_redis_key("ip", ip)
        await asyncio.to_thread(self.redis.delete, key)

    def add_to_whitelist(self, ip: Optional[str] = None, user_id: Optional[str] = None):
        """添加到白名单"""
        if ip:
            self.config.WHITELIST_IPS.add(ip)
        if user_id:
            self.config.WHITELIST_USERS.add(user_id)

    def add_to_blacklist(self, ip: Optional[str] = None, user_id: Optional[str] = None):
        """添加到黑名单"""
        if ip:
            self.config.BLACKLIST_IPS.add(ip)
        if user_id:
            self.config.BLACKLIST_USERS.add(user_id)

    def remove_from_whitelist(self, ip: Optional[str] = None, user_id: Optional[str] = None):
        """从白名单移除"""
        if ip and ip in self.config.WHITELIST_IPS:
            self.config.WHITELIST_IPS.remove(ip)
        if user_id and user_id in self.config.WHITELIST_USERS:
            self.config.WHITELIST_USERS.remove(user_id)

    def remove_from_blacklist(self, ip: Optional[str] = None, user_id: Optional[str] = None):
        """从黑名单移除"""
        if ip and ip in self.config.BLACKLIST_IPS:
            self.config.BLACKLIST_IPS.remove(ip)
        if user_id and user_id in self.config.BLACKLIST_USERS:
            self.config.BLACKLIST_USERS.remove(user_id)


# 创建全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器实例（依赖注入）"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
