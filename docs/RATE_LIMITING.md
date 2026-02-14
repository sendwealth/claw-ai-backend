# CLAW.AI API 限流策略文档

## 概述

CLAW.AI 实现了基于令牌桶算法的多层级 API 限流系统，用于保护系统免受滥用和过度负载的影响。

## 限流算法

### 令牌桶算法（Token Bucket）

CLAW.AI 使用令牌桶算法实现限流，该算法具有以下特点：

- **平滑流量控制**：允许一定程度的突发请求
- **精确控制**：可以精确控制请求速率
- **灵活性高**：支持不同的限流策略

**算法原理**：
1. 桶中固定容量的令牌
2. 以恒定速率向桶中添加令牌
3. 每个请求消费一个令牌
4. 如果桶中有足够令牌，请求通过
5. 如果令牌不足，请求被拒绝

## 限流层级

CLAW.AI 实现了四个层级的限流，所有层级都会同时检查：

### 1. 全局限流

**目的**：保护整个系统免受过载影响

| 配置项 | 值 |
|--------|-----|
| 限制 | 10,000 请求/分钟 |
| 时间窗口 | 60 秒 |
| 突发容量 | 20,000 令牌（2 倍） |

**使用场景**：防止系统整体过载

---

### 2. 用户限流

**目的**：根据用户订阅级别限制请求频率

| 订阅级别 | 限制 | 时间窗口 |
|----------|------|----------|
| 免费版（free） | 100 请求/分钟 | 60 秒 |
| 专业版（professional） | 500 请求/分钟 | 60 秒 |
| 企业版（enterprise） | 2,000 请求/分钟 | 60 秒 |

**突发容量**：各级别都是 2 倍容量

**使用场景**：根据用户订阅级别提供差异化服务

---

### 3. IP 限流

**目的**：防止恶意 IP 进行滥用攻击

| 配置项 | 值 |
|--------|-----|
| 限制 | 200 请求/分钟 |
| 时间窗口 | 60 秒 |
| 突发容量 | 400 令牌（2 倍） |

**使用场景**：防止 DDoS 攻击和恶意扫描

---

### 4. API 级限流

**目的**：根据 API 的重要性设置不同限制

| API 路径 | 限制 | 时间窗口 |
|----------|------|----------|
| `/api/v1/conversations` | 60 请求/分钟 | 60 秒 |
| `/api/v1/messages` | 120 请求/分钟 | 60 秒 |
| `/api/v1/knowledge` | 30 请求/分钟 | 60 秒 |

**突发容量**：各 API 都是 2 倍容量

**使用场景**：保护关键 API 端点

---

## 技术实现

### 存储

- **Redis**：用于存储令牌桶状态
- **键格式**：`rate_limit:{level}:{identifier}`
  - 全局：`rate_limit:global:all`
  - 用户：`rate_limit:user:{user_id}`
  - IP：`rate_limit:ip:{client_ip}`
  - API：`rate_limit:api:{api_path}`

### Lua 脚本

使用 Redis Lua 脚本保证令牌桶操作的原子性，防止竞态条件。

### 响应头

当限流生效时，API 会返回以下响应头：

| 响应头 | 说明 |
|--------|------|
| `X-RateLimit-Remaining` | 剩余请求次数 |
| `X-RateLimit-Limit` | 请求限制总数 |
| `X-RateLimit-Reset` | 重试时间（秒） |
| `X-RateLimit-UserTier` | 用户订阅级别 |
| `Retry-After` | HTTP 标准重试时间头 |

### 错误响应

当请求被限流时，返回 `429 Too Many Requests`：

```json
{
  "error": "Too Many Requests",
  "message": "请求过于频繁，请稍后再试",
  "retry_after": 45,
  "remaining": 0
}
```

---

## 白名单和黑名单

### 白名单

白名单中的 IP 或用户不受限流限制。

**管理接口**：

```bash
# 添加到白名单
POST /api/v1/rate-limit/whitelist
{
  "type": "ip",      # 或 "user"
  "value": "192.168.1.100"
}

# 获取白名单
GET /api/v1/rate-limit/whitelist

# 从白名单移除
DELETE /api/v1/rate-limit/whitelist
{
  "type": "ip",
  "value": "192.168.1.100"
}
```

---

### 黑名单

黑名单中的 IP 或用户会被直接拒绝请求（403 Forbidden）。

**管理接口**：

```bash
# 添加到黑名单
POST /api/v1/rate-limit/blacklist
{
  "type": "ip",      # 或 "user"
  "value": "192.168.1.100"
}

# 获取黑名单
GET /api/v1/rate-limit/blacklist

# 从黑名单移除
DELETE /api/v1/rate-limit/blacklist
{
  "type": "ip",
  "value": "192.168.1.100"
}
```

---

## 限流监控

### 监控接口

```bash
# 获取限流监控数据
GET /api/v1/rate-limit/monitor

# 获取当前限流配置
GET /api/v1/rate-limit/config

# 获取当前用户的限流状态
GET /api/v1/rate-limit/status
```

### 监控告警

当限流使用率达到 90% 时，系统会自动触发告警。

**告警触发条件**：
- 全局限流使用率 ≥ 90%
- 用户限流使用率 ≥ 90%
- IP 限流使用率 ≥ 90%
- API 限流使用率 ≥ 90%

---

## 限流重置

管理员可以手动重置某个用户或 IP 的限流状态：

```bash
POST /api/v1/rate-limit/reset
{
  "type": "user",  # 或 "ip"
  "identifier": "user_123"
}
```

---

## 使用装饰器

除了全局中间件，还可以使用装饰器对特定端点进行自定义限流：

```python
from app.core.rate_limit_middleware import rate_limit
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/special")
@rate_limit(limit=10, window=60)  # 每分钟最多 10 次请求
async def special_endpoint():
    return {"message": "ok"}
```

---

## 降级策略

当 Redis 不可用时，系统会自动降级：
- 允许所有请求通过
- 记录错误日志
- 不返回限流信息

这确保了即使限流系统故障，核心业务不受影响。

---

## 最佳实践

### 1. 合理设置限流阈值

根据业务特点和系统容量设置合理的限流阈值，避免：
- 阈值过低：影响正常用户体验
- 阈值过高：无法有效保护系统

### 2. 监控和告警

- 定期检查限流监控数据
- 关注限流使用率
- 及时调整限流策略

### 3. 优雅降级

客户端应该正确处理 429 响应：
- 读取 `Retry-After` 头
- 使用指数退避策略重试
- 避免立即重试导致更严重的限流

### 4. 用户分级

根据用户价值提供不同级别的限流：
- VIP 用户：更高限流阈值
- 普通用户：标准限流
- 可疑用户：严格限流

### 5. 定期审查

定期审查：
- 黑名单列表
- 白名单列表
- 限流配置
- 监控数据

---

## 故障排查

### 1. 用户反馈被限流

**步骤**：
1. 检查 `/api/v1/rate-limit/status` 获取限流详情
2. 确认是哪个层级触发了限流
3. 检查用户订阅级别是否正确
4. 如需，使用重置接口解除限流

### 2. Redis 连接失败

**症状**：所有请求都通过，没有限流信息

**解决**：
1. 检查 Redis 服务是否运行
2. 检查 Redis 连接配置
3. 查看应用日志中的错误信息

### 3. 限流不生效

**症状**：超过限制仍能正常请求

**排查**：
1. 检查限流配置是否启用
2. 检查请求是否在白名单中
3. 检查中间件是否正确加载
4. 查看 Redis 中的限流数据

---

## 配置文件

限流相关配置在 `app/core/config.py` 中：

```python
# 限流配置
RATE_LIMIT_ENABLED: bool = True
RATE_LIMIT_REDIS_URL: str = "redis://localhost:6379/0"
```

核心限流配置在 `app/core/rate_limit.py` 中的 `RateLimitConfig` 类：

```python
class RateLimitConfig:
    GLOBAL_LIMIT = 10000
    GLOBAL_WINDOW = 60

    USER_LIMITS = {
        "free": 100,
        "professional": 500,
        "enterprise": 2000,
    }
    USER_WINDOW = 60

    IP_LIMIT = 200
    IP_WINDOW = 60

    API_LIMITS = {
        "/api/v1/conversations": 60,
        "/api/v1/messages": 120,
        "/api/v1/knowledge": 30,
    }
    API_WINDOW = 60

    BURST_CAPACITY = 2
    DEFAULT_CAPACITY = 100
```

---

## 性能考虑

### Redis 性能

- 使用连接池管理 Redis 连接
- 使用 Pipeline 批量操作
- 定期清理过期限流数据

### Lua 脚本

- 所有令牌桶操作使用 Lua 脚本保证原子性
- 脚本执行时间 ≤ 1ms

### 内存占用

- 每个限流键约占用 100-200 字节
- Redis 键自动过期（5 分钟）
- 建议定期清理

---

## 测试

### 测试接口

系统提供了专门的测试接口：

```bash
# 测试限流
GET /api/v1/rate-limit/test
```

多次调用该接口会触发限流，可以用于验证限流是否正常工作。

### 压力测试

建议使用压力测试工具验证限流配置：

```bash
# 使用 Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/rate-limit/test

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/rate-limit/test
```

---

## 安全建议

1. **保护管理接口**：限流管理接口应该需要管理员权限
2. **限制黑名单大小**：黑名单过大会影响性能
3. **定期清理**：定期清理不再需要的黑/白名单项
4. **日志审计**：记录所有黑/白名单的修改操作
5. **IP 验证**：对添加到黑/白名单的 IP 进行验证

---

## 未来优化方向

1. **动态限流**：根据系统负载动态调整限流阈值
2. **智能限流**：使用机器学习识别异常流量
3. **分布式限流**：支持多实例部署的限流
4. **更细粒度控制**：支持按用户角色、时间段等维度限流
5. **可视化仪表盘**：提供限流数据的可视化展示

---

## 参考文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Redis 令牌桶算法](https://redis.io/commands/incr/)
- [HTTP 429 状态码](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)

---

**文档版本**：1.0.0
**最后更新**：2025-02-14
**维护者**：CLAW.AI Team
