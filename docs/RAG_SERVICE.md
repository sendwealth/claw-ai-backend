# RAG 服务文档

## 概述

RAG（Retrieval-Augmented Generation，检索增强生成）服务为 CLAW.AI 项目提供了基于知识库的智能问答能力。它结合了向量检索和大语言生成模型，能够从知识库中检索相关信息并生成准确的回答。

## 架构设计

### 核心组件

1. **VectorService** (`app/services/vector_service.py`)
   - 管理 Milvus 向量数据库连接
   - 文档分块和向量化
   - 向量相似度搜索
   - Embedding 缓存（Redis）

2. **RAGService** (`app/services/rag_service.py`)
   - 完整的 RAG 流程编排
   - 上下文构建
   - 增强生成
   - 知识库索引管理

3. **Knowledge API** (`app/api/knowledge.py`)
   - 知识库 CRUD 接口
   - 文档管理接口
   - RAG 查询接口

### RAG 流程

```
用户提问
    ↓
提取关键词（可选）
    ↓
向量检索（Milvus）
    ↓
构建上下文
    ↓
增强生成（GLM-4）
    ↓
返回结果 + 引用来源
```

### 数据流

```
文档上传
    ↓
文本分块（Chunking）
    ↓
向量化（Embedding API）
    ↓
存储到 Milvus
    ↓
可用于检索
```

## 技术栈

- **向量数据库**: Milvus 2.3+
- **向量化**: Zhipu AI Embedding API (embedding-2)
- **生成模型**: Zhipu AI GLM-4
- **缓存**: Redis
- **数据库**: PostgreSQL
- **后端框架**: FastAPI

## 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# Milvus 配置
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=knowledge_vectors
MILVUS_DIMENSION=1024

# RAG 配置
RAG_TOP_K=5                      # 检索最相似的 K 个文档片段
RAG_CHUNK_SIZE=500               # 文档分块大小（字符数）
RAG_CHUNK_OVERLAP=50             # 分块重叠大小
RAG_REDIS_CACHE_TTL=3600         # Redis 缓存时间（秒）

# MinIO 配置（Milvus 依赖）
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Milvus 集合 Schema

Milvus 集合包含以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT64 | 主键（自增） |
| knowledge_base_id | INT64 | 知识库 ID |
| document_id | INT64 | 文档 ID |
| chunk_index | INT64 | 文本块索引 |
| text | VARCHAR | 文本内容 |
| embedding | FLOAT_VECTOR | 向量表示（1024 维） |

### 向量索引

- **索引类型**: HNSW
- **距离度量**: COSINE
- **参数**:
  - M: 16
  - efConstruction: 256

## API 使用指南

### 1. 创建知识库

```bash
POST /api/knowledge/
Authorization: Bearer <token>

{
  "name": "产品手册",
  "description": "公司产品相关的文档",
  "embedding_model": "embedding-2"
}
```

### 2. 添加文档

```bash
POST /api/knowledge/{knowledge_base_id}/documents
Authorization: Bearer <token>

{
  "title": "用户指南 v1.0",
  "content": "这里是文档内容...",
  "file_type": "txt"
}
```

文档会自动：
1. 分块（默认 500 字符/块）
2. 向量化（调用 Zhipu AI Embedding API）
3. 存储到 Milvus

### 3. RAG 查询

#### 查询单个知识库

```bash
POST /api/knowledge/{knowledge_base_id}/query
Authorization: Bearer <token>

{
  "question": "如何注册账号？",
  "top_k": 5
}
```

#### 查询所有知识库

```bash
POST /api/knowledge/query
Authorization: Bearer <token>

{
  "question": "产品定价是多少？",
  "top_k": 5
}
```

### 4. 响应格式

```json
{
  "success": true,
  "answer": "根据产品文档，账号注册流程如下：\n1. 访问官网\n2. 点击注册按钮...",
  "sources": [
    {
      "document_id": 123,
      "title": "用户指南 v1.0",
      "score": 0.856
    },
    {
      "document_id": 124,
      "title": "FAQ 文档",
      "score": 0.723
    }
  ],
  "context": "【来源 1】用户指南 v1.0 (相似度: 0.856)\n...",
  "tokens": {
    "prompt": 1523,
    "completion": 389,
    "total": 1912
  },
  "cost": 0.0382,
  "rag_enabled": true,
  "search_results_count": 5
}
```

## 在对话服务中集成 RAG

### 创建 RAG 对话

在创建对话时，可以指定使用知识库：

```python
from app.services.conversation_service import ConversationService

conversation_service = ConversationService(db)

# 创建对话
conversation = conversation_service.create_conversation(
    user_id=user_id,
    conversation_data=ConversationCreate(
        title="产品咨询",
        conversation_type="rag",  # 标记为 RAG 对话
        system_prompt="你是一个专业的产品顾问。",
    ),
)

# 使用 RAG 生成响应
result = await conversation_service.generate_rag_response(
    conversation_id=conversation.id,
    user_id=user_id,
    user_message="如何退款？",
    knowledge_base_id=1,  # 指定知识库
    top_k=5,
)
```

### WebSocket 集成

在 WebSocket 消息中支持 RAG：

```python
# 客户端发送消息
{
  "conversation_id": 123,
  "message": "如何使用 API？",
  "use_rag": true,
  "knowledge_base_id": 1
}

# 服务端处理
if message_data.get("use_rag"):
    result = await conversation_service.generate_rag_response(
        conversation_id=conversation_id,
        user_id=current_user.id,
        user_message=message_data["message"],
        knowledge_base_id=message_data.get("knowledge_base_id"),
    )
else:
    result = await conversation_service.generate_ai_response(...)
```

## 部署指南

### 1. 启动 Milvus 服务

```bash
# 启动所有依赖服务（包括 Milvus）
docker-compose -f docker-compose.prod.yml up -d postgres redis etcd minio milvus-standalone

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 2. 启动后端服务

```bash
# 启动后端
docker-compose -f docker-compose.prod.yml up -d claw-ai-backend

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f claw-ai-backend
```

### 3. 验证连接

```python
from app.services.vector_service import vector_service

# 测试 Milvus 连接
try:
    vector_service._connect_milvus()
    print("✅ Milvus 连接成功")
except Exception as e:
    print(f"❌ Milvus 连接失败: {e}")
```

### 4. 健康检查

```bash
# Milvus 健康检查
curl http://localhost:9091/healthz

# 后端健康检查
curl http://localhost:8000/health
```

## 性能优化

### 1. Embedding 缓存

使用 Redis 缓存文本的向量表示，避免重复调用 API：

```python
from app.services.vector_service import vector_service

# 缓存键格式: embedding:{md5(text)}
# 默认缓存时间: 3600 秒（可配置）
```

### 2. 向量索引优化

- 调整 HNSW 参数：
  - `M`: 增大可提高召回率，但会增加内存占用
  - `efConstruction`: 增大可提高索引质量，但会降低构建速度

### 3. 检索优化

- 合理设置 `top_k` 值（推荐 5-10）
- 限制上下文长度（默认 3000 字符）
- 使用过滤条件缩小搜索范围

### 4. 批量操作

批量添加文档：

```python
async def batch_index_documents(knowledge_base_id: int, documents: List[dict]):
    """批量索引文档"""
    tasks = []
    for doc in documents:
        task = rag_service.index_document(
            knowledge_base_id=knowledge_base_id,
            document_id=doc["id"],
            text=doc["content"],
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return results
```

## 监控和维护

### 1. Milvus 监控

```bash
# 查看 Milvus 指标
curl http://localhost:9091/metrics
```

### 2. 日志查看

```bash
# 查看 Milvus 日志
docker logs claw_ai_milvus

# 查看后端 RAG 日志
docker logs claw_ai_backend | grep "RAG"
```

### 3. 数据备份

```bash
# 备份 Milvus 数据
docker exec claw_ai_milvus cp -r /var/lib/milvus /backup/milvus_$(date +%Y%m%d)

# 备份向量集合数据
# 使用 Milvus Backup 工具（需要单独部署）
```

### 4. 清理过期缓存

```bash
# 清理 Redis 中的过期 Embedding 缓存
redis-cli KEYS "embedding:*" | xargs redis-cli DEL
```

## 常见问题

### 1. Milvus 连接失败

**问题**: `Connection refused: localhost:19530`

**解决方案**:
- 检查 Milvus 服务是否运行：`docker ps | grep milvus`
- 检查环境变量 `MILVUS_HOST` 和 `MILVUS_PORT`
- 查看 Milvus 日志：`docker logs claw_ai_milvus`

### 2. 向量化失败

**问题**: `Embedding API error: ...`

**解决方案**:
- 检查 Zhipu AI API Key 是否正确
- 检查 API 配额是否用完
- 查看后端日志获取详细错误信息

### 3. 检索结果为空

**问题**: 向量搜索返回空结果

**解决方案**:
- 确认知识库中有文档
- 确认文档已成功索引（检查 `chunk_count` 字段）
- 调整 `top_k` 或搜索参数
- 检查 Milvus 集合是否有数据

### 4. 性能问题

**问题**: 查询响应慢

**解决方案**:
- 减少 `top_k` 值
- 缩小上下文长度
- 优化向量索引参数
- 增加 Milvus 资源（CPU/内存）

## 未来优化方向

1. **混合检索**: 结合关键词检索和向量检索
2. **重排序（Reranking）**: 对检索结果进行二次排序
3. **多模态支持**: 支持图片、视频等多媒体文档
4. **自动摘要**: 自动生成知识库摘要
5. **知识图谱**: 结合知识图谱增强检索
6. **增量更新**: 支持文档增量索引
7. **联邦检索**: 支持跨用户知识库检索

## 参考资料

- [Milvus 官方文档](https://milvus.io/docs)
- [Zhipu AI API 文档](https://open.bigmodel.cn/dev/api)
- [RAG 最佳实践](https://www.anthropic.com/index/retrieval-augmented-generation)

---

**文档版本**: v1.0.0
**最后更新**: 2025-02-18
**维护者**: CLAW.AI Team
