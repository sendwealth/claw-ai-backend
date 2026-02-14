# CLAW.AI Celery 快速参考

## 🚀 常用命令

### 启动服务

```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 仅启动 Celery 相关服务
docker-compose -f docker-compose.prod.yml up -d celery-worker celery-beat celery-flower

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 日志查看

```bash
# 查看 Worker 日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# 查看 Beat 日志
docker-compose -f docker-compose.prod.yml logs -f celery-beat

# 查看 Flower 日志
docker-compose -f docker-compose.prod.yml logs -f celery-flower

# 查看所有 Celery 服务日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker celery-beat celery-flower
```

### Worker 管理

```bash
# 重启 Worker
docker-compose -f docker-compose.prod.yml restart celery-worker

# 停止 Worker
docker-compose -f docker-compose.prod.yml stop celery-worker

# 扩展 Worker 数量
docker-compose -f docker-compose.prod.yml up --scale celery-worker=4 -d

# 进入 Worker 容器
docker exec -it claw_ai_celery_worker bash
```

### 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 停止并删除卷
docker-compose -f docker-compose.prod.yml down -v
```

---

## 📡 API 端点

### 基础 URL
```
http://localhost:8000/api/v1/tasks
```

### 端点列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/status/{task_id}` | 查询任务状态 |
| GET | `/list` | 列出所有任务 |
| POST | `/cancel/{task_id}` | 取消任务 |
| POST | `/retry/{task_id}` | 重试任务 |
| GET | `/stats` | 获取任务统计 |
| POST | `/ai/generate` | 提交 AI 响应生成任务 |
| GET | `/workers` | 获取 Worker 信息 |
| POST | `/workers/pool/restart` | 重启 Worker 进程池 |
| POST | `/workers/shutdown` | 关闭 Worker |

---

## 💻 Python 示例

### 提交任务

```python
from app.tasks.ai_tasks import generate_ai_response

# 基础提交
task = generate_ai_response.apply_async(
    kwargs={
        "conversation_id": "conv_123",
        "user_message": "你好",
    }
)

# 带优先级提交
task = generate_ai_response.apply_async(
    kwargs={
        "conversation_id": "conv_123",
        "user_message": "你好",
    },
    queue="ai_high_priority",
    priority=8,
)

# 延迟执行（10 秒后）
task = generate_ai_response.apply_async(
    kwargs={"conversation_id": "conv_123", "user_message": "你好"},
    countdown=10,
)

# 定时执行（5 分钟后）
from datetime import timedelta
task = generate_ai_response.apply_async(
    kwargs={"conversation_id": "conv_123", "user_message": "你好"},
    countdown=timedelta(minutes=5).total_seconds(),
)
```

### 查询任务状态

```python
from app.tasks.celery_app import celery_app

# 获取任务结果
result = celery_app.AsyncResult(task_id)

# 检查状态
if result.status == "SUCCESS":
    print("任务成功:", result.result)
elif result.status == "FAILURE":
    print("任务失败:", result.result)
elif result.status == "PENDING":
    print("任务等待中")
elif result.status == "STARTED":
    print("任务执行中")
```

### 同步等待结果

```python
# 等待任务完成（最多 60 秒）
result = generate_ai_response.apply_async(
    kwargs={"conversation_id": "conv_123", "user_message": "你好"},
).get(timeout=60)

print(result)
```

---

## 🌐 cURL 示例

### 提交 AI 生成任务

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

响应示例：
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PENDING",
  "message": "AI 响应生成任务已提交"
}
```

### 查询任务状态

```bash
curl "http://localhost:8000/api/v1/tasks/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

响应示例：
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
  "date_done": "2025-01-15T10:30:00",
  "runtime": 2.5
}
```

### 列出所有任务

```bash
# 列出最近 50 个任务
curl "http://localhost:8000/api/v1/tasks/list?limit=50"

# 只列出成功的任务
curl "http://localhost:8000/api/v1/tasks/list?status=SUCCESS&limit=20"
```

### 获取任务统计

```bash
curl "http://localhost:8000/api/v1/tasks/stats"
```

响应示例：
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

### 取消任务

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/cancel/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### 获取 Worker 信息

```bash
curl "http://localhost:8000/api/v1/tasks/workers"
```

---

## 🎨 任务队列

### 队列列表

| 队列名称 | 用途 | 优先级 |
|---------|------|--------|
| `ai_high_priority` | AI 响应生成 | 高 |
| `knowledge_default` | 知识库任务 | 中 |
| `notification_default` | 通知任务 | 低 |
| `default` | 默认任务 | 中 |

### 提交到指定队列

```python
# 提交到高优先级队列
task = my_task.apply_async(
    kwargs={"param": "value"},
    queue="ai_high_priority",
)
```

---

## 🔧 配置参考

### 任务超时配置

```python
@celery_app.task(
    name="my_task",
    soft_time_limit=300,  # 软超时 5 分钟
    time_limit=600,       # 硬超时 10 分钟
)
def my_task():
    pass
```

### 任务重试配置

```python
@celery_app.task(
    name="my_task",
    base=BaseTaskWithRetry,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,  # 最大退避时间 10 分钟
)
def my_task():
    pass
```

### 任务优先级

```python
task = my_task.apply_async(
    kwargs={"param": "value"},
    priority=9,  # 0-9，9 为最高优先级
)
```

### 速率限制

```python
celery_app.conf.update(
    task_annotations={
        "app.tasks.ai_tasks.generate_ai_response": {
            "rate_limit": "10/m",  # 每分钟最多 10 个任务
        },
    },
)
```

---

## 🌸 Flower 监控

### 访问地址
```
URL: http://localhost:5555
用户名: admin
密码: admin
```

### 修改密码

在 `.env` 文件中配置：
```bash
FLOWER_USER=your_username
FLOWER_PASSWORD=your_secure_password
```

### 主要功能

- **Tasks** - 查看所有任务
- **Workers** - 查看 Worker 状态
- **Broker** - 查看消息队列
- **Monitor** - 实时监控任务执行

---

## 🐛 故障排除

### 任务一直处于 PENDING

```bash
# 检查 Worker 是否运行
docker-compose -f docker-compose.prod.yml ps celery-worker

# 查看 Worker 日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# 重启 Worker
docker-compose -f docker-compose.prod.yml restart celery-worker
```

### 任务执行失败

```bash
# 查看错误详情
curl "http://localhost:8000/api/v1/tasks/status/{task_id}"

# 查看 Worker 日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker
```

### Flower 无法访问

```bash
# 检查 Flower 服务状态
docker-compose -f docker-compose.prod.yml ps celery-flower

# 查看 Flower 日志
docker-compose -f docker-compose.prod.yml logs -f celery-flower

# 重启 Flower
docker-compose -f docker-compose.prod.yml restart celery-flower
```

---

## 📚 相关文档

- [详细使用文档](./celery-usage.md)
- [实现总结](./CELERY_IMPLEMENTATION_SUMMARY.md)
- [文件清单](../CELERY_FILES.md)
- [异步对话示例](./celery-async-conversation-example.py)

---

*快速参考 - CLAW.AI Celery 系统*
