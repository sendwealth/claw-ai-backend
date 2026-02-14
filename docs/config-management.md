# 配置管理文档

**版本：** v1.0
**更新日期：** 2026-02-14
**公司：** OpenSpark 智能科技

---

## 📋 概述

CLAW.AI 支持多种配置方式，从简单到企业级：

### 配置方式对比

| 方式 | 复杂度 | 动态更新 | 版本管理 | 适用场景 |
|------|---------|---------|---------|---------|
| 环境变量 | ⭐ | ❌ | ❌ | 开发/测试 |
| .env 文件 | ⭐⭐ | ❌ | ⚠️ | 单机部署 |
| 配置 API | ⭐⭐⭐ | ✅ | ✅ | 企业生产 |
| 配置中心 | ⭐⭐⭐⭐ | ✅ | ✅ | 大规模生产 |

---

## 🚀 快速开始

### 方式 1：环境变量（开发/测试）

```bash
# 直接设置环境变量
export ZHIPUAI_API_KEY=your_key_here
export DATABASE_URL=postgresql://...

# 启动服务
uvicorn app.main:app
```

### 方式 2：.env 文件（单机部署）

```bash
# 1. 创建 .env 文件
cp .env.prod.example .env

# 2. 编辑配置
nano .env

# 3. 启动服务
docker-compose up
```

### 方式 3：配置 API（企业部署）

```bash
# 1. 启动服务
docker-compose up

# 2. 访问配置管理界面
# https://openspark.online/docs

# 3. 通过 API 管理配置
```

---

## 🔌 配置 API

### 端点列表

#### 公开端点（无需认证）

**GET /api/v1/configs/public**
- 获取公开配置
- 示例响应：
  ```json
  [
    {
      "key": "DEBUG",
      "value": "False",
      "description": "调试模式",
      "is_sensitive": false,
      "is_public": true
    }
  ]
  ```

#### 管理端点（需要管理员权限）

**GET /api/v1/configs**
- 获取所有配置（包含敏感信息）
- 参数：`include_sensitive` - 是否包含敏感信息
- 示例：`GET /api/v1/configs?include_sensitive=true`

**GET /api/v1/configs/{key}**
- 获取单个配置

**POST /api/v1/configs**
- 创建新配置
- 请求体：
  ```json
  {
    "key": "NEW_CONFIG",
    "value": "value_here",
    "description": "配置描述",
    "is_sensitive": false,
    "is_public": true
  }
  ```

**PUT /api/v1/configs/{key}**
- 更新配置
- 请求体：
  ```json
  {
    "value": "new_value"
  }
  ```

**DELETE /api/v1/configs/{key}**
- 删除配置

**POST /api/v1/configs/reload**
- 重新加载配置（无需重启服务）
- 响应：
  ```json
  {
    "success": true,
    "message": "配置已重新加载",
    "timestamp": "2026-02-14T21:00:00"
  }
  ```

**POST /api/v1/configs/export**
- 导出配置（用于备份）
- 响应：
  ```json
  {
    "configs": {...},
    "exported_at": "2026-02-14T21:00:00"
  }
  ```

**POST /api/v1/configs/import**
- 导入配置（用于恢复）
- 请求体：
  ```json
  {
    "DEBUG": "False",
    "DATABASE_URL": "postgresql://...",
    ...
  }
  ```

---

## 🔐 安全配置

### 敏感信息保护

以下配置默认标记为**敏感信息**：
- `DATABASE_URL` - 数据库连接字符串
- `REDIS_URL` - Redis 连接字符串
- `ZHIPUAI_API_KEY` - AI API Key
- `PINECONE_API_KEY` - 向量数据库 API Key
- `SECRET_KEY` - JWT 密钥

**保护机制：**
- ✅ API 默认不返回敏感信息（除非显式请求）
- ✅ 敏感信息脱敏显示（`******`）
- ✅ 仅管理员可访问完整配置

### 配置访问控制

| 用户角色 | 可访问配置 |
|---------|-----------|
| 普通用户 | 仅公开配置 |
| 管理员 | 所有配置（包括敏感） |

---

## 🔄 动态配置更新

### 热重载配置

无需重启服务即可更新配置：

```bash
# 方式 1：通过 API
curl -X POST https://openspark.online/api/v1/configs/reload \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 方式 2：通过管理界面
# https://openspark.online/docs → 配置管理 API
```

### 配置优先级

```
1. 配置中心（网络）← 最高优先级
   ↓
2. 环境变量
   ↓
3. .env 文件
   ↓
4. 默认值 ← 最低优先级
```

---

## 📊 企业级配置中心

### 推荐方案

#### 方案 1：Consul（推荐）

**优势：**
- 服务发现
- 健康检查
- KV 存储
- 分布式一致

**集成方式：**
```python
# 从 Consul 拉取配置
import consul

client = consul.Consul()
index, data = client.kv.get('ZHIPUAI_API_KEY')
```

#### 方案 2：Etcd

**优势：**
- 高可用
- 分布式存储
- 版本管理

#### 方案 3：Vault（企业级）

**优势：**
- 密钥管理
- 加密存储
- 细粒度权限
- 审计日志

---

## 🚀 部署配置

### 开发环境

```bash
# 使用 .env 文件
export ENVIRONMENT=development
uvicorn app.main:app --reload
```

### 测试环境

```bash
# 使用 .env 文件
export ENVIRONMENT=testing
docker-compose up
```

### 生产环境

```bash
# 使用配置 API
export ENVIRONMENT=production
export CONFIG_CENTER_URL=https://config.openspark.online/api/configs/public
docker-compose -f docker-compose.prod.yml up
```

---

## 📋 配置清单

### 必须配置的变量

| 变量名 | 是否必需 | 敏感 | 说明 |
|---------|---------|------|------|
| `DATABASE_URL` | ✅ | ✅ | 数据库连接字符串 |
| `REDIS_URL` | ✅ | ✅ | Redis 连接字符串 |
| `ZHIPUAI_API_KEY` | ✅ | ✅ | 智谱 AI API Key |
| `PINECONE_API_KEY` | ⚠️ | ✅ | Pinecone API Key（RAG 功能需要） |
| `SECRET_KEY` | ✅ | ✅ | JWT 密钥 |

### 可选配置

| 变量名 | 默认值 | 说明 |
|---------|---------|------|
| `DEBUG` | `False` | 调试模式 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 访问令牌有效期 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新令牌有效期 |

---

## 📝 配置最佳实践

### 1. 敏感信息管理

- ✅ 永远不要将敏感信息提交到 Git
- ✅ 使用 `.env.example` 模板（不包含真实值）
- ✅ 使用 Docker Secrets 存储密码
- ✅ 定期轮换密钥

### 2. 配置版本控制

- ✅ 使用配置中心管理版本
- ✅ 记录配置变更历史
- ✅ 支持配置回滚

### 3. 环境隔离

- ✅ 开发、测试、生产配置分离
- ✅ 每个环境独立配置中心
- ✅ 防止误操作影响生产环境

---

## 🔍 故障排查

### 配置加载失败

```bash
# 检查环境变量
env | grep CONFIG

# 检查 .env 文件
cat .env

# 查看日志
docker logs claw_ai_backend
```

### 配置不生效

```bash
# 重新加载配置
curl -X POST /api/v1/configs/reload

# 或者重启服务
docker-compose restart claw-ai-backend
```

---

## 📞 技术支持

- **CTO：** OpenClaw
- **文档：** https://github.com/sendwealth/claw-ai-backend
- **API 文档：** https://openspark.online/docs

---

*配置管理文档 v1.0 - OpenSpark 智能科技*
