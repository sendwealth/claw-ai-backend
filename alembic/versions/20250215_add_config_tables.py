"""add config management tables with history and audit support

Revision ID: add_config_tables
Revises: add_indexes
Create Date: 2025-02-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_config_tables'
down_revision: Union[str, None] = 'add_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    升级：创建配置管理相关的表

    包含：
    - configs: 配置表，存储所有配置项
    - config_history: 配置历史表，记录所有配置变更

    功能特性：
    - 支持敏感信息标记和公开访问控制
    - 版本控制，支持配置回滚
    - 完整的审计日志
    - 索引优化常见查询场景
    """

    # 创建 configs 表
    op.create_table(
        'configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 为 configs 表创建索引
    op.create_index('ix_configs_key', 'configs', ['key'], unique=True)
    op.create_index('idx_config_key_public', 'configs', ['key', 'is_public'], unique=False)

    # 创建 config_history 表
    op.create_table(
        'config_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['config_id'], ['configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 为 config_history 表创建索引
    op.create_index('idx_config_history_config_id', 'config_history', ['config_id'], unique=False)
    op.create_index('idx_config_history_key', 'config_history', ['key'], unique=False)
    op.create_index('idx_config_history_changed_at', 'config_history', ['changed_at'], unique=False)


def downgrade() -> None:
    """
    降级：删除配置管理相关的表

    按照依赖关系逆序删除
    """

    # 删除 config_history 表及其索引
    op.drop_index('idx_config_history_changed_at', table_name='config_history')
    op.drop_index('idx_config_history_key', table_name='config_history')
    op.drop_index('idx_config_history_config_id', table_name='config_history')
    op.drop_table('config_history')

    # 删除 configs 表及其索引
    op.drop_index('idx_config_key_public', table_name='configs')
    op.drop_index('ix_configs_key', table_name='configs')
    op.drop_table('configs')
