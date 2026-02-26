"""
向量服务 - 基于 Qdrant
处理 Qdrant 向量数据库和文档向量化
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    OptimizersConfigDiff,
)
from qdrant_client.http.exceptions import UnexpectedResponse
from zhipuai import ZhipuAI
import redis
import json
import hashlib
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.logger import logger


class VectorService:
    """向量服务类 - Qdrant 实现"""

    def __init__(self):
        """初始化向量服务"""
        # Qdrant 连接配置
        self.qdrant_host = settings.QDRANT_HOST
        self.qdrant_port = settings.QDRANT_PORT
        self.qdrant_api_key = settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.vector_size = settings.QDRANT_VECTOR_SIZE
        self.distance = Distance.COSINE if settings.QDRANT_DISTANCE == "Cosine" else Distance.EUCLID

        # Zhipu AI Embedding API
        self.embedding_client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

        # Redis 缓存
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            logger.info("✅ Redis 缓存客户端初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ Redis 连接失败，将禁用缓存: {e}")
            self.redis_client = None

        # 连接 Qdrant
        self._connect_qdrant()

        # 确保集合存在
        self._ensure_collection()

    def _connect_qdrant(self):
        """连接到 Qdrant"""
        try:
            self.client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                api_key=self.qdrant_api_key,
            )
            logger.info(f"✅ 已连接到 Qdrant: {self.qdrant_host}:{self.qdrant_port}")
        except Exception as e:
            logger.error(f"❌ 连接 Qdrant 失败: {e}")
            raise

    def _ensure_collection(self):
        """确保向量集合存在"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # 创建集合
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=self.distance,
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        indexing_threshold=10000,  # 10000 个点后开始索引
                    ),
                )
                logger.info(f"✅ 创建 Qdrant 集合: {self.collection_name}")
            else:
                logger.info(f"✅ Qdrant 集合已存在: {self.collection_name}")

        except Exception as e:
            logger.error(f"❌ 确保 Qdrant 集合失败: {e}")
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示

        Args:
            text: 输入文本

        Returns:
            List[float]: 向量表示
        """
        if not text or not text.strip():
            raise ValueError("文本不能为空")

        # 生成缓存键
        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"

        # 尝试从缓存获取
        if settings.RAG_ENABLE_CACHE and self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.debug(f"🎯 从缓存获取向量: {cache_key[:20]}...")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"⚠️ Redis 缓存读取失败: {e}")

        try:
            # 调用 Zhipu AI Embedding API
            response = self.embedding_client.embeddings.create(
                model="embedding-2",
                input=text,
            )

            embedding = response.data[0].embedding

            # 缓存结果
            if settings.RAG_ENABLE_CACHE and self.redis_client:
                try:
                    self.redis_client.setex(
                        cache_key,
                        settings.RAG_REDIS_CACHE_TTL,
                        json.dumps(embedding),
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Redis 缓存写入失败: {e}")

            return embedding

        except Exception as e:
            logger.error(f"❌ 获取 Embedding 失败: {e}")
            raise

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        将文本分割成多个块（智能分块）

        Args:
            text: 输入文本
            chunk_size: 块大小（字符数）
            overlap: 重叠大小

        Returns:
            List[Dict]: 文本块列表，包含文本和元数据
        """
        if not text or not text.strip():
            return []

        chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        overlap = overlap or settings.RAG_CHUNK_OVERLAP

        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        chunk_index = 0

        for line in lines:
            line_length = len(line)

            # 如果当前行超过块大小，需要拆分
            if line_length > chunk_size:
                # 先保存当前块
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'index': chunk_index,
                        'length': len(chunk_text),
                    })
                    chunk_index += 1
                    current_chunk = []
                    current_length = 0

                # 拆分长行
                for i in range(0, line_length, chunk_size - overlap):
                    chunk_text = line[i:i + chunk_size]
                    chunks.append({
                        'text': chunk_text,
                        'index': chunk_index,
                        'length': len(chunk_text),
                    })
                    chunk_index += 1
            else:
                # 检查是否需要创建新块
                if current_length + line_length + 1 > chunk_size and current_chunk:
                    # 保存当前块
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'index': chunk_index,
                        'length': len(chunk_text),
                    })
                    chunk_index += 1

                    # 保留部分重叠内容
                    if overlap > 0 and len(current_chunk) > 1:
                        overlap_text = '\n'.join(current_chunk[-2:])  # 保留最后 2 行
                        current_chunk = [overlap_text]
                        current_length = len(overlap_text)
                    else:
                        current_chunk = []
                        current_length = 0

                # 添加行到当前块
                current_chunk.append(line)
                current_length += line_length + 1  # +1 for newline

        # 保存最后一个块
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'index': chunk_index,
                'length': len(chunk_text),
            })

        logger.info(f"📄 文本分块完成: {len(chunks)} 个块")
        return chunks

    async def add_document_chunks(
        self,
        knowledge_base_id: int,
        document_id: int,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        添加文档的文本块到向量数据库

        Args:
            knowledge_base_id: 知识库 ID
            document_id: 文档 ID
            text: 文档内容
            metadata: 额外元数据

        Returns:
            Dict: 包含添加的块数量等信息
        """
        try:
            # 分割文本
            chunks = self.chunk_text(text)

            if not chunks:
                return {
                    "success": False,
                    "error": "文本为空或无法分割",
                }

            # 为每个块生成向量和点
            points = []
            for chunk in chunks:
                # 生成向量
                embedding = await self.get_embedding(chunk['text'])

                # 创建唯一 ID
                point_id = str(uuid.uuid4())

                # 准备元数据
                point_metadata = {
                    "knowledge_base_id": knowledge_base_id,
                    "document_id": document_id,
                    "chunk_index": chunk['index'],
                    "text": chunk['text'],
                    "length": chunk['length'],
                    "created_at": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                }

                # 创建点结构
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=point_metadata,
                )
                points.append(point)

            # 批量插入到 Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(f"✅ 添加了 {len(chunks)} 个文档块到 Qdrant")

            return {
                "success": True,
                "chunk_count": len(chunks),
                "point_ids": [p.id for p in points],
            }

        except Exception as e:
            logger.error(f"❌ 添加文档块失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def search(
        self,
        query: str,
        knowledge_base_id: Optional[int] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索

        Args:
            query: 查询文本
            knowledge_base_id: 知识库 ID（可选，用于过滤）
            top_k: 返回最相似的前 K 个结果
            score_threshold: 相似度阈值（0-1）

        Returns:
            List[Dict]: 搜索结果列表
        """
        if top_k is None:
            top_k = settings.RAG_TOP_K

        try:
            # 获取查询向量
            query_embedding = await self.get_embedding(query)

            # 构建过滤条件
            query_filter = None
            if knowledge_base_id is not None:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="knowledge_base_id",
                            match=MatchValue(value=knowledge_base_id),
                        )
                    ]
                )

            # 执行搜索
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )

            # 解析结果
            results = []
            for hit in search_result:
                results.append({
                    "point_id": hit.id,
                    "document_id": hit.payload.get("document_id"),
                    "chunk_index": hit.payload.get("chunk_index"),
                    "text": hit.payload.get("text"),
                    "score": hit.score,
                    "metadata": hit.payload,
                })

            logger.info(f"🔍 向量搜索完成: {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"❌ 向量搜索失败: {e}")
            return []

    async def delete_document_chunks(self, document_id: int) -> bool:
        """
        删除文档的所有文本块

        Args:
            document_id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 使用过滤条件删除
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )

            logger.info(f"✅ 删除了文档 {document_id} 的所有文本块")
            return True

        except Exception as e:
            logger.error(f"❌ 删除文档块失败: {e}")
            return False

    async def delete_knowledge_base_chunks(self, knowledge_base_id: int) -> bool:
        """
        删除知识库的所有文本块

        Args:
            knowledge_base_id: 知识库 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 使用过滤条件删除
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="knowledge_base_id",
                            match=MatchValue(value=knowledge_base_id),
                        )
                    ]
                ),
            )

            logger.info(f"✅ 删除了知识库 {knowledge_base_id} 的所有文本块")
            return True

        except Exception as e:
            logger.error(f"❌ 删除知识库块失败: {e}")
            return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            Dict: 统计信息
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": collection_info.status.value,
                "optimizer_status": collection_info.optimizer_status,
            }
        except Exception as e:
            logger.error(f"❌ 获取集合统计信息失败: {e}")
            return {}


# 创建全局向量服务实例
vector_service = VectorService()
