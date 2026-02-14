"""
限流中间件和装饰器
"""

from functools import wraps
from typing import Optional, Callable, Any, Dict
from fastapi import Request, HTTPException, status, Response
from fastapi.responses import JSONResponse
from fastapi.middleware import Middleware
from fastapi.middleware.base import BaseHTTPMiddleware

from app.core.rate_limit import RateLimiter, get_rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(self, app, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""

        # 跳过健康检查和 metrics 端点
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        try:
            # 检查限流
            allowed, info = await self.limiter.check_rate_limit(request)

            if not allowed:
                # 返回 429 Too Many Requests
                retry_after = int(info.get("retry_after", 60))

                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Too Many Requests",
                        "message": "请求过于频繁，请稍后再试",
                        "retry_after": retry_after,
                        "remaining": max(0, info.get("remaining", 0)),
                    },
                )
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Remaining"] = str(max(0, info.get("remaining", 0)))
                response.headers["X-RateLimit-Reset"] = str(retry_after)

                return response

            # 添加限流信息到响应头
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(int(info.get("remaining", 0)))
            response.headers["X-RateLimit-Limit"] = str(info.get("capacity", 0))

            # 添加各层级限流信息
            if "user" in info and "user_tier" in info["user"]:
                response.headers["X-RateLimit-UserTier"] = info["user"]["user_tier"]

            return response

        except HTTPException:
            # 如果已经抛出 HTTPException（如黑名单），直接传递
            raise
        except Exception as e:
            # 限流出错时，降级处理：允许请求通过
            print(f"Rate limit middleware error: {e}")
            return await call_next(request)


def rate_limit(
    key_prefix: Optional[str] = None,
    limit: Optional[int] = None,
    window: Optional[int] = None,
):
    """
    限流装饰器

    Args:
        key_prefix: 限流键前缀（用于自定义限流键）
        limit: 自定义限流数量（不指定则使用默认配置）
        window: 时间窗口（秒，不指定则使用默认配置）

    Example:
        @router.get("/api/special")
        @rate_limit(limit=10, window=60)  # 每分钟最多 10 次请求
        async def special_endpoint():
            return {"message": "ok"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 从 kwargs 中获取 Request 对象
            request: Optional[Request] = kwargs.get("request")

            if not request:
                # 如果没有 request，尝试从 args 中获取
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                # 没有找到 Request 对象，直接调用函数
                return await func(*args, **kwargs)

            limiter = get_rate_limiter()

            try:
                # 检查黑名单和白名单
                if await limiter.check_blacklist(request):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="您的 IP 或账户已被封禁",
                    )

                if await limiter.check_whitelist(request):
                    return await func(*args, **kwargs)

                # 如果指定了自定义限流，使用自定义限流
                if limit is not None and window is not None:
                    from app.core.rate_limit import TokenBucket

                    # 使用 IP + 路径作为限流键
                    client_ip = limiter._get_client_ip(request)
                    key_suffix = f"{key_prefix}:{request.url.path}" if key_prefix else request.url.path
                    key = limiter._get_redis_key("custom", f"{client_ip}:{key_suffix}")

                    bucket = TokenBucket(
                        capacity=limit * limiter.config.BURST_CAPACITY,
                        refill_rate=limiter._get_refill_rate(limit, window),
                        redis_client=limiter.redis,
                        key=key,
                    )

                    allowed, info = await bucket.consume()

                    if not allowed:
                        retry_after = int(info.get("retry_after", window))

                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail={
                                "error": "Too Many Requests",
                                "message": "请求过于频繁，请稍后再试",
                                "retry_after": retry_after,
                                "remaining": max(0, info.get("remaining", 0)),
                            },
                            headers={
                                "Retry-After": str(retry_after),
                                "X-RateLimit-Remaining": str(max(0, info.get("remaining", 0))),
                            },
                        )
                else:
                    # 使用默认的多层级限流
                    allowed, info = await limiter.check_rate_limit(request)

                    if not allowed:
                        retry_after = int(info.get("retry_after", 60))

                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail={
                                "error": "Too Many Requests",
                                "message": "请求过于频繁，请稍后再试",
                                "retry_after": retry_after,
                                "remaining": max(0, info.get("remaining", 0)),
                            },
                            headers={
                                "Retry-After": str(retry_after),
                                "X-RateLimit-Remaining": str(max(0, info.get("remaining", 0))),
                            },
                        )

                # 添加限流信息到响应（如果函数返回 Response 对象）
                result = await func(*args, **kwargs)

                if isinstance(result, Response):
                    result.headers["X-RateLimit-Remaining"] = str(int(info.get("remaining", 0)))
                    result.headers["X-RateLimit-Limit"] = str(info.get("capacity", 0))

                return result

            except HTTPException:
                raise
            except Exception as e:
                print(f"Rate limit decorator error: {e}")
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def create_rate_limit_middleware(limiter: Optional[RateLimiter] = None) -> Middleware:
    """
    创建限流中间件（用于 app.add_middleware）

    Args:
        limiter: 自定义限流器实例

    Example:
        from fastapi import FastAPI
        from app.core.rate_limit_middleware import create_rate_limit_middleware

        app = FastAPI()
        app.add_middleware(create_rate_limit_middleware())
    """
    return Middleware(RateLimitMiddleware, limiter=limiter)
