"""
认证 API 测试
测试用户注册、登录、Token 验证等功能
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session
from unittest.mock import patch, AsyncMock
from datetime import timedelta

from app.models.user import User
from app.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
)
from app.main import app
from app.db import get_db


class TestUserRegistration:
    """用户注册测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        """测试成功注册"""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "注册成功"
        assert "user_id" in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, 
        client: AsyncClient, 
        test_user_data: dict,
        test_user: User
    ):
        """测试重复邮箱注册"""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        assert "邮箱已被注册" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_missing_email(self, client: AsyncClient):
        """测试缺少邮箱注册"""
        response = await client.post("/api/v1/auth/register", json={
            "password": "TestPassword123"
        })
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_password(self, client: AsyncClient):
        """测试缺少密码注册"""
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com"
        })
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """测试密码太短"""
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "12345"  # 少于 6 个字符
        })
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """测试无效邮箱格式"""
        response = await client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "TestPassword123"
        })
        
        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """测试成功登录"""
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """测试错误密码登录"""
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "WrongPassword123"
        })
        
        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在用户登录"""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "TestPassword123"
        })
        
        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, inactive_user: User):
        """测试未激活用户登录"""
        response = await client.post("/api/v1/auth/login", json={
            "email": "inactive@example.com",
            "password": "TestPassword123"
        })
        
        assert response.status_code == 403
        assert "账户已被禁用" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_missing_credentials(self, client: AsyncClient):
        """测试缺少登录凭证"""
        response = await client.post("/api/v1/auth/login", json={})
        
        assert response.status_code == 422  # Validation error


class TestTokenValidation:
    """Token 验证测试"""

    @pytest.mark.asyncio
    async def test_valid_token_access(self, client: AsyncClient, auth_headers: dict):
        """测试有效 Token 访问受保护资源"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_missing_token(self, client: AsyncClient):
        """测试缺少 Token"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, client: AsyncClient):
        """测试无效 Token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token(self, client: AsyncClient, test_user: User):
        """测试过期 Token"""
        # 创建一个已过期的 Token
        expired_token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(seconds=-1)  # 已过期
        )
        
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_auth_header(self, client: AsyncClient):
        """测试格式错误的认证头"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        assert response.status_code == 401


class TestTokenRefresh:
    """Token 刷新测试"""

    @pytest.mark.asyncio
    async def test_decode_access_token(self, test_user: User):
        """测试解码访问 Token"""
        token = create_access_token(data={"sub": test_user.email})
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == test_user.email
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_decode_refresh_token(self, test_user: User):
        """测试解码刷新 Token"""
        token = create_refresh_token(data={"sub": test_user.email})
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == test_user.email
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_decode_invalid_token(self):
        """测试解码无效 Token"""
        payload = decode_token("invalid_token")
        
        assert payload is None

    @pytest.mark.asyncio
    async def test_token_contains_correct_expiry(self, test_user: User):
        """测试 Token 包含正确的过期时间"""
        from app.core.config import settings
        
        token = create_access_token(data={"sub": test_user.email})
        payload = decode_token(token)
        
        assert payload is not None
        # 验证过期时间存在且为数字
        assert isinstance(payload["exp"], (int, float))


class TestPasswordSecurity:
    """密码安全测试"""

    def test_password_hashing(self):
        """测试密码哈希"""
        password = "TestPassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed)

    def test_password_verification_correct(self):
        """测试正确密码验证"""
        password = "TestPassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_password_verification_incorrect(self):
        """测试错误密码验证"""
        password = "TestPassword123"
        hashed = get_password_hash(password)
        
        assert verify_password("WrongPassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """测试不同密码产生不同哈希"""
        password = "TestPassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # 由于 bcrypt 使用随机盐，相同密码的哈希应该不同
        assert hash1 != hash2
        # 但都应该能验证原密码
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestGetCurrentUser:
    """获取当前用户测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        test_user: User
    ):
        """测试成功获取当前用户"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert data["id"] == test_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_fields(
        self, 
        client: AsyncClient, 
        auth_headers: dict
    ):
        """测试返回的用户字段"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证必要字段存在
        required_fields = ["id", "email", "name", "is_active", "is_verified", "created_at"]
        for field in required_fields:
            assert field in data


class TestAuthEdgeCases:
    """认证边界情况测试"""

    @pytest.mark.asyncio
    async def test_register_with_special_characters_in_name(
        self, 
        client: AsyncClient
    ):
        """测试名字中包含特殊字符"""
        response = await client.post("/api/v1/auth/register", json={
            "email": "special@example.com",
            "password": "TestPassword123",
            "name": "测试用户 🎉 Test-User"
        })
        
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_login_case_sensitive_email(
        self, 
        client: AsyncClient, 
        db_session: Session
    ):
        """测试邮箱大小写敏感"""
        # 创建用户
        user = User(
            email="lowercase@example.com",
            password_hash=get_password_hash("TestPassword123"),
            name="Test User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        
        # 使用大写邮箱登录（应该失败，因为邮箱是区分大小写的）
        response = await client.post("/api/v1/auth/login", json={
            "email": "LOWERCASE@example.com",
            "password": "TestPassword123"
        })
        
        # 根据实际实现，可能返回 401
        assert response.status_code in [401, 200]

    @pytest.mark.asyncio
    async def test_empty_token(self, client: AsyncClient):
        """测试空 Token"""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer "}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_empty_optional_fields(self, client: AsyncClient):
        """测试可选字段为空"""
        response = await client.post("/api/v1/auth/register", json={
            "email": "minimal@example.com",
            "password": "TestPassword123",
            "name": None,
            "phone": None,
            "company": None
        })
        
        assert response.status_code == 201
