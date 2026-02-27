"""
API 功能测试
测试对话 API 和知识库 API 的基本功能
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock, MagicMock
import json

from app.models.user import User
from app.models.conversation import Conversation
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.main import app
from app.db import get_db


class TestConversationAPI:
    """对话 API 测试"""

    @pytest.mark.asyncio
    async def test_create_conversation_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation_data: dict
    ):
        """测试成功创建对话"""
        response = await client.post(
            "/api/v1/conversations/",
            json=test_conversation_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == test_conversation_data["title"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_conversation_unauthorized(
        self,
        client: AsyncClient,
        test_conversation_data: dict
    ):
        """测试未授权创建对话"""
        response = await client.post(
            "/api/v1/conversations/",
            json=test_conversation_data
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_conversation_missing_title(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试缺少标题创建对话"""
        response = await client.post(
            "/api/v1/conversations/",
            json={"conversation_type": "chat"},
            headers=auth_headers
        )
        
        # 根据实际验证规则
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_get_conversations_list(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """测试获取对话列表"""
        response = await client.get(
            "/api/v1/conversations/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_conversations_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试对话列表分页"""
        response = await client.get(
            "/api/v1/conversations/?skip=0&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_conversation_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """测试获取对话详情"""
        response = await client.get(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_conversation.id
        assert data["title"] == test_conversation.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试获取不存在的对话"""
        response = await client.get(
            "/api/v1/conversations/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "对话不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """测试更新对话"""
        update_data = {"title": "Updated Title"}
        
        response = await client.put(
            f"/api/v1/conversations/{test_conversation.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """测试删除对话"""
        response = await client.delete(
            f"/api/v1/conversations/{test_conversation.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试删除不存在的对话"""
        response = await client.delete(
            "/api/v1/conversations/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_user_conversation(
        self,
        client: AsyncClient,
        db_session: Session,
        test_user: User
    ):
        """测试访问其他用户的对话（应该失败）"""
        # 创建另一个用户
        from app.utils.security import get_password_hash, create_access_token
        
        other_user = User(
            email="other@example.com",
            password_hash=get_password_hash("password123"),
            name="Other User",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)
        
        # 创建属于其他用户的对话
        other_conversation = Conversation(
            user_id=other_user.id,
            title="Other's Conversation",
            status="active",
            conversation_type="chat",
            model="glm-4",
        )
        db_session.add(other_conversation)
        db_session.commit()
        db_session.refresh(other_conversation)
        
        # 用原用户登录
        token = create_access_token(data={"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        # 尝试访问其他用户的对话
        response = await client.get(
            f"/api/v1/conversations/{other_conversation.id}",
            headers=headers
        )
        
        assert response.status_code == 404


class TestMessageAPI:
    """消息 API 测试"""

    @pytest.mark.asyncio
    async def test_create_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """测试创建消息"""
        message_data = {
            "role": "user",
            "content": "Hello, this is a test message"
        }
        
        response = await client.post(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            json=message_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == message_data["content"]
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_messages(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_conversation: Conversation
    ):
        """测试获取消息列表"""
        response = await client.get(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_chat_endpoint_unauthorized(
        self,
        client: AsyncClient,
        test_conversation: Conversation
    ):
        """测试未授权的聊天请求"""
        response = await client.post(
            f"/api/v1/conversations/{test_conversation.id}/chat",
            json={"user_message": "Hello"}
        )
        
        assert response.status_code == 401


class TestKnowledgeBaseAPI:
    """知识库 API 测试"""

    @pytest.mark.asyncio
    async def test_create_knowledge_base(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base_data: dict
    ):
        """测试创建知识库"""
        response = await client.post(
            "/api/v1/knowledge/",
            json=test_knowledge_base_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == test_knowledge_base_data["name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_knowledge_base_unauthorized(
        self,
        client: AsyncClient,
        test_knowledge_base_data: dict
    ):
        """测试未授权创建知识库"""
        response = await client.post(
            "/api/v1/knowledge/",
            json=test_knowledge_base_data
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_knowledge_bases_list(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试获取知识库列表"""
        response = await client.get(
            "/api/v1/knowledge/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_knowledge_base_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试获取知识库详情"""
        response = await client.get(
            f"/api/v1/knowledge/{test_knowledge_base.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_knowledge_base.id
        assert data["name"] == test_knowledge_base.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_knowledge_base(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试获取不存在的知识库"""
        response = await client.get(
            "/api/v1/knowledge/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "知识库不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_knowledge_base(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试更新知识库"""
        update_data = {
            "name": "Updated Knowledge Base",
            "description": "Updated description"
        }
        
        response = await client.put(
            f"/api/v1/knowledge/{test_knowledge_base.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Knowledge Base"

    @pytest.mark.asyncio
    async def test_delete_knowledge_base(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试删除知识库"""
        with patch("app.api.knowledge.create_rag_service") as mock_rag:
            mock_rag_instance = AsyncMock()
            mock_rag_instance.delete_knowledge_base_index = AsyncMock()
            mock_rag.return_value = mock_rag_instance
            
            response = await client.delete(
                f"/api/v1/knowledge/{test_knowledge_base.id}",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert "删除成功" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_knowledge_base(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试删除不存在的知识库"""
        response = await client.delete(
            "/api/v1/knowledge/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestDocumentAPI:
    """文档 API 测试"""

    @pytest.mark.asyncio
    async def test_create_document(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试创建文档"""
        document_data = {
            "title": "Test Document",
            "content": "This is the content of the test document.",
            "file_type": "txt"
        }
        
        with patch("app.api.knowledge.create_rag_service") as mock_rag:
            mock_rag_instance = AsyncMock()
            mock_rag_instance.index_document = AsyncMock(return_value={
                "success": True,
                "chunk_count": 3
            })
            mock_rag.return_value = mock_rag_instance
            
            response = await client.post(
                f"/api/v1/knowledge/{test_knowledge_base.id}/documents",
                json=document_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == document_data["title"]

    @pytest.mark.asyncio
    async def test_get_documents(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试获取文档列表"""
        response = await client.get(
            f"/api/v1/knowledge/{test_knowledge_base.id}/documents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_create_document_nonexistent_kb(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试在不存在的知识库中创建文档"""
        document_data = {
            "title": "Test Document",
            "content": "Content here"
        }
        
        response = await client.post(
            "/api/v1/knowledge/99999/documents",
            json=document_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestRAGQueryAPI:
    """RAG 查询 API 测试"""

    @pytest.mark.asyncio
    async def test_rag_query(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_knowledge_base: KnowledgeBase
    ):
        """测试 RAG 查询"""
        with patch("app.api.knowledge.create_rag_service") as mock_rag:
            mock_rag_instance = AsyncMock()
            mock_rag_instance.query = AsyncMock(return_value={
                "success": True,
                "answer": "This is the answer to your question.",
                "sources": []
            })
            mock_rag.return_value = mock_rag_instance
            
            response = await client.post(
                f"/api/v1/knowledge/{test_knowledge_base.id}/query",
                params={"question": "What is this about?"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_rag_query_unauthorized(
        self,
        client: AsyncClient,
        test_knowledge_base: KnowledgeBase
    ):
        """测试未授权的 RAG 查询"""
        response = await client.post(
            f"/api/v1/knowledge/{test_knowledge_base.id}/query",
            params={"question": "What is this about?"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_rag_query_all(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试在所有知识库中查询"""
        with patch("app.api.knowledge.create_rag_service") as mock_rag:
            mock_rag_instance = AsyncMock()
            mock_rag_instance.query = AsyncMock(return_value={
                "success": True,
                "answer": "Search result from all knowledge bases.",
                "sources": []
            })
            mock_rag.return_value = mock_rag_instance
            
            response = await client.post(
                "/api/v1/knowledge/query",
                params={"question": "What is this about?"},
                headers=auth_headers
            )
            
            assert response.status_code == 200


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_404_not_found(self, client: AsyncClient):
        """测试 404 错误"""
        response = await client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_error(self, client: AsyncClient, auth_headers: dict):
        """测试数据验证错误"""
        # 发送无效数据
        response = await client.post(
            "/api/v1/conversations/",
            json={"title": 12345},  # 标题应该是字符串
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_json(self, client: AsyncClient, auth_headers: dict):
        """测试无效 JSON"""
        response = await client.post(
            "/api/v1/conversations/",
            content="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """测试不允许的 HTTP 方法"""
        response = await client.patch("/api/v1/auth/login")
        
        assert response.status_code == 405


class TestAPIAccessControl:
    """API 访问控制测试"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """测试无 Token 访问受保护端点"""
        endpoints = [
            "/api/v1/conversations/",
            "/api/v1/knowledge/",
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_cross_user_access_prevention(
        self,
        client: AsyncClient,
        db_session: Session,
        test_user: User
    ):
        """测试跨用户访问防护"""
        from app.utils.security import get_password_hash, create_access_token
        
        # 创建两个用户
        user1 = User(
            email="user1@example.com",
            password_hash=get_password_hash("password123"),
            name="User 1",
            is_active=True,
        )
        user2 = User(
            email="user2@example.com",
            password_hash=get_password_hash("password123"),
            name="User 2",
            is_active=True,
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        db_session.refresh(user1)
        db_session.refresh(user2)
        
        # 用户1创建知识库
        kb = KnowledgeBase(
            user_id=user1.id,
            name="User1's KB",
        )
        db_session.add(kb)
        db_session.commit()
        db_session.refresh(kb)
        
        # 用户2尝试访问用户1的知识库
        token2 = create_access_token(data={"sub": user2.email})
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response = await client.get(
            f"/api/v1/knowledge/{kb.id}",
            headers=headers2
        )
        
        # 应该返回 404（因为用户2没有这个知识库）
        assert response.status_code == 404


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """测试根路径"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
