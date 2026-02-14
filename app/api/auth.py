"""
认证相关 API
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    RegisterRequest,
    Token,
    UserResponse,
    MessageResponse,
)
from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.core.config import settings
from app.api.dependencies import get_current_user


router = APIRouter()


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册

    Args:
        user_data: 注册请求数据
        db: 数据库会话

    Returns:
        MessageResponse: 注册结果消息
    """
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册",
        )

    # 创建新用户
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
        phone=user_data.phone,
        company=user_data.company,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return MessageResponse(
        success=True,
        message="注册成功",
        data={"user_id": new_user.id},
    )


@router.post("/login", response_model=Token)
async def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录

    Args:
        user_data: 登录请求数据
        db: 数据库会话

    Returns:
        Token: 访问令牌和刷新令牌
    """
    # 查找用户
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # 验证密码
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )

    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用",
        )

    # 生成令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户信息

    Args:
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        UserResponse: 用户信息
    """
    # 刷新用户数据（从数据库重新查询）
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return user
