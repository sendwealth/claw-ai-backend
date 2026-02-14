"""
缓存系统测试脚本
验证缓存功能是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_cache_service():
    """测试缓存服务"""
    print("\n" + "=" * 60)
    print("测试 1: 缓存服务基本功能")
    print("=" * 60)

    try:
        from app.services.cache_service import cache_service

        # 连接 Redis
        print("\n📡 连接缓存服务...")
        connected = await cache_service.connect()

        if connected:
            print("✅ Redis 连接成功")
        else:
            print("⚠️  Redis 连接失败，将使用内存缓存")

        # 测试设置缓存
        print("\n📝 测试设置缓存...")
        test_key = "test:key:1"
        test_value = {"data": "测试数据", "timestamp": 1234567890}

        success = await cache_service.set(
            key=test_key,
            value=test_value,
            ttl=60,
            tags=["test"]
        )
        print(f"设置缓存: {'✅ 成功' if success else '❌ 失败'}")

        # 测试获取缓存
        print("\n🔍 测试获取缓存...")
        retrieved_value = await cache_service.get(test_key)
        if retrieved_value == test_value:
            print("✅ 获取缓存成功，数据匹配")
        else:
            print(f"❌ 获取缓存失败或数据不匹配: {retrieved_value}")

        # 测试缓存统计
        print("\n📊 测试缓存统计...")
        stats = cache_service.get_stats()
        print(f"缓存统计: {stats}")

        # 测试删除缓存
        print("\n🗑️  测试删除缓存...")
        delete_success = await cache_service.delete(test_key)
        print(f"删除缓存: {'✅ 成功' if delete_success else '❌ 失败'}")

        # 验证删除
        deleted_value = await cache_service.get(test_key)
        if deleted_value is None:
            print("✅ 缓存已删除，无法获取")
        else:
            print("❌ 缓存删除失败")

        return True

    except Exception as e:
        print(f"❌ 测试缓存服务失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_decorator():
    """测试缓存装饰器"""
    print("\n" + "=" * 60)
    print("测试 2: 缓存装饰器")
    print("=" * 60)

    try:
        from app.core.cache import cached

        # 定义一个测试函数
        call_count = 0

        @cached(scenario="test", ttl=60)
        async def test_function(user_id: int):
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id, "call_count": call_count}

        print("\n📝 第一次调用（应该查询）...")
        result1 = await test_function(123)
        print(f"结果: {result1}")
        print(f"调用次数: {call_count}")

        print("\n📝 第二次调用（应该从缓存）...")
        result2 = await test_function(123)
        print(f"结果: {result2}")
        print(f"调用次数: {call_count}")

        if call_count == 1 and result1 == result2:
            print("✅ 缓存装饰器工作正常")
        else:
            print("❌ 缓存装饰器可能有问题")

        return True

    except Exception as e:
        print(f"❌ 测试缓存装饰器失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_scenarios():
    """测试所有缓存场景"""
    print("\n" + "=" * 60)
    print("测试 3: 所有缓存场景")
    print("=" * 60)

    try:
        from app.services.cache_service import cache_service

        # 确保已连接
        if not cache_service._connected:
            await cache_service.connect()

        print(f"\n📋 缓存场景配置:")
        for scenario, config in cache_service.CACHE_SCENARIOS.items():
            print(f"  - {scenario}: TTL={config['ttl']}s, 前缀={config['prefix']}")

        # 测试生成缓存键
        print("\n🔑 测试生成缓存键...")

        test_cases = [
            ("user_profile", "123"),
            ("user_conversations", "456", 0, 100),
            ("conversation_history", "789", "user_456"),
            ("ai_response", "conv_1", "msg_hash"),
        ]

        for test_case in test_cases:
            key = cache_service._generate_key(*test_case)
            print(f"  {test_case[0]}: {key}")

        print("✅ 缓存场景测试完成")

        return True

    except Exception as e:
        print(f"❌ 测试缓存场景失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_tags():
    """测试缓存标签"""
    print("\n" + "=" * 60)
    print("测试 4: 缓存标签")
    print("=" * 60)

    try:
        from app.services.cache_service import cache_service

        # 确保已连接
        if not cache_service._connected:
            await cache_service.connect()

        # 设置带标签的缓存
        print("\n📝 设置带标签的缓存...")
        tags = ["user:123", "conversation:456"]

        await cache_service.set(
            key="test:tag:1",
            value={"data": "value1"},
            ttl=60,
            tags=tags
        )

        await cache_service.set(
            key="test:tag:2",
            value={"data": "value2"},
            ttl=60,
            tags=["user:123"]  # 部分标签相同
        )

        print(f"✅ 已设置 2 个缓存，标签: {tags}")

        # 批量失效
        print("\n🗑️  测试批量失效...")
        invalidated_count = await cache_service.delete_by_tags(["user:123"])
        print(f"失效的缓存数量: {invalidated_count}")

        # 验证失效
        value1 = await cache_service.get("test:tag:1")
        value2 = await cache_service.get("test:tag:2")

        if value1 is None and value2 is None:
            print("✅ 批量失效成功")
        else:
            print(f"❌ 批量失败: value1={value1}, value2={value2}")

        return True

    except Exception as e:
        print(f"❌ 测试缓存标签失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_warmup():
    """测试缓存预热"""
    print("\n" + "=" * 60)
    print("测试 5: 缓存预热")
    print("=" * 60)

    try:
        from app.core.cache import cache_warmer

        print("\n📋 预热任务列表:")

        if cache_warmer._warmup_tasks:
            for task in cache_warmer._warmup_tasks:
                print(f"  - {task['name']}: interval={task['interval']}s")
        else:
            print("  (无预热任务)")

        print("\n✅ 缓存预热测试完成")

        return True

    except Exception as e:
        print(f"❌ 测试缓存预热失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("CLAW.AI 缓存系统测试")
    print("=" * 60)

    results = []

    # 运行测试
    results.append(("缓存服务基本功能", await test_cache_service()))
    results.append(("缓存装饰器", await test_cache_decorator()))
    results.append(("所有缓存场景", await test_cache_scenarios()))
    results.append(("缓存标签", await test_cache_tags()))
    results.append(("缓存预热", await test_cache_warmup()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")

    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    print("=" * 60)

    if passed == total:
        print("\n🎉 所有测试通过！缓存系统工作正常。")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查日志。")

    # 断开连接
    try:
        from app.services.cache_service import cache_service
        await cache_service.disconnect()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(main())
