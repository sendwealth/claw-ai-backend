"""
RAG 服务使用示例
展示如何创建知识库、添加文档、进行查询
"""

import asyncio
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.rag_service import create_rag_service
from app.services.vector_service import vector_service
from app.models import KnowledgeBase, Document, User


def create_sample_documents():
    """创建示例文档"""
    return [
        {
            "title": "CLAW.AI 产品介绍",
            "content": """
CLAW.AI 是一款智能 AI 咨询服务产品，提供以下核心功能：

1. 智能对话
   - 基于大语言模型的自然语言对话
   - 支持多轮对话和上下文理解
   - 支持流式输出，实时响应

2. 知识库问答
   - 基于向量检索的 RAG 技术
   - 支持自定义知识库
   - 准确引用来源

3. 咨询服务
   - 专业领域知识咨询
   - 多领域专家支持
   - 快速响应和解答

4. API 集成
   - RESTful API 接口
   - WebSocket 实时通信
   - 灵活的后端对接

产品特点：
- 高性能：响应时间 < 1 秒
- 高准确率：基于最新 GLM-4 模型
- 易集成：简单的 API 调用
- 可扩展：支持自定义配置
            """
        },
        {
            "title": "用户注册指南",
            "content": """
CLAW.AI 用户注册流程：

步骤 1：访问官网
打开浏览器，访问 CLAW.AI 官方网站：https://openspark.online

步骤 2：点击注册
在首页右上角点击"注册"按钮

步骤 3：填写信息
- 用户名：3-20 个字符
- 邮箱：有效的邮箱地址
- 密码：至少 8 个字符，包含字母和数字
- 确认密码：再次输入密码

步骤 4：验证邮箱
系统会发送验证邮件到您的邮箱，点击邮件中的验证链接

步骤 5：完成注册
验证成功后，自动跳转到登录页面

注意事项：
- 每个邮箱只能注册一个账号
- 请使用真实有效的邮箱地址
- 验证链接有效期为 24 小时
- 如未收到邮件，请检查垃圾箱
            """
        },
        {
            "title": "价格方案",
            "content": """
CLAW.AI 提供多种价格方案，满足不同用户需求：

免费版（体验）
- 价格：¥0 / 月
- 功能：
  - 每日 10 次对话
  - 每月 100 条消息
  - 基础知识库问答
  - 社区支持

标准版（个人）
- 价格：¥99 / 月
- 功能：
  - 无限对话次数
  - 每月 10,000 条消息
  - 创建 3 个知识库
  - 文件上传支持
  - 邮件支持

专业版（团队）
- 价格：¥299 / 月
- 功能：
  - 无限对话次数
  - 每月 50,000 条消息
  - 创建 10 个知识库
  - 团队协作功能
  - 优先技术支持
  - API 访问权限

企业版（定制）
- 价格：联系销售
- 功能：
  - 无限制使用
  - 专属知识库
  - 私有化部署
  - 24/7 专属支持
  - 定制开发

年度优惠：
- 标准版年付：¥999 / 年（优惠 15%）
- 专业版年付：¥2999 / 年（优惠 16%）
            """
        },
        {
            "title": "常见问题（FAQ）",
            "content": """
CLAW.AI 常见问题解答：

Q: 如何重置密码？
A: 在登录页面点击"忘记密码"，输入注册邮箱，系统会发送重置链接到您的邮箱。

Q: 支持哪些支付方式？
A: 我们支持支付宝、微信支付、银行转账和企业对公转账。

Q: 可以申请退款吗？
A: 支持。购买后 7 天内，如不满意可以申请全额退款。

Q: 知识库支持哪些格式？
A: 支持 TXT、MD、PDF（文本提取）、Word（文本提取）等格式。

Q: API 有调用限制吗？
A: 免费版不支持 API 调用，标准版及以上支持 API 调用，具体限制见价格方案。

Q: 数据安全吗？
A: 我们采用企业级安全措施，包括数据加密、访问控制、安全审计等，确保您的数据安全。

Q: 如何联系客服？
A: 您可以通过以下方式联系我们：
- 邮箱：support@clawai.com
- 微信：CLAW_AI_Support
- 在线客服：官网右下角

Q: 可以私有化部署吗？
A: 企业版支持私有化部署，请联系我们的销售团队获取详细信息。

Q: 支持多语言吗？
A: 目前主要支持中文和英文，其他语言正在开发中。

Q: 如何升级套餐？
A: 登录后在"我的账户"中可以随时升级或降级套餐。
            """
        },
        {
            "title": "API 使用说明",
            "content": """
CLAW.AI API 使用指南：

认证方式：
所有 API 请求需要在 Header 中包含认证 Token：
Authorization: Bearer <your_access_token>

获取 Token：
POST /api/v1/auth/login
{
  "username": "your_username",
  "password": "your_password"
}

响应：
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

对话 API：
POST /api/v1/conversations/{id}/messages
{
  "message": "你好",
  "use_rag": true,
  "knowledge_base_id": 1
}

知识库 API：
创建知识库：
POST /api/v1/knowledge/
{
  "name": "产品文档",
  "description": "产品相关文档"
}

添加文档：
POST /api/v1/knowledge/{kb_id}/documents
{
  "title": "用户指南",
  "content": "文档内容...",
  "file_type": "txt"
}

RAG 查询：
POST /api/v1/knowledge/{kb_id}/query
{
  "question": "如何注册？",
  "top_k": 5
}

错误处理：
API 返回标准 HTTP 状态码：
- 200: 成功
- 400: 请求参数错误
- 401: 未授权
- 404: 资源不存在
- 429: 请求过于频繁（限流）
- 500: 服务器错误

错误响应格式：
{
  "detail": "错误描述信息"
}

速率限制：
- 免费版：10 次 / 分钟
- 标准版：100 次 / 分钟
- 专业版：500 次 / 分钟
- 企业版：无限制
            """
        }
    ]


async def demo_rag_service():
    """RAG 服务演示"""
    print("=" * 60)
    print("CLAW.AI RAG 服务演示")
    print("=" * 60)

    # 创建数据库会话
    db = SessionLocal()

    try:
        # 创建 RAG 服务实例
        rag_service = create_rag_service(db)

        # 演示 1: 创建知识库
        print("\n【演示 1】创建知识库")
        print("-" * 60)

        # 假设有一个用户 ID 为 1
        user_id = 1

        knowledge_base = KnowledgeBase(
            user_id=user_id,
            name="CLAW.AI 产品文档",
            description="CLAW.AI 产品相关的所有文档",
            embedding_model="embedding-2",
        )

        db.add(knowledge_base)
        db.commit()
        db.refresh(knowledge_base)

        print(f"✅ 创建知识库成功")
        print(f"   ID: {knowledge_base.id}")
        print(f"   名称: {knowledge_base.name}")
        print(f"   描述: {knowledge_base.description}")

        # 演示 2: 添加文档并索引
        print("\n【演示 2】添加文档并索引")
        print("-" * 60)

        documents = create_sample_documents()

        for idx, doc_data in enumerate(documents, 1):
            # 创建文档记录
            document = Document(
                knowledge_base_id=knowledge_base.id,
                title=doc_data["title"],
                content=doc_data["content"].strip(),
                file_type="txt",
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            # 索引到向量数据库
            print(f"正在索引文档 {idx}/{len(documents)}: {doc_data['title']}...")

            index_result = await rag_service.index_document(
                knowledge_base_id=knowledge_base.id,
                document_id=document.id,
                text=document.content,
            )

            if index_result["success"]:
                document.chunk_count = index_result["chunk_count"]
                db.commit()
                print(f"   ✅ 索引成功，生成了 {index_result['chunk_count']} 个文本块")
            else:
                print(f"   ❌ 索引失败: {index_result.get('error', 'Unknown error')}")

        # 演示 3: RAG 查询
        print("\n【演示 3】RAG 查询")
        print("-" * 60)

        questions = [
            "如何注册 CLAW.AI 账号？",
            "CLAW.AI 的价格是多少？",
            "支持哪些支付方式？",
            "如何重置密码？",
            "API 如何使用？",
        ]

        for question in questions:
            print(f"\n问题: {question}")

            # 执行 RAG 查询
            result = await rag_service.query(
                question=question,
                knowledge_base_id=knowledge_base.id,
                top_k=5,
            )

            if result["success"]:
                print(f"✅ RAG 启用: {result.get('rag_enabled', False)}")
                print(f"✅ 搜索结果数: {result.get('search_results_count', 0)}")
                print(f"\n回答:\n{result['answer']}")

                if result.get("sources"):
                    print(f"\n引用来源:")
                    for source in result["sources"]:
                        print(f"   - {source['title']} (相似度: {source['score']:.3f})")

                if result.get("tokens"):
                    print(f"\nToken 消耗: {result['tokens']['total']}")
                    print(f"成本: ¥{result['cost']:.4f}")
            else:
                print(f"❌ 查询失败: {result.get('error', 'Unknown error')}")

            print("-" * 60)

        # 演示 4: 向量搜索测试
        print("\n【演示 4】向量搜索测试")
        print("-" * 60)

        test_query = "产品功能有哪些？"
        print(f"查询: {test_query}")

        search_results = await vector_service.search(
            query=test_query,
            knowledge_base_id=knowledge_base.id,
            top_k=3,
        )

        print(f"找到 {len(search_results)} 个相关片段:")
        for idx, result in enumerate(search_results, 1):
            print(f"\n片段 {idx}:")
            print(f"  相似度: {result['score']:.3f}")
            print(f"  文本: {result['text'][:100]}...")

        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)

        # 清理演示数据
        print("\n清理演示数据...")
        await rag_service.delete_knowledge_base_index(knowledge_base.id)
        db.delete(knowledge_base)
        db.commit()
        print("✅ 清理完成")

    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    print("⚠️ 注意：运行此脚本需要：")
    print("   1. Milvus 服务正在运行")
    print("   2. 数据库中存在 ID=1 的用户")
    print("   3. 正确的环境变量配置（ZHIPUAI_API_KEY 等）")
    print()

    # 运行演示
    asyncio.run(demo_rag_service())
