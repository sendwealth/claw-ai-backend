"""
文档模型
"""

from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Document(Base):
    """文档表"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(500))  # 原始文件 URL
    file_type: Mapped[str | None] = mapped_column(String(50))  # 文件类型（pdf/txt/md 等）
    file_size: Mapped[int | None] = mapped_column(Integer)  # 文件大小（字节）
    chunk_count: Mapped[int] = mapped_column(default=0)  # 分片数量
    embedding_vector: Mapped[str | None] = mapped_column(String(500))  # 向量 ID（如 Pinecone vector ID）
    metadata: Mapped[dict | None] = mapped_column(default=None)

    # 关系
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title})>"
