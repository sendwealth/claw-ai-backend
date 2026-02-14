"""
RAG 服务（检索增强生成）
实现向量检索 + 上下文增强 + 生成回答的完整流程
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.vector_service import vector_service
from app.services.ai_service import ai_service
from app.models import Document, KnowledgeBase


class RAGService:
    """RAG 服务类"""

    def __init__(self, db: Session):
        """初始化服务"""
        self.db = db
        self.vector_service = vector_service
        self.ai_service = ai_service

    def _extract_keywords(self, query: str) -> List[str]:
        """
        从查询中提取关键词（简单实现）

        Args:
            query: 用户查询

        Returns:
            List[str]: 关键词列表
        """
        # 简单实现：按空格和标点分割
        import re

        # 移除标点符号
        query_clean = re.sub(r'[^\w\s]', ' ', query)
        # 分割并过滤空字符串
        keywords = [k for k in query_clean.split() if len(k) > 1]

        return keywords[:5]  # 返回前 5 个关键词

    async def _vector_search(
        self,
        query: str,
        knowledge_base_id: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            query: 用户查询
            knowledge_base_id: 知识库 ID（可选）
            top_k: 返回前 K 个结果

        Returns:
            List[Dict]: 检索结果
        """
        return await self.vector_service.search(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
        )

    def _build_context(
        self,
        search_results: List[Dict[str, Any]],
        max_context_length: int = 3000,
    ) -> str:
        """
        构建上下文

        Args:
            search_results: 向量搜索结果
            max_context_length: 最大上下文长度（字符数）

        Returns:
            str: 构建的上下文字符串
        """
        if not search_results:
            return ""

        context_parts = []
        current_length = 0

        for idx, result in enumerate(search_results):
            text = result["text"]
            score = result["score"]
            document_id = result["document_id"]

            # 获取文档标题
            document = self.db.query(Document).filter(Document.id == document_id).first()
            title = document.title if document else "未知文档"

            # 构建上下文片段
            context_part = f"\n【来源 {idx + 1}】{title} (相似度: {score:.3f})\n{text}\n"

            # 检查长度
            if current_length + len(context_part) > max_context_length:
                break

            context_parts.append(context_part)
            current_length += len(context_part)

        return "".join(context_parts)

    async def _generate_answer(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        增强生成

        Args:
            query: 用户查询
            context: 检索到的上下文
            system_prompt: 系统提示词（可选）

        Returns:
            Dict: 生成结果
        """
        # 默认系统提示词
        if system_prompt is None:
            system_prompt = """你是一个智能助手，擅长基于提供的知识库内容回答用户问题。

请遵循以下原则：
1. 优先使用提供的上下文信息回答问题
2. 如果上下文中没有相关信息，请诚实告知用户
3. 引用具体的来源（文档标题）
4. 回答要准确、简洁、有逻辑
5. 如果问题涉及多个方面，请分点回答"""

        # 构建用户消息
        user_message = f"""参考信息：
{context}

问题：{query}

请根据参考信息回答上述问题。"""

        # 调用 AI 生成
        ai_response = await self.ai_service.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            temperature=0.7,
        )

        return ai_response

    async def query(
        self,
        question: str,
        knowledge_base_id: Optional[int] = None,
        top_k: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        完整的 RAG 查询流程

        Args:
            question: 用户问题
            knowledge_base_id: 知识库 ID（可选，不指定则搜索全部）
            top_k: 返回最相似的前 K 个文档片段
            system_prompt: 自定义系统提示词

        Returns:
            Dict: RAG 查询结果，包含：
                - success: 是否成功
                - answer: 生成的回答
                - sources: 引用的来源文档列表
                - context: 使用的上下文
                - tokens: Token 消耗
                - cost: 成本
        """
        try:
            # Step 1: 提取关键词（可选，用于调试）
            keywords = self._extract_keywords(question)
            print(f"🔍 提取的关键词: {keywords}")

            # Step 2: 向量检索
            print(f"🔍 开始向量检索...")
            search_results = await self._vector_search(
                query=question,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
            )

            print(f"🔍 检索到 {len(search_results)} 个相关文档片段")

            if not search_results:
                # 如果没有检索结果，直接生成回答（不使用 RAG）
                print("⚠️ 未检索到相关文档，直接生成回答")
                ai_response = await self.ai_service.chat(
                    messages=[{"role": "user", "content": question}],
                    system_prompt="你是一个智能助手。请基于你的知识回答用户问题。",
                )

                return {
                    "success": ai_response["success"],
                    "answer": ai_response["content"] if ai_response["success"] else "抱歉，我无法回答这个问题。",
                    "sources": [],
                    "context": "",
                    "tokens": ai_response.get("tokens"),
                    "cost": ai_response.get("cost"),
                    "rag_enabled": False,
                }

            # Step 3: 构建上下文
            print("🔍 构建上下文...")
            context = self._build_context(search_results)

            # Step 4: 增强生成
            print("🔍 增强生成中...")
            ai_response = await self._generate_answer(
                query=question,
                context=context,
                system_prompt=system_prompt,
            )

            # Step 5: 构建返回结果
            if ai_response["success"]:
                # 提取来源信息
                sources = []
                seen_docs = set()

                for result in search_results:
                    doc_id = result["document_id"]
                    if doc_id not in seen_docs:
                        document = self.db.query(Document).filter(Document.id == doc_id).first()
                        if document:
                            sources.append({
                                "document_id": doc_id,
                                "title": document.title,
                                "score": result["score"],
                            })
                            seen_docs.add(doc_id)

                return {
                    "success": True,
                    "answer": ai_response["content"],
                    "sources": sources,
                    "context": context,
                    "tokens": ai_response["tokens"],
                    "cost": ai_response["cost"],
                    "rag_enabled": True,
                    "search_results_count": len(search_results),
                }
            else:
                return {
                    "success": False,
                    "error": ai_response["error"],
                    "answer": "抱歉，生成回答时出现错误。",
                }

        except Exception as e:
            print(f"❌ RAG 查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，系统出现错误，请稍后再试。",
            }

    async def index_document(
        self,
        knowledge_base_id: int,
        document_id: int,
        text: str,
    ) -> Dict[str, Any]:
        """
        索引文档到向量数据库

        Args:
            knowledge_base_id: 知识库 ID
            document_id: 文档 ID
            text: 文档内容

        Returns:
            Dict: 索引结果
        """
        return await self.vector_service.add_document_chunks(
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            text=text,
        )

    async def delete_document_index(self, document_id: int) -> bool:
        """
        删除文档的向量索引

        Args:
            document_id: 文档 ID

        Returns:
            bool: 是否成功
        """
        return await self.vector_service.delete_document_chunks(document_id)

    async def delete_knowledge_base_index(self, knowledge_base_id: int) -> bool:
        """
        删除知识库的向量索引

        Args:
            knowledge_base_id: 知识库 ID

        Returns:
            bool: 是否成功
        """
        return await self.vector_service.delete_knowledge_base_chunks(knowledge_base_id)


# 工厂函数：创建 RAG 服务实例
def create_rag_service(db: Session) -> RAGService:
    """创建 RAG 服务实例"""
    return RAGService(db)
