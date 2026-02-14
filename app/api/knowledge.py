"""
知识库相关 API
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_knowledge_bases():
    """获取知识库列表"""
    return {"message": "知识库列表 API"}
