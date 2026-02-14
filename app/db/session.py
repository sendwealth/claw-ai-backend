"""
数据库会话管理

已迁移至 database.py 以提供更完整的连接池配置和性能监控

该模块保留用于向后兼容，建议使用 database.py 模块
"""

from app.db.database import engine, SessionLocal, get_db

# 重新导出以保持向后兼容
__all__ = ["engine", "SessionLocal", "get_db"]
