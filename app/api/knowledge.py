"""
知识库管理 API
实现知识库和文档的 CRUD 操作
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseDetailResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse,
)
from app.models import KnowledgeBase, Document, User
from app.api.auth import get_current_user
from app.services.rag_service import create_rag_service


router = APIRouter()


# ====================
# 知识库管理
# ====================


@router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    knowledge_base_data: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建新知识库

    Args:
        knowledge_base_data: 知识库数据
        db: 数据库会话
        current_user: 当前用户

    Returns:
        KnowledgeBaseResponse: 创建的知识库
    """
    knowledge_base = KnowledgeBase(
        user_id=current_user.id,
        name=knowledge_base_data.name,
        description=knowledge_base_data.description,
        embedding_model=knowledge_base_data.embedding_model,
    )

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    return knowledge_base


@router.get("/", response_model=List[KnowledgeBaseResponse])
async def get_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的知识库列表

    Args:
        skip: 跳过数量
        limit: 返回数量
        db: 数据库会话
        current_user: 当前用户

    Returns:
        List[KnowledgeBaseResponse]: 知识库列表
    """
    knowledge_bases = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.user_id == current_user.id)
        .order_by(KnowledgeBase.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 添加文档数量
    result = []
    for kb in knowledge_bases:
        doc_count = db.query(Document).filter(Document.knowledge_base_id == kb.id).count()
        kb_dict = {
            "id": kb.id,
            "user_id": kb.user_id,
            "name": kb.name,
            "description": kb.description,
            "embedding_model": kb.embedding_model,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
            "document_count": doc_count,
        }
        result.append(KnowledgeBaseResponse(**kb_dict))

    return result


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseDetailResponse)
async def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取知识库详情（包含文档列表）

    Args:
        knowledge_base_id: 知识库 ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        KnowledgeBaseDetailResponse: 知识库详情
    """
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 获取文档列表
    documents = (
        db.query(Document)
        .filter(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return KnowledgeBaseDetailResponse(
        id=knowledge_base.id,
        user_id=knowledge_base.user_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        embedding_model=knowledge_base.embedding_model,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
        document_count=len(documents),
        documents=documents,
    )


@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    knowledge_base_id: int,
    update_data: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新知识库

    Args:
        knowledge_base_id: 知识库 ID
        update_data: 更新数据
        db: 数据库会话
        current_user: 当前用户

    Returns:
        KnowledgeBaseResponse: 更新后的知识库
    """
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 更新字段
    if update_data.name is not None:
        knowledge_base.name = update_data.name
    if update_data.description is not None:
        knowledge_base.description = update_data.description

    db.commit()
    db.refresh(knowledge_base)

    # 添加文档数量
    doc_count = db.query(Document).filter(Document.knowledge_base_id == knowledge_base.id).count()

    return KnowledgeBaseResponse(
        id=knowledge_base.id,
        user_id=knowledge_base.user_id,
        name=knowledge_base.name,
        description=knowledge_base.description,
        embedding_model=knowledge_base.embedding_model,
        created_at=knowledge_base.created_at,
        updated_at=knowledge_base.updated_at,
        document_count=doc_count,
    )


@router.delete("/{knowledge_base_id}")
async def delete_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除知识库（包括所有文档和向量索引）

    Args:
        knowledge_base_id: 知识库 ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 删除结果
    """
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 删除向量索引
    rag_service = create_rag_service(db)
    await rag_service.delete_knowledge_base_index(knowledge_base_id)

    # 删除知识库（级联删除所有文档）
    db.delete(knowledge_base)
    db.commit()

    return {"message": "知识库删除成功"}


# ====================
# 文档管理
# ====================


@router.post("/{knowledge_base_id}/documents", response_model=DocumentResponse)
async def create_document(
    knowledge_base_id: int,
    document_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建文档（并索引到向量数据库）

    Args:
        knowledge_base_id: 知识库 ID
        document_data: 文档数据
        db: 数据库会话
        current_user: 当前用户

    Returns:
        DocumentResponse: 创建的文档
    """
    # 验证知识库所有权
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 创建文档
    document = Document(
        knowledge_base_id=knowledge_base_id,
        title=document_data.title,
        content=document_data.content,
        file_url=document_data.file_url,
        file_type=document_data.file_type,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # 索引到向量数据库
    try:
        rag_service = create_rag_service(db)
        index_result = await rag_service.index_document(
            knowledge_base_id=knowledge_base_id,
            document_id=document.id,
            text=document.content,
        )

        if index_result["success"]:
            document.chunk_count = index_result["chunk_count"]
            db.commit()

    except Exception as e:
        print(f"⚠️ 文档索引失败: {e}")

    return document


@router.get("/{knowledge_base_id}/documents", response_model=DocumentListResponse)
async def get_documents(
    knowledge_base_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取知识库的文档列表

    Args:
        knowledge_base_id: 知识库 ID
        skip: 跳过数量
        limit: 返回数量
        db: 数据库会话
        current_user: 当前用户

    Returns:
        DocumentListResponse: 文档列表
    """
    # 验证知识库所有权
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 获取文档
    documents = (
        db.query(Document)
        .filter(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).count()

    return DocumentListResponse(total=total, items=documents)


@router.get("/{knowledge_base_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    knowledge_base_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取文档详情

    Args:
        knowledge_base_id: 知识库 ID
        document_id: 文档 ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        DocumentResponse: 文档详情
    """
    # 验证知识库所有权
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 获取文档
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    return document


@router.delete("/{knowledge_base_id}/documents/{document_id}")
async def delete_document(
    knowledge_base_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除文档（包括向量索引）

    Args:
        knowledge_base_id: 知识库 ID
        document_id: 文档 ID
        db: 数据库会话
        current_user: 当前用户

    Returns:
        dict: 删除结果
    """
    # 验证知识库所有权
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 获取文档
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.knowledge_base_id == knowledge_base_id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除向量索引
    try:
        rag_service = create_rag_service(db)
        await rag_service.delete_document_index(document_id)
    except Exception as e:
        print(f"⚠️ 删除向量索引失败: {e}")

    # 删除文档
    db.delete(document)
    db.commit()

    return {"message": "文档删除成功"}


# ====================
# RAG 查询接口
# ====================


@router.post("/{knowledge_base_id}/query")
async def rag_query(
    knowledge_base_id: int,
    question: str,
    top_k: Optional[int] = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    使用知识库进行 RAG 查询

    Args:
        knowledge_base_id: 知识库 ID
        question: 用户问题
        top_k: 返回最相似的前 K 个文档片段
        db: 数据库会话
        current_user: 当前用户

    Returns:
        dict: RAG 查询结果
    """
    # 验证知识库所有权
    knowledge_base = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.user_id == current_user.id,
        )
        .first()
    )

    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 执行 RAG 查询
    rag_service = create_rag_service(db)
    result = await rag_service.query(
        question=question,
        knowledge_base_id=knowledge_base_id,
        top_k=top_k,
    )

    return result


@router.post("/query")
async def rag_query_all(
    question: str,
    top_k: Optional[int] = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    使用用户的所有知识库进行 RAG 查询

    Args:
        question: 用户问题
        top_k: 返回最相似的前 K 个文档片段
        db: 数据库会话
        current_user: 当前用户

    Returns:
        dict: RAG 查询结果
    """
    # 执行 RAG 查询（不指定 knowledge_base_id，会搜索全部）
    rag_service = create_rag_service(db)
    result = await rag_service.query(
        question=question,
        knowledge_base_id=None,
        top_k=top_k,
    )

    return result
