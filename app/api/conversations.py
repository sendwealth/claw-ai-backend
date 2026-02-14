"""
对话相关 API
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_conversations():
    """获取对话列表"""
    return {"message": "对话列表 API"}
