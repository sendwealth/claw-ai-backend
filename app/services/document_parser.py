"""
文档解析服务
支持 PDF、TXT、Markdown 等格式的文档解析
"""

from typing import Dict, Any, Optional
from pathlib import Path
import re
from abc import ABC, abstractmethod

from app.core.logger import logger


class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            Dict: 包含 text, metadata 等字段
        """
        pass


class TextParser(DocumentParser):
    """TXT 文本文件解析器"""

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """解析 TXT 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            return {
                "success": True,
                "text": text,
                "metadata": {
                    "file_type": "txt",
                    "char_count": len(text),
                    "line_count": text.count('\n') + 1,
                },
            }
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    text = f.read()

                return {
                    "success": True,
                    "text": text,
                    "metadata": {
                        "file_type": "txt",
                        "char_count": len(text),
                        "line_count": text.count('\n') + 1,
                        "encoding": "gbk",
                    },
                }
            except Exception as e:
                logger.error(f"❌ TXT 文件解析失败: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }
        except Exception as e:
            logger.error(f"❌ TXT 文件解析失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class MarkdownParser(DocumentParser):
    """Markdown 文件解析器"""

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """解析 Markdown 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            # 提取标题结构
            headings = []
            for line in text.split('\n'):
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    title = line.lstrip('#').strip()
                    headings.append({
                        "level": level,
                        "title": title,
                    })

            # 提取代码块
            code_blocks = []
            code_pattern = r'```[\s\S]*?```'
            for match in re.finditer(code_pattern, text):
                code_blocks.append(match.group())

            # 提取链接
            links = []
            link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
            for match in re.finditer(link_pattern, text):
                links.append({
                    "text": match.group(1),
                    "url": match.group(2),
                })

            return {
                "success": True,
                "text": text,
                "metadata": {
                    "file_type": "markdown",
                    "char_count": len(text),
                    "line_count": text.count('\n') + 1,
                    "heading_count": len(headings),
                    "headings": headings[:10],  # 只保留前 10 个标题
                    "code_block_count": len(code_blocks),
                    "link_count": len(links),
                },
            }
        except Exception as e:
            logger.error(f"❌ Markdown 文件解析失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class PDFParser(DocumentParser):
    """PDF 文件解析器"""

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """解析 PDF 文件"""
        try:
            # 尝试使用 PyMuPDF (fitz)
            try:
                import fitz  # PyMuPDF

                doc = fitz.open(file_path)
                text_parts = []
                page_count = len(doc)

                for page_num in range(page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    text_parts.append(f"[第 {page_num + 1} 页]\n{text}")

                full_text = '\n\n'.join(text_parts)
                doc.close()

                return {
                    "success": True,
                    "text": full_text,
                    "metadata": {
                        "file_type": "pdf",
                        "page_count": page_count,
                        "char_count": len(full_text),
                    },
                }

            except ImportError:
                # 如果没有 PyMuPDF，尝试使用 PyPDF2
                try:
                    from PyPDF2 import PdfReader

                    reader = PdfReader(file_path)
                    text_parts = []
                    page_count = len(reader.pages)

                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text()
                        text_parts.append(f"[第 {page_num + 1} 页]\n{text}")

                    full_text = '\n\n'.join(text_parts)

                    return {
                        "success": True,
                        "text": full_text,
                        "metadata": {
                            "file_type": "pdf",
                            "page_count": page_count,
                            "char_count": len(full_text),
                        },
                    }

                except ImportError:
                    logger.error("❌ 需要安装 PyMuPDF 或 PyPDF2 库来解析 PDF")
                    return {
                        "success": False,
                        "error": "需要安装 PyMuPDF (pip install pymupdf) 或 PyPDF2 (pip install PyPDF2)",
                    }

        except Exception as e:
            logger.error(f"❌ PDF 文件解析失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }


class DocumentParserFactory:
    """文档解析器工厂"""

    def __init__(self):
        self.parsers = {
            ".txt": TextParser(),
            ".md": MarkdownParser(),
            ".markdown": MarkdownParser(),
            ".pdf": PDFParser(),
        }

    def get_parser(self, file_extension: str) -> Optional[DocumentParser]:
        """
        根据文件扩展名获取解析器

        Args:
            file_extension: 文件扩展名（包含点号，如 .txt）

        Returns:
            DocumentParser: 文档解析器
        """
        ext = file_extension.lower()
        return self.parsers.get(ext)

    def supports_format(self, file_extension: str) -> bool:
        """
        检查是否支持该文件格式

        Args:
            file_extension: 文件扩展名

        Returns:
            bool: 是否支持
        """
        return file_extension.lower() in self.parsers

    def get_supported_formats(self) -> list:
        """获取支持的文件格式列表"""
        return list(self.parsers.keys())


class DocumentParserService:
    """文档解析服务"""

    def __init__(self):
        self.factory = DocumentParserFactory()

    async def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析文件

        Args:
            file_path: 文件路径

        Returns:
            Dict: 解析结果
        """
        # 获取文件扩展名
        path = Path(file_path)
        file_extension = path.suffix

        # 检查是否支持
        if not self.factory.supports_format(file_extension):
            return {
                "success": False,
                "error": f"不支持的文件格式: {file_extension}。支持的格式: {', '.join(self.factory.get_supported_formats())}",
            }

        # 获取解析器
        parser = self.factory.get_parser(file_extension)

        # 解析文件
        result = await parser.parse(file_path)

        # 添加文件信息
        if result["success"]:
            result["metadata"]["file_name"] = path.name
            result["metadata"]["file_path"] = str(file_path)

        return result

    async def parse_content(
        self,
        content: str,
        file_type: str,
    ) -> Dict[str, Any]:
        """
        解析文本内容

        Args:
            content: 文本内容
            file_type: 文件类型（txt/md/pdf）

        Returns:
            Dict: 解析结果
        """
        if file_type in ["txt", "text"]:
            return {
                "success": True,
                "text": content,
                "metadata": {
                    "file_type": "txt",
                    "char_count": len(content),
                    "line_count": content.count('\n') + 1,
                },
            }
        elif file_type in ["md", "markdown"]:
            parser = MarkdownParser()
            # 创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name

            try:
                result = await parser.parse(temp_path)
                return result
            finally:
                # 删除临时文件
                Path(temp_path).unlink(missing_ok=True)
        else:
            return {
                "success": False,
                "error": f"不支持的文件类型: {file_type}",
            }


# 创建全局文档解析服务实例
document_parser_service = DocumentParserService()
