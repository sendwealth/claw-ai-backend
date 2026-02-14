"""
缓存预热初始化
在系统启动时预加载热点数据
"""

import asyncio
from typing import List, Callable, Optional
from sqlalchemy.orm import Session

from app.services.cache_service import cache_service
from app.core.cache import cache_warmer
from app.db.session import SessionLocal


class CacheWarmupInitializer:
    """缓存预热初始化器"""

    def __init__(self):
        self.db: Optional[Session] = None

    async def initialize(self):
        """初始化缓存预热任务"""
        # 注册预热任务
        self.register_warmup_tasks()

        # 连接缓存服务
        if not cache_service._connected:
            await cache_service.connect()

    def register_warmup_tasks(self):
        """注册所有预热任务"""

        # 1. 预热活跃用户信息
        cache_warmer.register_task(
            name="active_users_profile",
            func=self.warmup_active_users,
            interval=3600,  # 每小时预热一次
        )

        # 2. 预热热门对话历史
        cache_warmer.register_task(
            name="popular_conversations",
            func=self.warmup_popular_conversations,
            interval=1800,  # 每30分钟预热一次
        )

        # 3. 预热常用知识库文档
        cache_warmer.register_task(
            name="popular_documents",
            func=self.warmup_popular_documents,
            interval=3600,  # 每小时预热一次
        )

    async def warmup_active_users(self):
        """预热活跃用户信息"""
        print("🔥 开始预热活跃用户信息...")

        try:
            if not self.db:
                self.db = SessionLocal()

            # 查询最近活跃的用户（最近24小时有对话的用户）
            from app.models import Conversation
            from datetime import datetime, timedelta

            yesterday = datetime.now() - timedelta(days=1)

            active_user_ids = (
                self.db.query(Conversation.user_id)
                .distinct()
                .filter(Conversation.updated_at >= yesterday)
                .limit(100)
                .all()
            )

            for (user_id,) in active_user_ids:
                # 获取用户信息（会自动缓存）
                await cache_service.get_or_set(
                    key=cache_service._generate_key(
                        scenario="user_profile",
                        identifier=str(user_id),
                    ),
                    factory=lambda: self._get_user_profile(user_id),
                    ttl=3600,
                )

            print(f"✅ 已预热 {len(active_user_ids)} 个活跃用户")

        except Exception as e:
            print(f"❌ 预热活跃用户失败: {e}")
        finally:
            if self.db:
                self.db.close()
                self.db = None

    async def warmup_popular_conversations(self):
        """预热热门对话历史"""
        print("🔥 开始预热热门对话历史...")

        try:
            if not self.db:
                self.db = SessionLocal()

            from app.models import Conversation
            from datetime import datetime, timedelta

            # 查询最近更新的对话
            recent_conversations = (
                self.db.query(Conversation)
                .order_by(Conversation.updated_at.desc())
                .limit(50)
                .all()
            )

            for conv in recent_conversations:
                # 缓存对话信息
                await cache_service.set(
                    key=cache_service._generate_key(
                        scenario="conversation_history",
                        identifier=f"{conv.id}",
                        args=(conv.user_id,),
                    ),
                    value={
                        "id": conv.id,
                        "user_id": conv.user_id,
                        "title": conv.title,
                        "status": conv.status,
                    },
                    ttl=1800,
                )

            print(f"✅ 已预热 {len(recent_conversations)} 个热门对话")

        except Exception as e:
            print(f"❌ 预热热门对话失败: {e}")
        finally:
            if self.db:
                self.db.close()
                self.db = None

    async def warmup_popular_documents(self):
        """预热常用知识库文档"""
        print("🔥 开始预热常用知识库文档...")

        try:
            if not self.db:
                self.db = SessionLocal()

            from app.models import Document

            # 查询最近更新的文档
            recent_documents = (
                self.db.query(Document)
                .order_by(Document.updated_at.desc())
                .limit(100)
                .all()
            )

            for doc in recent_documents:
                # 缓存文档内容
                await cache_service.set(
                    key=cache_service._generate_key(
                        scenario="document_content",
                        identifier=str(doc.id),
                    ),
                    value={
                        "id": doc.id,
                        "title": doc.title,
                        "content": doc.content,
                        "knowledge_base_id": doc.knowledge_base_id,
                    },
                    ttl=3600,
                )

            print(f"✅ 已预热 {len(recent_documents)} 个文档")

        except Exception as e:
            print(f"❌ 预热文档失败: {e}")
        finally:
            if self.db:
                self.db.close()
                self.db = None

    def _get_user_profile(self, user_id: int) -> dict:
        """获取用户配置文件（用于缓存工厂函数）"""
        if not self.db:
            self.db = SessionLocal()

        from app.models import User

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
        }

    async def warmup_all(self):
        """执行所有预热任务"""
        print("🔥 开始执行缓存预热...")

        await self.warmup_active_users()
        await self.warmup_popular_conversations()
        await self.warmup_popular_documents()

        print("✅ 缓存预热完成")

    async def start_periodic_warmup(self):
        """启动周期性预热（后台任务）"""
        print("⏰ 启动周期性缓存预热...")

        while True:
            await self.warmup_all()
            # 每5分钟执行一次预热
            await asyncio.sleep(300)


# 全局预热器实例
cache_warmup_initializer = CacheWarmupInitializer()


# FastAPI 启动事件
async def on_startup():
    """应用启动时的初始化"""
    await cache_warmup_initializer.initialize()


# FastAPI 关闭事件
async def on_shutdown():
    """应用关闭时的清理"""
    await cache_service.disconnect()
