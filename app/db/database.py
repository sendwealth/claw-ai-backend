"""
数据库连接池配置和引擎管理

提供优化的 PostgreSQL 连接池配置，包括：
- 连接池大小配置
- 连接回收策略
- 连接健康检查
- 查询性能监控
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
import time
import logging

from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)


# PostgreSQL 连接池配置
# 参考：https://docs.sqlalchemy.org/en/20/core/pooling.html
engine = create_engine(
    settings.DATABASE_URL,
    # 连接池配置
    poolclass=QueuePool,
    pool_size=10,              # 连接池大小（保持的连接数）
    max_overflow=20,           # 最大溢出连接数（总连接数 = pool_size + max_overflow）
    pool_timeout=30,           # 获取连接超时时间（秒）
    pool_recycle=3600,         # 连接回收时间（秒），防止连接长时间使用后失效
    pool_pre_ping=True,        # 连接前检查连接有效性（推荐开启）

    # 连接行为
    echo=settings.DEBUG,      # 开发环境打印 SQL 日志
    echo_pool=False,           # 不打印连接池日志
    future=True,               # 使用 SQLAlchemy 2.0 风格

    # 性能优化
    connect_args={
        "connect_timeout": 10,     # 连接超时
        "options": "-c timezone=utc"  # 设置时区为 UTC
    } if "postgresql" in settings.DATABASE_URL else {}
)


# 查询性能监控
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    在执行 SQL 之前记录时间戳

    用于查询性能监控
    """
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    在执行 SQL 之后记录执行时间

    用于查询性能监控和慢查询识别
    """
    total = time.time() - context._query_start_time

    # 记录慢查询（执行时间超过 1 秒）
    if total > 1.0:
        logger.warning(
            f"Slow Query: {total:.2f}s\n"
            f"Statement: {statement[:200]}...\n"
            f"Parameters: {parameters}"
        )
    elif settings.DEBUG:
        # 开发环境记录所有查询
        logger.debug(f"Query executed in {total:.4f}s")


# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """
    获取数据库会话

    用于 FastAPI 依赖注入

    使用示例：
        from fastapi import Depends
        from app.db.database import get_db
        from sqlalchemy.orm import Session

        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_pool_status():
    """
    获取连接池状态信息

    用于监控和诊断连接池健康状况

    返回:
        dict: 包含连接池统计信息的字典
    """
    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),          # 已借出的连接数
        "overflow": pool.overflow(),               # 溢出连接数
        "checked_in": pool.checkedin(),            # 已归还的连接数
        "max_overflow": pool._max_overflow,        # 最大溢出连接数配置
        "pool_timeout": pool._timeout,             # 获取连接超时配置
        "status": "healthy" if pool.checkedout() < (pool.size() + pool._max_overflow) else "under_pressure"
    }


def close_all_connections():
    """
    关闭所有数据库连接

    用于应用关闭时清理资源，或需要重置连接池时
    """
    engine.dispose()
    logger.info("All database connections closed")


# 导出以便其他模块使用
__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_pool_status",
    "close_all_connections"
]
