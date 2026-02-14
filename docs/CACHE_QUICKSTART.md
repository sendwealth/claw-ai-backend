# CLAW.AI 缓存系统快速开始指南

本指南将帮助您快速了解和使用 CLAW.AI 的缓存系统。

## 功能特性

✅ **多级缓存架构** - 内存缓存 + Redis 二级缓存
✅ **智能缓存装饰器** - 简单的注解即可启用缓存
✅ **自动 TTL 管理** - 自动清理过期数据
✅ **缓存标签系统** - 支持批量失效
✅ **缓存监控 API** - 实时查看缓存状态和统计
✅ **缓存预热** - 系统启动时预加载热点数据
✅ **API 限流** - 基于 Redis 的请求频率限制

## 快速开始

### 1. 启动 Redis

确保 Redis 服务正在运行：

```bash
# Docker 方式
docker run -d -p 6379:6379 redis:latest

# 或者使用系统包管理器安装
sudo apt-get install redis-server
sudo systemctl start redis
```

### 2. 配置 Redis 连接

在 `.env` 文件中配置 Redis URL：

```bash
REDIS_URL=redis://localhost:6379/0
```

### 3. 启动应用

```bash
cd /home/wuying/clawd/claw-ai-backend
python -m uvicorn app.main:app --reload
```

应用启动时会自动：
- 连接 Redis 缓存服务
- 执行缓存预热
- 注册缓存管理 API

## 使用缓存装饰器

### 基础缓存

```python
from app.core.cache import cached

@cached(scenario="user_profile", ttl=3600)
async def get_user(user_id: int):
    # 这里的结果会被缓存 1 小时
    return await db.query(User).filter(User.id == user_id).first()
```

### 使用缓存标签

```python
from app.core.cache import cache_by_tags

@cache_by_tags(tags=["user:123", "conversation:456"])
async def get_user_data(user_id: int):
    # 缓存结果并关联标签，用于批量失效
    return await db.query(User).filter(User.id == user_id).first()
```

### API 限流

```python
from app.core.cache import rate_limit

@router.get("/api/endpoint")
@rate_limit(max_requests=100, window=60)
async def my_endpoint():
    return {"message": "每分钟最多 100 次请求"}
```

## 缓存场景

| 场景 | TTL | 用途 |
|------|-----|------|
| `user_profile` | 1 小时 | 用户信息 |
| `user_conversations` | 10 分钟 | 用户对话列表 |
| `conversation_history` | 30 分钟 | 对话历史 |
| `document_content` | 1 小时 | 知识库文档 |
| `ai_response` | 24 小时 | AI 响应内容 |
| `rate_limit` | 1 分钟 | API 限流计数 |

## 手动使用缓存服务

```python
from app.services.cache_service import cache_service

# 设置缓存
await cache_service.set(
    key="my_key",
    value={"data": "value"},
    ttl=3600,
    tags=["tag1", "tag2"]
)

# 获取缓存
value = await cache_service.get("my_key")

# 删除缓存
await cache_service.delete("my_key")

# 批量失效（根据标签）
await cache_service.delete_by_tags(["tag1"])

# 清空所有缓存
await cache_service.clear_all()
```

## 缓存监控 API

### 查看缓存统计

```bash
curl http://localhost:8000/api/v1/cache/stats
```

响应示例：
```json
{
  "hits": 12500,
  "misses": 3500,
  "hit_rate": 78.13,
  "memory_cache_size": 1250,
  "redis_connected": true
}
```

### 查看缓存键列表

```bash
curl "http://localhost:8000/api/v1/cache/keys?scenario=user_profile&limit=100"
```

### 失效特定场景的缓存

```bash
curl -X POST "http://localhost:8000/api/v1/cache/invalidate/by-scenario?scenario=user_profile"
```

### 缓存健康检查

```bash
curl http://localhost:8000/api/v1/cache/health
```

## 缓存失效策略

### 主动失效

数据更新时主动失效相关缓存：

```python
async def update_user(user_id: int, data: dict):
    # 1. 更新数据库
    await db.update_user(user_id, data)

    # 2. 失效相关缓存
    cache_key = cache_service._generate_key(
        scenario="user_profile",
        identifier=str(user_id)
    )
    await cache_service.delete(cache_key)
```

### 标签失效

使用标签批量失效：

```python
# 设置缓存时指定标签
await cache_service.set(key, value, ttl=3600, tags=["user:123"])

# 失效所有关联的缓存
await cache_service.delete_by_tags(["user:123"])
```

### TTL 自动过期

所有缓存都有 TTL，到期自动清理：

```python
# 这个缓存会在 1 小时后自动过期
@cached(scenario="user_profile", ttl=3600)
async def get_user(user_id: int):
    return await db.query(User).filter(User.id == user_id).first()
```

## 缓存预热

### 启动时预热

应用启动时自动预加载热点数据（活跃用户、热门对话、常用文档等）。

### 手动触发预热

```bash
curl -X POST "http://localhost:8000/api/v1/cache/warmup"
```

## 性能调优

### 1. 调整 TTL

根据数据更新频率调整 TTL：

```python
# 频繁更新的数据 - 短 TTL
@cached(scenario="user_conversations", ttl=600)  # 10 分钟

# 相对稳定的数据 - 长 TTL
@cached(scenario="user_profile", ttl=3600)  # 1 小时
```

### 2. 监控命中率

定期检查缓存命中率，目标 > 70%：

```bash
curl http://localhost:8000/api/v1/cache/stats
```

### 3. 预加载热点数据

在业务低峰期预热缓存：

```python
from app.services.cache_warmup import cache_warmup_initializer

await cache_warmup_initializer.warmup_all()
```

## 常见问题

### Q: Redis 连接失败怎么办？

A: 缓存服务会自动降级到内存缓存，系统仍可正常运行。检查 Redis 服务状态和网络连接。

### Q: 如何清空所有缓存？

A: 调用清理 API（需要确认）：

```bash
curl -X DELETE "http://localhost:8000/api/v1/cache/all?confirm=true"
```

### Q: 缓存数据不一致怎么办？

A: 确保在数据更新时正确失效相关缓存，或使用更短的 TTL。

### Q: 如何查看缓存的实时内容？

A: 使用缓存键查询 API：

```bash
curl http://localhost:8000/api/v1/cache/keys/{cache_key}
```

## 高级用法

### 自定义缓存键生成

```python
def custom_key_builder(scenario, func, args, kwargs):
    """自定义缓存键生成函数"""
    user_id = args[0]
    return f"custom:{user_id}:data"

@cached(scenario="custom", key_builder=custom_key_builder)
async def get_custom_data(user_id: int):
    return await db.query(...)
```

### 跳过某些参数参与键生成

```python
@cached(scenario="user_profile", skip_args=[0])  # 跳过第一个参数（通常是 self）
async def get_user(self, user_id: int):
    return await db.query(User).filter(User.id == user_id).first()
```

## 最佳实践

1. ✅ 合理设置 TTL，平衡性能和一致性
2. ✅ 使用缓存标签，便于批量管理
3. ✅ 监控缓存命中率，及时调整策略
4. ✅ 定期预加载热点数据
5. ✅ 数据更新时主动失效缓存
6. ✅ 不要缓存敏感信息（如密码）
7. ✅ 在生产环境使用 Redis 持久化

## 下一步

- 📖 阅读完整的缓存策略文档：`docs/CACHE_STRATEGY.md`
- 🔍 查看缓存 API 文档：访问 `/docs`
- 📊 查看 Prometheus 指标：访问 `/metrics`

## 支持

如有问题，请查看：
- [缓存策略文档](docs/CACHE_STRATEGY.md)
- [API 文档](http://localhost:8000/docs)
- [GitHub Issues](https://github.com/your-repo/issues)

---

**文档版本：** 1.0.0
**最后更新：** 2024-01-15
