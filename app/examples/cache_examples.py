"""
缓存使用示例
展示如何在现有 API 和服务中集成缓存功能
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.cache import cached, cache_by_tags, rate_limit
from app.services.cache_service import cache_service


# ========== 示例 1: 在服务方法中使用缓存装饰器 ==========

class ExampleService:
    """示例服务类"""

    def __init__(self, db: Session):
        self.db = db

    @cached(scenario="user_profile", ttl=3600)
    async def get_user_profile(self, user_id: int) -> dict:
        """
        获取用户配置文件（已缓存 - TTL 1 小时）

        Args:
            user_id: 用户 ID

        Returns:
            dict: 用户配置文件
        """
        # 模拟数据库查询
        return await self._query_user_from_db(user_id)

    async def _query_user_from_db(self, user_id: int) -> dict:
        """从数据库查询用户"""
        # 实际实现：return self.db.query(User).filter(User.id == user_id).first()
        return {"id": user_id, "name": "John Doe"}

    @cached(scenario="user_conversations", ttl=600)
    def get_user_conversations(self, user_id: int, skip: int = 0, limit: int = 100) -> list:
        """
        获取用户对话列表（已缓存 - TTL 10 分钟）

        Args:
            user_id: 用户 ID
            skip: 跳过数量
            limit: 返回数量

        Returns:
            list: 对话列表
        """
        # 模拟数据库查询
        return self._query_conversations_from_db(user_id, skip, limit)

    def _query_conversations_from_db(self, user_id: int, skip: int, limit: int) -> list:
        """从数据库查询对话列表"""
        # 实际实现：
        # return self.db.query(Conversation).filter(Conversation.user_id == user_id)...
        return [{"id": 1, "title": "对话 1"}, {"id": 2, "title": "对话 2"}]


# ========== 示例 2: 使用缓存标签实现批量失效 ==========

@cache_by_tags(tags=["user:123"])
async def get_user_with_posts(user_id: int) -> dict:
    """
    获取用户及其文章（带缓存标签）

    当用户数据更新时，可以通过标签批量失效所有相关缓存
    """
    # 模拟查询
    return {
        "user": {"id": user_id, "name": "John"},
        "posts": [
            {"id": 1, "title": "文章 1"},
            {"id": 2, "title": "文章 2"},
        ]
    }


async def update_user(user_id: int, data: dict):
    """
    更新用户信息并失效相关缓存

    当用户信息更新时，所有使用该用户标签的缓存都会失效
    """
    # 1. 更新数据库
    print(f"更新用户 {user_id}: {data}")

    # 2. 失效所有与该用户相关的缓存
    await cache_service.delete_by_tags([f"user:{user_id}"])

    print(f"已失效用户 {user_id} 的所有缓存")


# ========== 示例 3: API 限流 ==========

router = APIRouter()


@router.get("/api/protected")
@rate_limit(max_requests=100, window=60)
async def protected_endpoint():
    """
    受限流保护的 API 端点

    每分钟最多 100 次请求
    """
    return {"message": "Hello from protected endpoint"}


# ========== 示例 4: 手动使用缓存服务 ==========

class ManualCacheExample:
    """手动使用缓存的示例"""

    @staticmethod
    async def example_cache_operations():
        """演示各种缓存操作"""

        # 1. 设置缓存
        await cache_service.set(
            key="example:key",
            value={"data": "这是缓存的数据", "timestamp": 1234567890},
            ttl=3600,  # 1 小时
            tags=["tag1", "tag2"]
        )
        print("✅ 缓存已设置")

        # 2. 获取缓存
        cached_value = await cache_service.get("example:key")
        if cached_value:
            print(f"✅ 从缓存获取: {cached_value}")
        else:
            print("❌ 缓存未命中")

        # 3. 使用 get_or_set
        def load_from_db():
            """模拟从数据库加载数据"""
            return {"data": "数据库数据", "loaded_at": "now"}

        value = await cache_service.get_or_set(
            key="example:auto_cache",
            factory=load_from_db,
            ttl=3600,
        )
        print(f"✅ get_or_set 结果: {value}")

        # 4. 删除缓存
        await cache_service.delete("example:key")
        print("✅ 缓存已删除")

        # 5. 批量失效（根据标签）
        await cache_service.delete_by_tags(["tag1", "tag2"])
        print("✅ 标签关联的缓存已失效")

        # 6. 获取缓存统计
        stats = cache_service.get_stats()
        print(f"📊 缓存统计: {stats}")


# ========== 示例 5: 自定义缓存键 ==========

def custom_key_builder(scenario, func, args, kwargs):
    """
    自定义缓存键生成函数

    Args:
        scenario: 缓存场景
        func: 被装饰的函数
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        str: 自定义缓存键
    """
    # 从参数中提取需要的部分
    user_id = args[0] if len(args) > 0 else kwargs.get('user_id')
    action = kwargs.get('action', 'default')

    # 生成自定义键
    return f"custom:{user_id}:{action}"


@cached(scenario="custom", key_builder=custom_key_builder)
async def custom_function(user_id: int, action: str = "default"):
    """
    使用自定义键生成器的函数
    """
    return {"user_id": user_id, "action": action}


# ========== 示例 6: AI 响应缓存 ==========

async def generate_ai_response_with_cache(conversation_id: int, user_message: str) -> dict:
    """
    生成 AI 响应（带缓存）

    相同的输入会从缓存返回，避免重复调用 AI 服务
    """
    import hashlib

    # 生成消息哈希
    message_hash = hashlib.md5(user_message.encode()).hexdigest()[:12]

    # 构建缓存键
    cache_key = cache_service._generate_key(
        scenario="ai_response",
        identifier=f"{conversation_id}:{message_hash}"
    )

    # 尝试从缓存获取
    cached_response = await cache_service.get(cache_key)

    if cached_response:
        print("✅ AI 响应来自缓存")
        return {
            "success": True,
            "content": cached_response["content"],
            "tokens": cached_response["tokens"],
            "from_cache": True,
        }

    # 模拟调用 AI 服务
    print("🤖 调用 AI 服务...")
    ai_response = {
        "content": f"AI 回复: {user_message}",
        "tokens": {"total": 100},
        "cost": 0.01,
    }

    # 缓存响应（24 小时）
    await cache_service.set(cache_key, ai_response, ttl=86400)

    return {
        "success": True,
        "content": ai_response["content"],
        "tokens": ai_response["tokens"],
        "from_cache": False,
    }


# ========== 示例 7: 缓存预热 ==========

from app.core.cache import cache_warmer


def setup_cache_warmup():
    """设置缓存预热任务"""

    @cache_warmer.register_task("warmup_hot_data", interval=3600)
    async def warmup_hot_data():
        """预热热点数据"""
        print("🔥 开始预热热点数据...")

        # 预热用户 1-10 的数据
        for user_id in range(1, 11):
            await cache_service.get_or_set(
                key=cache_service._generate_key(
                    scenario="user_profile",
                    identifier=str(user_id)
                ),
                factory=lambda uid=user_id: load_user_data(uid),
                ttl=3600,
            )

        print("✅ 热点数据预热完成")


async def load_user_data(user_id: int) -> dict:
    """加载用户数据（用于预热）"""
    return {"id": user_id, "name": f"User {user_id}"}


# ========== 示例 8: 缓存失效策略 ==========

class CacheInvalidationExample:
    """缓存失效示例"""

    async def update_user_and_invalidate(self, user_id: int, data: dict):
        """
        更新用户并失效相关缓存

        演示多种缓存失效方式
        """
        # 1. 更新数据库
        print(f"更新用户 {user_id}")

        # 2. 方式一：直接删除特定缓存键
        cache_key = cache_service._generate_key(
            scenario="user_profile",
            identifier=str(user_id)
        )
        await cache_service.delete(cache_key)

        # 3. 方式二：使用标签批量失效
        await cache_service.delete_by_tags([f"user:{user_id}"])

        # 4. 方式三：失效整个场景的缓存
        # 注意：这会失效该场景的所有缓存，慎用
        # await cache_service.delete_by_pattern("user:profile:*")


# ========== 使用示例 ==========

async def main():
    """运行所有示例"""

    print("=" * 60)
    print("缓存使用示例")
    print("=" * 60)

    # 示例 1: 基础缓存
    print("\n📌 示例 1: 基础缓存装饰器")
    service = ExampleService(None)  # 传入 None 作为 db，仅用于演示
    user = await service.get_user_profile(123)
    print(f"获取用户: {user}")

    # 示例 2: 缓存标签
    print("\n📌 示例 2: 缓存标签和批量失效")
    await update_user(123, {"name": "Jane Doe"})

    # 示例 3: 手动缓存操作
    print("\n📌 示例 3: 手动使用缓存服务")
    await ManualCacheExample.example_cache_operations()

    # 示例 4: AI 响应缓存
    print("\n📌 示例 4: AI 响应缓存")
    response = await generate_ai_response_with_cache(1, "你好")
    print(f"AI 响应: {response}")

    # 第二次调用会从缓存获取
    response = await generate_ai_response_with_cache(1, "你好")
    print(f"AI 响应（第二次）: {response}")

    # 示例 5: 自定义缓存键
    print("\n📌 示例 5: 自定义缓存键")
    result = await custom_function(456, "search")
    print(f"自定义函数结果: {result}")

    # 示例 6: 缓存预热
    print("\n📌 示例 6: 缓存预热")
    setup_cache_warmup()
    await cache_warmer.warmup_all()

    # 示例 7: 缓存统计
    print("\n📌 示例 7: 缓存统计")
    stats = cache_service.get_stats()
    print(f"缓存统计: {stats}")

    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
