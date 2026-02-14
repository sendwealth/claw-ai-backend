# Celery 异步任务队列使用文档

## 目录

1. [系统架构](#系统架构)
2. [快速开始](#快速开始)
3. [任务定义](#任务定义)
4. [任务提交](#任务提交)
5. [任务监控](#任务监控)
6. [API 接口](#api-接口)
7. [配置说明](#配置说明)
8. [常见问题](#常见问题)

---

## 系统架构

### 组件说明

CLAW.AI 项目的 Celery 异步任务队列系统由以下组件组成：

1. **Celery Worker** - 任务执行器，负责处理异步任务
2. **Celery Beat** - 定时任务调度器，负责执行定时任务
3. **Flower** - 任务监控面板，提供 Web UI 监控任务状态
4. **Redis** - 消息代理和结果后端，存储任务队列和结果

### 任务队列

系统配置了多个任务队列，用于不同类型的任务：

- `ai_high_priority` - AI 响应生成任务（高优先级）
- `knowledge_default` - 知识库相关任务
- `notification_default` - 通知发送任务
- `default` - 默认任务队列

### 任务状态

Celery 任务有以下状态：

- **PENDING** - 任务等待执行
- **STARTED** - 任务已开始执行
- **SUCCESS** - 任务执行成功
- **FAILURE** - 任务执行失败
- **RETRY** - 任务正在重试

---

## 快速开始

### 启动服务

使用 Docker Compose 启动所有服务：

```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

### 访问监控面板

Flower 监控面板默认运行在 `http://localhost:5555`

默认登录凭证：
- 用户名: `admin`
- 密码: `admin`

可以通过环境变量 `FLOWER_USER` 和 `FLOWER_PASSWORD` 修改登录凭证。

---

## 任务定义

### 创建新任务

1. 在 `app/tasks/` 目录下创建新的任务文件（如 `custom_tasks.py`）

2. 定义任务：

```python
from celery import Task
from app.tasks.celery_app import celery_app
from app.tasks.ai_tasks import BaseTaskWithRetry

@celery_app.task(
    name="app.tasks.custom_tasks.my_task",
    base=BaseTaskWithRetry,
    bind=True,
    max_retries=3,
)
def my_task(self, param1: str, param2: int) -> dict:
    """
    我的自定义任务

    Args:
        self: 任务实例（用于重试）
        param1: 参数1
        param2: 参数2

    Returns:
        dict: 任务结果
    """
    try:
        # 任务逻辑
        result = {
            "param1": param1,
            "param2": param2,
            "status": "SUCCESS"
        }

        return result

    except Exception as exc:
        # 自动重试（由 BaseTaskWithRetry 处理）
        raise
```

3. 在 `app/tasks/celery_app.py` 中注册任务：

```python
celery_app = Celery(
    "claw_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.ai_tasks",
        "app.tasks.knowledge_tasks",
        "app.tasks.custom_tasks",  # 添加新任务模块
    ]
)
```

4. 在 `app/tasks/__init__.py` 中导出任务：

```python
from app.tasks.custom_tasks import my_task

__all__ = ["celery_app", "my_task"]
```

### 任务配置选项

```python
@celery_app.task(
    name="app.tasks.example.task_name",  # 任务名称（唯一）
    base=BaseTaskWithRetry,              # 任务基类
    bind=True,                           # 绑定任务实例
    max_retries=3,                       # 最大重试次数
    soft_time_limit=300,                 # 软超时（秒）
    time_limit=600,                      # 硬超时（秒）
    rate_limit="10/m",                   # 速率限制
    priority=5,                          # 任务优先级（0-9）
    queue="default",                     # 目标队列
)
def my_task(self):
    pass
```

---

## 任务提交

### Python 代码中提交任务

#### 同步调用（等待结果）

```python
from app.tasks.ai_tasks import generate_ai_response

# 提交任务并等待结果（阻塞）
result = generate_ai_response.apply_async(
    kwargs={
        "conversation_id": "conv_123",
        "user_message": "你好",
        "user_id": "user_456"
    },
    queue="ai_high_priority",
    priority=8,
).get(timeout=60)  # 等待最多 60 秒

print(result)
```

#### 异步调用（立即返回）

```python
from app.tasks.ai_tasks import generate_ai_response

# 提交任务，立即返回任务 ID
task = generate_ai_response.apply_async(
    kwargs={
        "conversation_id": "conv_123",
        "user_message": "你好",
    },
    queue="ai_high_priority",
    priority=8,
)

print(f"任务已提交: {task.id}")
```

#### 延迟执行

```python
from datetime import timedelta

# 10 秒后执行
task = generate_ai_response.apply_async(
    kwargs={"conversation_id": "conv_123", "user_message": "你好"},
    countdown=10,  # 延迟秒数
)

# 或在特定时间执行
from datetime import datetime, timedelta
eta = datetime.utcnow() + timedelta(minutes=5)
task = generate_ai_response.apply_async(
    kwargs={"conversation_id": "conv_123", "user_message": "你好"},
    eta=eta,  # 执行时间
)
```

### 通过 HTTP API 提交任务

#### 提交 AI 响应生成任务

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/ai/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_123",
    "user_message": "你好",
    "temperature": 0.7,
    "user_id": "user_456"
  }'
```

响应：

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PENDING",
  "message": "AI 响应生成任务已提交"
}
```

---

## 任务监控

### 通过 Flower Web UI

1. 访问 `http://localhost:5555`
2. 登录（默认 admin/admin）
3. 在仪表板中查看：
   - 任务队列状态
   - Worker 状态
   - 任务执行历史
   - 任务成功/失败统计

### 通过 API

#### 查询任务状态

```bash
curl "http://localhost:8000/api/v1/tasks/status/{task_id}"
```

响应：

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS",
  "result": {
    "conversation_id": "conv_123",
    "response": "你好！有什么可以帮助你的吗？",
    "tokens": {"total": 123},
    "cost": 0.0025
  },
  "error": null,
  "date_done": "2025-01-15T10:30:00",
  "runtime": 2.5
}
```

#### 列出所有任务

```bash
curl "http://localhost:8000/api/v1/tasks/list?limit=50&status=SUCCESS"
```

#### 获取任务统计

```bash
curl "http://localhost:8000/api/v1/tasks/stats"
```

响应：

```json
{
  "total_tasks": 1234,
  "pending": 5,
  "started": 2,
  "success": 1200,
  "failure": 20,
  "retry": 7,
  "workers": 4
}
```

---

## API 接口

### 任务管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tasks/status/{task_id}` | 查询任务状态 |
| GET | `/api/v1/tasks/list` | 列出所有任务 |
| POST | `/api/v1/tasks/cancel/{task_id}` | 取消任务 |
| POST | `/api/v1/tasks/retry/{task_id}` | 重试任务 |
| GET | `/api/v1/tasks/stats` | 获取任务统计 |
| POST | `/api/v1/tasks/ai/generate` | 提交 AI 响应生成任务 |
| GET | `/api/v1/tasks/workers` | 获取 Worker 信息 |
| POST | `/api/v1/tasks/workers/pool/restart` | 重启 Worker 进程池 |
| POST | `/api/v1/tasks/workers/shutdown` | 关闭 Worker |

### API 使用示例

#### 取消任务

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/cancel/{task_id}"
```

#### 获取 Worker 信息

```bash
curl "http://localhost:8000/api/v1/tasks/workers"
```

#### 重启 Worker 进程池

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/workers/pool/restart?worker_name=celery@hostname"
```

---

## 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# Redis 配置（Celery 消息代理）
REDIS_URL=redis://:password@redis:6379/0

# Flower 监控配置
FLOWER_USER=admin
FLOWER_PASSWORD=your_secure_password
```

### Celery 配置项

在 `app/tasks/celery_app.py` 中可以调整以下配置：

```python
celery_app.conf.update(
    # 任务超时
    task_soft_time_limit=300,      # 软超时 5 分钟
    task_time_limit=600,            # 硬超时 10 分钟

    # 任务结果保存时间
    result_expires=3600,            # 1 小时

    # Worker 配置
    worker_concurrency=4,           # 并发任务数
    worker_max_tasks_per_child=100, # 每个 worker 执行 100 个任务后重启

    # 任务重试配置
    task_acks_late=True,           # 任务成功后才确认
    task_reject_on_worker_lost=True, # worker 丢失时重新入队
)
```

### 定时任务配置

在 `celery_app.conf.beat_schedule` 中配置定时任务：

```python
beat_schedule={
    # 每天凌晨 2 点清理过期任务结果
    "cleanup-expired-results": {
        "task": "app.tasks.ai_tasks.cleanup_expired_results",
        "schedule": crontab(hour=2, minute=0),
    },
    # 每 30 分钟检查任务状态
    "check-task-status": {
        "task": "app.tasks.ai_tasks.check_task_health",
        "schedule": crontab(minute="*/30"),
    },
}
```

---

## 常见问题

### 1. 任务一直处于 PENDING 状态

**原因**：Worker 未启动或未正确连接到 Redis

**解决方案**：
```bash
# 检查 Worker 状态
docker-compose -f docker-compose.prod.yml ps celery-worker

# 查看 Worker 日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# 重启 Worker
docker-compose -f docker-compose.prod.yml restart celery-worker
```

### 2. 任务执行失败，如何查看错误信息？

**解决方案**：
- 通过 API 查询任务状态，错误信息在 `error` 字段
- 查看 Worker 日志
- 在 Flower 监控面板查看任务详情

### 3. 如何调整任务优先级？

**解决方案**：
```python
task = my_task.apply_async(
    kwargs={"param": "value"},
    priority=9,  # 0-9，9 为最高优先级
)
```

### 4. 如何增加 Worker 数量？

**解决方案**：

在 `docker-compose.prod.yml` 中复制 `celery-worker` 服务，或使用 `--scale` 参数：

```bash
# 启动 4 个 Worker 实例
docker-compose -f docker-compose.prod.yml up --scale celery-worker=4 -d
```

### 5. 任务重试机制如何工作？

**说明**：
- 使用 `BaseTaskWithRetry` 基类的任务会自动重试
- 默认最大重试次数为 3 次
- 重试间隔采用指数退避策略（1min, 2min, 4min...）
- 可在任务装饰器中配置 `max_retries`

```python
@celery_app.task(
    name="my_task",
    base=BaseTaskWithRetry,
    max_retries=5,  # 自定义重试次数
)
def my_task(self):
    pass
```

### 6. 如何清理过期的任务结果？

**说明**：
- Celery 会根据 `result_expires` 配置自动清理过期结果
- 默认设置为 1 小时（3600 秒）
- 可在 `celery_app.conf.update()` 中修改

### 7. Flower 监控面板无法访问

**解决方案**：
```bash
# 检查 Flower 服务状态
docker-compose -f docker-compose.prod.yml ps celery-flower

# 查看 Flower 日志
docker-compose -f docker-compose.prod.yml logs -f celery-flower

# 确认端口是否正确暴露
netstat -tulpn | grep 5555
```

### 8. 如何调试任务？

**解决方案**：
1. 在任务代码中添加日志：
```python
import logging
logger = logging.getLogger(__name__)

logger.info("任务开始执行")
logger.debug(f"参数: {kwargs}")
logger.error("任务执行失败")
```

2. 使用 Celery 的 `--loglevel=debug` 启动 Worker：
```bash
celery -A app.tasks.celery_app worker --loglevel=debug
```

3. 在 Flower 中查看实时任务执行情况

---

## 内置任务列表

### AI 任务（app.tasks.ai_tasks）

| 任务名称 | 说明 | 队列 | 速率限制 |
|---------|------|------|---------|
| `generate_ai_response` | 异步生成 AI 响应 | ai_high_priority | 10/min |
| `send_notification` | 异步发送通知 | notification_default | - |
| `cleanup_expired_results` | 清理过期任务结果（定时任务） | default | - |
| `check_task_health` | 检查任务健康状态（定时任务） | default | - |

### 知识库任务（app.tasks.knowledge_tasks）

| 任务名称 | 说明 | 队列 | 速率限制 |
|---------|------|------|---------|
| `vectorize_document` | 异步文档向量化 | knowledge_default | 5/min |
| `update_knowledge_base` | 异步更新知识库 | knowledge_default | - |
| `delete_knowledge_vectors` | 异步删除知识向量 | knowledge_default | - |

---

## 最佳实践

1. **任务设计**
   - 任务应该幂等（可以安全地重复执行）
   - 任务参数应该简单可序列化（JSON 兼容）
   - 避免在任务中使用闭包或引用外部状态

2. **错误处理**
   - 使用 `BaseTaskWithRetry` 基类自动处理重试
   - 在任务中捕获特定异常，提供有意义的错误信息
   - 记录详细的日志以便调试

3. **性能优化**
   - 合理设置任务超时时间
   - 使用任务优先级管理重要任务
   - 根据负载调整 Worker 数量和并发度

4. **监控**
   - 定期检查 Flower 监控面板
   - 设置任务失败告警
   - 监控 Redis 内存使用情况

---

## 技术支持

如有问题，请查阅：
- [Celery 官方文档](https://docs.celeryproject.org/)
- [Flower 文档](https://flower.readthedocs.io/)
- 项目 GitHub Issues

---

*最后更新时间: 2025-01-15*
