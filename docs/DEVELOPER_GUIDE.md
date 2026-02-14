# CLAW.AI 开发者指南

本指南面向想要参与 CLAW.AI 项目开发的开发者，涵盖了环境搭建、代码结构、开发规范、测试指南等内容。

---

## 目录

- [快速上手](#快速上手)
- [开发环境搭建](#开发环境搭建)
- [项目结构](#项目结构)
- [代码规范](#代码规范)
- [开发工作流](#开发工作流)
- [测试指南](#测试指南)
- [数据库迁移](#数据库迁移)
- [调试技巧](#调试技巧)
- [贡献代码](#贡献代码)
- [常见问题](#常见问题)

---

## 快速上手

### 前置要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Git 2.30+
- Docker & Docker Compose（可选）

### 5 分钟快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/claw-ai-backend.git
cd claw-ai-backend

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写必要配置

# 5. 初始化数据库
alembic upgrade head
python scripts/init_db.py

# 6. 启动开发服务器
make dev
```

访问 http://localhost:8000/docs 查看 API 文档。

---

## 开发环境搭建

### 1. 安装 Python 3.11+

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# macOS
brew install python@3.11

# Windows
# 从 https://www.python.org/downloads/ 下载安装
```

### 2. 安装 PostgreSQL 15+

```bash
# Ubuntu/Debian
sudo apt install postgresql-15 postgresql-contrib-15

# macOS
brew install postgresql@15

# Windows
# 从 https://www.postgresql.org/download/ 下载安装

# 启动 PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql    # macOS

# 创建数据库
sudo -u postgres psql
CREATE DATABASE claw_ai;
CREATE USER claw_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE claw_ai TO claw_user;
\q
```

### 3. 安装 Redis 7+

```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis

# 启动 Redis
sudo systemctl start redis  # Linux
brew services start redis  # macOS

# 测试连接
redis-cli ping
# 应该返回 PONG
```

### 4. 安装开发工具

```bash
# 代码格式化
pip install black

# 代码检查
pip install flake8

# 类型检查
pip install mypy

# 测试
pip install pytest pytest-asyncio pytest-cov

# Git 钩子
pip install pre-commit
```

### 5. 配置开发环境

编辑 `.env` 文件：

```bash
# 应用配置
APP_NAME=CLAW.AI
APP_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=postgresql://claw_user:your_password@localhost:5432/claw_ai

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# JWT 配置
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Zhipu AI 配置
ZHIPUAI_API_KEY=your-zhipu-ai-api-key

# CORS 配置
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### 6. 配置 Git Hooks

```bash
# 安装 pre-commit
pre-commit install

# 运行 pre-commit
pre-commit run --all-files
```

---

## 项目结构

```
claw-ai-backend/
├── app/                        # 应用主目录
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── core/                   # 核心功能
│   │   ├── __init__.py
│   │   ├── config.py           # 配置管理
│   │   ├── security.py         # 安全相关
│   │   ├── metrics.py          # Prometheus 监控
│   │   └── rate_limit.py       # 限流逻辑
│   ├── api/                    # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证相关
│   │   ├── users.py            # 用户管理
│   │   ├── conversations.py    # 对话管理
│   │   ├── knowledge.py        # 知识库管理
│   │   ├── consulting.py       # 咨询服务
│   │   ├── configs.py          # 配置管理
│   │   ├── tasks.py            # 任务管理
│   │   ├── rate_limit.py       # 限流管理
│   │   ├── cache.py            # 缓存管理
│   │   ├── ws.py               # WebSocket
│   │   └── dependencies.py     # 依赖注入
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── knowledge_base.py
│   │   └── document.py
│   ├── schemas/                # Pydantic 模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── knowledge.py
│   │   └── consulting.py
│   ├── services/               # 业务逻辑
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── conversation_service.py
│   │   ├── knowledge_service.py
│   │   ├── rag_service.py
│   │   ├── ai_service.py
│   │   └── cache_service.py
│   ├── db/                     # 数据库
│   │   ├── __init__.py
│   │   ├── session.py          # 数据库会话
│   │   └── base.py             # 基类
│   ├── worker/                 # Celery Worker
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery 应用
│   │   └── tasks.py            # 异步任务
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── security.py         # 加密和 JWT
│       └── logger.py           # 日志
├── alembic/                    # 数据库迁移
│   ├── versions/
│   └── env.py
├── tests/                      # 测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_conversations.py
│   └── test_knowledge.py
├── scripts/                    # 脚本
│   ├── init_db.py
│   └── demo_rate_limit.py
├── docs/                       # 文档
│   ├── API_REFERENCE.md
│   ├── USER_MANUAL.md
│   ├── DEVELOPER_GUIDE.md
│   ├── TROUBLESHOOTING.md
│   └── FAQ.md
├── config/                     # 配置文件
├── logs/                       # 日志文件
├── requirements.txt            # Python 依赖
├── .env.example               # 环境变量模板
├── .gitignore
├── alembic.ini                 # Alembic 配置
├── docker-compose.yml         # Docker Compose 配置
├── Dockerfile                  # Docker 镜像
├── Makefile                    # 常用命令
└── README.md                   # 项目说明
```

---

## 代码规范

### 1. Python 代码风格

遵循 PEP 8 规范，使用 Black 进行格式化。

```bash
# 格式化代码
black app/ tests/

# 检查代码风格
flake8 app/ tests/
```

### 2. 类型注解

使用类型注解提高代码可读性：

```python
from typing import List, Optional
from pydantic import BaseModel

class UserCreate(BaseModel):
    """用户创建模型"""
    email: str
    password: str
    name: str
    phone: Optional[str] = None

async def create_user(
    user_data: UserCreate,
    db: Session
) -> User:
    """创建用户"""
    user = User(**user_data.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

### 3. 文档字符串

使用 Google 风格的文档字符串：

```python
def get_user_by_email(
    email: str,
    db: Session
) -> Optional[User]:
    """根据邮箱获取用户

    Args:
        email: 用户邮箱
        db: 数据库会话

    Returns:
        User 对象，如果不存在则返回 None

    Raises:
        DatabaseError: 数据库查询错误
    """
    return db.query(User).filter(User.email == email).first()
```

### 4. 错误处理

使用 FastAPI 的 HTTPException：

```python
from fastapi import HTTPException, status

async def get_conversation(
    conversation_id: int,
    db: Session
) -> Conversation:
    """获取对话"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在"
        )

    return conversation
```

### 5. 日志记录

使用 Python 的 logging 模块：

```python
import logging

logger = logging.getLogger(__name__)

async def process_document(document_id: int):
    """处理文档"""
    logger.info(f"开始处理文档: {document_id}")

    try:
        # 处理逻辑
        logger.info(f"文档处理成功: {document_id}")
    except Exception as e:
        logger.error(f"文档处理失败: {document_id}, 错误: {e}")
        raise
```

---

## 开发工作流

### 1. 分支策略

- `main`: 主分支，始终保持稳定
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: 修复分支
- `hotfix/*`: 紧急修复分支

### 2. 提交规范

使用约定式提交：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链相关

示例：

```
feat(conversations): 添加对话归档功能

- 添加对话状态字段
- 实现归档 API
- 更新文档

Closes #123
```

### 3. Pull Request 流程

1. 从 `develop` 分支创建功能分支
2. 在功能分支上进行开发
3. 提交代码并推送到远程
4. 创建 Pull Request 到 `develop`
5. 等待 Code Review
6. 根据反馈修改代码
7. 合并到 `develop`

---

## 测试指南

### 1. 测试框架

使用 pytest 进行测试：

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_auth.py

# 运行特定测试函数
pytest tests/test_auth.py::test_login

# 显示详细输出
pytest -v

# 显示代码覆盖率
pytest --cov=app --cov-report=html
```

### 2. 测试示例

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_user():
    """测试用户注册"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "name": "测试用户"
        }
    )
    assert response.status_code == 201
    assert response.json()["success"] == True

def test_login_user():
    """测试用户登录"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### 3. 异步测试

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_async_conversation():
    """测试异步对话"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/conversations/1/chat",
            content="你好",
            headers={"Authorization": "Bearer token"}
        )
    assert response.status_code == 200
```

### 4. 数据库测试

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    """测试数据库 fixture"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

---

## 数据库迁移

### 1. 创建迁移

```bash
# 自动生成迁移
alembic revision --autogenerate -m "添加用户表"

# 手动创建迁移
alembic revision -m "自定义迁移"
```

### 2. 应用迁移

```bash
# 应用所有迁移
alembic upgrade head

# 应用到特定版本
alembic upgrade <revision_id>

# 回滚迁移
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>
```

### 3. 查看迁移状态

```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

---

## 调试技巧

### 1. 使用 pdb 调试

```python
import pdb

def process_data(data):
    """处理数据"""
    pdb.set_trace()  # 设置断点
    result = data * 2
    return result
```

### 2. 使用 VS Code 调试

创建 `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    }
  ]
}
```

### 3. 日志调试

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

---

## 贡献代码

### 1. 代码审查清单

提交 PR 前检查：

- [ ] 代码符合 PEP 8 规范
- [ ] 通过所有测试
- [ ] 添加了必要的测试
- [ ] 更新了文档
- [ ] 提交信息符合约定式提交
- [ ] 没有引入新的警告
- [ ] 代码覆盖率没有降低

### 2. 报告 Bug

报告 Bug 时请提供：

1. Bug 描述
2. 重现步骤
3. 预期行为
4. 实际行为
5. 环境信息（OS、Python 版本等）
6. 错误日志

### 3. 功能请求

提出功能请求时请说明：

1. 功能描述
2. 使用场景
3. 预期效果
4. 实现建议（可选）

---

## 常见问题

### Q1: 如何运行 Celery Worker？

```bash
# 启动 Celery Worker
celery -A app.worker.celery_app worker --loglevel=info

# 启动 Celery Beat
celery -A app.worker.celery_app beat --loglevel=info

# 或使用 Makefile
make celery-worker
make celery-beat
```

### Q2: 如何重置数据库？

```bash
# 删除所有表
alembic downgrade base

# 重新创建
alembic upgrade head

# 初始化数据
python scripts/init_db.py
```

### Q3: 如何添加新的 API 端点？

1. 在 `app/api/` 目录下创建新的路由文件
2. 在 `app/main.py` 中注册路由
3. 添加对应的模型和模式
4. 编写测试

示例：

```python
# app/api/new_feature.py
from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/hello")
async def hello(current_user = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.name}!"}

# app/main.py
from app.api import new_feature

app.include_router(new_feature.router, prefix="/api/v1/new-feature", tags=["新功能"])
```

### Q4: 如何处理异步任务？

```python
# app/worker/tasks.py
from app.worker.celery_app import celery_app

@celery_app.task
async def process_document_async(document_id: int):
    """异步处理文档"""
    # 处理逻辑
    return {"success": True, "document_id": document_id}

# 调用任务
from app.worker.tasks import process_document_async

task = process_document_async.delay(document_id=123)
result = task.get(timeout=60)
```

---

## 资源链接

### 官方文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [Celery 文档](https://docs.celeryproject.org/)

### 工具

- [Black](https://black.readthedocs.io/) - 代码格式化
- [Flake8](https://flake8.pycqa.org/) - 代码检查
- [Pytest](https://docs.pytest.org/) - 测试框架
- [MyPy](https://mypy.readthedocs.io/) - 类型检查

---

## 获取帮助

如果您在开发过程中遇到问题：

1. 📖 查看项目文档
2. 🔍 搜索 Issue
3. 💬 加入开发者社区
4. 📧 联系技术支持：dev-support@openspark.online

---

**欢迎贡献代码！🎉**

*最后更新：2024-02-14*
