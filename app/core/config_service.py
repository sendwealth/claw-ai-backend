"""
动态配置服务
支持从网络 API 拉取配置
"""

import os
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings

# 配置中心 URL（环境变量配置）
CONFIG_CENTER_URL = os.getenv("CONFIG_CENTER_URL", None)

# 本地配置缓存
_config_cache: Dict[str, Any] = {}


async def load_config_from_network() -> bool:
    """
    从配置中心加载配置

    Returns:
        bool: 是否加载成功
    """
    if not CONFIG_CENTER_URL:
        print("⚠️  配置中心 URL 未配置，使用本地环境变量")
        return False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(CONFIG_CENTER_URL)
            response.raise_for_status()

            # 更新配置缓存
            global _config_cache
            _config_cache = response.json()

            print("✅ 从配置中心加载配置成功")
            return True

    except Exception as e:
        print(f"❌ 从配置中心加载配置失败: {e}")
        print("⚠️  使用本地环境变量作为后备")
        return False


async def reload_config() -> bool:
    """
    重新加载配置

    Returns:
        bool: 是否加载成功
    """
    # 优先从网络加载
    success = await load_config_from_network()

    if not success:
        # 使用本地环境变量
        global _config_cache
        _config_cache = {
            "DATABASE_URL": os.getenv("DATABASE_URL", settings.DATABASE_URL),
            "REDIS_URL": os.getenv("REDIS_URL", settings.REDIS_URL),
            "ZHIPUAI_API_KEY": os.getenv("ZHIPUAI_API_KEY", settings.ZHIPUAI_API_KEY),
            "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY", settings.PINECONE_API_KEY),
            "SECRET_KEY": os.getenv("SECRET_KEY", settings.SECRET_KEY),
            # ... 其他配置
        }

    return True


def get_config(key: str, default: Optional[str] = None) -> str:
    """
    获取配置值

    Args:
        key: 配置键
        default: 默认值

    Returns:
        str: 配置值
    """
    # 优先从缓存读取
    if _config_cache and key in _config_cache:
        return _config_cache[key]

    # 后备：从环境变量读取
    return os.getenv(key, default or "")


def set_config(key: str, value: str) -> bool:
    """
    设置配置值（仅缓存）

    Args:
        key: 配置键
        value: 配置值

    Returns:
        bool: 是否设置成功
    """
    global _config_cache
    _config_cache[key] = value
    return True


def get_all_config() -> Dict[str, Any]:
    """
    获取所有配置

    Returns:
        Dict[str, Any]: 所有配置
    """
    return _config_cache.copy()


# 启动时自动加载配置
async def init_config():
    """初始化配置"""
    await reload_config()
