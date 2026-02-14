"""
用户相关的 Pydantic 模型
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models.user import SubscriptionTier


# ========== 用户相关 ==========

class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=6, max_length=50)


class UserUpdate(BaseModel):
    """更新用户模型"""
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    role: str
    subscription_tier: SubscriptionTier
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== 认证相关 ==========

class Token(BaseModel):
    """Token 响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 数据模型"""
    email: str | None = None


class LoginRequest(BaseModel):
    """登录请求模型"""
    email: EmailStr
    password: str


class RegisterRequest(UserCreate):
    """注册请求模型（继承 UserCreate）"""
    pass


# ========== 订阅相关 ==========

class SubscriptionUpdate(BaseModel):
    """更新订阅模型"""
    subscription_tier: SubscriptionTier


class SubscriptionResponse(BaseModel):
    """订阅响应模型"""
    tier: SubscriptionTier
    can_access: bool
    features: list[str]


# ========== 响应包装 ==========

class MessageResponse(BaseModel):
    """消息响应"""
    success: bool
    message: str
    data: Optional[dict] = None
