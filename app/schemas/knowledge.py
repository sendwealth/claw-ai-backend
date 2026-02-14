"""
知识库相关的 Pydantic 模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class KnowledgeBaseBase(BaseModel):
    """知识库基础模型"""
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    embedding_model: Optional[str] = "text-embedding-ada-002"


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库模型"""
    pass


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库模型"""
    name: Optional[str] = None
    description: Optional[str] = None


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """知识库响应模型"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0  # 文档数量

    class Config:
        from_attributes = True


# ========== 文档相关 ==========

class DocumentBase(BaseModel):
    """文档基础模型"""
    title: str = Field(..., max_length=200)
    content: str
    file_url: Optional[str] = None
    file_type: Optional[str] = None


class DocumentCreate(DocumentBase):
    """创建文档模型"""
    knowledge_base_id: int


class DocumentResponse(DocumentBase):
    """文档响应模型"""
    id: int
    knowledge_base_id: int
    file_size: Optional[int] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseDetailResponse(KnowledgeBaseResponse):
    """知识库详情响应（包含文档列表）"""
    documents: List[DocumentResponse] = []


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    items: List[DocumentResponse]
