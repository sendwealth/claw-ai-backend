"""
应用配置
使用 pydantic-settings 管理配置
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用设置"""

    # 应用配置
    APP_NAME: str = "CLAW.AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False  # 安全：生产环境默认关闭调试模式

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置 - 安全：必须从环境变量获取
    DATABASE_URL: str = ""
    TEST_DATABASE_URL: str = ""

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery 配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # JWT 认证配置 - 安全：SECRET_KEY 必须从环境变量获取
    SECRET_KEY: str = ""  # 必须设置！生产环境必须提供
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 安全：缩短为 30 分钟
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Zhipu AI 配置
    ZHIPUAI_API_KEY: str = ""
    ZHIPUAI_MODEL: str = "glm-4"

    # Qdrant 向量数据库配置
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""  # 可选，如果 Qdrant 启用了认证
    QDRANT_COLLECTION_NAME: str = "knowledge_vectors"
    QDRANT_VECTOR_SIZE: int = 1024  # Zhipu AI embedding 维度
    QDRANT_DISTANCE: str = "Cosine"  # 距离度量：Cosine, Euclid, Dot

    # Milvus 向量数据库配置（保留用于兼容）
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "knowledge_vectors"
    MILVUS_DIMENSION: int = 1024  # Zhipu AI embedding 维度

    # Pinecone 向量数据库配置
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX: str = "claw-ai"

    # RAG 配置
    RAG_TOP_K: int = 5  # 检索最相似的 K 个文档片段
    RAG_CHUNK_SIZE: int = 500  # 文档分块大小（字符数）
    RAG_CHUNK_OVERLAP: int = 50  # 分块重叠大小
    RAG_REDIS_CACHE_TTL: int = 3600  # Redis 缓存时间（秒）
    RAG_ENABLE_CACHE: bool = True  # 是否启用向量缓存

    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://openspark.online"]

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "uploads"

    # 安全配置
    ALLOWED_HOSTS: List[str] = ["openspark.online", "www.openspark.online"]

    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()
