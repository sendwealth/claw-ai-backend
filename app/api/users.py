"""
用户相关 API
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_users():
    """获取用户列表"""
    return {"message": "用户列表 API"}
