"""
咨询相关 API
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_consulting_projects():
    """获取咨询项目列表"""
    return {"message": "咨询项目列表 API"}
