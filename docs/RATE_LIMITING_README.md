# CLAW.AI API 限流系统 - 快速开始

## 📋 概述

CLAW.AI API 限流系统是一个基于令牌桶算法的多层级限流解决方案，用于保护 API 免受滥用和过载。

## ✨ 特性

- ✅ **多层级限流**：全局、用户、IP、API 四层防护
- ✅ **令牌桶算法**：支持突发请求，平滑流量控制
- ✅ **白名单/黑名单**：灵活的访问控制
- ✅ **Redis 存储**：高性能分布式限流状态
- ✅ **监控告警**：实时监控和自动告警
- ✅ **降级策略**：Redis 故障时自动降级
- ✅ **RESTful API**：完整的管理接口
- ✅ **装饰器支持**：灵活的自定义限流

## 📦 安装

### 1. 依赖要求

```bash
# Redis（必需）
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### 2. 安装 Python 依赖

```bash
cd /home/wuying/clawd/claw-ai-backend
pip install -r requirements.txt
```

主要依赖：
- `redis==5.0.1` - Redis 客户端
- `fastapi==0.104.1` - Web 框架
- `pydantic==2.5.0` - 数据验证

## 🚀 快速开始

### 1. 启动 Redis

```bash
# 启动 Redis 服务
redis-server

# 或使用 Docker
docker start redis
```

### 2. 配置应用

检查 `app/core/config.py` 中的配置：

```python
# Redis 配置
REDIS_URL: str = "redis://localhost:6379/0"

# 限流配置
RATE_LIMIT_ENABLED: bool = True
RATE_LIMIT_REDIS_URL: str = "redis://localhost:6379/0"
```

### 3. 启动应用

```bash
cd /home/wuying/clawd/claw-ai-backend
python -m app.main
```

### 4. 验证安装

```bash
# 健康检查
curl http://localhost:8000/health

# 检查限流配置
curl http://localhost:8000/api/v1/rate-limit/config

# 测试限流
curl http://localhost:8000/api/v1/rate-limit/test
```

## 📊 限流配置

### 默认配置

| 层级 | 限制 | 时间窗口 | 突发容量 |
|------|------|----------|----------|
| 全局 | 10,000 req/min | 60s | 20,000 |
| 用户-免费 | 100 req/min | 60s | 200 |
| 用户-专业 | 500 req/min | 60s | 1,000 |
| 用户-企业 | 2,000 req/min | 60s | 4,000 |
| IP | 200 req/min | 60s | 400 |
| API-对话 | 60 req/min | 60s | 120 |
| API-消息 | 120 req/min | 60s | 240 |
| API-知识库 | 30 req/min | 60s | 60 |

### 修改配置

编辑 `app/core/rate_limit.py` 中的 `RateLimitConfig` 类：

```python
class RateLimitConfig:
    GLOBAL_LIMIT = 20000  # 修改全局限制
    # ... 其他配置
```

## 🔧 API 接口

### 监控接口

```bash
# 获取监控数据
GET /api/v1/rate-limit/monitor

# 获取限流配置
GET /api/v1/rate-limit/config

# 获取当前状态
GET /api/v1/rate-limit/status
```

### 白名单管理

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

### 黑名单管理

```bash
# 添加到黑名单
POST /api/v1/rate-limit/blacklist
{
  "type": "ip",
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

### 重置限流

```bash
# 重置用户限流
POST /api/v1/rate-limit/reset
{
  "type": "user",
  "identifier": "user_12345"
}

# 重置 IP 限流
POST /api/v1/rate-limit/reset
{
  "type": "ip",
  "identifier": "192.168.1.100"
}
```

## 💡 使用示例

### 1. 全局限流（自动启用）

所有 API 端点自动应用限流：

```bash
curl -X GET http://localhost:8000/api/v1/conversations \
  -H "Authorization: Bearer YOUR_TOKEN"

# 响应头
X-RateLimit-Remaining: 95
X-RateLimit-Limit: 100
```

### 2. 自定义限流装饰器

```python
from fastapi import APIRouter
from app.core.rate_limit_middleware import rate_limit

router = APIRouter()

@router.get("/special")
@rate_limit(limit=10, window=60)  # 每分钟 10 次
async def special_endpoint():
    return {"message": "ok"}
```

### 3. 客户端处理限流

```python
import requests
import time

def make_request(url, token):
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", 60)
            print(f"限流中，{retry_after} 秒后重试...")
            time.sleep(int(retry_after))
        else:
            raise Exception(f"请求失败: {response.status_code}")
```

## 📈 监控和告警

### 监控指标

系统会自动收集以下指标：
- 总请求数（按端点和方法）
- 被拦截的请求数
- 限流使用率

### 告警阈值

当任一层级的限流使用率达到 **90%** 时，系统会自动触发告警。

### 查看监控数据

```bash
curl http://localhost:8000/api/v1/rate-limit/monitor
```

响应示例：

```json
{
  "endpoints": {
    "/api/v1/conversations": {
      "total_requests": 1523,
      "blocked_requests": 23,
      "methods": {
        "GET": {"total": 1200, "blocked": 18},
        "POST": {"total": 300, "blocked": 5}
      }
    }
  }
}
```

## 🧪 测试

### 运行测试

```bash
cd /home/wuying/clawd/claw-ai-backend
pytest tests/test_rate_limit.py -v
```

### 压力测试

```bash
# 使用 Apache Bench
ab -n 15000 -c 100 http://localhost:8000/api/v1/rate-limit/test

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/rate-limit/test
```

### 测试脚本

```python
import asyncio
import requests

async def test_rate_limit():
    url = "http://localhost:8000/api/v1/conversations"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}

    success = 0
    blocked = 0

    for i in range(150):
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            success += 1
        elif response.status_code == 429:
            blocked += 1

    print(f"成功: {success}, 被限流: {blocked}")

asyncio.run(test_rate_limit())
```

## 📚 文档

完整文档请查看：

- **[限流策略文档](./RATE_LIMITING.md)** - 详细的限流策略和配置说明
- **[使用示例文档](./RATE_LIMITING_EXAMPLES.md)** - 实际使用示例和集成指南

## 🛠️ 故障排查

### 1. Redis 连接失败

**症状**：所有请求都通过，没有限流信息

**解决**：
```bash
# 检查 Redis 是否运行
redis-cli ping

# 查看应用日志
tail -f logs/app.log
```

### 2. 限流不生效

**症状**：超过限制仍能正常请求

**排查**：
1. 检查限流配置是否启用
2. 检查请求是否在白名单中
3. 检查中间件是否正确加载

### 3. 用户被误判限流

**步骤**：
1. 查看限流状态：`GET /api/v1/rate-limit/status`
2. 检查用户订阅级别
3. 如需，使用重置接口解除限流

## 🔒 安全建议

1. **保护管理接口**：限流管理接口应该需要管理员权限
2. **限制黑名单大小**：黑名单过大会影响性能
3. **定期清理**：定期清理不再需要的黑/白名单项
4. **日志审计**：记录所有黑/白名单的修改操作

## 📝 最佳实践

### 1. 客户端处理

- 正确处理 429 响应
- 读取 `Retry-After` 头
- 使用指数退避策略重试

### 2. 监控和告警

- 定期检查限流监控数据
- 关注限流使用率
- 及时调整限流策略

### 3. 用户分级

根据用户价值提供不同级别的限流：
- VIP 用户：更高限流阈值
- 普通用户：标准限流
- 可疑用户：严格限流

## 🚀 未来优化

- [ ] 动态限流：根据系统负载动态调整限流阈值
- [ ] 智能限流：使用机器学习识别异常流量
- [ ] 可视化仪表盘：提供限流数据的可视化展示
- [ ] 分布式限流：支持多实例部署的限流
- [ ] 更细粒度控制：支持按用户角色、时间段等维度限流

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👥 维护者

CLAW.AI Team

---

**最后更新**: 2025-02-14
**版本**: 1.0.0
