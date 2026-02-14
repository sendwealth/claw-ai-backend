#!/usr/bin/env python3
"""
CLAW.AI 限流系统演示脚本
演示如何使用限流系统的各个功能
"""

import asyncio
import time
import requests
from typing import Dict, Any

# 配置
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "your_admin_token"  # 替换为实际的管理员 token
USER_TOKEN = "your_user_token"    # 替换为实际的用户 token


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = ""):
    """打印结果"""
    status = "✓" if success else "✗"
    print(f"{status} {name}")
    if message:
        print(f"  → {message}")


class RateLimitDemo:
    """限流系统演示类"""

    def __init__(self):
        self.base_url = BASE_URL

    def get_headers(self, admin: bool = False) -> Dict[str, str]:
        """获取请求头"""
        token = ADMIN_TOKEN if admin else USER_TOKEN
        return {"Authorization": f"Bearer {token}"}

    def demo_1_health_check(self):
        """演示 1：健康检查"""
        print_section("1. 健康检查")

        try:
            response = requests.get(f"{self.base_url}/health")
            data = response.json()
            print_result("健康检查", response.status_code == 200)
            print(f"  → 状态: {data['status']}")
            print(f"  → 应用: {data['app']}")
            print(f"  → 版本: {data['version']}")
        except Exception as e:
            print_result("健康检查", False, str(e))

    def demo_2_get_config(self):
        """演示 2：获取限流配置"""
        print_section("2. 获取限流配置")

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/rate-limit/config",
                headers=self.get_headers(admin=True)
            )
            data = response.json()
            print_result("获取限流配置", response.status_code == 200)
            print(f"  → 全局限流: {data['global_limit']} req/min")
            print(f"  → 用户限流 (免费): {data['user_limits']['free']} req/min")
            print(f"  → 用户限流 (专业): {data['user_limits']['professional']} req/min")
            print(f"  → 用户限流 (企业): {data['user_limits']['enterprise']} req/min")
            print(f"  → IP 限流: {data['ip_limit']} req/min")
            print(f"  → 突发容量: {data['burst_capacity']}x")
        except Exception as e:
            print_result("获取限流配置", False, str(e))

    def demo_3_whitelist_management(self):
        """演示 3：白名单管理"""
        print_section("3. 白名单管理")

        # 添加 IP 到白名单
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/rate-limit/whitelist",
                headers=self.get_headers(admin=True),
                json={"type": "ip", "value": "192.168.1.100"}
            )
            print_result("添加 IP 到白名单", response.status_code == 200, response.json().get("message"))

            # 获取白名单
            response = requests.get(
                f"{self.base_url}/api/v1/rate-limit/whitelist",
                headers=self.get_headers(admin=True)
            )
            whitelist = response.json()
            print_result("获取白名单", response.status_code == 200)
            print(f"  → 白名单数量: {len(whitelist)}")

            # 从白名单移除
            response = requests.delete(
                f"{self.base_url}/api/v1/rate-limit/whitelist",
                headers=self.get_headers(admin=True),
                json={"type": "ip", "value": "192.168.1.100"}
            )
            print_result("从白名单移除", response.status_code == 200, response.json().get("message"))

        except Exception as e:
            print_result("白名单管理", False, str(e))

    def demo_4_blacklist_management(self):
        """演示 4：黑名单管理"""
        print_section("4. 黑名单管理")

        # 添加 IP 到黑名单
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/rate-limit/blacklist",
                headers=self.get_headers(admin=True),
                json={"type": "ip", "value": "192.168.1.200"}
            )
            print_result("添加 IP 到黑名单", response.status_code == 200, response.json().get("message"))

            # 获取黑名单
            response = requests.get(
                f"{self.base_url}/api/v1/rate-limit/blacklist",
                headers=self.get_headers(admin=True)
            )
            blacklist = response.json()
            print_result("获取黑名单", response.status_code == 200)
            print(f"  → 黑名单数量: {len(blacklist)}")

            # 从黑名单移除
            response = requests.delete(
                f"{self.base_url}/api/v1/rate-limit/blacklist",
                headers=self.get_headers(admin=True),
                json={"type": "ip", "value": "192.168.1.200"}
            )
            print_result("从黑名单移除", response.status_code == 200, response.json().get("message"))

        except Exception as e:
            print_result("黑名单管理", False, str(e))

    def demo_5_get_status(self):
        """演示 5：获取限流状态"""
        print_section("5. 获取限流状态")

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/rate-limit/status",
                headers=self.get_headers()
            )
            data = response.json()
            print_result("获取限流状态", response.status_code == 200)
            print(f"  → 客户端 IP: {data['client_ip']}")
            print(f"  → 用户 ID: {data.get('user_id', '未认证')}")
            print(f"  → 用户订阅: {data['user_tier']}")
            print(f"  → 白名单: {data['is_whitelisted']}")
            print(f"  → 黑名单: {data['is_blacklisted']}")

            if "limits" in data:
                print("  → 限流状态:")
                for level, info in data["limits"].items():
                    remaining = info.get("tokens", 0)
                    capacity = info.get("capacity", 0)
                    usage = (1 - remaining / capacity) * 100 if capacity > 0 else 0
                    print(f"    - {level}: {remaining:.0f}/{capacity:.0f} ({usage:.1f}%)")

        except Exception as e:
            print_result("获取限流状态", False, str(e))

    def demo_6_monitoring(self):
        """演示 6：监控数据"""
        print_section("6. 监控数据")

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/rate-limit/monitor",
                headers=self.get_headers(admin=True)
            )
            data = response.json()
            print_result("获取监控数据", response.status_code == 200)

            if "endpoints" in data:
                print("  → 端点统计:")
                for endpoint, stats in data["endpoints"].items():
                    total = stats["total_requests"]
                    blocked = stats["blocked_requests"]
                    block_rate = (blocked / total * 100) if total > 0 else 0
                    print(f"    - {endpoint}:")
                    print(f"      总请求: {total}, 被拦截: {blocked}, 拦截率: {block_rate:.1f}%")

        except Exception as e:
            print_result("获取监控数据", False, str(e))

    def demo_7_rate_limit_test(self):
        """演示 7：限流测试"""
        print_section("7. 限流测试")

        try:
            # 发送多个请求
            print("  发送 10 个请求...")
            success = 0
            blocked = 0

            for i in range(10):
                response = requests.get(
                    f"{self.base_url}/api/v1/rate-limit/test",
                    headers=self.get_headers()
                )

                if response.status_code == 200:
                    success += 1
                    if i < 3:  # 只打印前几个
                        print(f"  → 请求 {i+1}: 成功")
                elif response.status_code == 429:
                    blocked += 1
                    retry_after = response.headers.get("Retry-After", "N/A")
                    print(f"  → 请求 {i+1}: 被限流 (Retry-After: {retry_after}s)")

            print(f"\n  统计: {success} 成功, {blocked} 被限流")

        except Exception as e:
            print_result("限流测试", False, str(e))

    def demo_8_reset_limit(self):
        """演示 8：重置限流"""
        print_section("8. 重置限流")

        try:
            # 重置用户限流
            response = requests.post(
                f"{self.base_url}/api/v1/rate-limit/reset",
                headers=self.get_headers(admin=True),
                json={"type": "user", "identifier": "test_user"}
            )
            print_result("重置用户限流", response.status_code == 200, response.json().get("message"))

            # 重置 IP 限流
            response = requests.post(
                f"{self.base_url}/api/v1/rate-limit/reset",
                headers=self.get_headers(admin=True),
                json={"type": "ip", "identifier": "192.168.1.100"}
            )
            print_result("重置 IP 限流", response.status_code == 200, response.json().get("message"))

        except Exception as e:
            print_result("重置限流", False, str(e))

    def demo_9_client_example(self):
        """演示 9：客户端处理限流示例"""
        print_section("9. 客户端处理限流示例")

        async def make_request_with_retry(url: str, max_retries: int = 3):
            """带重试的请求函数"""
            for attempt in range(max_retries):
                response = requests.get(url, headers=self.get_headers())

                if response.status_code == 200:
                    return response.json()

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", 60)
                    wait_time = int(retry_after)
                    print(f"  → 限流中，{wait_time} 秒后重试 (尝试 {attempt + 1}/{max_retries})")

                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                    else:
                        raise Exception("超过最大重试次数")

                else:
                    raise Exception(f"请求失败: {response.status_code}")

            raise Exception("未知错误")

        try:
            # 模拟多次请求
            url = f"{self.base_url}/api/v1/conversations"
            print("  尝试访问受限的 API 端点...")

            # 只演示一次，避免实际触发限流
            # result = await make_request_with_retry(url)
            # print(f"  → 请求成功")

            print("  → 客户端重试逻辑已实现")

        except Exception as e:
            print_result("客户端处理示例", False, str(e))

    def demo_10_all_features(self):
        """演示 10：所有功能总览"""
        print_section("10. 功能总览")

        features = [
            "✅ 多层级限流（全局、用户、IP、API）",
            "✅ 令牌桶算法",
            "✅ 白名单和黑名单管理",
            "✅ 限流监控和告警",
            "✅ 自定义限流装饰器",
            "✅ 降级策略",
            "✅ RESTful API",
            "✅ 完整的测试覆盖",
            "✅ 详细的文档",
        ]

        print("\n  已实现的功能:")
        for feature in features:
            print(f"    {feature}")

        print("\n  📚 相关文档:")
        print("    - /docs/RATE_LIMITING.md (限流策略文档)")
        print("    - /docs/RATE_LIMITING_EXAMPLES.md (使用示例)")
        print("    - /docs/RATE_LIMITING_README.md (快速开始)")
        print("    - /docs/RATE_LIMITING_SUMMARY.md (项目总结)")

    def run_all(self):
        """运行所有演示"""
        print("\n" + "=" * 60)
        print("  CLAW.AI API 限流系统演示")
        print("=" * 60)

        self.demo_1_health_check()
        self.demo_2_get_config()
        self.demo_3_whitelist_management()
        self.demo_4_blacklist_management()
        self.demo_5_get_status()
        self.demo_6_monitoring()
        self.demo_7_rate_limit_test()
        self.demo_8_reset_limit()
        self.demo_9_client_example()
        self.demo_10_all_features()

        print("\n" + "=" * 60)
        print("  演示完成！")
        print("=" * 60)


async def main():
    """主函数"""
    demo = RateLimitDemo()
    demo.run_all()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
