"""
知识库相关异步任务
处理文档向量化、知识库更新等任务
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback
import os

from celery import Task
from celery.exceptions import Retry

from app.tasks.celery_app import celery_app
from app.tasks.ai_tasks import BaseTaskWithRetry
from app.core.config import settings


# 配置日志
logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.knowledge_tasks.vectorize_document",
    base=BaseTaskWithRetry,
    bind=True,
    max_retries=3,
    soft_time_limit=300,  # 5 分钟软超时
    time_limit=600,  # 10 分钟硬超时
)
def vectorize_document(
    self,
    document_id: str,
    file_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    knowledge_base_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    异步文档向量化

    Args:
        self: 任务实例（用于重试）
        document_id: 文档 ID
        file_path: 文件路径
        chunk_size: 文本分块大小
        chunk_overlap: 分块重叠大小
        knowledge_base_id: 知识库 ID
        user_id: 用户 ID（可选）

    Returns:
        dict: 向量化结果，包含向量数量、处理时间等

    Raises:
        Exception: 向量化失败时抛出异常
    """
    try:
        logger.info(
            f"开始文档向量化: document_id={document_id}, "
            f"file_path={file_path}, user_id={user_id}"
        )

        start_time = datetime.utcnow()

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取文件内容
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"文件读取成功: document_id={document_id}, size={len(content)} 字符")

        # 文本分块（实际实现应该使用 LangChain 的文本分割器）
        chunks = _split_text(content, chunk_size, chunk_overlap)
        logger.info(f"文本分块完成: document_id={document_id}, chunks={len(chunks)}")

        # 生成向量（实际实现应该调用向量模型）
        vectors = _generate_vectors(chunks)
        logger.info(f"向量生成完成: document_id={document_id}, vectors={len(vectors)}")

        # 存储向量到 Pinecone 或其他向量数据库
        # 这里应该是实际的向量存储逻辑
        storage_result = _store_vectors(
            document_id=document_id,
            vectors=vectors,
            knowledge_base_id=knowledge_base_id,
        )
        logger.info(f"向量存储完成: document_id={document_id}")

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        return {
            "document_id": document_id,
            "knowledge_base_id": knowledge_base_id,
            "user_id": user_id,
            "file_path": file_path,
            "chunk_count": len(chunks),
            "vector_count": len(vectors),
            "processing_time": processing_time,
            "storage_result": storage_result,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "SUCCESS",
        }

    except Exception as exc:
        logger.error(
            f"文档向量化失败: document_id={document_id}, "
            f"error={exc}, traceback={traceback.format_exc()}"
        )

        if self.request.retries < self.max_retries:
            # 文档向量化失败后，等待更长时间再重试
            wait_time = 120 * (self.request.retries + 1)
            logger.info(f"正在重试任务: retry_count={self.request.retries + 1}, wait={wait_time}s")
            raise self.retry(exc=exc, countdown=wait_time)
        else:
            raise


@celery_app.task(
    name="app.tasks.knowledge_tasks.update_knowledge_base",
    base=BaseTaskWithRetry,
    bind=True,
    max_retries=2,
    soft_time_limit=180,  # 3 分钟软超时
    time_limit=300,  # 5 分钟硬超时
)
def update_knowledge_base(
    self,
    knowledge_base_id: str,
    update_type: str = "full",
    document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    异步更新知识库

    Args:
        self: 任务实例（用于重试）
        knowledge_base_id: 知识库 ID
        update_type: 更新类型（full, incremental, rebuild）
        document_ids: 要更新的文档 ID 列表（仅用于增量更新）
        user_id: 用户 ID（可选）

    Returns:
        dict: 更新结果，包含更新的文档数量、状态等

    Raises:
        Exception: 更新失败时抛出异常
    """
    try:
        logger.info(
            f"开始更新知识库: knowledge_base_id={knowledge_base_id}, "
            f"update_type={update_type}, user_id={user_id}"
        )

        start_time = datetime.utcnow()

        updated_documents = []
        failed_documents = []

        if update_type == "incremental" and document_ids:
            # 增量更新：仅更新指定的文档
            logger.info(f"增量更新: document_count={len(document_ids)}")

            for doc_id in document_ids:
                try:
                    # 这里应该调用文档向量化的逻辑
                    # 模拟文档更新
                    updated_documents.append(doc_id)
                    logger.info(f"文档更新成功: document_id={doc_id}")
                except Exception as e:
                    logger.error(f"文档更新失败: document_id={doc_id}, error={e}")
                    failed_documents.append({"document_id": doc_id, "error": str(e)})

        elif update_type == "full" or update_type == "rebuild":
            # 全量更新或重建：重新索引所有文档
            logger.info(f"全量更新: update_type={update_type}")

            # 这里应该从数据库获取知识库中的所有文档
            # 然后对每个文档进行向量化
            # 模拟更新 10 个文档
            for i in range(10):
                doc_id = f"doc_{i}"
                updated_documents.append(doc_id)
                logger.info(f"文档更新成功: document_id={doc_id}")

        else:
            raise ValueError(f"不支持的更新类型: {update_type}")

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        result = {
            "knowledge_base_id": knowledge_base_id,
            "update_type": update_type,
            "user_id": user_id,
            "updated_count": len(updated_documents),
            "failed_count": len(failed_documents),
            "updated_documents": updated_documents[:10],  # 只返回前 10 个
            "failed_documents": failed_documents,
            "processing_time": processing_time,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "SUCCESS",
        }

        logger.info(
            f"知识库更新完成: knowledge_base_id={knowledge_base_id}, "
            f"updated={len(updated_documents)}, failed={len(failed_documents)}"
        )

        return result

    except Exception as exc:
        logger.error(
            f"知识库更新失败: knowledge_base_id={knowledge_base_id}, "
            f"error={exc}, traceback={traceback.format_exc()}"
        )

        if self.request.retries < self.max_retries:
            # 知识库更新失败后，等待更长时间再重试
            wait_time = 180 * (self.request.retries + 1)
            logger.info(f"正在重试任务: retry_count={self.request.retries + 1}, wait={wait_time}s")
            raise self.retry(exc=exc, countdown=wait_time)
        else:
            raise


@celery_app.task(
    name="app.tasks.knowledge_tasks.delete_knowledge_vectors",
    base=BaseTaskWithRetry,
    bind=True,
    max_retries=2,
)
def delete_knowledge_vectors(
    self,
    document_id: str,
    knowledge_base_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    异步删除知识向量

    Args:
        self: 任务实例（用于重试）
        document_id: 文档 ID
        knowledge_base_id: 知识库 ID
        user_id: 用户 ID（可选）

    Returns:
        dict: 删除结果

    Raises:
        Exception: 删除失败时抛出异常
    """
    try:
        logger.info(
            f"开始删除知识向量: document_id={document_id}, "
            f"knowledge_base_id={knowledge_base_id}"
        )

        # 这里应该调用向量数据库的删除接口
        # 模拟删除操作
        deleted_count = 0

        logger.info(f"知识向量删除完成: document_id={document_id}, deleted={deleted_count}")

        return {
            "document_id": document_id,
            "knowledge_base_id": knowledge_base_id,
            "user_id": user_id,
            "deleted_count": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "SUCCESS",
        }

    except Exception as exc:
        logger.error(
            f"删除知识向量失败: document_id={document_id}, "
            f"error={exc}, traceback={traceback.format_exc()}"
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        else:
            raise


# ==================== 辅助函数 ====================

def _split_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[str]:
    """
    文本分块

    Args:
        text: 输入文本
        chunk_size: 分块大小
        chunk_overlap: 分块重叠大小

    Returns:
        list: 分块后的文本列表
    """
    # 简单实现：按字符分割
    # 实际实现应该使用 LangChain 的文本分割器
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap

        if chunk_overlap >= chunk_size:
            break

    return chunks


def _generate_vectors(chunks: List[str]) -> List[Dict[str, Any]]:
    """
    生成向量

    Args:
        chunks: 文本块列表

    Returns:
        list: 向量列表
    """
    # 模拟向量生成
    # 实际实现应该调用 sentence-transformers 或其他向量模型
    vectors = []
    for i, chunk in enumerate(chunks):
        # 模拟 768 维向量
        import random
        vector = [random.random() for _ in range(768)]
        vectors.append({
            "id": f"chunk_{i}",
            "text": chunk[:100],  # 只保留前 100 个字符
            "vector": vector,
        })

    return vectors


def _store_vectors(
    document_id: str,
    vectors: List[Dict[str, Any]],
    knowledge_base_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    存储向量

    Args:
        document_id: 文档 ID
        vectors: 向量列表
        knowledge_base_id: 知识库 ID

    Returns:
        dict: 存储结果
    """
    # 模拟向量存储
    # 实际实现应该调用 Pinecone 或其他向量数据库
    return {
        "stored_count": len(vectors),
        "document_id": document_id,
        "knowledge_base_id": knowledge_base_id,
    }


# 导出所有任务
__all__ = [
    "vectorize_document",
    "update_knowledge_base",
    "delete_knowledge_vectors",
]
