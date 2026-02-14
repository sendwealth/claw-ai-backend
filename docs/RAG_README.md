# CLAW.AI RAG 服务

> 为 CLAW.AI 项目提供基于知识库的智能问答能力

## 📖 简介

RAG（Retrieval-Augmented Generation，检索增强生成）服务是 CLAW.AI 的核心功能之一。它结合了向量检索和大语言生成模型，能够从自定义知识库中检索相关信息，并基于这些信息生成准确、有据可查的回答。

### 核心特性

- 🚀 **高性能**: 基于 Milvus 向量数据库，毫秒级响应
- 🎯 **高准确率**: 使用 Zhipu AI GLM-4 模型，生成质量高
- 🔍 **智能检索**: 向量相似度搜索，精准匹配相关文档
- 📚 **知识库管理**: 支持多个知识库，灵活组织文档
- 💾 **自动索引**: 文档上传自动分块、向量化、索引
- 🔄 **引用溯源**: 自动标注来源，可追溯答案依据
- ⚡ **缓存优化**: Redis 缓存 Embedding，减少 API 调用
- 🛡️ **安全可靠**: 完整的认证授权和错误处理

## 🏗️ 架构

```
用户提问
    ↓
【1】关键词提取（可选）
    ↓
【2】向量检索（Milvus）
    ↓   Top-K 相似文档片段
    ↓
【3】上下文构建
    ↓   拼接文本块（自动截断）
    ↓
【4】增强生成（GLM-4）
    ↓   基于上下文生成回答
    ↓
【5】返回结果
    ↓   回答 + 引用来源 + 元数据
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 向量数据库 | Milvus 2.3+ | 高性能向量检索 |
| 向量化 | Zhipu AI embedding-2 | 1024 维向量 |
| 生成模型 | Zhipu AI GLM-4 | 对话生成 |
| 缓存 | Redis | Embedding 缓存 |
| 数据库 | PostgreSQL | 元数据存储 |
| 后端框架 | FastAPI | RESTful API |
| 部署 | Docker Compose | 容器化部署 |

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Docker & Docker Compose
- Zhipu AI API Key

### 1. 环境检查

```bash
# 运行环境检查脚本
python scripts/check_rag_env.py
```

### 2. 启动服务

```bash
# 启动所有服务（包括 Milvus）
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 3. 创建知识库

```bash
# 登录获取 Token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'

# 创建知识库
curl -X POST "http://localhost:8000/api/v1/knowledge/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档",
    "description": "产品相关文档"
  }'
```

### 4. 添加文档

```bash
# 添加文档（自动索引）
curl -X POST "http://localhost:8000/api/v1/knowledge/1/documents" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "用户指南",
    "content": "文档内容...",
    "file_type": "txt"
  }'
```

### 5. RAG 查询

```bash
# 使用知识库进行问答
curl -X POST "http://localhost:8000/api/v1/knowledge/1/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何注册账号？",
    "top_k": 5
  }'
```

## 📚 文档

- 📘 [RAG 服务文档](./RAG_SERVICE.md) - 完整的技术文档
- 📗 [快速开始指南](./RAG_QUICKSTART.md) - 快速上手教程
- 📕 [完成总结](./RAG_COMPLETION_SUMMARY.md) - 实现细节

## 🧪 示例代码

运行演示脚本查看完整示例：

```bash
python examples/rag_demo.py
```

演示包含：
- 创建知识库
- 添加 5 个示例文档
- 执行 5 个 RAG 查询
- 向量搜索测试

## 📁 项目结构

```
claw-ai-backend/
├── app/
│   ├── services/
│   │   ├── vector_service.py    # 向量服务
│   │   ├── rag_service.py      # RAG 服务
│   │   └── conversation_service.py  # 对话服务（已更新）
│   ├── api/
│   │   └── knowledge.py        # 知识库 API
│   └── core/
│       └── config.py           # 配置（已更新）
├── docs/
│   ├── RAG_SERVICE.md          # 服务文档
│   ├── RAG_QUICKSTART.md       # 快速开始
│   └── RAG_COMPLETION_SUMMARY.md  # 完成总结
├── examples/
│   └── rag_demo.py             # 演示脚本
├── scripts/
│   └── check_rag_env.py        # 环境检查
├── docker-compose.prod.yml     # Docker Compose（已更新）
└── requirements.txt            # 依赖（已更新）
```

## 🔧 配置

### 环境变量

```bash
# Milvus 配置
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=knowledge_vectors
MILVUS_DIMENSION=1024

# RAG 配置
RAG_TOP_K=5                    # 检索最相似的 K 个文档片段
RAG_CHUNK_SIZE=500             # 文档分块大小（字符数）
RAG_CHUNK_OVERLAP=50            # 分块重叠大小
RAG_REDIS_CACHE_TTL=3600        # Redis 缓存时间（秒）

# Zhipu AI
ZHIPUAI_API_KEY=your_api_key
ZHIPUAI_MODEL=glm-4

# MinIO（Milvus 依赖）
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Milvus 集合 Schema

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT64 | 主键（自增） |
| knowledge_base_id | INT64 | 知识库 ID |
| document_id | INT64 | 文档 ID |
| chunk_index | INT64 | 文本块索引 |
| text | VARCHAR | 文本内容 |
| embedding | FLOAT_VECTOR | 向量（1024 维） |

### 向量索引

- **索引类型**: HNSW
- **距离度量**: COSINE
- **参数**: M=16, efConstruction=256

## 📊 API 端点

### 知识库管理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/knowledge/` | 创建知识库 |
| GET | `/api/v1/knowledge/` | 获取知识库列表 |
| GET | `/api/v1/knowledge/{id}` | 获取知识库详情 |
| PUT | `/api/v1/knowledge/{id}` | 更新知识库 |
| DELETE | `/api/v1/knowledge/{id}` | 删除知识库 |

### 文档管理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/knowledge/{kb_id}/documents` | 添加文档 |
| GET | `/api/v1/knowledge/{kb_id}/documents` | 获取文档列表 |
| GET | `/api/v1/knowledge/{kb_id}/documents/{doc_id}` | 获取文档详情 |
| DELETE | `/api/v1/knowledge/{kb_id}/documents/{doc_id}` | 删除文档 |

### RAG 查询

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/knowledge/{kb_id}/query` | 查询单个知识库 |
| POST | `/api/v1/knowledge/query` | 查询所有知识库 |

## 🔍 使用场景

### 1. 客服问答

将产品文档、FAQ、用户手册等上传到知识库，用户提问时自动从知识库中检索相关内容并生成回答。

### 2. 企业知识管理

企业内部文档、制度、流程等上传到知识库，员工可以快速查询相关信息。

### 3. 教育培训

将课程材料、讲义、练习题等上传到知识库，学生可以随时提问并获得基于教材的解答。

### 4. 技术支持

将技术文档、故障排除指南等上传到知识库，技术人员或用户可以快速查找解决方案。

## 🎯 核心优势

### 相比传统搜索

| 特性 | 传统搜索 | RAG |
|------|----------|-----|
| 理解能力 | 关键词匹配 | 语义理解 |
| 回答方式 | 返回文档列表 | 生成自然语言回答 |
| 上下文 | 无上下文 | 融合多文档上下文 |
| 准确性 | 依赖关键词 | 语义相似度 |

### 相比纯 LLM

| 特性 | 纯 LLM | RAG |
|------|--------|-----|
| 知识来源 | 训练数据 | 自定义知识库 |
| 准确性 | 可能幻觉 | 基于事实 |
| 更新性 | 需重新训练 | 实时更新 |
| 可追溯性 | 无 | 明确引用来源 |

## 🚧 性能指标

- **向量检索**: < 100ms (Top-K=5)
- **Embedding 生成**: < 500ms (首次)
- **RAG 总响应**: < 2s (包含生成)
- **并发支持**: 100+ QPS

## 🛡️ 安全性

- ✅ JWT 认证
- ✅ 用户权限隔离
- ✅ 数据加密传输
- ✅ SQL 注入防护
- ✅ XSS 防护

## 📈 监控和维护

### 健康检查

```bash
# Milvus
curl http://localhost:9091/healthz

# 后端
curl http://localhost:8000/health
```

### 日志查看

```bash
# Milvus 日志
docker logs claw_ai_milvus

# 后端 RAG 日志
docker logs claw_ai_backend | grep "RAG"
```

## 🔮 未来规划

- [ ] 支持更多文件格式（PDF、Word 解析）
- [ ] 混合检索（关键词 + 向量）
- [ ] 重排序（Reranking）
- [ ] 多模态支持（图片、视频）
- [ ] 知识图谱集成
- [ ] 增量更新
- [ ] 联邦检索
- [ ] 多语言支持

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 支持

如有问题，请参考：
- 📘 [RAG 服务文档](./RAG_SERVICE.md)
- 📗 [快速开始指南](./RAG_QUICKSTART.md)
- 📧 Email: support@clawai.com

---

**版本**: v1.0.0
**更新时间**: 2025-02-18
**维护者**: CLAW.AI Team
