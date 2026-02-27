"""
Pytest 配置文件
定义共享的 fixtures 和测试配置
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.base import Base
from app.main import app
from app.models.user import User
from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.utils.security import get_password_hash, create_access_token
from app.core.config import settings


# 测试数据库 URL（使用内存 SQLite）
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_engine():
    """创建测试数据库引擎（内存 SQLite）"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 清理
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话"""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def override_get_db(db_session: Session):
    """覆盖 FastAPI 的 get_db 依赖"""
    def _get_db():
        try:
            yield db_session
        finally:
            pass
    
    return _get_db


@pytest.fixture(scope="function")
async def client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """创建测试 HTTP 客户端"""
    from app.db import get_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123",
        "name": "Test User",
        "phone": "13800138000",
        "company": "Test Company"
    }


@pytest.fixture
def test_user(db_session: Session) -> User:
    """创建测试用户"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("TestPassword123"),
        name="Test User",
        phone="13800138000",
        company="Test Company",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """创建未激活用户"""
    user = User(
        email="inactive@example.com",
        password_hash=get_password_hash("TestPassword123"),
        name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """创建认证请求头"""
    access_token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_conversation_data():
    """测试对话数据"""
    return {
        "title": "Test Conversation",
        "conversation_type": "chat",
        "model": "glm-4",
        "system_prompt": "You are a helpful assistant."
    }


@pytest.fixture
def test_conversation(db_session: Session, test_user: User) -> Conversation:
    """创建测试对话"""
    from app.schemas.conversation import ConversationCreate
    from app.services.conversation_service import ConversationService
    
    service = ConversationService(db_session)
    conversation = service.create_conversation(
        user_id=test_user.id,
        conversation_data=ConversationCreate(
            title="Test Conversation",
            conversation_type="chat",
            model="glm-4",
        )
    )
    return conversation


@pytest.fixture
def test_knowledge_base_data():
    """测试知识库数据"""
    return {
        "name": "Test Knowledge Base",
        "description": "A test knowledge base for testing",
        "embedding_model": "embedding-2"
    }


@pytest.fixture
def test_knowledge_base(db_session: Session, test_user: User) -> KnowledgeBase:
    """创建测试知识库"""
    kb = KnowledgeBase(
        user_id=test_user.id,
        name="Test Knowledge Base",
        description="A test knowledge base",
        embedding_model="embedding-2",
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)
    return kb


@pytest.fixture
def mock_cache_service():
    """Mock 缓存服务"""
    with patch("app.services.cache_service.cache_service") as mock:
        mock.connect = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        mock.disconnect = AsyncMock(return_value=None)
        yield mock


@pytest.fixture
def mock_ai_service():
    """Mock AI 服务"""
    with patch("app.services.ai_service.AIService") as mock:
        mock_instance = mock.return_value
        mock_instance.generate_response = AsyncMock(return_value={
            "content": "This is a test AI response",
            "tokens": 100,
            "cost": 0.001,
        })
        yield mock_instance


@pytest.fixture
def mock_rag_service():
    """Mock RAG 服务"""
    with patch("app.services.rag_service.create_rag_service") as mock:
        mock_instance = AsyncMock()
        mock_instance.index_document = AsyncMock(return_value={
            "success": True,
            "chunk_count": 5,
        })
        mock_instance.query = AsyncMock(return_value={
            "success": True,
            "answer": "Test answer",
            "sources": [],
        })
        mock_instance.delete_knowledge_base_index = AsyncMock(return_value=None)
        mock_instance.delete_document_index = AsyncMock(return_value=None)
        mock.return_value = mock_instance
        yield mock_instance
