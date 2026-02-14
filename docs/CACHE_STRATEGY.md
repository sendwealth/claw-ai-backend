# CLAW.AI 缓存策略文档

## 概述

本文档描述了 CLAW.AI 项目的完整缓存策略，包括缓存架构、技术实现、使用场景和管理方法。

## 缓存架构

### 多级缓存设计

CLAW.AI 采用两级缓存架构：

```
┌─────────────────┐
│   应用层代码     │
└────────┬────────┘
         │
    ┌────▼────┐
    │ 缓存装饰器 │
    └────┬────┘
         │
    ┌────▼─────────────────────┐
    │     缓存服务层           │
    │  (CacheService)          │
    └────┬─────────────────────┘
         │
    ┌────▼─────────────────────┐
    │  一级缓存：内存缓存       │
    │  (_memory_cache)         │
    │  - 基于字典的快速访问     │
    │  - 自动 TTL 过期          │
    └────┬─────────────────────┘
         │ (miss)
    ┌────▼─────────────────────┐
    │  二级缓存：Redis           │
    │  - 分布式缓存              │
    │  - 持久化存储              │
    │  - 自动 TTL 过期          │
    └───────────────────────────┘
```

### 缓存流程

1. **读取流程：**
   - 请求到达缓存服务
   - 首先检查一级缓存（内存）
   - 如果命中，直接返回数据
   - 如果未命中，检查二级缓存（Redis）
   - 如果命中，回填到一级缓存并返回数据
   - 如果未命中，从数据库读取数据并写入两级缓存

2. **写入流程：**
   - 同时写入一级缓存和二级缓存
   - 设置 TTL（生存时间）
   - 可选设置缓存标签（用于批量失效）

## 缓存场景

### 1. 用户信息缓存 (user_profile)

- **场景描述：** 用户的基本信息和偏好设置
- **TTL：** 3600 秒（1 小时）
- **缓存键前缀：** `user:profile`
- **使用示例：**
  ```python
  @cached(scenario="user_profile", ttl=3600)
  async def get_user_profile(user_id: int):
      return await db.get_user(user_id)
  ```

### 2. 对话列表缓存 (user_conversations)

- **场景描述：** 用户的对话列表（按更新时间排序）
- **TTL：** 600 秒（10 分钟）
- **缓存键前缀：** `user:conversations`
- **使用示例：**
  ```python
  @cached(scenario="user_conversations", ttl=600)
  def get_user_conversations(user_id: int, skip=0, limit=100):
      return db.query_conversations(user_id, skip, limit)
  ```

### 3. 对话历史缓存 (conversation_history)

- **场景描述：** 单个对话的详细信息和消息列表
- **TTL：** 1800 秒（30 分钟）
- **缓存键前缀：** `conversation:history`
- **使用示例：**
  ```python
  @cached(scenario="conversation_history", ttl=1800)
  def get_conversation(conversation_id: int, user_id: int):
      return db.get_conversation(conversation_id, user_id)
  ```

### 4. 知识库文档缓存 (document_content)

- **场景描述：** 知识库中的文档内容和元数据
- **TTL：** 3600 秒（1 小时）
- **缓存键前缀：** `doc:content`
- **使用示例：**
  ```python
  @cached(scenario="document_content", ttl=3600)
  def get_document(document_id: int):
      return db.get_document(document_id)
  ```

### 5. AI 响应缓存 (ai_response)

- **场景描述：** AI 生成的响应内容，用于重复查询
- **TTL：** 86400 秒（24 小时）
- **缓存键前缀：** `ai:response`
- **使用示例：**
  ```python
  # 在服务内部手动使用
  cache_key = cache_service._generate_key(
      scenario="ai_response",
      identifier=f"{conversation_id}:{hash(user_message)}"
  )
  cached_response = await cache_service.get(cache_key)
  if cached_response:
      return cached_response
  # ... 调用 AI 服务并缓存响应
  ```

### 6. API 限流缓存 (rate_limit)

- **场景描述：** API 请求频率限制计数
- **TTL：** 60 秒（1 分钟）
- **缓存键前缀：** `rate:limit`
- **使用示例：**
  ```python
  @rate_limit(max_requests=100, window=60)
  async def api_endpoint():
      return {"message": "Hello"}
  ```

## 技术实现

### 缓存服务 (CacheService)

缓存服务提供以下核心功能：

1. **多级缓存管理：** 自动在内存和 Redis 之间协调
2. **缓存键生成：** 基于场景和参数生成唯一键
3. **TTL 管理：** 自动清理过期数据
4. **缓存标签：** 支持批量失效
5. **统计监控：** 追踪缓存命中率

### 缓存装饰器

提供多种装饰器，简化缓存使用：

1. **@cached：** 基础缓存装饰器
   ```python
   @cached(scenario="user_profile", ttl=3600)
   async def get_user(user_id: int):
       return await db.get_user(user_id)
   ```

2. **@cache_by_tags：** 基于标签的缓存
   ```python
   @cache_by_tags(tags=["user:123", "conversation:456"])
   async def get_data():
       return await db.query()
   ```

3. **@rate_limit：** API 限流
   ```python
   @rate_limit(max_requests=100, window=60)
   async def api_endpoint():
       return {"data": "value"}
   ```

### 缓存失效策略

#### 1. TTL 自动过期
- 所有缓存都有 TTL，到期自动清理
- 不同场景根据数据更新频率设置不同的 TTL

#### 2. 主动失效
- 数据更新时主动失效相关缓存
- 使用缓存标签实现批量失效

#### 3. 缓存预热
- 系统启动时预加载热点数据
- 定期刷新常用数据

```python
# 缓存预热示例
cache_warmer = CacheWarmer()

@cache_warmer.register_task("user_profiles", interval=3600)
async def warmup_user_profiles():
    active_users = await get_active_users()
    for user_id in active_users:
        await get_user_profile(user_id)
```

## 缓存监控

### 监控指标

1. **命中率 (Hit Rate)：** 缓存命中请求 / 总请求
2. **未命中数 (Misses)：** 缓存未命中次数
3. **设置数 (Sets)：** 缓存设置次数
4. **删除数 (Deletes)：** 缓存删除次数
5. **错误数 (Errors)：** 缓存操作错误次数
6. **内存缓存大小：** 当前内存缓存中的键数量

### 监控 API

#### 获取缓存统计

```bash
GET /api/cache/stats
```

响应示例：
```json
{
  "hits": 12500,
  "misses": 3500,
  "sets": 8000,
  "deletes": 500,
  "errors": 10,
  "hit_rate": 78.13,
  "memory_cache_size": 1250,
  "redis_connected": true
}
```

#### 获取缓存键列表

```bash
GET /api/cache/keys?scenario=user_conversations&limit=100
```

#### 获取特定缓存值

```bash
GET /api/cache/keys/{key}
```

#### 批量失效缓存

```bash
POST /api/cache/invalidate/by-tags
Content-Type: application/json

{
  "tags": ["user:123", "conversation:456"]
}
```

#### 清空所有缓存

```bash
DELETE /api/cache/all?confirm=true
```

#### 缓存健康检查

```bash
GET /api/cache/health
```

## 配置

### Redis 配置

在 `app/core/config.py` 中配置 Redis 连接：

```python
REDIS_URL: str = "redis://localhost:6379/0"
```

### 缓存场景配置

在 `app/services/cache_service.py` 的 `CacheService.CACHE_SCENARIOS` 中配置：

```python
CACHE_SCENARIOS = {
    "user_profile": {
        "ttl": 3600,
        "prefix": "user:profile",
    },
    # ... 其他场景
}
```

## 使用指南

### 1. 在服务中使用缓存装饰器

```python
from app.core.cache import cached

class MyService:
    @cached(scenario="user_profile", ttl=3600)
    async def get_user(self, user_id: int):
        return await self.db.query(User).filter(User.id == user_id).first()
```

### 2. 手动使用缓存服务

```python
from app.services.cache_service import cache_service

# 设置缓存
await cache_service.set(key, value, ttl=3600, tags=["user:123"])

# 获取缓存
value = await cache_service.get(key)

# 删除缓存
await cache_service.delete(key)

# 批量失效
await cache_service.delete_by_tags(["user:123"])
```

### 3. API 限流

```python
from app.core.cache import rate_limit

@router.get("/api/endpoint")
@rate_limit(max_requests=100, window=60)
async def my_endpoint():
    return {"message": "Hello"}
```

### 4. 缓存预热

```python
from app.core.cache import cache_warmer

# 启动时预热
@app.on_event("startup")
async def startup_event():
    await cache_service.connect()
    await cache_warmer.warmup_all()
```

## 性能优化建议

### 1. 合理设置 TTL

- 频繁更新的数据：短 TTL（几分钟）
- 相对稳定的数据：长 TTL（几小时）
- 基本不变的数据：很长 TTL（几天）

### 2. 使用缓存标签

- 为相关数据设置相同的标签
- 数据更新时批量失效，避免缓存不一致

### 3. 监控缓存命中率

- 定期检查缓存统计
- 命中率低于 70% 时，考虑调整策略
- 关注错误次数，及时发现缓存问题

### 4. 预加载热点数据

- 在业务低峰期预热缓存
- 减少高峰期的数据库压力

## 故障处理

### Redis 连接失败

- 缓存服务会自动降级到只使用内存缓存
- 监控 `redis_connected` 字段
- 检查 Redis 服务状态和网络连接

### 缓存雪崩

- 使用随机 TTL 避免同时过期
- 实施缓存预热机制
- 考虑使用缓存锁（Cache Aside with Lock）

### 缓存穿透

- 对不存在的数据也进行缓存（短 TTL）
- 使用布隆过滤器提前判断

### 缓存击穿

- 使用互斥锁防止大量请求同时查询数据库
- 实施逻辑过期（Logical Expiration）

## 安全考虑

1. **敏感数据缓存：**
   - 不要缓存用户密码等敏感信息
   - 对缓存数据进行加密（如果需要）

2. **缓存权限：**
   - 限制缓存 API 的访问权限
   - 只允许管理员操作缓存管理接口

3. **Redis 安全：**
   - 设置 Redis 密码
   - 使用 TLS 加密连接
   - 限制 Redis 网络访问

## 未来扩展

1. **缓存穿透保护：** 实现布隆过滤器
2. **缓存降级：** 在缓存故障时的降级策略
3. **缓存预热智能调度：** 基于访问模式的自动预热
4. **多级缓存扩展：** 添加 CDN、本地缓存等更多层级
5. **缓存压缩：** 对大对象进行压缩存储
6. **分布式锁：** 支持跨实例的缓存操作

## 附录

### 相关文件

- `app/services/cache_service.py` - 缓存服务实现
- `app/core/cache.py` - 缓存装饰器实现
- `app/api/cache.py` - 缓存管理 API
- `app/services/cached_conversation_service.py` - 缓存增强的对话服务

### 参考资料

- [Redis 官方文档](https://redis.io/documentation)
- [FastAPI 缓存最佳实践](https://fastapi.tiangolo.com/advanced/additional-responses/)
- [Python 缓存模式](https://docs.python.org/3/library/functools.html#functools.lru_cache)

---

**文档版本：** 1.0.0
**最后更新：** 2024-01-15
