"""
RAG 系统测试
测试向量服务、文档解析和 RAG 查询功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import tempfile
from pathlib import Path

from app.services.vector_service import VectorService
from app.services.document_parser import DocumentParserService
from app.services.rag_service import RAGService


class TestVectorService:
    """向量服务测试"""

    @pytest.fixture
    def vector_service(self):
        """创建向量服务实例"""
        with patch('app.services.vector_service.QdrantClient') as mock_client:
            service = VectorService()
            service.client = mock_client.return_value
            return service

    def test_chunk_text_basic(self, vector_service):
        """测试基本文本分块"""
        text = "这是一个测试文本。" * 100  # 创建较长文本
        chunks = vector_service.chunk_text(text, chunk_size=100, overlap=10)

        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('index' in chunk for chunk in chunks)
        assert all('length' in chunk for chunk in chunks)

    def test_chunk_text_empty(self, vector_service):
        """测试空文本分块"""
        chunks = vector_service.chunk_text("")
        assert chunks == []

        chunks = vector_service.chunk_text(None)
        assert chunks == []

    def test_chunk_text_with_newlines(self, vector_service):
        """测试包含换行符的文本分块"""
        text = "第一行\n第二行\n第三行\n" * 50
        chunks = vector_service.chunk_text(text, chunk_size=100, overlap=20)

        assert len(chunks) > 0
        # 检查块是否包含完整行
        for chunk in chunks:
            assert 'text' in chunk
            assert len(chunk['text']) > 0

    @pytest.mark.asyncio
    async def test_get_embedding(self, vector_service):
        """测试获取文本向量"""
        with patch.object(vector_service, 'get_embedding', new_callable=AsyncMock) as mock_get_embedding:
            mock_get_embedding.return_value = [0.1] * 1024

            embedding = await vector_service.get_embedding("测试文本")

            assert isinstance(embedding, list)
            assert len(embedding) == 1024

    @pytest.mark.asyncio
    async def test_search(self, vector_service):
        """测试向量搜索"""
        with patch.object(vector_service.client, 'search') as mock_search:
            mock_search.return_value = [
                Mock(
                    id="test-id-1",
                    score=0.9,
                    payload={
                        "document_id": 1,
                        "chunk_index": 0,
                        "text": "测试文本",
                    }
                )
            ]

            results = await vector_service.search(
                query="测试查询",
                knowledge_base_id=1,
                top_k=5,
            )

            assert len(results) > 0
            assert results[0]['document_id'] == 1
            assert results[0]['score'] == 0.9


class TestDocumentParser:
    """文档解析器测试"""

    @pytest.fixture
    def parser_service(self):
        """创建文档解析服务实例"""
        return DocumentParserService()

    @pytest.mark.asyncio
    async def test_parse_txt_file(self, parser_service):
        """测试解析 TXT 文件"""
        # 创建临时 TXT 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("这是一个测试文本文件。\n第二行内容。")
            temp_path = f.name

        try:
            result = await parser_service.parse_file(temp_path)

            assert result['success']
            assert 'text' in result
            assert '这是一个测试文本文件' in result['text']
            assert result['metadata']['file_type'] == 'txt'
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_parse_markdown_file(self, parser_service):
        """测试解析 Markdown 文件"""
        # 创建临时 Markdown 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("# 标题\n\n这是内容。\n\n## 副标题\n\n更多内容。")
            temp_path = f.name

        try:
            result = await parser_service.parse_file(temp_path)

            assert result['success']
            assert 'text' in result
            assert '# 标题' in result['text']
            assert result['metadata']['file_type'] == 'markdown'
            assert result['metadata']['heading_count'] > 0
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_parse_unsupported_format(self, parser_service):
        """测试不支持的文件格式"""
        # 创建临时不支持的文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False) as f:
            f.write("test")
            temp_path = f.name

        try:
            result = await parser_service.parse_file(temp_path)

            assert not result['success']
            assert 'error' in result
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_parse_content_txt(self, parser_service):
        """测试解析 TXT 内容"""
        content = "这是纯文本内容。"
        result = await parser_service.parse_content(content, 'txt')

        assert result['success']
        assert result['text'] == content
        assert result['metadata']['file_type'] == 'txt'


class TestRAGService:
    """RAG 服务测试"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def rag_service(self, mock_db):
        """创建 RAG 服务实例"""
        return RAGService(mock_db)

    def test_extract_keywords(self, rag_service):
        """测试关键词提取"""
        query = "如何使用 Python 进行数据分析"
        keywords = rag_service._extract_keywords(query)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 5

    def test_build_context(self, rag_service, mock_db):
        """测试构建上下文"""
        # 模拟数据库查询
        mock_document = Mock()
        mock_document.title = "测试文档"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document

        search_results = [
            {
                'text': '这是第一个文档片段。',
                'score': 0.9,
                'document_id': 1,
            },
            {
                'text': '这是第二个文档片段。',
                'score': 0.8,
                'document_id': 2,
            }
        ]

        context = rag_service._build_context(search_results)

        assert isinstance(context, str)
        assert '第一个文档片段' in context
        assert '第二个文档片段' in context
        assert '来源' in context

    def test_build_context_empty(self, rag_service):
        """测试空搜索结果的上下文构建"""
        context = rag_service._build_context([])
        assert context == ""

    @pytest.mark.asyncio
    async def test_query(self, rag_service):
        """测试 RAG 查询"""
        with patch.object(rag_service, '_vector_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [
                {
                    'text': '相关文档内容',
                    'score': 0.9,
                    'document_id': 1,
                }
            ]

            with patch.object(rag_service, '_generate_answer', new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = {
                    'success': True,
                    'content': '这是生成的回答。',
                    'tokens': 100,
                    'cost': 0.001,
                }

                # 模拟数据库查询
                mock_document = Mock()
                mock_document.id = 1
                mock_document.title = "测试文档"
                rag_service.db.query.return_value.filter.return_value.first.return_value = mock_document

                result = await rag_service.query(
                    question="测试问题",
                    knowledge_base_id=1,
                    top_k=5,
                )

                assert result['success']
                assert 'answer' in result
                assert result['rag_enabled']


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_document_upload_and_parse_flow(self):
        """测试文档上传和解析流程"""
        # 模拟完整流程
        parser_service = DocumentParserService()

        # 创建测试文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            test_content = "这是测试文档的内容。\n" * 10
            f.write(test_content)
            temp_path = f.name

        try:
            # 解析文档
            parse_result = await parser_service.parse_file(temp_path)
            assert parse_result['success']

            # 模拟分块
            with patch('app.services.vector_service.VectorService') as MockVectorService:
                mock_service = MockVectorService.return_value
                mock_service.chunk_text.return_value = [
                    {'text': 'chunk1', 'index': 0, 'length': 6},
                    {'text': 'chunk2', 'index': 1, 'length': 6},
                ]

                chunks = mock_service.chunk_text(parse_result['text'])
                assert len(chunks) == 2

        finally:
            Path(temp_path).unlink()


# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--cov=app/services',
        '--cov-report=term-missing',
    ])


if __name__ == '__main__':
    run_tests()
