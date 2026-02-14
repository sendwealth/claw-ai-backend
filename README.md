# CLAW.AI - Backend

**项目名称：** CLAW.AI Backend
**框架：** FastAPI (Python 3.11+)
**数据库：** PostgreSQL 15
**缓存：** Redis 7

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15
- Redis 7
- Zhipu AI API Key

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写配置
nano .env
```

### 数据库初始化

```bash
# 运行数据库迁移
alembic upgrade head

# 创建初始数据
python scripts/init_db.py
```

### 启动开发服务器

```bash
# 启动 Uvicorn 服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Makefile
make dev
```

---

## 📁 项目结构

```
claw-ai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py          # 认证相关
│   │   ├── users.py         # 用户管理
│   │   ├── conversations.py # 对话管理
│   │   ├── knowledge.py     # 知识库管理
│   │   └── consulting.py    # 咨询服务
│   ├── models/              # 数据库模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── knowledge_base.py
│   │   └── consulting_project.py
│   ├── schemas/             # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   └── knowledge.py
│   ├── services/            # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── ai_service.py
│   │   └── conversation_service.py
│   ├── db/                  # 数据库
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── base.py
│   └── utils/               # 工具函数
│       ├── __init__.py
│       ├── security.py
│       └── jwt.py
├── alembic/                  # 数据库迁移
├── tests/                    # 测试
├── scripts/                  # 脚本
├── requirements.txt          # 依赖列表
├── .env.example             # 环境变量模板
├── docker-compose.yml        # Docker 配置
├── Dockerfile               # Docker 镜像
└── README.md                # 本文件
```

---

## 🔌 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🗄️ 数据库 Schema

### 主要表

- `users` - 用户表
- `conversations` - 对话表
- `messages` - 消息表
- `knowledge_bases` - 知识库表
- `documents` - 文档表
- `consulting_projects` - 咨询项目表
- `orders` - 订单表

---

## 🔐 认证

使用 JWT Token 认证：
- Access Token: 1 小时有效期
- Refresh Token: 7 天有效期

---

## 🤖 AI 集成

- Zhipu AI API (GLM-4)
- LangChain
- 向量数据库: Pinecone

---

## 📝 开发命令

```bash
# 开发服务器
make dev

# 测试
make test

# 代码检查
make lint

# 数据库迁移
make migrate

# 重置数据库
make reset-db
```

---

## 🚀 部署

### Docker 部署

```bash
# 构建镜像
docker build -t claw-ai-backend .

# 运行容器
docker-compose up -d
```

### 传统部署

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 📊 监控和日志

- 访问日志：`/var/log/nginx/claw_ai_access.log`
- 错误日志：`/var/log/nginx/claw_ai_error.log`
- 应用日志：`logs/app.log`

---

## 🤝 贡献

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

---

## 📄 许可证

MIT License

---

## 📞 联系方式

- CTO: OpenClaw
- Email: contact@openspark.online

---

*Built with ❤️ by OpenSpark 智能科技*
