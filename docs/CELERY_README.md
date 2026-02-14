# CLAW.AI Celery 异步任务队列系统

## 概述

CLAW.AI 项目现已完全集成 Celery 异步任务队列系统，提供强大的后台任务处理能力。

---

## 🎯 核心特性

- ✅ **异步任务处理** - 解耦耗时操作，提升响应速度
- ✅ **多任务队列** - 支持优先级管理和任务分类
- ✅ **自动重试** - 智能重试机制，提高任务成功率
- ✅ **任务监控** - Flower Web UI 实时监控任务状态
- ✅ **定时任务** - Celery Beat + RedBeat 支持动态定时任务
- ✅ **完整 API** - 9 个 RESTful API 接口管理任务

---

## 📊 实现统计

### 任务数量
- **AI 任务**: 4 个
- **知识库任务**: 3 个
- **总计**: 7 个任务

### API 端点
- **9 个任务管理接口**
  - 查询任务状态
  - 列出任务
  - 取消任务
  - 重试任务
  - 获取统计
  - 提交 AI 生成任务
  - Worker 管理

### 服务组件
- **3 个 Docker 服务**
  - celery-worker (任务执行器)
  - celery-beat (定时任务调度器)
  - celery-flower (监控面板)

---

## 🚀 快速开始

### 1. 启动服务

```bash
cd /home/wuying/clawd/claw-ai-backend
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 查看状态

```bash
docker-compose -f docker-compose.prod.yml ps
```

### 3. 访问监控面板

URL: http://localhost:5555
- 默认用户名: `admin`
- 默认密码: `admin`

---

## 📝 可用任务

| 任务 | 说明 | 队列 | 速率限制 |
|------|------|------|---------|
| `generate_ai_response` | AI 响应生成 | ai_high_priority | 10/min |
| `vectorize_document` | 文档向量化 | knowledge_default | 5/min |
| `update_knowledge_base` | 知识库更新 | knowledge_default | - |
| `delete_knowledge_vectors` | 删除知识向量 | knowledge_default | - |
| `send_notification` | 发送通知 | notification_default | - |
| `cleanup_expired_results` | 清理过期结果 | default | 定时 |
| `check_task_health` | 检查任务健康 | default | 定时 |

---

## 💡 使用示例

### Python 代码提交任务

```python
from app.tasks.ai_tasks import generate_ai_response

# 提交异步任务
task = generate_ai_response.apply_async(
    kwargs={
        "conversation_id": "conv_123",
        "user_message": "你好",
    },
    queue="ai_high_priority",
    priority=8,
)

print(f"任务 ID: {task.id}")
```

### HTTP API 提交任务

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/ai/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_123",
    "user_message": "你好"
  }'
```

### 查询任务状态

```bash
curl "http://localhost:8000/api/v1/tasks/status/{task_id}"
```

---

## 📚 文档

| 文档 | 说明 |
|------|------|
| [celery-usage.md](./celery-usage.md) | 详细使用文档 (16KB) |
| [CELERY_IMPLEMENTATION_SUMMARY.md](./CELERY_IMPLEMENTATION_SUMMARY.md) | 实现总结 (12KB) |
| [celery.md](./celery.md) | 快速入门 (4KB) |
| [celery-async-conversation-example.py](./celery-async-conversation-example.py) | 异步对话示例 (12KB) |

---

## 🔧 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# Redis 配置
REDIS_URL=redis://:password@redis:6379/0

# Flower 认证
FLOWER_USER=admin
FLOWER_PASSWORD=your_secure_password
```

### Celery 配置

主要配置在 `app/tasks/celery_app.py`：

```python
celery_app.conf.update(
    # 时区
    timezone="Asia/Shanghai",

    # 任务超时
    task_soft_time_limit=300,  # 软超时 5 分钟
    task_time_limit=600,        # 硬超时 10 分钟

    # Worker 配置
    worker_concurrency=4,       # 并发任务数

    # 任务重试
    task_acks_late=True,       # 成功后才确认
)
```

---

## 📊 监控和日志

### Flower 监控面板

访问 http://localhost:5555 查看：
- 任务队列状态
- Worker 状态
- 任务执行历史
- 成功/失败统计

### 日志查看

```bash
# 查看 Worker 日志
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# 查看 Beat 日志
docker-compose -f docker-compose.prod.yml logs -f celery-beat

# 查看 Flower 日志
docker-compose -f docker-compose.prod.yml logs -f celery-flower
```

---

## 🛠️ 验证

运行验证脚本检查所有文件：

```bash
bash scripts/verify_celery.sh
```

预期输出：
- ✅ 所有任务模块文件存在
- ✅ API 文件存在（9 个端点）
- ✅ 配置文件已更新
- ✅ Docker Compose 已配置
- ✅ 依赖已添加
- ✅ 文档已创建

---

## 🎨 架构

```
┌─────────────────┐
│   FastAPI       │
│   (Web API)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│   Celery        │────▶│    Redis     │
│   Broker        │     │   (Broker)   │
└─────────────────┘     └──────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────┐
│  Celery Worker  │◀────│   Redis     │
│  (Tasks)        │     │   (Backend)  │
└─────────────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│   Flower        │
│   (Monitor)     │
└─────────────────┘
```

---

## 🔐 安全建议

1. **修改默认密码**
   ```bash
   # .env
   FLOWER_USER=your_username
   FLOWER_PASSWORD=your_secure_password
   ```

2. **限制外网访问**
   - Flower 仅在内网使用
   - 配置 Nginx 反向代理时添加认证

3. **Redis 认证**
   - 确保 Redis 使用密码认证
   - 不要暴露 Redis 端口到公网

---

## 🚀 性能优化

### 增加 Worker 数量

```bash
# 启动 4 个 Worker 实例
docker-compose -f docker-compose.prod.yml up --scale celery-worker=4 -d
```

### 调整并发数

在 `app/tasks/celery_app.py` 中修改：
```python
worker_concurrency=8,  # 根据 CPU 核心数调整
```

### 调整任务限流

```python
task_annotations={
    "app.tasks.ai_tasks.generate_ai_response": {
        "rate_limit": "20/m",  # 提高到 20/min
    },
}
```

---

## 📞 技术支持

如有问题，请查阅：
- [Celery 官方文档](https://docs.celeryproject.org/)
- [Flower 文档](https://flower.readthedocs.io/)
- 项目详细文档

---

## ✨ 总结

✅ Celery 5.3.6 集成完成
✅ 7 个异步任务实现
✅ 9 个任务管理 API
✅ 3 个 Docker 服务配置
✅ Flower 监控面板配置
✅ 完整使用文档
✅ 异步对话示例代码

**系统已就绪，可以立即使用！**

---

*最后更新: 2025-01-15*
*实现者: 异步任务队列专家*
