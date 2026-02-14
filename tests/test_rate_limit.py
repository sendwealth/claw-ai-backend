"""
限流系统测试
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from fastapi.testclient import TestClient

from app.core.rate_limit import (
    RateLimiter,
    TokenBucket,
    RateLimitConfig,
    get_rate_limiter,
)
from app.core.rate_limit_middleware import RateLimitMiddleware, rate_limit
from app.main import app


# ============ TokenBucket 测试 ============


@pytest.mark.asyncio
class TestTokenBucket:
    """令牌桶测试"""

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis = Mock()
        redis.eval = Mock(return_value=[1, 90.0, 0.0])  # 允许通过
        return redis

    @pytest.fixture
    def token_bucket(self, mock_redis):
        """创建令牌桶实例"""
        return TokenBucket(
            capacity=100,
            refill_rate=100 / 60,  # 每分钟 100 个令牌
            redis_client=mock_redis,
            key="test:bucket",
        )

    async def test_consume_success(self, token_bucket, mock_redis):
        """测试成功消费令牌"""
        allowed, info = await token_bucket.consume(1)

        assert allowed is True
        assert info["remaining"] >= 0
        assert info["retry_after"] == 0
        assert info["capacity"] == 100
        assert mock_redis.eval.called

    async def test_consume_blocked(self, token_bucket, mock_redis):
        """测试令牌不足被阻止"""
        mock_redis.eval = Mock(return_value=[0, 0.0, 30.0])  # 被阻止

        allowed, info = await token_bucket.consume(1)

        assert allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] == 30.0

    async def test_consume_multiple_tokens(self, token_bucket, mock_redis):
        """测试消费多个令牌"""
        mock_redis.eval = Mock(return_value=[1, 80.0, 0.0])

        allowed, info = await token_bucket.consume(20)

        assert allowed is True
        assert info["remaining"] >= 0

    async def test_get_status(self, token_bucket, mock_redis):
        """测试获取令牌桶状态"""
        mock_redis.hgetall = Mock(
            return_value={
                b"tokens": b"85.5",
                b"last_update": b"1707901234.567",
            }
        )

        status = await token_bucket.get_status()

        assert status["tokens"] == 85.5
        assert status["capacity"] == 100
        assert "last_update" in status

    async def test_redis_error_fallback(self, token_bucket, mock_redis):
        """测试 Redis 出错时的降级处理"""
        mock_redis.eval = Mock(side_effect=Exception("Redis connection error"))

        # 不应抛出异常，而是返回允许通过
        allowed, info = await token_bucket.consume(1)

        assert allowed is True
        assert info["remaining"] == token_bucket.capacity


# ============ RateLimiter 测试 ============


@pytest.mark.asyncio
class TestRateLimiter:
    """限流器测试"""

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis = Mock()
        redis.eval = Mock(return_value=[1, 90.0, 0.0])
        redis.hgetall = Mock(return_value={})
        redis.delete = Mock()
        return redis

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """创建限流器实例"""
        return RateLimiter(redis_client=mock_redis)

    @pytest.fixture
    def mock_request(self):
        """模拟请求对象"""
        request = Mock(spec=Request)
        request.url.path = "/api/v1/conversations"
        request.url = Mock()
        request.url.path = "/api/v1/conversations"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        request.state.user = None

        return request

    async def test_get_redis_key(self, rate_limiter):
        """测试 Redis 键生成"""
        key = rate_limiter._get_redis_key("global", "all")
        assert key == "rate_limit:global:all"

        key = rate_limiter._get_redis_key("user", "user_123")
        assert key == "rate_limit:user:user_123"

    async def test_get_client_ip(self, rate_limiter, mock_request):
        """测试获取客户端 IP"""
        ip = rate_limiter._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_get_user_id_no_user(self, rate_limiter, mock_request):
        """测试未认证用户获取 ID"""
        user_id = rate_limiter._get_user_id(mock_request)
        assert user_id is None

    def test_get_user_tier(self, rate_limiter, mock_request):
        """测试获取用户订阅级别"""
        tier = rate_limiter._get_user_tier(mock_request)
        assert tier == "free"  # 默认值

    async def test_check_whitelist_empty(self, rate_limiter, mock_request):
        """测试检查空白名单"""
        is_whitelisted = await rate_limiter.check_whitelist(mock_request)
        assert is_whitelisted is False

    async def test_check_blacklist_empty(self, rate_limiter, mock_request):
        """测试检查空黑名单"""
        is_blacklisted = await rate_limiter.check_blacklist(mock_request)
        assert is_blacklisted is False

    async def test_add_to_whitelist_ip(self, rate_limiter):
        """测试添加 IP 到白名单"""
        rate_limiter.add_to_whitelist(ip="192.168.1.100")
        assert "192.168.1.100" in rate_limiter.config.WHITELIST_IPS

    async def test_add_to_blacklist_ip(self, rate_limiter):
        """测试添加 IP 到黑名单"""
        rate_limiter.add_to_blacklist(ip="192.168.1.200")
        assert "192.168.1.200" in rate_limiter.config.BLACKLIST_IPS

    async def test_remove_from_whitelist(self, rate_limiter):
        """测试从白名单移除"""
        rate_limiter.add_to_whitelist(ip="192.168.1.100")
        assert "192.168.1.100" in rate_limiter.config.WHITELIST_IPS

        rate_limiter.remove_from_whitelist(ip="192.168.1.100")
        assert "192.168.1.100" not in rate_limiter.config.WHITELIST_IPS

    async def test_check_blacklist_raises_exception(self, rate_limiter, mock_request, mock_redis):
        """测试黑名单检查抛出异常"""
        rate_limiter.add_to_blacklist(ip="192.168.1.100")

        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter.check_blacklist(mock_request)

        assert exc_info.value.status_code == 403

    async def test_check_rate_limit(self, rate_limiter, mock_request, mock_redis):
        """测试综合限流检查"""
        allowed, info = await rate_limiter.check_rate_limit(mock_request)

        assert allowed is True
        assert "global" in info
        assert "user" in info
        assert "ip" in info
        assert "api" in info

    async def test_check_rate_limit_blacklisted(self, rate_limiter, mock_request):
        """测试黑名单用户的限流"""
        rate_limiter.add_to_blacklist(ip="192.168.1.100")

        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter.check_rate_limit(mock_request)

        assert exc_info.value.status_code == 403

    async def test_check_rate_limit_whitelisted(self, rate_limiter, mock_request):
        """测试白名单用户"""
        rate_limiter.add_to_whitelist(ip="192.168.1.100")

        allowed, info = await rate_limiter.check_rate_limit(mock_request)

        assert allowed is True
        assert info.get("whitelisted") is True

    async def test_reset_user_limit(self, rate_limiter, mock_redis):
        """测试重置用户限流"""
        await rate_limiter.reset_user_limit("user_123")

        mock_redis.delete.assert_called_once_with("rate_limit:user:user_123")

    async def test_reset_ip_limit(self, rate_limiter, mock_redis):
        """测试重置 IP 限流"""
        await rate_limiter.reset_ip_limit("192.168.1.100")

        mock_redis.delete.assert_called_once_with("rate_limit:ip:192.168.1.100")


# ============ RateLimitMiddleware 测试 ============


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """限流中间件测试"""

    @pytest.fixture
    def mock_redis(self):
        redis = Mock()
        redis.eval = Mock(return_value=[1, 90.0, 0.0])
        redis.hgetall = Mock(return_value={})
        return redis

    @pytest.fixture
    def middleware(self, mock_redis):
        """创建中间件实例"""
        mock_app = Mock()
        return RateLimitMiddleware(mock_app, RateLimiter(redis_client=mock_redis))

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        request.state.user = None
        return request

    async def test_dispatch_health_check(self, middleware):
        """测试健康检查端点跳过限流"""
        from unittest.mock import AsyncMock

        request = Mock(spec=Request)
        request.url.path = "/health"
        call_next = AsyncMock(return_value=Mock(headers={}))
        call_next.return_value.headers = {}

        response = await middleware.dispatch(request, call_next)

        assert call_next.called
        assert response is not None

    async def test_dispatch_metrics_endpoint(self, middleware):
        """测试 metrics 端点跳过限流"""
        from unittest.mock import AsyncMock

        request = Mock(spec=Request)
        request.url.path = "/metrics"
        call_next = AsyncMock(return_value=Mock(headers={}))
        call_next.return_value.headers = {}

        response = await middleware.dispatch(request, call_next)

        assert call_next.called

    async def test_dispatch_rate_limited(self, middleware, mock_redis, mock_request):
        """测试限流触发"""
        mock_redis.eval = Mock(return_value=[0, 0.0, 30.0])

        from unittest.mock import AsyncMock

        call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, call_next)

        # 不应该调用 call_next
        assert not call_next.called

    async def test_dispatch_success(self, middleware, mock_request):
        """测试请求成功"""
        from unittest.mock import AsyncMock

        mock_response = Mock()
        mock_response.headers = {}
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert call_next.called
        assert "X-RateLimit-Remaining" in response.headers


# ============ 集成测试 ============


@pytest.mark.integration
class TestRateLimitIntegration:
    """限流系统集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_rate_limit_config_endpoint(self, client):
        """测试获取限流配置端点"""
        response = client.get("/api/v1/rate-limit/config")

        assert response.status_code == 200
        data = response.json()
        assert "global_limit" in data
        assert "user_limits" in data
        assert "ip_limit" in data
        assert "api_limits" in data

    def test_rate_limit_status_endpoint(self, client):
        """测试获取限流状态端点"""
        response = client.get("/api/v1/rate-limit/status")

        assert response.status_code == 200
        data = response.json()
        assert "client_ip" in data
        assert "limits" in data

    def test_whitelist_management(self, client):
        """测试白名单管理"""
        # 添加到白名单
        response = client.post(
            "/api/v1/rate-limit/whitelist",
            json={"type": "ip", "value": "192.168.1.100"},
        )
        assert response.status_code == 200

        # 获取白名单
        response = client.get("/api/v1/rate-limit/whitelist")
        assert response.status_code == 200
        data = response.json()
        assert any(item["value"] == "192.168.1.100" for item in data)

        # 从白名单移除
        response = client.delete(
            "/api/v1/rate-limit/whitelist",
            json={"type": "ip", "value": "192.168.1.100"},
        )
        assert response.status_code == 200

    def test_blacklist_management(self, client):
        """测试黑名单管理"""
        # 添加到黑名单
        response = client.post(
            "/api/v1/rate-limit/blacklist",
            json={"type": "ip", "value": "192.168.1.200"},
        )
        assert response.status_code == 200

        # 获取黑名单
        response = client.get("/api/v1/rate-limit/blacklist")
        assert response.status_code == 200
        data = response.json()
        assert any(item["value"] == "192.168.1.200" for item in data)

        # 从黑名单移除
        response = client.delete(
            "/api/v1/rate-limit/blacklist",
            json={"type": "ip", "value": "192.168.1.200"},
        )
        assert response.status_code == 200

    def test_rate_limit_test_endpoint(self, client):
        """测试限流测试端点"""
        response = client.get("/api/v1/rate-limit/test")

        assert response.status_code == 200
        assert "message" in response.json()


# ============ 装饰器测试 ============


@pytest.mark.asyncio
class TestRateLimitDecorator:
    """限流装饰器测试"""

    @pytest.fixture
    def mock_redis(self):
        redis = Mock()
        redis.eval = Mock(return_value=[1, 90.0, 0.0])
        redis.hgetall = Mock(return_value={})
        return redis

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        request.state.user = None
        return request

    async def test_decorator_default(self, mock_redis, mock_request):
        """测试默认限流装饰器"""
        @rate_limit()
        async def test_func(request: Request):
            return {"message": "ok"}

        result = await test_func(request=mock_request)
        assert result == {"message": "ok"}

    async def test_decorator_custom_limit(self, mock_redis, mock_request):
        """测试自定义限流装饰器"""
        @rate_limit(limit=10, window=60)
        async def test_func(request: Request):
            return {"message": "ok"}

        result = await test_func(request=mock_request)
        assert result == {"message": "ok"}

    async def test_decorator_rate_limited(self, mock_redis, mock_request):
        """测试装饰器限流触发"""
        mock_redis.eval = Mock(return_value=[0, 0.0, 30.0])

        @rate_limit(limit=5, window=60)
        async def test_func(request: Request):
            return {"message": "ok"}

        with pytest.raises(HTTPException) as exc_info:
            await test_func(request=mock_request)

        assert exc_info.value.status_code == 429

    async def test_decorator_whitelisted(self, mock_redis, mock_request):
        """测试白名单用户绕过限流"""
        limiter = get_rate_limiter()
        limiter.add_to_whitelist(ip="192.168.1.100")

        @rate_limit(limit=5, window=60)
        async def test_func(request: Request):
            return {"message": "ok"}

        result = await test_func(request=mock_request)
        assert result == {"message": "ok"}

        limiter.remove_from_whitelist(ip="192.168.1.100")


# ============ 配置测试 ============


class TestRateLimitConfig:
    """限流配置测试"""

    def test_global_limit_config(self):
        """测试全局限流配置"""
        config = RateLimitConfig()
        assert config.GLOBAL_LIMIT == 10000
        assert config.GLOBAL_WINDOW == 60

    def test_user_limit_config(self):
        """测试用户限流配置"""
        config = RateLimitConfig()
        assert config.USER_LIMITS["free"] == 100
        assert config.USER_LIMITS["professional"] == 500
        assert config.USER_LIMITS["enterprise"] == 2000

    def test_ip_limit_config(self):
        """测试 IP 限流配置"""
        config = RateLimitConfig()
        assert config.IP_LIMIT == 200
        assert config.IP_WINDOW == 60

    def test_api_limit_config(self):
        """测试 API 限流配置"""
        config = RateLimitConfig()
        assert config.API_LIMITS["/api/v1/conversations"] == 60
        assert config.API_LIMITS["/api/v1/messages"] == 120
        assert config.API_LIMITS["/api/v1/knowledge"] == 30

    def test_burst_capacity_config(self):
        """测试突发容量配置"""
        config = RateLimitConfig()
        assert config.BURST_CAPACITY == 2
        assert config.DEFAULT_CAPACITY == 100
