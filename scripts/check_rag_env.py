#!/usr/bin/env python3
"""
RAG 服务环境检查脚本
验证所有依赖服务是否正常运行
"""

import sys
import os


def check_python_version():
    """检查 Python 版本"""
    print("=" * 60)
    print("检查 Python 版本...")
    print("-" * 60)
    version = sys.version_info
    print(f"Python 版本: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 8:
        print("✅ Python 版本符合要求 (>= 3.8)")
        return True
    else:
        print("❌ Python 版本过低，需要 3.8 或更高版本")
        return False


def check_dependencies():
    """检查 Python 依赖包"""
    print("\n" + "=" * 60)
    print("检查 Python 依赖包...")
    print("-" * 60)

    required_packages = {
        "pymilvus": "2.3.4",
        "zhipuai": "4.0.0",
        "fastapi": "0.104.1",
        "sqlalchemy": "2.0.23",
        "redis": "5.0.1",
    }

    all_ok = True

    for package, version in required_packages.items():
        try:
            mod = __import__(package)
            installed_version = getattr(mod, "__version__", "unknown")
            print(f"✅ {package}: {installed_version}")
        except ImportError:
            print(f"❌ {package}: 未安装")
            all_ok = False

    return all_ok


def check_env_vars():
    """检查环境变量"""
    print("\n" + "=" * 60)
    print("检查环境变量...")
    print("-" * 60)

    required_vars = [
        "ZHIPUAI_API_KEY",
        "DATABASE_URL",
        "REDIS_URL",
    ]

    optional_vars = [
        "MILVUS_HOST",
        "MILVUS_PORT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
    ]

    all_ok = True

    print("必需的环境变量:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感信息
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: 未设置")
            all_ok = False

    print("\n可选的环境变量:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"⚠️  {var}: 未设置（使用默认值）")

    return all_ok


def check_milvus_connection():
    """检查 Milvus 连接"""
    print("\n" + "=" * 60)
    print("检查 Milvus 连接...")
    print("-" * 60)

    try:
        from pymilvus import connections

        host = os.getenv("MILVUS_HOST", "localhost")
        port = int(os.getenv("MILVUS_PORT", "19530"))

        print(f"尝试连接到 Milvus: {host}:{port}")

        connections.connect(host=host, port=port)

        # 获取连接状态
        from pymilvus import utility

        list_collections = utility.list_collections()
        print(f"✅ 成功连接到 Milvus")
        print(f"   当前集合数量: {len(list_collections)}")

        if list_collections:
            print(f"   集合列表: {', '.join(list_collections)}")

        connections.disconnect("default")

        return True

    except Exception as e:
        print(f"❌ 连接 Milvus 失败: {e}")
        print("\n提示:")
        print("  - 确保 Milvus 服务正在运行")
        print("  - 检查 MILVUS_HOST 和 MILVUS_PORT 环境变量")
        print("  - 运行: docker-compose -f docker-compose.prod.yml ps")
        return False


def check_redis_connection():
    """检查 Redis 连接"""
    print("\n" + "=" * 60)
    print("检查 Redis 连接...")
    print("-" * 60)

    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        print(f"尝试连接到 Redis: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")

        client = redis.from_url(redis_url, decode_responses=True)

        # 测试连接
        client.ping()

        # 获取信息
        info = client.info()
        print(f"✅ 成功连接到 Redis")
        print(f"   Redis 版本: {info.get('redis_version', 'unknown')}")
        print(f"   连接的客户端数: {info.get('connected_clients', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ 连接 Redis 失败: {e}")
        print("\n提示:")
        print("  - 确保 Redis 服务正在运行")
        print("  - 检查 REDIS_URL 环境变量")
        print("  - 运行: docker-compose -f docker-compose.prod.yml ps")
        return False


def check_zhipuai_api():
    """检查 Zhipu AI API"""
    print("\n" + "=" * 60)
    print("检查 Zhipu AI API...")
    print("-" * 60)

    try:
        from zhipuai import ZhipuAI

        api_key = os.getenv("ZHIPUAI_API_KEY")
        if not api_key:
            print("❌ ZHIPUAI_API_KEY 环境变量未设置")
            return False

        print(f"API Key: {api_key[:8]}...{api_key[-8:]}")

        client = ZhipuAI(api_key=api_key)

        # 测试 Embedding API
        print("\n测试 Embedding API...")
        response = client.embeddings.create(
            model="embedding-2",
            input="测试文本",
        )

        if response.data:
            embedding = response.data[0].embedding
            print(f"✅ Embedding API 调用成功")
            print(f"   向量维度: {len(embedding)}")
            print(f"   前 5 个值: {embedding[:5]}")
        else:
            print("❌ Embedding API 响应为空")
            return False

        # 测试 Chat API
        print("\n测试 Chat API...")
        response = client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10,
        )

        if response.choices:
            content = response.choices[0].message.content
            print(f"✅ Chat API 调用成功")
            print(f"   响应内容: {content}")
        else:
            print("❌ Chat API 响应为空")
            return False

        return True

    except Exception as e:
        print(f"❌ Zhipu AI API 调用失败: {e}")
        print("\n提示:")
        print("  - 检查 ZHIPUAI_API_KEY 环境变量")
        print("  - 确认 API Key 有效且有足够的配额")
        print("  - 访问: https://open.bigmodel.cn/")
        return False


def check_database():
    """检查数据库连接"""
    print("\n" + "=" * 60)
    print("检查数据库连接...")
    print("-" * 60)

    try:
        from sqlalchemy import create_engine, text

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL 环境变量未设置")
            return False

        # 隐藏密码
        masked_url = database_url.split("@")[-1] if "@" in database_url else database_url
        print(f"尝试连接到数据库: {masked_url}")

        engine = create_engine(database_url)

        # 测试连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ 成功连接到数据库")
            print(f"   PostgreSQL 版本: {version.split(',')[0]}")

        return True

    except Exception as e:
        print(f"❌ 连接数据库失败: {e}")
        print("\n提示:")
        print("  - 确保 PostgreSQL 服务正在运行")
        print("  - 检查 DATABASE_URL 环境变量")
        print("  - 运行: docker-compose -f docker-compose.prod.yml ps")
        return False


def check_files():
    """检查必要文件是否存在"""
    print("\n" + "=" * 60)
    print("检查必要文件...")
    print("-" * 60)

    base_dir = "/home/wuying/clawd/claw-ai-backend"

    required_files = [
        "app/services/vector_service.py",
        "app/services/rag_service.py",
        "app/api/knowledge.py",
        "app/core/config.py",
        "app/services/conversation_service.py",
        "docs/RAG_SERVICE.md",
        "docs/RAG_QUICKSTART.md",
        "examples/rag_demo.py",
    ]

    all_ok = True

    for file_path in required_files:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            all_ok = False

    return all_ok


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("RAG 服务环境检查")
    print("=" * 60)

    results = {
        "Python 版本": check_python_version(),
        "Python 依赖包": check_dependencies(),
        "环境变量": check_env_vars(),
        "必要文件": check_files(),
    }

    # 检查服务连接（需要成功导入）
    if results["Python 依赖包"]:
        results["Milvus 连接"] = check_milvus_connection()
        results["Redis 连接"] = check_redis_connection()
        results["Zhipu AI API"] = check_zhipuai_api()
        results["数据库连接"] = check_database()
    else:
        print("\n⚠️  由于缺少必要依赖包，跳过服务连接检查")
        results["Milvus 连接"] = False
        results["Redis 连接"] = False
        results["Zhipu AI API"] = False
        results["数据库连接"] = False

    # 输出总结
    print("\n" + "=" * 60)
    print("检查结果总结")
    print("=" * 60)

    for check, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check:20s} {status}")

    # 总体评估
    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！RAG 服务环境已准备就绪。")
        print("\n下一步:")
        print("  1. 启动服务: docker-compose -f docker-compose.prod.yml up -d")
        print("  2. 运行演示: python examples/rag_demo.py")
        print("  3. 查看文档: docs/RAG_QUICKSTART.md")
    else:
        print("❌ 部分检查失败，请根据上述提示修复问题。")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
