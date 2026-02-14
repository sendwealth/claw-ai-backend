# CLAW.AI API 参考文档

本文档提供 CLAW.AI 后端 API 的完整参考，包括所有端点、请求/响应格式和错误码。

---

## 目录

- [API 概述](#api-概述)
- [认证方式](#认证方式)
- [通用响应格式](#通用响应格式)
- [错误码说明](#错误码说明)
- [API 端点](#api-端点)
  - [认证 API](#认证-api)
  - [用户 API](#用户-api)
  - [对话 API](#对话-api)
  - [知识库 API](#知识库-api)
  - [咨询 API](#咨询-api)
  - [配置管理 API](#配置管理-api)
  - [任务管理 API](#任务管理-api)
  - [限流管理 API](#限流管理-api)
  - [缓存管理 API](#缓存管理-api)
  - [WebSocket API](#websocket-api)

---

## API 概述

### Base URL

- **开发环境**: `http://localhost:8000`
- **生产环境**: `https://api.claw.ai`

### API 版本

当前 API 版本: `v1`

所有 API 端点都以 `/api/v1` 开头。

### 请求格式

- Content-Type: `application/json`
- 编码: `UTF-8`

### 响应格式

- Content-Type: `application/json`
- 编码: `UTF-8`

---

## 认证方式

CLAW.AI 使用 JWT (JSON Web Token) 进行身份认证。

### 获取 Token

通过登录接口获取 Access Token 和 Refresh Token。

```bash
POST /api/v1/auth/login
```

### 使用 Token

在请求头中携带 Token：

```http
Authorization: Bearer {access_token}
```

### Token 有效期

- **Access Token**: 60 分钟
- **Refresh Token**: 7 天

### 刷新 Token

当 Access Token 过期时，使用 Refresh Token 获取新的 Access Token：

```bash
POST /api/v1/auth/refresh
```

**请求体**:

```json
{
  "refresh_token": "your-refresh-token"
}
```

**响应**:

```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token"
}
```

---

## 通用响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "error message",
  "detail": "detailed error information"
}
```

### 分页响应

```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "items": [ ... ]
}
```

---

## 错误码说明

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误 |
| 401 | 401 | 未认证 |
| 403 | 403 | 无权限 |
| 404 | 404 | 资源不存在 |
| 429 | 429 | 请求过于频繁 |
| 500 | 500 | 服务器内部错误 |

### 常见错误码详情

#### 400 Bad Request

请求参数错误或缺失必需参数。

**响应示例**:

```json
{
  "code": 400,
  "message": "Validation Error",
  "detail": [
    {
      "field": "email",
      "message": "Invalid email format"
    }
  ]
}
```

#### 401 Unauthorized

未提供有效的认证信息或 Token 过期。

**响应示例**:

```json
{
  "code": 401,
  "message": "Unauthorized",
  "detail": "Invalid or expired token"
}
```

#### 403 Forbidden

已认证但无权限访问该资源。

**响应示例**:

```json
{
  "code": 403,
  "message": "Forbidden",
  "detail": "You do not have permission to access this resource"
}
```

#### 404 Not Found

请求的资源不存在。

**响应示例**:

```json
{
  "code": 404,
  "message": "Not Found",
  "detail": "Conversation with id 999 does not exist"
}
```

#### 429 Too Many Requests

超过 API 调用频率限制。

**响应示例**:

```json
{
  "code": 429,
  "message": "Too Many Requests",
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60
}
```

#### 500 Internal Server Error

服务器内部错误。

**响应示例**:

```json
{
  "code": 500,
  "message": "Internal Server Error",
  "detail": "An unexpected error occurred"
}
```

---

## API 端点

### 认证 API

#### 1. 用户注册

创建新用户账户。

**端点**: `POST /api/v1/auth/register`

**认证**: 不需要

**请求参数**:

```json
{
  "email": "string (required)",
  "password": "string (required, min 8 chars)",
  "name": "string (required)",
  "phone": "string (optional)",
  "company": "string (optional)"
}
```

**响应示例**:

```json
{
  "success": true,
  "message": "注册成功",
  "data": {
    "user_id": 123
  }
}
```

**错误码**: 400, 409 (邮箱已存在), 500

---

#### 2. 用户登录

用户登录获取 Token。

**端点**: `POST /api/v1/auth/login`

**认证**: 不需要

**请求参数**:

```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**响应示例**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**错误码**: 400, 401 (密码错误), 403 (账户被禁用), 500

---

#### 3. 获取当前用户信息

获取当前登录用户的详细信息。

**端点**: `GET /api/v1/auth/me`

**认证**: 需要

**响应示例**:

```json
{
  "id": 123,
  "email": "user@example.com",
  "name": "张三",
  "phone": "13800138000",
  "company": "示例公司",
  "is_active": true,
  "created_at": "2024-02-14T10:00:00Z",
  "updated_at": "2024-02-14T10:00:00Z"
}
```

**错误码**: 401, 404, 500

---

#### 4. 刷新 Token

使用 Refresh Token 获取新的 Access Token。

**端点**: `POST /api/v1/auth/refresh`

**认证**: 不需要

**请求参数**:

```json
{
  "refresh_token": "string (required)"
}
```

**响应示例**:

```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token"
}
```

**错误码**: 400, 401 (Refresh Token 无效), 500

---

### 用户 API

#### 1. 更新用户信息

更新当前用户的信息。

**端点**: `PUT /api/v1/users/me`

**认证**: 需要

**请求参数**:

```json
{
  "name": "string (optional)",
  "phone": "string (optional)",
  "company": "string (optional)"
}
```

**响应示例**:

```json
{
  "id": 123,
  "email": "user@example.com",
  "name": "张三",
  "phone": "13800138000",
  "company": "示例公司"
}
```

**错误码**: 400, 401, 500

---

#### 2. 获取用户统计信息

获取当前用户的使用统计数据。

**端点**: `GET /api/v1/users/stats`

**认证**: 需要

**响应示例**:

```json
{
  "conversations_count": 50,
  "messages_count": 1250,
  "knowledge_bases_count": 5,
  "documents_count": 100,
  "total_tokens": 50000,
  "total_cost": 1.25
}
```

**错误码**: 401, 500

---

### 对话 API

#### 1. 创建对话

创建新的对话会话。

**端点**: `POST /api/v1/conversations`

**认证**: 需要

**请求参数**:

```json
{
  "title": "string (required)",
  "model": "string (required)",
  "conversation_type": "string (required)",
  "system_prompt": "string (optional)"
}
```

**字段说明**:
- `model`: 可选值：`glm-4`, `glm-3-turbo`
- `conversation_type`: 可选值：`chat`, `consulting`

**响应示例**:

```json
{
  "id": 1,
  "user_id": 123,
  "title": "产品咨询",
  "status": "active",
  "conversation_type": "chat",
  "model": "glm-4",
  "created_at": "2024-02-14T10:00:00Z",
  "updated_at": "2024-02-14T10:00:00Z"
}
```

**错误码**: 400, 401, 500

---

#### 2. 获取对话列表

获取当前用户的所有对话。

**端点**: `GET /api/v1/conversations`

**认证**: 需要

**查询参数**:
- `skip`: 跳过数量，默认 0
- `limit`: 返回数量，默认 100

**响应示例**:

```json
[
  {
    "id": 1,
    "title": "产品咨询",
    "status": "active",
    "model": "glm-4",
    "created_at": "2024-02-14T10:00:00Z",
    "updated_at": "2024-02-14T10:00:00Z"
  }
]
```

**错误码**: 401, 500

---

#### 3. 获取对话详情

获取指定对话的详细信息，包括所有消息。

**端点**: `GET /api/v1/conversations/{conversation_id}`

**认证**: 需要

**路径参数**:
- `conversation_id`: 对话 ID

**响应示例**:

```json
{
  "id": 1,
  "title": "产品咨询",
  "status": "active",
  "conversation_type": "chat",
  "model": "glm-4",
  "created_at": "2024-02-14T10:00:00Z",
  "updated_at": "2024-02-14T10:00:00Z",
  "messages": [
    {
      "id": 1,
      "content": "你好",
      "role": "user",
      "created_at": "2024-02-14T10:00:00Z"
    },
    {
      "id": 2,
      "content": "你好！有什么可以帮助你的吗？",
      "role": "assistant",
      "created_at": "2024-02-14T10:00:05Z"
    }
  ]
}
```

**错误码**: 401, 404, 500

---

#### 4. 更新对话

更新对话信息。

**端点**: `PUT /api/v1/conversations/{conversation_id}`

**认证**: 需要

**路径参数**:
- `conversation_id`: 对话 ID

**请求参数**:

```json
{
  "title": "string (optional)",
  "status": "string (optional)",
  "system_prompt": "string (optional)"
}
```

**字段说明**:
- `status`: 可选值：`active`, `completed`, `archived`

**响应示例**:

```json
{
  "id": 1,
  "title": "产品咨询 - 已完成",
  "status": "completed",
  "updated_at": "2024-02-14T11:00:00Z"
}
```

**错误码**: 400, 401, 404, 500

---

#### 5. 删除对话

删除指定对话。

**端点**: `DELETE /api/v1/conversations/{conversation_id}`

**认证**: 需要

**路径参数**:
- `conversation_id`: 对话 ID

**响应**: 204 No Content

**错误码**: 401, 404, 500

---

#### 6. 发送消息

向对话发送消息并获取 AI 响应。

**端点**: `POST /api/v1/conversations/{conversation_id}/chat`

**认证**: 需要

**路径参数**:
- `conversation_id`: 对话 ID

**请求体**: 纯文本消息

```
用户消息内容
```

**响应示例**:

```json
{
  "content": "AI 响应内容",
  "message_id": 3,
  "tokens": {
    "prompt": 15,
    "completion": 100,
    "total": 115
  },
  "cost": 0.0023
}
```

**错误码**: 400, 401, 404, 500

---

#### 7. 获取对话消息列表

获取对话的所有消息。

**端点**: `GET /api/v1/conversations/{conversation_id}/messages`

**认证**: 需要

**路径参数**:
- `conversation_id`: 对话 ID

**查询参数**:
- `skip`: 跳过数量，默认 0
- `limit`: 返回数量，默认 100

**响应示例**:

```json
{
  "total": 2,
  "items": [
    {
      "id": 1,
      "content": "你好",
      "role": "user",
      "created_at": "2024-02-14T10:00:00Z"
    },
    {
      "id": 2,
      "content": "你好！有什么可以帮助你的吗？",
      "role": "assistant",
      "created_at": "2024-02-14T10:00:05Z"
    }
  ]
}
```

**错误码**: 401, 404, 500

---

### 知识库 API

#### 1. 创建知识库

创建新的知识库。

**端点**: `POST /api/v1/knowledge`

**认证**: 需要

**请求参数**:

```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "embedding_model": "string (optional, default: text-embedding-ada-002)"
}
```

**响应示例**:

```json
{
  "id": 1,
  "name": "产品文档",
  "description": "公司产品相关文档",
  "embedding_model": "text-embedding-ada-002",
  "document_count": 0,
  "created_at": "2024-02-14T10:00:00Z",
  "updated_at": "2024-02-14T10:00:00Z"
}
```

**错误码**: 400, 401, 500

---

#### 2. 获取知识库列表

获取当前用户的所有知识库。

**端点**: `GET /api/v1/knowledge`

**认证**: 需要

**查询参数**:
- `skip`: 跳过数量，默认 0
- `limit`: 返回数量，默认 100

**响应示例**:

```json
[
  {
    "id": 1,
    "name": "产品文档",
    "description": "公司产品相关文档",
    "document_count": 15,
    "created_at": "2024-02-14T10:00:00Z"
  }
]
```

**错误码**: 401, 500

---

#### 3. 获取知识库详情

获取指定知识库的详细信息，包括文档列表。

**端点**: `GET /api/v1/knowledge/{knowledge_base_id}`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID

**响应示例**:

```json
{
  "id": 1,
  "name": "产品文档",
  "description": "公司产品相关文档",
  "embedding_model": "text-embedding-ada-002",
  "document_count": 2,
  "created_at": "2024-02-14T10:00:00Z",
  "documents": [
    {
      "id": 1,
      "title": "产品功能说明",
      "file_type": "pdf",
      "chunk_count": 10,
      "created_at": "2024-02-14T10:00:00Z"
    }
  ]
}
```

**错误码**: 401, 404, 500

---

#### 4. 更新知识库

更新知识库信息。

**端点**: `PUT /api/v1/knowledge/{knowledge_base_id}`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID

**请求参数**:

```json
{
  "name": "string (optional)",
  "description": "string (optional)"
}
```

**响应示例**:

```json
{
  "id": 1,
  "name": "产品文档 v2",
  "description": "更新后的描述",
  "document_count": 15,
  "updated_at": "2024-02-14T11:00:00Z"
}
```

**错误码**: 400, 401, 404, 500

---

#### 5. 删除知识库

删除知识库及其所有文档和向量索引。

**端点**: `DELETE /api/v1/knowledge/{knowledge_base_id}`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID

**响应示例**:

```json
{
  "message": "知识库删除成功"
}
```

**错误码**: 401, 404, 500

---

#### 6. 创建文档

向知识库添加文档。

**端点**: `POST /api/v1/knowledge/{knowledge_base_id}/documents`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID

**请求参数**:

```json
{
  "title": "string (required)",
  "content": "string (required)",
  "file_url": "string (optional)",
  "file_type": "string (optional)"
}
```

**响应示例**:

```json
{
  "id": 1,
  "knowledge_base_id": 1,
  "title": "产品功能说明",
  "file_url": "https://example.com/docs/product.pdf",
  "file_type": "pdf",
  "chunk_count": 10,
  "indexed": true,
  "created_at": "2024-02-14T10:00:00Z"
}
```

**错误码**: 400, 401, 404, 500

---

#### 7. 获取知识库文档列表

获取知识库的所有文档。

**端点**: `GET /api/v1/knowledge/{knowledge_base_id}/documents`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID

**查询参数**:
- `skip`: 跳过数量，默认 0
- `limit`: 返回数量，默认 100

**响应示例**:

```json
{
  "total": 10,
  "items": [
    {
      "id": 1,
      "title": "产品功能说明",
      "file_type": "pdf",
      "chunk_count": 10,
      "created_at": "2024-02-14T10:00:00Z"
    }
  ]
}
```

**错误码**: 401, 404, 500

---

#### 8. 删除文档

删除知识库中的文档及其向量索引。

**端点**: `DELETE /api/v1/knowledge/{knowledge_base_id}/documents/{document_id}`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID
- `document_id`: 文档 ID

**响应示例**:

```json
{
  "message": "文档删除成功"
}
```

**错误码**: 401, 404, 500

---

#### 9. RAG 查询

使用知识库进行检索增强生成查询。

**端点**: `POST /api/v1/knowledge/{knowledge_base_id}/query`

**认证**: 需要

**路径参数**:
- `knowledge_base_id`: 知识库 ID

**查询参数**:
- `question`: 查询问题
- `top_k`: 返回最相关的文档片段数量，默认 5

**响应示例**:

```json
{
  "question": "产品有哪些功能",
  "answer": "根据知识库，产品主要功能包括...",
  "sources": [
    {
      "document_id": 1,
      "title": "产品功能说明",
      "content": "产品功能说明的详细内容...",
      "score": 0.95
    }
  ]
}
```

**错误码**: 400, 401, 404, 500

---

#### 10. 全部知识库查询

使用用户的所有知识库进行 RAG 查询。

**端点**: `POST /api/v1/knowledge/query`

**认证**: 需要

**查询参数**:
- `question`: 查询问题
- `top_k`: 返回最相关的文档片段数量，默认 5

**响应格式**: 同上

**错误码**: 400, 401, 500

---

### 咨询 API

#### 1. 创建咨询项目

创建新的咨询项目。

**端点**: `POST /api/v1/consulting/projects`

**认证**: 需要

**请求参数**:

```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "knowledge_base_ids": [1, 2] (optional)
}
```

**响应示例**:

```json
{
  "id": 1,
  "title": "技术咨询",
  "description": "需要技术方面的咨询服务",
  "knowledge_base_ids": [1, 2],
  "created_at": "2024-02-14T10:00:00Z"
}
```

**错误码**: 400, 401, 500

---

#### 2. 提交咨询

向咨询项目提交问题。

**端点**: `POST /api/v1/consulting/projects/{project_id}/consult`

**认证**: 需要

**路径参数**:
- `project_id`: 咨询项目 ID

**请求体**: 纯文本问题

**响应示例**:

```json
{
  "answer": "根据咨询项目的知识库，这是针对您问题的解答...",
  "sources": [...]
}
```

**错误码**: 401, 404, 500

---

### 配置管理 API

#### 1. 获取配置

获取系统或用户的配置。

**端点**: `GET /api/v1/configs/{config_key}`

**认证**: 需要

**响应示例**:

```json
{
  "key": "model",
  "value": "glm-4",
  "description": "默认 AI 模型"
}
```

**错误码**: 401, 404, 500

---

#### 2. 更新配置

更新配置值。

**端点**: `PUT /api/v1/configs/{config_key}`

**认证**: 需要

**请求参数**:

```json
{
  "value": "string (required)"
}
```

**响应示例**:

```json
{
  "key": "model",
  "value": "glm-3-turbo",
  "updated_at": "2024-02-14T11:00:00Z"
}
```

**错误码**: 400, 401, 404, 500

---

### 任务管理 API

#### 1. 获取任务列表

获取异步任务的列表。

**端点**: `GET /api/v1/tasks`

**认证**: 需要

**查询参数**:
- `status`: 任务状态（pending, running, completed, failed）
- `skip`: 跳过数量
- `limit`: 返回数量

**响应示例**:

```json
{
  "total": 10,
  "items": [
    {
      "id": "task-123",
      "type": "document_indexing",
      "status": "completed",
      "created_at": "2024-02-14T10:00:00Z",
      "updated_at": "2024-02-14T10:05:00Z"
    }
  ]
}
```

**错误码**: 401, 500

---

#### 2. 获取任务状态

获取指定任务的状态。

**端点**: `GET /api/v1/tasks/{task_id}`

**认证**: 需要

**响应示例**:

```json
{
  "id": "task-123",
  "type": "document_indexing",
  "status": "running",
  "progress": 75,
  "created_at": "2024-02-14T10:00:00Z",
  "updated_at": "2024-02-14T10:03:00Z"
}
```

**错误码**: 401, 404, 500

---

### 限流管理 API

#### 1. 获取限流配置

获取当前用户的限流配置。

**端点**: `GET /api/v1/rate-limit/config`

**认证**: 需要

**响应示例**:

```json
{
  "requests_per_minute": 60,
  "requests_per_hour": 1000,
  "requests_per_day": 10000
}
```

**错误码**: 401, 500

---

#### 2. 获取当前配额

获取当前用户的剩余配额。

**端点**: `GET /api/v1/rate-limit/quota`

**认证**: 需要

**响应示例**:

```json
{
  "requests_remaining": 45,
  "requests_limit": 60,
  "reset_time": "2024-02-14T11:00:00Z"
}
```

**错误码**: 401, 500

---

### 缓存管理 API

#### 1. 清除缓存

清除指定缓存。

**端点**: `DELETE /api/v1/cache/{cache_key}`

**认证**: 需要

**响应示例**:

```json
{
  "success": true,
  "message": "缓存清除成功"
}
```

**错误码**: 401, 500

---

#### 2. 清除所有缓存

清除当前用户的所有缓存。

**端点**: `DELETE /api/v1/cache`

**认证**: 需要

**响应示例**:

```json
{
  "success": true,
  "message": "所有缓存清除成功"
}
```

**错误码**: 401, 500

---

### WebSocket API

#### 实时对话

通过 WebSocket 建立实时对话连接。

**连接 URL**: `ws://localhost:8000/api/v1/ws/{conversation_id}?token={access_token}`

**消息格式**:

客户端发送:

```json
{
  "type": "message",
  "content": "用户消息"
}
```

服务器发送:

```json
{
  "type": "message",
  "content": "AI 响应",
  "role": "assistant",
  "message_id": 123,
  "tokens": {
    "prompt": 10,
    "completion": 50,
    "total": 60
  }
}
```

**事件类型**:

| 事件类型 | 说明 |
|---------|------|
| message | 消息 |
| typing | 输入状态 |
| error | 错误 |
| close | 连接关闭 |

**示例**:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/1?token=YOUR_TOKEN');

ws.onopen = () => {
  console.log('Connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

// 发送消息
ws.send(JSON.stringify({
  type: 'message',
  content: '你好'
}));
```

---

## 健康检查

### 健康检查端点

检查服务健康状态。

**端点**: `GET /health`

**认证**: 不需要

**响应示例**:

```json
{
  "status": "healthy",
  "app": "CLAW.AI",
  "version": "1.0.0"
}
```

---

## Prometheus 指标

### 指标端点

获取 Prometheus 格式的监控指标。

**端点**: `GET /metrics`

**认证**: 不需要

**响应**: Prometheus 指标格式

---

## SDK 和客户端

### Python SDK

```python
from claw_ai import CLAWClient

# 初始化客户端
client = CLAWClient(
    api_key="your-access-token",
    base_url="https://api.claw.ai"
)

# 创建对话
conversation = client.conversations.create(
    title="产品咨询",
    model="glm-4"
)

# 发送消息
response = client.conversations.chat(
    conversation_id=conversation.id,
    message="你好"
)

print(response.content)
```

### JavaScript SDK

```javascript
import { CLAWClient } from 'claw-ai-sdk';

const client = new CLAWClient({
  apiKey: 'your-access-token',
  baseUrl: 'https://api.claw.ai'
});

// 创建对话
const conversation = await client.conversations.create({
  title: '产品咨询',
  model: 'glm-4'
});

// 发送消息
const response = await client.conversations.chat({
  conversationId: conversation.id,
  message: '你好'
});

console.log(response.content);
```

---

## 变更日志

### v1.0.0 (2024-02-14)
- 初始版本发布
- 认证 API
- 用户 API
- 对话 API
- 知识库 API
- 咨询 API
- WebSocket API

---

## 获取帮助

如果您在 API 使用过程中遇到问题：

1. 📖 查看 [用户手册](USER_MANUAL.md)
2. 🔧 参考 [故障排查指南](TROUBLESHOOTING.md)
3. ❓ 查看 [常见问题](FAQ.md)
4. 📧 联系 API 支持：api-support@openspark.online

---

*最后更新：2024-02-14*
