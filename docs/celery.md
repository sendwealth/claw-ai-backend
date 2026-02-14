# Celery 集成

CLAW.AI 项目集成了 Celery 异步任务队列系统，用于处理耗时的后台任务。

## 快速链接

- [详细使用文档](./celery-usage.md)
- [API 文档](http://localhost:8000/docs)
- [Flower 监控面板](http://localhost:5555)

## 启动服务

```bash
# 启动所有服务（包括 Celery Worker, Beat, Flower）
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

## 使用示例

### 1. 提交异步任务

```python
from app.tasks.ai_tasks import generate_ai_response

# 提交任务
task = generate_ai_response.apply_async(
    kwargs={
        "conversation_id": "conv_123",
        "user_message": "你好",
    },
    queue="ai_high_priority",
)

print(f"任务 ID: {task.id}")
```

### 2. 查询任务状态

```bash
curl "http://localhost:8000/api/v1/tasks/status/{task_id}"
```

### 3. 查看监控面板

访问 http://localhost:5555（默认用户名/密码: admin/admin）

## 可用任务

| 任务 | 说明 | 优先级 |
|------|------|--------|
| `generate_ai_response` | AI 响应生成 | 高 |
| `vectorize_document` | 文档向量化 | 中 |
| `update_knowledge_base` | 知识库更新 | 中 |
| `send_notification` | 发送通知 | 低 |

详细文档请参考 [celery-usage.md](./celery-usage.md)。
