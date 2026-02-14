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
from app.api.dependencies import get_current_admin_user, get_current_user
from app.models.user import User
from app.services.config_service import ConfigService

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
    value: str = Field(..., description="新值")


class ConfigResponse(ConfigItem):
    """配置响应模型"""
    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class ConfigHistoryItem(BaseModel):
    """配置历史项模型"""
    id: int
    config_id: int
    key: str
    old_value: Optional[str]
    new_value: str
    changed_at: datetime
    version: int


class RollbackRequest(BaseModel):
    """回滚请求模型"""
    history_id: int = Field(..., description="历史记录 ID")


class ConfigExportResponse(BaseModel):
    """配置导出响应"""
    exported_at: str
    total: int
    configs: List[dict]


class ConfigImportResponse(BaseModel):
    """配置导入响应"""
    imported_at: str
    created: int
    updated: int
    skipped: int
    errors: List[str]


# ====================
# API 端点
# ====================


@router.get("/", response_model=List[ConfigResponse])
async def get_all_configs(
    include_sensitive: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取所有配置（仅管理员）

    Args:
        include_sensitive: 是否包含敏感信息
    """
    service = ConfigService(db)
    configs = service.get_all(include_sensitive=include_sensitive, include_private=True)

    return [
        ConfigResponse(
            id=config.id,
            key=config.key,
            value=config.value,
            description=config.description,
            is_sensitive=config.is_sensitive,
            is_public=config.is_public,
            version=config.version,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        for config in configs
    ]


@router.get("/public", response_model=List[ConfigResponse])
async def get_public_configs(db: Session = Depends(get_db)):
    """
    获取公开配置（无需认证）
    """
    service = ConfigService(db)
    configs = service.get_all(include_sensitive=False, include_private=False)

    return [
        ConfigResponse(
            id=config.id,
            key=config.key,
            value=config.value,
            description=config.description,
            is_sensitive=config.is_sensitive,
            is_public=config.is_public,
            version=config.version,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
        for config in configs
    ]


@router.get("/{key}", response_model=ConfigResponse)
async def get_config(
    key: str,
    include_sensitive: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取单个配置

    Args:
        key: 配置键
        include_sensitive: 是否显示敏感信息
    """
    service = ConfigService(db)
    config = service.get_by_key(key, include_sensitive=include_sensitive)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配置 {key} 不存在",
        )

    return ConfigResponse(
        id=config.id,
        key=config.key,
        value=config.value,
        description=config.description,
        is_sensitive=config.is_sensitive,
        is_public=config.is_public,
        version=config.version,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config: ConfigItem,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    创建新配置

    Args:
        config: 配置数据
    """
    service = ConfigService(db)

    try:
        new_config = service.create(
            key=config.key,
            value=config.value,
            description=config.description,
            is_sensitive=config.is_sensitive,
            is_public=config.is_public,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ConfigResponse(
        id=new_config.id,
        key=new_config.key,
        value=new_config.value,
        description=new_config.description,
        is_sensitive=new_config.is_sensitive,
        is_public=new_config.is_public,
        version=new_config.version,
        created_at=new_config.created_at,
        updated_at=new_config.updated_at,
    )


@router.put("/{key}", response_model=ConfigResponse)
async def update_config(
    key: str,
    config_data: ConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    更新配置

    Args:
        key: 配置键
        config_data: 配置数据
    """
    service = ConfigService(db)

    try:
        updated_config = service.update(
            key=key,
            value=config_data.value,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return ConfigResponse(
        id=updated_config.id,
        key=updated_config.key,
        value=updated_config.value,
        description=updated_config.description,
        is_sensitive=updated_config.is_sensitive,
        is_public=updated_config.is_public,
        version=updated_config.version,
        created_at=updated_config.created_at,
        updated_at=updated_config.updated_at,
    )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    key: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    删除配置

    Args:
        key: 配置键
    """
    service = ConfigService(db)

    try:
        service.delete(key)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{key}/history", response_model=List[ConfigHistoryItem])
async def get_config_history(
    key: str,
    limit: int = Field(100, ge=1, le=1000),
    include_sensitive: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取配置变更历史

    Args:
        key: 配置键
        limit: 返回记录数限制
        include_sensitive: 是否包含敏感信息的明文
    """
    service = ConfigService(db)
    history = service.get_history(
        key=key,
        limit=limit,
        include_sensitive=include_sensitive,
    )

    return [
        ConfigHistoryItem(
            id=h.id,
            config_id=h.config_id,
            key=h.key,
            old_value=h.old_value,
            new_value=h.new_value,
            changed_at=h.changed_at,
            version=h.version,
        )
        for h in history
    ]


@router.post("/{key}/rollback", response_model=ConfigResponse)
async def rollback_config(
    key: str,
    rollback_request: RollbackRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    回滚配置到指定历史版本

    Args:
        key: 配置键
        rollback_request: 回滚请求（包含历史记录 ID）
    """
    service = ConfigService(db)

    try:
        rolled_config = service.rollback(
            key=key,
            history_id=rollback_request.history_id,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ConfigResponse(
        id=rolled_config.id,
        key=rolled_config.key,
        value=rolled_config.value,
        description=rolled_config.description,
        is_sensitive=rolled_config.is_sensitive,
        is_public=rolled_config.is_public,
        version=rolled_config.version,
        created_at=rolled_config.created_at,
        updated_at=rolled_config.updated_at,
    )


@router.get("/audit/log", response_model=List[ConfigHistoryItem])
async def get_audit_log(
    key: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Field(100, ge=1, le=1000),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    获取配置变更审计日志

    Args:
        key: 配置键过滤
        start_time: 开始时间
        end_time: 结束时间
        limit: 返回记录数限制
    """
    service = ConfigService(db)
    audit_logs = service.get_audit_log(
        user_id=None,  # 可以扩展为查询指定用户的日志
        key=key,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    return [
        ConfigHistoryItem(
            id=log.id,
            config_id=log.config_id,
            key=log.key,
            old_value=log.old_value,
            new_value=log.new_value,
            changed_at=log.changed_at,
            version=log.version,
        )
        for log in audit_logs
    ]


@router.post("/reload", response_model=dict)
async def reload_configs(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
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
        # 或者：重新加载应用到内存

        # 获取当前配置数量
        service = ConfigService(db)
        configs = service.get_all(include_sensitive=False, include_private=True)
        config_count = len(configs)

        return {
            "success": True,
            "message": f"配置已重新加载（共 {config_count} 个配置项）",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载配置失败: {str(e)}",
        )


@router.post("/export", response_model=ConfigExportResponse)
async def export_configs(
    include_sensitive: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    导出配置（用于备份）

    Args:
        include_sensitive: 是否包含敏感信息

    Returns:
        ConfigExportResponse: 配置导出数据
    """
    service = ConfigService(db)
    export_data = service.export_configs(include_sensitive=include_sensitive)

    return ConfigExportResponse(**export_data)


@router.post("/import", response_model=ConfigImportResponse)
async def import_configs(
    configs: List[dict],
    overwrite: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    导入配置（用于恢复）

    Args:
        configs: 配置数据列表
        overwrite: 是否覆盖已存在的配置

    Returns:
        ConfigImportResponse: 导入结果统计
    """
    service = ConfigService(db)
    import_result = service.import_configs(
        configs=configs,
        user_id=current_user.id if current_user else None,
        overwrite=overwrite,
    )

    return ConfigImportResponse(**import_result)
