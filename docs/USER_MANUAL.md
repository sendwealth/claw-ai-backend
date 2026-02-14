# CLAW.AI 用户手册

欢迎使用 CLAW.AI！本手册将帮助您了解如何使用 CLAW.AI 的各项功能。

---

## 目录

- [系统概述](#系统概述)
- [账户管理](#账户管理)
- [对话管理](#对话管理)
- [知识库管理](#知识库管理)
- [咨询服务](#咨询服务)
- [监控与统计](#监控与统计)
- [常见操作](#常见操作)

---

## 系统概述

CLAW.AI 是一个智能咨询服务平台，提供以下核心功能：

### 核心功能

| 功能 | 描述 |
|------|------|
| 💬 智能对话 | 与 AI 助手进行自然语言对话 |
| 📚 知识库管理 | 上传和管理文档，构建企业知识库 |
| 🔍 RAG 检索 | 基于知识库的精准问答 |
| 📊 数据统计 | 查看使用情况和统计分析 |
| 🤖 多模型支持 | 支持多种 AI 模型切换 |
| 🔄 对话历史 | 保存和管理对话历史 |

---

## 账户管理

### 1. 用户注册

**接口**: `POST /api/v1/auth/register`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "name": "张三",
    "phone": "13800138000",
    "company": "示例公司"
  }'
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| email | string | 是 | 邮箱地址，用于登录 |
| password | string | 是 | 密码，至少 8 位 |
| name | string | 是 | 用户姓名 |
| phone | string | 否 | 手机号码 |
| company | string | 否 | 公司名称 |

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

### 2. 用户登录

**接口**: `POST /api/v1/auth/login`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| email | string | 是 | 注册时的邮箱地址 |
| password | string | 是 | 注册时的密码 |

**响应示例**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Token 说明**:

- **Access Token**: 有效期 60 分钟，用于 API 认证
- **Refresh Token**: 有效期 7 天，用于刷新 Access Token
- 在请求头中携带: `Authorization: Bearer {access_token}`

### 3. 获取用户信息

**接口**: `GET /api/v1/auth/me`

**请求示例**:

```bash
curl -X GET https://api.claw.ai/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

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

---

## 对话管理

### 1. 创建对话

**接口**: `POST /api/v1/conversations`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/conversations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "产品咨询",
    "model": "glm-4",
    "conversation_type": "chat",
    "system_prompt": "你是一个专业的产品顾问"
  }'
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| title | string | 是 | 对话标题 |
| model | string | 是 | AI 模型，可选：glm-4, glm-3-turbo |
| conversation_type | string | 是 | 对话类型：chat, consulting |
| system_prompt | string | 否 | 系统提示词 |

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

### 2. 获取对话列表

**接口**: `GET /api/v1/conversations`

**请求示例**:

```bash
curl -X GET "https://api.claw.ai/api/v1/conversations?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| skip | integer | 否 | 跳过数量，默认 0 |
| limit | integer | 否 | 返回数量，默认 100 |

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
  },
  {
    "id": 2,
    "title": "技术支持",
    "status": "active",
    "model": "glm-4",
    "created_at": "2024-02-14T11:00:00Z",
    "updated_at": "2024-02-14T11:00:00Z"
  }
]
```

### 3. 获取对话详情

**接口**: `GET /api/v1/conversations/{conversation_id}`

**请求示例**:

```bash
curl -X GET https://api.claw.ai/api/v1/conversations/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

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
      "content": "你好，我想了解你们的产品",
      "role": "user",
      "created_at": "2024-02-14T10:00:00Z"
    },
    {
      "id": 2,
      "content": "您好！很高兴为您介绍我们的产品...",
      "role": "assistant",
      "created_at": "2024-02-14T10:00:05Z"
    }
  ]
}
```

### 4. 发送消息

**接口**: `POST /api/v1/conversations/{conversation_id}/chat`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/conversations/1/chat \
  -H "Content-Type: text/plain" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "你们的产品有哪些功能？"
```

**响应示例**:

```json
{
  "content": "我们的产品主要有以下功能：\n1. 智能对话\n2. 知识库管理\n3. RAG 检索...",
  "message_id": 3,
  "tokens": {
    "prompt": 15,
    "completion": 100,
    "total": 115
  },
  "cost": 0.0023
}
```

### 5. 更新对话

**接口**: `PUT /api/v1/conversations/{conversation_id}`

**请求示例**:

```bash
curl -X PUT https://api.claw.ai/api/v1/conversations/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "产品咨询 - 已完成",
    "status": "completed"
  }'
```

**状态说明**:

| 状态 | 说明 |
|------|------|
| active | 活跃中 |
| completed | 已完成 |
| archived | 已归档 |

### 6. 删除对话

**接口**: `DELETE /api/v1/conversations/{conversation_id}`

**请求示例**:

```bash
curl -X DELETE https://api.claw.ai/api/v1/conversations/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应**: 204 No Content

---

## 知识库管理

### 1. 创建知识库

**接口**: `POST /api/v1/knowledge`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/knowledge \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "产品文档",
    "description": "公司产品相关文档",
    "embedding_model": "text-embedding-ada-002"
  }'
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | string | 是 | 知识库名称 |
| description | string | 否 | 知识库描述 |
| embedding_model | string | 否 | 嵌入模型，默认 text-embedding-ada-002 |

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

### 2. 获取知识库列表

**接口**: `GET /api/v1/knowledge`

**请求示例**:

```bash
curl -X GET "https://api.claw.ai/api/v1/knowledge?skip=0&limit=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应示例**:

```json
[
  {
    "id": 1,
    "name": "产品文档",
    "description": "公司产品相关文档",
    "document_count": 15,
    "created_at": "2024-02-14T10:00:00Z"
  },
  {
    "id": 2,
    "name": "技术手册",
    "description": "技术实现文档",
    "document_count": 8,
    "created_at": "2024-02-14T11:00:00Z"
  }
]
```

### 3. 上传文档

**接口**: `POST /api/v1/knowledge/{knowledge_base_id}/documents`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/knowledge/1/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "产品功能说明",
    "content": "产品功能说明的详细内容...",
    "file_url": "https://example.com/docs/product.pdf",
    "file_type": "pdf"
  }'
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| title | string | 是 | 文档标题 |
| content | string | 是 | 文档内容 |
| file_url | string | 否 | 文件 URL |
| file_type | string | 否 | 文件类型：pdf, txt, md, docx |

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

### 4. 查询知识库

**接口**: `POST /api/v1/knowledge/{knowledge_base_id}/query`

**请求示例**:

```bash
curl -X POST "https://api.claw.ai/api/v1/knowledge/1/query?question=产品有哪些功能&top_k=5" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**参数说明**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| question | string | 是 | 查询问题 |
| top_k | integer | 否 | 返回最相关的文档片段数量，默认 5 |

**响应示例**:

```json
{
  "question": "产品有哪些功能",
  "answer": "根据知识库，产品主要功能包括：\n1. 智能对话\n2. 知识库管理\n3. RAG 检索...",
  "sources": [
    {
      "document_id": 1,
      "title": "产品功能说明",
      "content": "产品功能说明的详细内容...",
      "score": 0.95
    },
    {
      "document_id": 2,
      "title": "产品介绍",
      "content": "产品介绍的详细内容...",
      "score": 0.87
    }
  ]
}
```

### 5. 删除文档

**接口**: `DELETE /api/v1/knowledge/{knowledge_base_id}/documents/{document_id}`

**请求示例**:

```bash
curl -X DELETE https://api.claw.ai/api/v1/knowledge/1/documents/1 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应示例**:

```json
{
  "message": "文档删除成功"
}
```

---

## 咨询服务

### 1. 创建咨询项目

**接口**: `POST /api/v1/consulting/projects`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/consulting/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "技术咨询",
    "description": "需要技术方面的咨询服务",
    "knowledge_base_ids": [1, 2]
  }'
```

### 2. 提交咨询

**接口**: `POST /api/v1/consulting/projects/{project_id}/consult`

**请求示例**:

```bash
curl -X POST https://api.claw.ai/api/v1/consulting/projects/1/consult \
  -H "Content-Type: text/plain" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "如何优化数据库查询性能？"
```

---

## 监控与统计

### 1. 查看使用统计

**接口**: `GET /api/v1/users/stats`

**请求示例**:

```bash
curl -X GET https://api.claw.ai/api/v1/users/stats \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

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

### 2. 查看对话统计

**接口**: `GET /api/v1/conversations/stats`

**请求示例**:

```bash
curl -X GET "https://api.claw.ai/api/v1/conversations/stats?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 常见操作

### WebSocket 实时对话

CLAW.AI 支持 WebSocket 实时对话，提供更好的用户体验。

**连接 URL**: `ws://localhost:8000/api/v1/ws/{conversation_id}?token={access_token}`

**示例**:

```javascript
// JavaScript 示例
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/1?token=YOUR_ACCESS_TOKEN');

ws.onopen = () => {
  console.log('WebSocket connected');
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

### 批量导入文档

如需批量导入文档到知识库，可以使用文件上传接口：

```bash
# 上传文件
curl -X POST https://api.claw.ai/api/v1/knowledge/1/upload \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.pdf"
```

---

## 最佳实践

### 1. 知识库管理

- ✅ 将相关文档归类到同一个知识库
- ✅ 使用清晰的文档标题和描述
- ✅ 定期更新文档内容
- ❌ 避免上传重复或过时的文档

### 2. 对话管理

- ✅ 使用有意义的对话标题
- ✅ 完成的对话及时标记为 "completed"
- ✅ 定期清理不需要的对话
- ❌ 避免在一个对话中混入多个主题

### 3. 系统提示词

使用系统提示词可以定制 AI 的回答风格：

```
你是一个专业的产品顾问，请用专业、友好的语气回答用户问题。
如果不确定答案，请诚实告知用户。
```

---

## 常见问题

### Q: 如何提高知识库检索准确率？

**A**: 
1. 确保文档内容清晰、结构化
2. 使用合理的文档分块大小
3. 选择合适的嵌入模型
4. 定期更新和优化知识库

### Q: 对话历史可以保存多久？

**A**: 
对话历史会永久保存，直到用户主动删除。您可以通过对话管理 API 管理历史对话。

### Q: 如何控制 API 调用成本？

**A**: 
1. 选择合适的模型（glm-3-turbo 更便宜）
2. 合理设置上下文长度
3. 使用缓存减少重复调用
4. 定期查看使用统计

---

## 获取帮助

如果您在使用过程中遇到问题：

1. 📖 查看 [常见问题](FAQ.md)
2. 🔧 参考 [故障排查指南](TROUBLESHOOTING.md)
3. 📧 联系支持：support@openspark.online
4. 💬 加入用户社区讨论

---

**祝您使用愉快！🎉**

*最后更新：2024-02-14*
