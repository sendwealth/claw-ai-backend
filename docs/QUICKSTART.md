# CLAW.AI 快速开始指南

欢迎使用 CLAW.AI！本指南将帮助您在 10 分钟内启动并运行 CLAW.AI 后端服务。

---

## 目录

- [前置要求](#前置要求)
- [安装步骤](#安装步骤)
- [配置环境变量](#配置环境变量)
- [启动服务](#启动服务)
- [验证安装](#验证安装)
- [下一步](#下一步)

---

## 前置要求

在开始之前，请确保您的系统已安装以下软件：

### 必需软件

| 软件 | 版本要求 | 检查命令 |
|------|----------|----------|
| Python | 3.11+ | `python --version` |
| PostgreSQL | 15+ | `psql --version` |
| Redis | 7+ | `redis-cli --version` |
| Git | 2.30+ | `git --version` |
| Docker | 20.10+ | `docker --version` （可选） |
| Docker Compose | 2.0+ | `docker-compose --version` （可选） |

### 获取 API Key

您需要准备以下 API Key：

- **Zhipu AI API Key** - 用于调用 GLM-4 模型
  - 访问：https://open.bigmodel.cn/
  - 注册账号并创建 API Key

---

## 安装步骤

### 方式一：Docker Compose（推荐）

这是最简单和快速的方式，所有依赖都通过 Docker 容器运行。

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/claw-ai-backend.git
cd claw-ai-backend

# 2. 复制环境变量模板
cp .env.example .env

# 3. 编辑 .env 文件，填写必要配置
nano .env

# 4. 启动所有服务
docker-compose up -d

# 5. 查看服务状态
docker-compose ps

# 6. 查看日志
docker-compose logs -f app
```

### 方式二：本地安装

如果您需要在本地开发环境运行，请按照以下步骤操作。

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/claw-ai-backend.git
cd claw-ai-backend

# 2. 创建 Python 虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate

# 4. 安装 Python 依赖
pip install -r requirements.txt
```

---

## 配置环境变量

### 必需配置

在 `.env` 文件中配置以下必需的环境变量：

```bash
# 应用配置
APP_NAME=CLAW.AI
APP_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/claw_ai

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# JWT 配置
SECRET_KEY=your-secret-key-here-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Zhipu AI 配置（必需）
ZHIPUAI_API_KEY=your-zhipu-ai-api-key

# CORS 配置
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### 数据库初始化

```bash
# 1. 运行数据库迁移
alembic upgrade head

# 2. 初始化数据库（创建管理员用户等）
python scripts/init_db.py
```

### 验证数据库连接

```bash
# 测试数据库连接
python -c "from app.db.session import engine; print(engine.url); print('Database connected!')"
```

---

## 启动服务

### 启动 FastAPI 应用

```bash
# 使用 Uvicorn 启动（开发模式）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Makefile
make dev

# 或直接运行 Python
python -m app.main
```

启动成功后，您应该看到类似以下的输出：

```
🚀 CLAW.AI v1.0.0 启动中...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
📊 Prometheus metrics initialized
💾 缓存服务已连接
🔥 缓存预热完成
INFO:     Application startup complete.
```

### 启动 Celery Worker（可选）

如果您需要使用异步任务功能，请启动 Celery Worker：

```bash
# 启动 Celery Worker
celery -A app.worker.celery_app worker --loglevel=info

# 启动 Celery Beat（定时任务）
celery -A app.worker.celery_app beat --loglevel=info

# 或使用 Makefile
make celery-worker
make celery-beat
```

### 启动监控服务（可选）

```bash
# 使用 Docker Compose 启动监控服务
docker-compose -f docker-compose.monitoring.yml up -d prometheus grafana loki promtail
```

---

## 验证安装

### 1. 健康检查

访问健康检查接口：

```bash
curl http://localhost:8000/health
```

预期响应：

```json
{
  "status": "healthy",
  "app": "CLAW.AI",
  "version": "1.0.0"
}
```

### 2. 访问 API 文档

打开浏览器访问以下地址：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

您应该能看到所有可用的 API 端点和交互式文档。

### 3. 测试用户注册

使用 cURL 测试用户注册：

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "测试用户",
    "phone": "13800138000",
    "company": "测试公司"
  }'
```

预期响应：

```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "user_id": 1
  }
}
```

### 4. 测试用户登录

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

预期响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 5. 测试创建对话

使用上面获取的 access_token：

```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "测试对话",
    "model": "glm-4",
    "conversation_type": "chat"
  }'
```

### 6. 测试 AI 对话

```bash
curl -X POST http://localhost:8000/api/v1/conversations/1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '你好'
```

预期响应：

```json
{
  "content": "你好！有什么可以帮助你的吗？",
  "message_id": 1,
  "tokens": {
    "prompt": 5,
    "completion": 10,
    "total": 15
  },
  "cost": 0.00015
}
```

---

## 常见问题

### 问题 1: 数据库连接失败

**错误信息**：
```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**解决方案**：
1. 检查 PostgreSQL 是否正在运行
2. 检查 DATABASE_URL 配置是否正确
3. 确认数据库用户名和密码

```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 测试数据库连接
psql -U postgres -h localhost -d claw_ai
```

### 问题 2: Redis 连接失败

**错误信息**：
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**解决方案**：
1. 检查 Redis 是否正在运行
2. 检查 REDIS_URL 配置是否正确

```bash
# 检查 Redis 状态
redis-cli ping

# 启动 Redis
sudo systemctl start redis
```

### 问题 3: Zhipu AI API 调用失败

**错误信息**：
```
zhipuai.core._errors.APIError: 401 Unauthorized
```

**解决方案**：
1. 检查 ZHIPUAI_API_KEY 是否正确配置
2. 确认 API Key 是否有效
3. 检查账户余额

### 问题 4: 端口已被占用

**错误信息**：
```
OSError: [Errno 48] Address already in use
```

**解决方案**：
1. 更改端口配置
2. 或者停止占用端口的进程

```bash
# 查找占用 8000 端口的进程
lsof -i :8000

# 停止进程
kill -9 <PID>
```

---

## 下一步

现在您已经成功启动了 CLAW.AI，接下来可以：

### 1. 了解核心功能
- 📖 阅读 [用户手册](USER_MANUAL.md)
- 🔌 查看 [API 文档](API_REFERENCE.md)
- 🏗️ 了解 [系统架构](ARCHITECTURE.md)

### 2. 开始开发
- 💻 查看 [开发者指南](DEVELOPER_GUIDE.md)
- 🧪 编写测试
- 🚀 部署到生产环境

### 3. 配置生产环境
- 📊 配置监控和告警
- 🔒 设置安全策略
- ⚡ 性能优化

### 4. 集成前端
- 🎨 集成前端应用
- 📱 移动端集成
- 🔗 第三方服务集成

---

## 开发命令参考

```bash
# 安装依赖
make install

# 启动开发服务器
make dev

# 运行测试
make test

# 代码格式化
make lint

# 数据库迁移
make migrate

# 重置数据库
make reset-db

# 启动 Celery Worker
make celery-worker

# 启动 Celery Beat
make celery-beat

# 查看日志
make logs
```

---

## 获取帮助

如果遇到问题，请：

1. 查看 [故障排查指南](TROUBLESHOOTING.md)
2. 搜索 [常见问题](FAQ.md)
3. 提交 Issue 到 GitHub
4. 联系技术支持：contact@openspark.online

---

**祝您使用愉快！🎉**

*最后更新：2024-02-14*
