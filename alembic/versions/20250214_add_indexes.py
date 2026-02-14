"""add timestamp indexes for conversations, messages, documents tables

Revision ID: add_indexes
Revises:
Create Date: 2025-02-14 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_indexes'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    升级：为表的时间戳字段添加索引

    索引策略：
    - conversations.created_at: 用于按创建时间排序和查询对话列表
    - messages.created_at: 用于按时间排序获取消息历史
    - documents.created_at: 用于按时间排序获取文档列表

    组合索引优化：
    - (conversations.user_id, conversations.created_at): 用于获取用户的对话列表并按时间排序
    - (messages.conversation_id, messages.created_at): 用于获取对话的消息历史并按时间排序
    - (documents.knowledge_base_id, documents.created_at): 用于获取知识库的文档列表并按时间排序
    """
    # 为 conversations 表添加 created_at 索引
    op.create_index(
        'ix_conversations_created_at',
        'conversations',
        ['created_at'],
        unique=False
    )

    # 为 messages 表添加 created_at 索引
    op.create_index(
        'ix_messages_created_at',
        'messages',
        ['created_at'],
        unique=False
    )

    # 为 documents 表添加 created_at 索引
    op.create_index(
        'ix_documents_created_at',
        'documents',
        ['created_at'],
        unique=False
    )

    # 添加组合索引以优化常见查询模式

    # conversations: user_id + created_at (获取用户对话列表并按时间排序)
    op.create_index(
        'idx_conversations_user_created',
        'conversations',
        ['user_id', 'created_at'],
        unique=False
    )

    # messages: conversation_id + created_at (获取对话消息历史)
    op.create_index(
        'idx_messages_conversation_created',
        'messages',
        ['conversation_id', 'created_at'],
        unique=False
    )

    # documents: knowledge_base_id + created_at (获取知识库文档列表)
    op.create_index(
        'idx_documents_kb_created',
        'documents',
        ['knowledge_base_id', 'created_at'],
        unique=False
    )


def downgrade() -> None:
    """
    降级：移除所有添加的索引

    按照依赖关系逆序删除索引
    """
    # 删除组合索引
    op.drop_index('idx_documents_kb_created', table_name='documents')
    op.drop_index('idx_messages_conversation_created', table_name='messages')
    op.drop_index('idx_conversations_user_created', table_name='conversations')

    # 删除单列索引
    op.drop_index('ix_documents_created_at', table_name='documents')
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_conversations_created_at', table_name='conversations')
