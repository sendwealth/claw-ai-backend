# RAG 系统使用文档

## 概述

本系统实现了基于 Qdrant 向量数据库和智谱 Embedding API 的知识库 RAG（检索增强生成）功能。

## 技术栈

- **FastAPI**: Web 框架
- **Qdrant**: 向量数据库
- **智谱 Embedding API**: 文本向量化
- **PostgreSQL**: 元数据存储
- **Redis**: 向量缓存

## 系统架构

```
┌─────────────────┐
│   用户请求      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI API    │
└────────┬────────┘
         │
         ├─ 知识库管理
         ├─ 文档上传
         ├─ 文档解析
         ├─ 向量化
         └─ RAG 查询
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│   PostgreSQL    │◄────►│  Qdrant 向量库  │
│   (元数据)      │      │   (向量存储)    │
└─────────────────┘      └─────────────────┘
         │                        │
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│     Redis       │      │  智谱 Embedding │
│   (向量缓存)    │      │      API        │
└─────────────────┘      └─────────────────┘
```

## 核心功能

### 1. 知识库管理

#### 创建知识库
```bash
POST /api/v1/knowledge/
{
  "name": "技术文档库",
  "description": "存储技术相关文档",
  "embedding_model": "text-embedding-ada-002"
}
```

#### 获取知识库列表
```bash
GET /api/v1/knowledge/
```

#### 获取知识库详情
```bash
GET /api/v1/knowledge/{knowledge_base_id}
```

#### 删除知识库
```bash
DELETE /api/v1/knowledge/{knowledge_base_id}
```

### 2. 文档管理

#### 上传文档（支持文件上传）
```bash
POST /api/v1/knowledge/{knowledge_base_id}/documents/upload
Content-Type: multipart/form-data

file: @document.pdf
title: "文档标题"  # 可选
```

**支持的文件格式:**
- `.txt` - 纯文本文件
- `.md`, `.markdown` - Markdown 文档
- `.pdf` - PDF 文档

#### 创建文档（直接提供内容）
```bash
POST /api/v1/knowledge/{knowledge_base_id}/documents
{
  "title": "文档标题",
  "content": "文档内容...",
  "file_type": "txt"
}
```

#### 获取文档列表
```bash
GET /api/v1/knowledge/{knowledge_base_id}/documents
```

#### 删除文档
```bash
DELETE /api/v1/knowledge/{knowledge_base_id}/documents/{document_id}
```

### 3. RAG 查询

#### 基于知识库查询
```bash
POST /api/v1/knowledge/{knowledge_base_id}/query
{
  "question": "如何使用 Python 进行数据分析？",
  "top_k": 5
}
```

#### 全局查询（搜索所有知识库）
```bash
POST /api/v1/knowledge/query
{
  "question": "如何使用 Python 进行数据分析？",
  "top_k": 5
}
```

**响应示例:**
```json
{
  "success": true,
  "answer": "基于知识库的回答...",
  "sources": [
    {
      "document_id": 1,
      "title": "Python 数据分析指南",
      "score": 0.92
    }
  ],
  "context": "检索到的上下文内容...",
  "tokens": 150,
  "cost": 0.001,
  "rag_enabled": true,
  "search_results_count": 5
}
```

## 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# Qdrant 配置
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=                    # 可选，如果 Qdrant 启用了认证
QDRANT_COLLECTION_NAME=knowledge_vectors
QDRANT_VECTOR_SIZE=1024            # 智谱 Embedding 维度
QDRANT_DISTANCE=Cosine             # 距离度量

# 智谱 AI 配置
ZHIPUAI_API_KEY=your-api-key-here
ZHIPUAI_MODEL=glm-4

# RAG 配置
RAG_TOP_K=5                        # 检索最相似的 K 个片段
RAG_CHUNK_SIZE=500                 # 文档分块大小（字符数）
RAG_CHUNK_OVERLAP=50               # 分块重叠大小
RAG_REDIS_CACHE_TTL=3600           # Redis 缓存时间（秒）
RAG_ENABLE_CACHE=true              # 是否启用向量缓存

# 文件上传配置
MAX_UPLOAD_SIZE=10485760           # 最大文件大小（10MB）
UPLOAD_DIR=uploads                 # 上传目录
```

## 部署指南

### 1. 安装依赖

```bash
cd claw-ai-backend
pip install -r requirements.txt
```

### 2. 启动 Qdrant

使用 Docker 启动 Qdrant：

```bash
docker run -p 6333:6333 qdrant/qdrant
```

或使用 Docker Compose（推荐）：

```yaml
# docker-compose.yml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage

volumes:
  qdrant_storage:
```

### 3. 启动服务

```bash
# 开发环境
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head
```

## 性能优化

### 1. 向量缓存

启用 Redis 缓存可以显著减少 Embedding API 调用次数：

```bash
RAG_ENABLE_CACHE=true
```

### 2. 批量处理

对于大量文档，建议使用异步任务队列（Celery）进行批量索引：

```python
from app.tasks import index_document_task

# 异步索引文档
index_document_task.delay(document_id=document.id)
```

### 3. 分块策略

根据文档类型调整分块参数：

```python
# 技术文档：较大分块
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=100

# 对话记录：较小分块
RAG_CHUNK_SIZE=300
RAG_CHUNK_OVERLAP=30
```

## 监控和日志

### 健康检查

```bash
GET /health
```

### Prometheus 指标

```bash
GET /metrics
```

### 日志

日志文件位置：`logs/app.log`

日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL

## 故障排查

### 常见问题

1. **Qdrant 连接失败**
   - 检查 Qdrant 是否正常运行
   - 验证 `QDRANT_HOST` 和 `QDRANT_PORT` 配置

2. **Embedding API 调用失败**
   - 检查 `ZHIPUAI_API_KEY` 是否正确
   - 检查 API 配额是否充足

3. **文档解析失败**
   - 检查文件格式是否支持
   - 检查文件编码（建议 UTF-8）

4. **向量搜索无结果**
   - 检查文档是否已成功索引
   - 检查 `knowledge_base_id` 是否正确

## 测试

运行测试：

```bash
# 运行所有测试
pytest tests/test_rag_system.py -v

# 运行测试并生成覆盖率报告
pytest tests/test_rag_system.py --cov=app/services --cov-report=html
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 许可证

MIT License

## 联系方式

如有问题，请联系开发团队。
