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
    DEBUG: bool = True

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/claw_ai"
    TEST_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/claw_ai_test"

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT 认证配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Zhipu AI 配置
    ZHIPUAI_API_KEY: str = ""
    ZHIPUAI_MODEL: str = "glm-4"

    # Pinecone 向量数据库配置
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX: str = "claw-ai"

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局设置实例
settings = Settings()
