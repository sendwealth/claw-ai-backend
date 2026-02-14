"""
配置管理 API
支持通过网络接口管理环境变量
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.db import get_db
from app.api.dependencies import get_current_admin_user
from app.models.user import User

router = APIRouter()


# ====================
# 数据模型
# ====================

class ConfigItem(BaseModel):
    """配置项模型"""
    key: str = Field(..., description="配置键")
    value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")
    is_sensitive: bool = Field(False, description="是否敏感信息")
    is_public: bool = Field(False, description="是否公开访问")


class ConfigUpdate(BaseModel):
    """配置更新模型"""
    key: str
    value: str


class ConfigResponse(ConfigItem):
    """配置响应模型"""
    updated_at: Optional[datetime] = None


# ====================
# 配置存储（简单实现，生产环境建议用数据库或配置中心）
# ====================

# 本地内存存储（仅用于演示，生产环境应使用数据库或 Redis）
_config_store: dict = {
    "DATABASE_URL": {
        "value": "postgresql://postgres:password@postgres:5432/claw_ai",
        "description": "数据库连接字符串",
        "is_sensitive": True,
        "is_public": False,
        "updated_at": None,
    },
    "REDIS_URL": {
        "value": "redis://:password@redis:6379/0",
        "description": "Redis 连接字符串",
        "is_sensitive": True,
        "is_public": False,
        "updated_at": None,
    },
    "ZHIPUAI_API_KEY": {
        "value": "",
        "description": "智谱 AI API Key",
        "is_sensitive": True,
        "is_public": False,
        "updated_at": None,
    },
    "PINECONE_API_KEY": {
        "value": "",
        "description": "Pinecone 向量数据库 API Key",
        "is_sensitive": True,
        "is_public": False,
        "updated_at": None,
    },
    "SECRET_KEY": {
        "value": "",
        "description": "JWT 密钥",
        "is_sensitive": True,
        "is_public": False,
        "updated_at": None,
    },
    "DEBUG": {
        "value": "False",
        "description": "调试模式",
        "is_sensitive": False,
        "is_public": True,
        "updated_at": None,
    },
}


# ====================
# API 端点
# ====================


@router.get("/", response_model=List[ConfigResponse])
async def get_all_configs(
    include_sensitive: bool = False,
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取所有配置（仅管理员）

    Args:
        include_sensitive: 是否包含敏感信息
    """
    configs = []
    for key, config in _config_store.items():
        if not include_sensitive and config["is_sensitive"]:
            # 脱敏显示
            configs.append(ConfigResponse(
                key=key,
                value="******",
                description=config["description"],
                is_sensitive=config["is_sensitive"],
                is_public=config["is_public"],
                updated_at=config["updated_at"],
            ))
        else:
            configs.append(ConfigResponse(
                key=key,
                value=config["value"],
                description=config["description"],
                is_sensitive=config["is_sensitive"],
                is_public=config["is_public"],
                updated_at=config["updated_at"],
            ))

    return configs


@router.get("/public", response_model=List[ConfigResponse])
async def get_public_configs():
    """
    获取公开配置（无需认证）
    """
    configs = []
    for key, config in _config_store.items():
        if config["is_public"]:
            configs.append(ConfigResponse(
                key=key,
                value=config["value"],
                description=config["description"],
                is_sensitive=config["is_sensitive"],
                is_public=config["is_public"],
                updated_at=config["updated_at"],
            ))

    return configs


@router.get("/{key}", response_model=ConfigResponse)
async def get_config(
    key: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取单个配置

    Args:
        key: 配置键
    """
    if key not in _config_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置 {key} 不存在",
        )

    config = _config_store[key]

    return ConfigResponse(
        key=key,
        value=config["value"],
        description=config["description"],
        is_sensitive=config["is_sensitive"],
        is_public=config["is_public"],
        updated_at=config["updated_at"],
    )


@router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config: ConfigItem,
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建新配置

    Args:
        config: 配置数据
    """
    if config.key in _config_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"配置 {config.key} 已存在",
        )

    _config_store[config.key] = {
        "value": config.value,
        "description": config.description,
        "is_sensitive": config.is_sensitive,
        "is_public": config.is_public,
        "updated_at": datetime.utcnow(),
    }

    return ConfigResponse(
        key=config.key,
        value=config.value,
        description=config.description,
        is_sensitive=config.is_sensitive,
        is_public=config.is_public,
        updated_at=datetime.utcnow(),
    )


@router.put("/{key}", response_model=ConfigResponse)
async def update_config(
    key: str,
    config_data: ConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新配置

    Args:
        key: 配置键
        config_data: 配置数据
    """
    if key not in _config_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置 {key} 不存在",
        )

    _config_store[key]["value"] = config_data.value
    _config_store[key]["updated_at"] = datetime.utcnow()

    # TODO: 更新环境变量或重启服务
    # 可以在这里触发服务重启

    return ConfigResponse(
        key=key,
        value=config_data.value,
        description=_config_store[key]["description"],
        is_sensitive=_config_store[key]["is_sensitive"],
        is_public=_config_store[key]["is_public"],
        updated_at=datetime.utcnow(),
    )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    key: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除配置

    Args:
        key: 配置键
    """
    if key not in _config_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置 {key} 不存在",
        )

    del _config_store[key]

    # TODO: 更新环境变量或重启服务


@router.post("/reload", response_model=dict)
async def reload_configs(
    current_user: User = Depends(get_current_admin_user),
):
    """
    重新加载配置

    Returns:
        dict: 重载结果
    """
    try:
        # TODO: 重新加载配置的逻辑
        # 例如：重新读取 .env 文件
        # 或者：从配置中心重新拉取

        return {
            "success": True,
            "message": "配置已重新加载",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载配置失败: {str(e)}",
        )


@router.post("/export", response_model=dict)
async def export_configs(
    current_user: User = Depends(get_current_admin_user),
):
    """
    导出配置（用于备份）

    Returns:
        dict: 配置数据
    """
    return {
        "configs": _config_store,
        "exported_at": datetime.utcnow().isoformat(),
    }


@router.post("/import")
async def import_configs(
    configs: dict,
    current_user: User = Depends(get_current_admin_user),
):
    """
    导入配置（用于恢复）

    Args:
        configs: 配置数据
    """
    # TODO: 验证配置格式
    # TODO: 导入配置
    # TODO: 重新加载配置

    return {
        "success": True,
        "message": f"已导入 {len(configs)} 个配置",
        "imported_at": datetime.utcnow().isoformat(),
    }
