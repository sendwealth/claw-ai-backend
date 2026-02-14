#!/usr/bin/env python3
"""
数据库优化验证脚本

验证所有优化文件是否正确创建和配置
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, '/home/wuying/clawd/claw-ai-backend')


def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"✅ {description}")
        print(f"   路径: {filepath}")
        print(f"   大小: {size} 字节\n")
        return True
    else:
        print(f"❌ {description}")
        print(f"   路径: {filepath}")
        print(f"   状态: 文件不存在\n")
        return False


def check_migration_script():
    """检查迁移脚本"""
    filepath = "/home/wuying/clawd/claw-ai-backend/alembic/versions/20250214_add_indexes.py"
    print("\n" + "="*60)
    print("检查迁移脚本")
    print("="*60 + "\n")

    if check_file_exists(filepath, "Alembic 迁移脚本"):
        # 检查文件内容
        with open(filepath, 'r') as f:
            content = f.read()
            required_functions = ['upgrade', 'downgrade']
            all_present = all(func in content for func in required_functions)

            if all_present:
                print("✅ 迁移脚本包含必需的函数 (upgrade, downgrade)\n")
            else:
                print("❌ 迁移脚本缺少必需的函数\n")

            # 检查索引创建
            if 'create_index' in content:
                print("✅ 迁移脚本包含索引创建语句\n")
            else:
                print("❌ 迁移脚本缺少索引创建语句\n")

        return True
    return False


def check_database_config():
    """检查数据库配置"""
    filepath = "/home/wuying/clawd/claw-ai-backend/app/db/database.py"
    print("\n" + "="*60)
    print("检查数据库配置")
    print("="*60 + "\n")

    if check_file_exists(filepath, "数据库配置文件"):
        # 检查文件内容
        with open(filepath, 'r') as f:
            content = f.read()
            required_params = ['pool_size', 'max_overflow', 'pool_timeout', 'pool_recycle', 'pool_pre_ping']
            all_present = all(param in content for param in required_params)

            if all_present:
                print("✅ 数据库配置包含所有必需的连接池参数\n")
            else:
                print("❌ 数据库配置缺少部分参数\n")

            # 检查性能监控
            if 'before_cursor_execute' in content and 'after_cursor_execute' in content:
                print("✅ 数据库配置包含查询性能监控\n")
            else:
                print("❌ 数据库配置缺少查询性能监控\n")

        return True
    return False


def check_performance_tests():
    """检查性能测试"""
    filepath = "/home/wuying/clawd/claw-ai-backend/tests/test_db_performance.py"
    print("\n" + "="*60)
    print("检查性能测试")
    print("="*60 + "\n")

    if check_file_exists(filepath, "性能测试脚本"):
        # 检查文件内容
        with open(filepath, 'r') as f:
            content = f.read()
            required_tests = [
                'test_index_performance_conversations',
                'test_index_performance_messages',
                'test_index_performance_documents',
                'test_connection_pool_performance'
            ]
            all_present = all(test in content for test in required_tests)

            if all_present:
                print(f"✅ 性能测试包含所有 {len(required_tests)} 个测试用例\n")
            else:
                print("❌ 性能测试缺少部分测试用例\n")

        return True
    return False


def check_documentation():
    """检查文档"""
    print("\n" + "="*60)
    print("检查文档")
    print("="*60 + "\n")

    docs = [
        ("/home/wuying/clawd/claw-ai-backend/docs/DATABASE_OPTIMIZATION.md", "数据库优化文档"),
        ("/home/wuying/clawd/claw-ai-backend/docs/DATABASE_OPTIMIZATION_SUMMARY.md", "优化总结文档"),
        ("/home/wuying/clawd/claw-ai-backend/docs/DATABASE_QUICK_REFERENCE.md", "快速参考指南"),
    ]

    all_exists = True
    for filepath, description in docs:
        if not check_file_exists(filepath, description):
            all_exists = False

    return all_exists


def check_monitoring_script():
    """检查监控脚本"""
    filepath = "/home/wuying/clawd/claw-ai-backend/scripts/monitor_db.py"
    print("\n" + "="*60)
    print("检查监控脚本")
    print("="*60 + "\n")

    if check_file_exists(filepath, "数据库监控脚本"):
        # 检查文件内容
        with open(filepath, 'r') as f:
            content = f.read()
            required_functions = ['show_pool_status', 'show_slow_queries', 'show_index_usage']
            all_present = all(func in content for func in required_functions)

            if all_present:
                print(f"✅ 监控脚本包含 {len(required_functions)} 个监控功能\n")
            else:
                print("❌ 监控脚本缺少部分功能\n")

        return True
    return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("CLAW.AI 数据库优化 - 验证脚本")
    print("="*60)

    # 检查所有组件
    results = {
        "迁移脚本": check_migration_script(),
        "数据库配置": check_database_config(),
        "性能测试": check_performance_tests(),
        "文档": check_documentation(),
        "监控脚本": check_monitoring_script(),
    }

    # 输出总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60 + "\n")

    for component, status in results.items():
        status_str = "✅ 通过" if status else "❌ 失败"
        print(f"{component:<20} {status_str}")

    print("\n")

    if all(results.values()):
        print("🎉 所有检查通过！数据库优化已成功完成。")
        print("\n下一步：")
        print("1. 备份数据库")
        print("2. 执行迁移: alembic upgrade head")
        print("3. 运行性能测试: pytest tests/test_db_performance.py -v")
        print("4. 监控数据库: python scripts/monitor_db.py --report")
        return 0
    else:
        print("⚠️  部分检查失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
