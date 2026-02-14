# RAG 服务快速开始指南

## 🚀 快速开始

### 1. 启动服务

```bash
# 启动所有服务（包括 Milvus）
cd /home/wuying/clawd/claw-ai-backend
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 2. 验证服务

```bash
# 检查 Milvus 健康状态
curl http://localhost:9091/healthz

# 检查后端健康状态
curl http://localhost:8000/health
```

### 3. 创建知识库

```bash
# 登录获取 Token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# 保存返回的 access_token

# 创建知识库
curl -X POST "http://localhost:8000/api/v1/knowledge/" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档",
    "description": "公司产品相关的文档",
    "embedding_model": "embedding-2"
  }'
```

### 4. 添加文档

```bash
# 添加文档（会自动索引）
curl -X POST "http://localhost:8000/api/v1/knowledge/1/documents" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "用户指南",
    "content": "欢迎使用我们的产品！\n\n注册流程：\n1. 访问官网\n2. 点击注册\n3. 填写信息\n4. 完成验证\n\n如有问题，请联系客服。",
    "file_type": "txt"
  }'
```

### 5. RAG 查询

```bash
# 使用知识库进行问答
curl -X POST "http://localhost:8000/api/v1/knowledge/1/query" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何注册账号？",
    "top_k": 5
  }'
```

### 6. 使用 Python SDK

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
import requests

# 配置
BASE_URL = "http://localhost:8000"
TOKEN = "your_access_token"

# 创建知识库
response = requests.post(
    f"{BASE_URL}/api/v1/knowledge/",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "name": "产品文档",
        "description": "公司产品相关的文档",
    }
)
knowledge_base = response.json()
kb_id = knowledge_base["id"]

# 添加文档
response = requests.post(
    f"{BASE_URL}/api/v1/knowledge/{kb_id}/documents",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "title": "用户指南",
        "content": "欢迎使用我们的产品！...",
        "file_type": "txt",
    }
)
document = response.json()

# RAG 查询
response = requests.post(
    f"{BASE_URL}/api/v1/knowledge/{kb_id}/query",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "question": "如何注册账号？",
        "top_k": 5,
    }
)
result = response.json()

print("回答:", result["answer"])
print("来源:", result["sources"])
```

## 📝 API 端点列表

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

## 🛠️ 常见操作

### 批量添加文档

```python
import asyncio
import requests

documents = [
    {"title": "产品介绍", "content": "..."},
    {"title": "FAQ", "content": "..."},
    {"title": "价格表", "content": "..."},
]

async def add_documents(kb_id: int, documents: list):
    tasks = []
    for doc in documents:
        task = requests.post(
            f"{BASE_URL}/api/v1/knowledge/{kb_id}/documents",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json=doc
        )
        tasks.append(task)

    # 使用 asyncio 或 concurrent.futures 并发执行
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(lambda d: d(), task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            print(future.result().json())

# 运行
add_documents(1, documents)
```

### 更新文档索引

```bash
# 删除旧文档索引
curl -X DELETE "http://localhost:8000/api/v1/knowledge/1/documents/1" \
  -H "Authorization: Bearer <your_token>"

# 重新添加文档
curl -X POST "http://localhost:8000/api/v1/knowledge/1/documents" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "用户指南（更新版）",
    "content": "新的文档内容...",
    "file_type": "txt"
  }'
```

### 查询所有知识库

```python
# 不指定 knowledge_base_id，会搜索所有知识库
response = requests.post(
    f"{BASE_URL}/api/v1/knowledge/query",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "question": "产品的价格是多少？",
        "top_k": 10,  # 可以返回更多结果
    }
)
result = response.json()

print("回答:", result["answer"])
print("找到", result["search_results_count"], "个相关文档片段")
```

## 🔍 调试技巧

### 查看日志

```bash
# 查看 Milvus 日志
docker logs -f claw_ai_milvus

# 查看后端日志
docker logs -f claw_ai_backend

# 查看 RAG 相关日志
docker logs claw_ai_backend | grep -i "rag"
```

### 检查向量集合

```python
from pymilvus import connections, Collection

# 连接 Milvus
connections.connect(host="localhost", port="19530")

# 获取集合
collection = Collection("knowledge_vectors")

# 查看集合信息
print(f"集合名称: {collection.name}")
print(f"文档数量: {collection.num_entities}")

# 查看索引信息
indexes = collection.indexes
for index in indexes:
    print(f"索引: {index.field_name}, 类型: {index.index_type}")
```

### 测试 Embedding

```python
from app.services.vector_service import vector_service

# 测试获取向量
text = "这是一段测试文本"
embedding = await vector_service.get_embedding(text)

print(f"向量维度: {len(embedding)}")
print(f"向量前 5 个值: {embedding[:5]}")
```

## 📊 性能测试

### 批量索引测试

```python
import time
import requests

# 准备测试数据
documents = [
    {"title": f"文档 {i}", "content": f"这是文档 {i} 的内容..." * 100}
    for i in range(1, 101)
]

# 批量添加文档并计时
start_time = time.time()

for doc in documents:
    response = requests.post(
        f"{BASE_URL}/api/v1/knowledge/1/documents",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=doc
    )
    if response.status_code == 200:
        print(f"✅ 添加文档: {doc['title']}")
    else:
        print(f"❌ 添加失败: {doc['title']}")

end_time = time.time()
print(f"\n总耗时: {end_time - start_time:.2f} 秒")
print(f"平均每文档: {(end_time - start_time) / len(documents):.2f} 秒")
```

### 查询性能测试

```python
import time

questions = [
    "如何注册账号？",
    "产品价格是多少？",
    "如何退款？",
    "支持哪些支付方式？",
    "如何联系客服？",
]

for q in questions:
    start = time.time()

    response = requests.post(
        f"{BASE_URL}/api/v1/knowledge/1/query",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"question": q, "top_k": 5}
    )

    elapsed = time.time() - start
    result = response.json()

    print(f"\n问题: {q}")
    print(f"耗时: {elapsed:.3f} 秒")
    print(f"RAG 启用: {result.get('rag_enabled', False)}")
    print(f"来源数: {len(result.get('sources', []))}")
```

## 🐛 故障排查

### Milvus 无法启动

```bash
# 检查依赖服务
docker-compose -f docker-compose.prod.yml logs etcd
docker-compose -f docker-compose.prod.yml logs minio

# 重启 Milvus
docker-compose -f docker-compose.prod.yml restart milvus-standalone
```

### 向量化失败

```bash
# 检查 Zhipu AI API Key
docker-compose -f docker-compose.prod.yml exec claw-ai-backend env | grep ZHIPUAI

# 测试 API 连接
curl -X POST "https://open.bigmodel.cn/api/paas/v4/embeddings" \
  -H "Authorization: Bearer <your_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"embedding-2","input":"test"}'
```

### 查询无结果

```python
# 检查集合是否有数据
from pymilvus import connections, Collection

connections.connect(host="localhost", port="19530")
collection = Collection("knowledge_vectors")
print(f"文档数量: {collection.num_entities}")

# 手动搜索测试
results = collection.search(
    data=[[0.0] * 1024],  # 使用零向量测试
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"ef": 64}},
    limit=5,
    output_fields=["text"]
)
print(f"搜索结果: {len(results[0])}")
```

## 📚 更多资源

- [完整 RAG 服务文档](./RAG_SERVICE.md)
- [Milvus 官方文档](https://milvus.io/docs)
- [FastAPI 官方文档](https://fastapi.tiangolo.com)
- [Zhipu AI API 文档](https://open.bigmodel.cn/dev/api)

---

**版本**: v1.0.0
**更新时间**: 2025-02-18
