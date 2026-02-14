"""
知识库模型
"""

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KnowledgeBase(Base):
    """知识库表"""

    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-ada-002")
    metadata: Mapped[dict | None] = mapped_column(default=None)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="knowledge_bases")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name={self.name})>"
