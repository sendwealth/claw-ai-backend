"""
配置服务
提供配置的 CRUD 操作、历史记录、回滚和审计功能
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.config import Config, ConfigHistory
from app.models.user import User


class ConfigService:
    """配置服务类"""

    def __init__(self, db: Session):
        self.db = db

    # ====================
    # 基础 CRUD 操作
    # ====================

    def get_all(
        self,
        include_sensitive: bool = False,
        include_private: bool = False,
    ) -> List[Config]:
        """
        获取所有配置

        Args:
            include_sensitive: 是否包含敏感信息
            include_private: 是否包含私有配置（非公开）

        Returns:
            List[Config]: 配置列表
        """
        query = self.db.query(Config)

        # 如果不包含私有配置，只返回公开配置
        if not include_private:
            query = query.filter(Config.is_public == True)

        configs = query.order_by(Config.key).all()

        # 如果不包含敏感信息，对敏感值进行脱敏
        if not include_sensitive:
            for config in configs:
                if config.is_sensitive:
                    config.value = config.mask_value()

        return configs

    def get_by_key(self, key: str, include_sensitive: bool = False) -> Optional[Config]:
        """
        根据键获取配置

        Args:
            key: 配置键
            include_sensitive: 是否显示敏感信息

        Returns:
            Optional[Config]: 配置对象
        """
        config = self.db.query(Config).filter(Config.key == key).first()

        if config and config.is_sensitive and not include_sensitive:
            # 创建副本以避免修改数据库
            config.value = config.mask_value()

        return config

    def create(
        self,
        key: str,
        value: str,
        description: Optional[str] = None,
        is_sensitive: bool = False,
        is_public: bool = False,
        user_id: Optional[int] = None,
    ) -> Config:
        """
        创建新配置

        Args:
            key: 配置键
            value: 配置值
            description: 配置描述
            is_sensitive: 是否敏感信息
            is_public: 是否公开访问
            user_id: 创建者用户 ID

        Returns:
            Config: 创建的配置对象

        Raises:
            ValueError: 配置键已存在
        """
        # 检查配置是否已存在
        existing = self.db.query(Config).filter(Config.key == key).first()
        if existing:
            raise ValueError(f"配置 {key} 已存在")

        # 创建配置
        config = Config(
            key=key,
            value=value,
            description=description,
            is_sensitive=is_sensitive,
            is_public=is_public,
            version=1,
            updated_by=user_id,
        )

        self.db.add(config)
        self.db.flush()

        # 记录历史（初始版本）
        history = ConfigHistory(
            config_id=config.id,
            key=key,
            old_value=None,
            new_value=value,
            changed_by=user_id,
            version=1,
        )
        self.db.add(history)

        self.db.commit()
        self.db.refresh(config)

        return config

    def update(
        self,
        key: str,
        value: str,
        user_id: Optional[int] = None,
    ) -> Config:
        """
        更新配置

        Args:
            key: 配置键
            value: 新值
            user_id: 更新者用户 ID

        Returns:
            Config: 更新后的配置对象

        Raises:
            ValueError: 配置不存在
        """
        config = self.db.query(Config).filter(Config.key == key).first()
        if not config:
            raise ValueError(f"配置 {key} 不存在")

        old_value = config.value

        # 更新配置
        config.value = value
        config.version += 1
        config.updated_by = user_id

        # 记录历史
        history = ConfigHistory(
            config_id=config.id,
            key=key,
            old_value=old_value,
            new_value=value,
            changed_by=user_id,
            version=config.version,
        )
        self.db.add(history)

        self.db.commit()
        self.db.refresh(config)

        return config

    def delete(self, key: str) -> bool:
        """
        删除配置

        Args:
            key: 配置键

        Returns:
            bool: 是否成功删除

        Raises:
            ValueError: 配置不存在
        """
        config = self.db.query(Config).filter(Config.key == key).first()
        if not config:
            raise ValueError(f"配置 {key} 不存在")

        self.db.delete(config)
        self.db.commit()

        return True

    # ====================
    # 历史记录操作
    # ====================

    def get_history(
        self,
        key: Optional[str] = None,
        config_id: Optional[int] = None,
        limit: int = 100,
        include_sensitive: bool = False,
    ) -> List[ConfigHistory]:
        """
        获取配置变更历史

        Args:
            key: 配置键（与 config_id 二选一）
            config_id: 配置 ID（与 key 二选一）
            limit: 返回记录数限制
            include_sensitive: 是否包含敏感信息的明文

        Returns:
            List[ConfigHistory]: 历史记录列表
        """
        query = self.db.query(ConfigHistory)

        if key:
            query = query.filter(ConfigHistory.key == key)
        elif config_id:
            query = query.filter(ConfigHistory.config_id == config_id)

        history_list = (
            query.order_by(desc(ConfigHistory.changed_at))
            .limit(limit)
            .all()
        )

        # 如果不包含敏感信息，对敏感值进行脱敏
        if not include_sensitive:
            for history in history_list:
                if history.old_value and len(history.old_value) > 8:
                    history.old_value = history.mask_old_value()
                if history.new_value and len(history.new_value) > 8:
                    history.new_value = history.mask_new_value()

        return history_list

    def rollback(
        self,
        key: str,
        history_id: int,
        user_id: Optional[int] = None,
    ) -> Config:
        """
        回滚配置到指定历史版本

        Args:
            key: 配置键
            history_id: 历史记录 ID
            user_id: 操作者用户 ID

        Returns:
            Config: 回滚后的配置对象

        Raises:
            ValueError: 配置或历史记录不存在
        """
        # 获取配置
        config = self.db.query(Config).filter(Config.key == key).first()
        if not config:
            raise ValueError(f"配置 {key} 不存在")

        # 获取历史记录
        history = (
            self.db.query(ConfigHistory)
            .filter(ConfigHistory.id == history_id)
            .first()
        )
        if not history or history.config_id != config.id:
            raise ValueError(f"历史记录 {history_id} 不存在或不属于配置 {key}")

        old_value = config.value

        # 回滚到历史版本的值
        config.value = history.new_value
        config.version += 1
        config.updated_by = user_id

        # 记录回滚操作
        rollback_history = ConfigHistory(
            config_id=config.id,
            key=key,
            old_value=old_value,
            new_value=history.new_value,
            changed_by=user_id,
            version=config.version,
        )
        self.db.add(rollback_history)

        self.db.commit()
        self.db.refresh(config)

        return config

    # ====================
    # 批量操作
    # ====================

    def export_configs(self, include_sensitive: bool = False) -> dict:
        """
        导出所有配置

        Args:
            include_sensitive: 是否包含敏感信息

        Returns:
            dict: 配置数据
        """
        configs = self.get_all(include_sensitive=include_sensitive, include_private=True)

        result = {
            "exported_at": datetime.utcnow().isoformat(),
            "total": len(configs),
            "configs": [
                {
                    "key": config.key,
                    "value": config.value,
                    "description": config.description,
                    "is_sensitive": config.is_sensitive,
                    "is_public": config.is_public,
                    "version": config.version,
                }
                for config in configs
            ],
        }

        return result

    def import_configs(
        self,
        configs: List[dict],
        user_id: Optional[int] = None,
        overwrite: bool = False,
    ) -> dict:
        """
        导入配置

        Args:
            configs: 配置列表
            user_id: 操作者用户 ID
            overwrite: 是否覆盖已存在的配置

        Returns:
            dict: 导入结果统计
        """
        created = 0
        updated = 0
        skipped = 0
        errors = []

        for config_data in configs:
            try:
                key = config_data.get("key")
                value = config_data.get("value")

                if not key or value is None:
                    errors.append(f"配置数据不完整: {config_data}")
                    continue

                existing = self.db.query(Config).filter(Config.key == key).first()

                if existing:
                    if overwrite:
                        self.update(
                            key=key,
                            value=value,
                            user_id=user_id,
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    self.create(
                        key=key,
                        value=value,
                        description=config_data.get("description"),
                        is_sensitive=config_data.get("is_sensitive", False),
                        is_public=config_data.get("is_public", False),
                        user_id=user_id,
                    )
                    created += 1

            except Exception as e:
                errors.append(f"导入配置 {config_data.get('key')} 失败: {str(e)}")

        return {
            "imported_at": datetime.utcnow().isoformat(),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }

    # ====================
    # 审计日志
    # ====================

    def get_audit_log(
        self,
        user_id: Optional[int] = None,
        key: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[ConfigHistory]:
        """
        获取审计日志

        Args:
            user_id: 用户 ID 过滤
            key: 配置键过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录数限制

        Returns:
            List[ConfigHistory]: 审计日志列表
        """
        query = self.db.query(ConfigHistory)

        if user_id:
            query = query.filter(ConfigHistory.changed_by == user_id)
        if key:
            query = query.filter(ConfigHistory.key == key)
        if start_time:
            query = query.filter(ConfigHistory.changed_at >= start_time)
        if end_time:
            query = query.filter(ConfigHistory.changed_at <= end_time)

        audit_logs = (
            query.order_by(desc(ConfigHistory.changed_at))
            .limit(limit)
            .all()
        )

        return audit_logs
