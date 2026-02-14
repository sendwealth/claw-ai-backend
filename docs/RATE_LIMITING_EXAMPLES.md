# CLAW.AI API 限流使用示例

本文档提供了限流系统的实际使用示例和集成指南。

## 目录

1. [基本使用](#基本使用)
2. [自定义限流装饰器](#自定义限流装饰器)
3. [白名单和黑名单管理](#白名单和黑名单管理)
4. [限流监控](#限流监控)
5. [客户端处理](#客户端处理)
6. [测试示例](#测试示例)

---

## 基本使用

### 1. 全局中间件（已启用）

系统已经自动在所有 API 端点上启用限流中间件，无需额外配置。

**示例：普通请求**

```bash
# 正常请求
curl -X GET "http://localhost:8000/api/v1/conversations" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 响应
HTTP/1.1 200 OK
X-RateLimit-Remaining: 95
X-RateLimit-Limit: 100
X-RateLimit-UserTier: free
```

### 2. 触发限流

```bash
# 超过限制的请求
curl -X GET "http://localhost:8000/api/v1/conversations" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 响应
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 45
X-RateLimit-Remaining: 0

{
  "error": "Too Many Requests",
  "message": "请求过于频繁，请稍后再试",
  "retry_after": 45,
  "remaining": 0
}
```

---

## 自定义限流装饰器

### 示例 1：基础自定义限流

对特定端点设置更严格的限流：

```python
from fastapi import APIRouter, Depends
from app.core.rate_limit_middleware import rate_limit
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/expensive-operation")
@rate_limit(limit=5, window=60)  # 每分钟最多 5 次请求
async def expensive_operation(
    current_user: get_current_user = Depends(get_current_user)
):
    """
    执行昂贵的操作，限流为每分钟 5 次
    """
    return {"message": "操作成功", "user_id": current_user.id}
```

### 示例 2：按用户类型限流

```python
from fastapi import Request

@router.get("/special-api")
async def special_api(
    request: Request,
    current_user: get_current_user = Depends(get_current_user)
):
    """
    根据用户订阅级别设置不同的限流
    """
    user_tier = request.state.user.tier

    limits = {
        "free": 10,
        "professional": 50,
        "enterprise": 200
    }

    @rate_limit(limit=limits.get(user_tier, 10), window=60)
    async def _handler():
        return {"message": "操作成功"}

    return await _handler()
```

### 示例 3：使用键前缀分组限流

```python
@router.get("/api/export/{export_type}")
@rate_limit(key_prefix="export", limit=3, window=3600)  # 每小时 3 次
async def export_data(export_type: str):
    """
    导出数据，每小时最多 3 次
    """
    return {"message": f"导出 {export_type} 成功"}
```

---

## 白名单和黑名单管理

### 1. 管理白名单

#### 添加 IP 到白名单

```bash
curl -X POST "http://localhost:8000/api/v1/rate-limit/whitelist" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "type": "ip",
    "value": "192.168.1.100"
  }'

# 响应
{
  "message": "已添加到白名单: ip=192.168.1.100"
}
```

#### 添加用户到白名单

```bash
curl -X POST "http://localhost:8000/api/v1/rate-limit/whitelist" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "type": "user",
    "value": "user_12345"
  }'

# 响应
{
  "message": "已添加到白名单: user=user_12345"
}
```

#### 查看白名单

```bash
curl -X GET "http://localhost:8000/api/v1/rate-limit/whitelist" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 响应
[
  {
    "type": "ip",
    "value": "192.168.1.100"
  },
  {
    "type": "user",
    "value": "user_12345"
  }
]
```

#### 从白名单移除

```bash
curl -X DELETE "http://localhost:8000/api/v1/rate-limit/whitelist" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "type": "ip",
    "value": "192.168.1.100"
  }'

# 响应
{
  "message": "已从白名单移除: ip=192.168.1.100"
}
```

---

### 2. 管理黑名单

#### 添加 IP 到黑名单

```bash
curl -X POST "http://localhost:8000/api/v1/rate-limit/blacklist" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "type": "ip",
    "value": "192.168.1.200"
  }'

# 响应
{
  "message": "已添加到黑名单: ip=192.168.1.200"
}
```

#### 黑名单用户请求会被拒绝

```bash
curl -X GET "http://localhost:8000/api/v1/conversations" \
  -H "Authorization: Bearer BLOCKED_USER_TOKEN"

# 响应
HTTP/1.1 403 Forbidden

{
  "detail": "您的 IP 或账户已被封禁"
}
```

---

## 限流监控

### 1. 查看监控数据

```bash
curl -X GET "http://localhost:8000/api/v1/rate-limit/monitor" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 响应
{
  "endpoints": {
    "/api/v1/conversations": {
      "total_requests": 1523,
      "blocked_requests": 23,
      "methods": {
        "GET": {
          "total": 1200,
          "blocked": 18
        },
        "POST": {
          "total": 300,
          "blocked": 5
        }
      }
    },
    "/api/v1/messages": {
      "total_requests": 3456,
      "blocked_requests": 156,
      "methods": {
        "POST": {
          "total": 3456,
          "blocked": 156
        }
      }
    }
  }
}
```

### 2. 查看当前配置

```bash
curl -X GET "http://localhost:8000/api/v1/rate-limit/config" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 响应
{
  "global_limit": 10000,
  "global_window": 60,
  "user_limits": {
    "free": 100,
    "professional": 500,
    "enterprise": 2000
  },
  "ip_limit": 200,
  "api_limits": {
    "/api/v1/conversations": 60,
    "/api/v1/messages": 120,
    "/api/v1/knowledge": 30
  },
  "burst_capacity": 2
}
```

### 3. 查看当前用户的限流状态

```bash
curl -X GET "http://localhost:8000/api/v1/rate-limit/status" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 响应
{
  "client_ip": "192.168.1.50",
  "user_id": "user_12345",
  "user_tier": "professional",
  "is_whitelisted": false,
  "is_blacklisted": false,
  "limits": {
    "global": {
      "tokens": 18500,
      "capacity": 20000,
      "last_update": 1707901234.567
    },
    "user": {
      "tokens": 450,
      "capacity": 1000,
      "last_update": 1707901234.567
    },
    "ip": {
      "tokens": 180,
      "capacity": 400,
      "last_update": 1707901234.567
    },
    "api": {
      "tokens": 110,
      "capacity": 120,
      "last_update": 1707901234.567,
      "api_path": "/api/v1/conversations"
    }
  }
}
```

---

## 重置限流

### 重置用户限流

```bash
curl -X POST "http://localhost:8000/api/v1/rate-limit/reset" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "type": "user",
    "identifier": "user_12345"
  }'

# 响应
{
  "message": "已重置用户限流: user_12345"
}
```

### 重置 IP 限流

```bash
curl -X POST "http://localhost:8000/api/v1/rate-limit/reset" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{
    "type": "ip",
    "identifier": "192.168.1.100"
  }'

# 响应
{
  "message": "已重置 IP 限流: 192.168.1.100"
}
```

---

## 客户端处理

### Python 示例

```python
import requests
import time

def make_api_request(url, token, max_retries=3):
    """
    带限流处理的 API 请求
    """
    headers = {
        "Authorization": f"Bearer {token}"
    }

    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()

        elif response.status_code == 429:
            # 限流，读取重试时间
            retry_after = response.headers.get("Retry-After", 60)
            print(f"限流中，{retry_after} 秒后重试...")
            time.sleep(int(retry_after))

        else:
            # 其他错误
            raise Exception(f"请求失败: {response.status_code}")

    raise Exception("超过最大重试次数")

# 使用示例
result = make_api_request(
    "http://localhost:8000/api/v1/conversations",
    "YOUR_TOKEN"
)
print(result)
```

### JavaScript 示例

```javascript
async function makeApiRequest(url, token, maxRetries = 3) {
  const headers = {
    'Authorization': `Bearer ${token}`
  };

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const response = await fetch(url, { headers });

    if (response.ok) {
      return await response.json();
    }

    if (response.status === 429) {
      // 限流，读取重试时间
      const retryAfter = response.headers.get('Retry-After') || '60';
      console.log(`限流中，${retryAfter} 秒后重试...`);

      // 使用指数退避
      const waitTime = parseInt(retryAfter) * Math.pow(2, attempt);
      await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
    } else {
      throw new Error(`请求失败: ${response.status}`);
    }
  }

  throw new Error('超过最大重试次数');
}

// 使用示例
makeApiRequest('http://localhost:8000/api/v1/conversations', 'YOUR_TOKEN')
  .then(result => console.log(result))
  .catch(error => console.error(error));
```

---

## 测试示例

### 1. 测试全局限流

```bash
# 使用 Apache Bench 进行压力测试
ab -n 15000 -c 100 \
   -H "Authorization: Bearer YOUR_TOKEN" \
   http://localhost:8000/api/v1/rate-limit/test

# 当超过 10,000 请求/分钟时，会看到 429 响应
```

### 2. 测试用户限流

```python
import requests
import asyncio

async def test_user_limit():
    token = "YOUR_TOKEN"
    url = "http://localhost:8000/api/v1/conversations"
    headers = {"Authorization": f"Bearer {token}"}

    success_count = 0
    blocked_count = 0

    for i in range(150):  # 尝试发送 150 次请求
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            blocked_count += 1
            print(f"请求 #{i+1}: 被限流")
        else:
            print(f"请求 #{i+1}: 错误 {response.status_code}")

    print(f"\n总计: {success_count} 成功, {blocked_count} 被限流")

asyncio.run(test_user_limit())
```

### 3. 测试自定义限流装饰器

```python
import requests

# 测试自定义限流的端点（每分钟 5 次）
url = "http://localhost:8000/api/v1/expensive-operation"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

success_count = 0
for i in range(10):
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        success_count += 1
        print(f"请求 #{i+1}: 成功")
    elif response.status_code == 429:
        print(f"请求 #{i+1}: 被限流（每分钟最多 5 次）")

print(f"\n总计: {success_count}/10 请求成功")
```

---

## 集成到现有项目

### 1. 确认中间件已启用

检查 `app/main.py` 中是否已添加限流中间件：

```python
from app.core.rate_limit_middleware import RateLimitMiddleware
from app.core.rate_limit import get_rate_limiter

# 添加限流中间件
app.add_middleware(RateLimitMiddleware, limiter=get_rate_limiter())
```

### 2. 确认路由已注册

```python
from app.api import rate_limit

# 注册限流管理路由
app.include_router(rate_limit.router, prefix="/api/v1/rate-limit", tags=["限流管理"])
```

### 3. 验证安装

启动应用后，访问健康检查：

```bash
curl http://localhost:8000/health

# 应该返回
{
  "status": "healthy",
  "app": "CLAW.AI",
  "version": "1.0.0"
}
```

### 4. 测试限流

```bash
# 测试限流接口
curl http://localhost:8000/api/v1/rate-limit/test

# 查看限流状态
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/rate-limit/status
```

---

## 常见问题

### Q1: 如何临时禁用限流？

在 `app/main.py` 中注释掉限流中间件：

```python
# app.add_middleware(RateLimitMiddleware, limiter=get_rate_limiter())
```

### Q2: 如何调整限流阈值？

编辑 `app/core/rate_limit.py` 中的 `RateLimitConfig` 类：

```python
class RateLimitConfig:
    GLOBAL_LIMIT = 20000  # 修改为 20,000
    # ...
```

### Q3: 如何查看 Redis 中的限流数据？

```bash
# 连接到 Redis
redis-cli

# 查看所有限流键
KEYS rate_limit:*

# 查看某个键的详情
HGETALL rate_limit:user:user_12345
```

### Q4: 如何清理过期的限流数据？

Redis 会自动清理过期键（5 分钟），也可以手动清理：

```bash
# 清理所有限流数据
redis-cli KEYS "rate_limit:*" | xargs redis-cli DEL
```

---

## 最佳实践

### 1. 客户端实现指数退避

```python
import time
import random

def exponential_backoff(attempt, base_wait=1, max_wait=60):
    """
    指数退避，加入随机抖动
    """
    wait_time = min(base_wait * (2 ** attempt), max_wait)
    jitter = random.uniform(0.5, 1.5)
    return wait_time * jitter
```

### 2. 监控限流指标

```python
import requests

def monitor_rate_limit():
    """定期监控限流数据"""
    url = "http://localhost:8000/api/v1/rate-limit/monitor"
    headers = {"Authorization": "Bearer ADMIN_TOKEN"}

    response = requests.get(url, headers=headers)
    data = response.json()

    for endpoint, stats in data["endpoints"].items():
        blocked_rate = stats["blocked_requests"] / stats["total_requests"]

        if blocked_rate > 0.1:  # 如果限流率超过 10%
            print(f"⚠️ 警告: {endpoint} 限流率 {blocked_rate:.1%}")

# 每分钟检查一次
import schedule
schedule.every(1).minutes.do(monitor_rate_limit)
```

### 3. 实现优雅降级

```python
from app.core.rate_limit import RateLimiter

class GracefulRateLimiter(RateLimiter):
    """带降级的限流器"""

    async def check_rate_limit(self, request):
        try:
            return await super().check_rate_limit(request)
        except Exception as e:
            print(f"限流出错，降级处理: {e}")
            # 返回允许通过，但记录日志
            return True, {"error": str(e)}
```

---

**文档版本**：1.0.0
**最后更新**：2025-02-14
