"""
向量服务
处理 Milvus 向量数据库和文档向量化
"""

from typing import List, Dict, Any, Optional
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    AnnSearchResult,
)
from zhipuai import ZhipuAI
import numpy as np
import redis
import json
import hashlib

from app.core.config import settings


class VectorService:
    """向量服务类"""

    def __init__(self):
        """初始化向量服务"""
        # Milvus 连接配置
        self.milvus_host = settings.MILVUS_HOST
        self.milvus_port = settings.MILVUS_PORT
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = settings.MILVUS_DIMENSION

        # Zhipu AI Embedding API
        self.embedding_client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

        # Redis 缓存
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

        # 连接 Milvus
        self._connect_milvus()

        # 确保集合存在
        self._ensure_collection()

    def _connect_milvus(self):
        """连接到 Milvus"""
        try:
            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port,
            )
            print(f"✅ 已连接到 Milvus: {self.milvus_host}:{self.milvus_port}")
        except Exception as e:
            print(f"❌ 连接 Milvus 失败: {e}")
            raise

    def _ensure_collection(self):
        """确保向量集合存在"""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            print(f"✅ 向量集合已存在: {self.collection_name}")
        else:
            # 创建集合 Schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="knowledge_base_id", dtype=DataType.INT64),
                FieldSchema(name="document_id", dtype=DataType.INT64),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            ]

            schema = CollectionSchema(fields, description="知识库文档向量")

            # 创建集合
            self.collection = Collection(
                name=self.collection_name,
                schema=schema,
            )

            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {
                    "M": 16,
                    "efConstruction": 256,
                },
            }
            self.collection.create_index(
                field_name="embedding",
                index_params=index_params,
            )
            self.collection.load()

            print(f"✅ 创建向量集合: {self.collection_name}")

    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示

        Args:
            text: 输入文本

        Returns:
            List[float]: 向量表示
        """
        # 生成缓存键
        cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"

        # 尝试从缓存获取
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        try:
            # 调用 Zhipu AI Embedding API
            response = self.embedding_client.embeddings.create(
                model="embedding-2",
                input=text,
            )

            embedding = response.data[0].embedding

            # 缓存结果
            self.redis_client.setex(
                cache_key,
                settings.RAG_REDIS_CACHE_TTL,
                json.dumps(embedding),
            )

            return embedding

        except Exception as e:
            print(f"❌ 获取 Embedding 失败: {e}")
            raise

    def chunk_text(self, text: str) -> List[str]:
        """
        将文本分割成多个块

        Args:
            text: 输入文本

        Returns:
            List[str]: 文本块列表
        """
        if not text:
            return []

        chunks = []
        chunk_size = settings.RAG_CHUNK_SIZE
        overlap = settings.RAG_CHUNK_OVERLAP

        # 按字符分割
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i : i + chunk_size]
            if chunk:
                chunks.append(chunk)

        return chunks

    async def add_document_chunks(
        self,
        knowledge_base_id: int,
        document_id: int,
        text: str,
    ) -> Dict[str, Any]:
        """
        添加文档的文本块到向量数据库

        Args:
            knowledge_base_id: 知识库 ID
            document_id: 文档 ID
            text: 文档内容

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

            # 为每个块生成向量
            embeddings = []
            for chunk in chunks:
                embedding = await self.get_embedding(chunk)
                embeddings.append(embedding)

            # 准备插入数据
            data = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                data.append([
                    knowledge_base_id,
                    document_id,
                    idx,
                    chunk,
                    embedding,
                ])

            # 插入到 Milvus
            insert_result = self.collection.insert(data)
            self.collection.flush()

            print(f"✅ 添加了 {len(chunks)} 个文档块到向量数据库")

            return {
                "success": True,
                "chunk_count": len(chunks),
                "insert_ids": insert_result.primary_keys,
            }

        except Exception as e:
            print(f"❌ 添加文档块失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def search(
        self,
        query: str,
        knowledge_base_id: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索

        Args:
            query: 查询文本
            knowledge_base_id: 知识库 ID（可选，用于过滤）
            top_k: 返回最相似的前 K 个结果

        Returns:
            List[Dict]: 搜索结果列表
        """
        if top_k is None:
            top_k = settings.RAG_TOP_K

        try:
            # 获取查询向量
            query_embedding = await self.get_embedding(query)

            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64},
            }

            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=f"knowledge_base_id == {knowledge_base_id}" if knowledge_base_id else None,
                output_fields=["knowledge_base_id", "document_id", "chunk_index", "text"],
            )

            # 解析结果
            search_results = []
            for hit in results[0]:
                search_results.append({
                    "document_id": hit.entity.get("document_id"),
                    "chunk_index": hit.entity.get("chunk_index"),
                    "text": hit.entity.get("text"),
                    "score": hit.score,
                })

            return search_results

        except Exception as e:
            print(f"❌ 向量搜索失败: {e}")
            return []

    async def delete_document_chunks(
        self,
        document_id: int,
    ) -> bool:
        """
        删除文档的所有文本块

        Args:
            document_id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取文档的所有块 ID
            results = self.collection.query(
                expr=f"document_id == {document_id}",
                output_fields=["id"],
            )

            if not results:
                return True

            # 删除所有块
            ids = [item["id"] for item in results]
            self.collection.delete(expr=f"id in {ids}")
            self.collection.flush()

            print(f"✅ 删除了文档 {document_id} 的 {len(ids)} 个文本块")

            return True

        except Exception as e:
            print(f"❌ 删除文档块失败: {e}")
            return False

    async def delete_knowledge_base_chunks(
        self,
        knowledge_base_id: int,
    ) -> bool:
        """
        删除知识库的所有文本块

        Args:
            knowledge_base_id: 知识库 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 获取知识库的所有块 ID
            results = self.collection.query(
                expr=f"knowledge_base_id == {knowledge_base_id}",
                output_fields=["id"],
            )

            if not results:
                return True

            # 删除所有块
            ids = [item["id"] for item in results]
            self.collection.delete(expr=f"id in {ids}")
            self.collection.flush()

            print(f"✅ 删除了知识库 {knowledge_base_id} 的 {len(ids)} 个文本块")

            return True

        except Exception as e:
            print(f"❌ 删除知识库块失败: {e}")
            return False


# 创建全局向量服务实例
vector_service = VectorService()
