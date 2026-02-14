# CLAW.AI 架构文档

## 目录

- [系统架构概览](#系统架构概览)
- [技术栈](#技术栈)
- [核心组件](#核心组件)
- [数据流](#数据流)
- [部署架构](#部署架构)
- [扩展性设计](#扩展性设计)

---

## 系统架构概览

CLAW.AI 是一个基于 FastAPI 构建的智能咨询服务平台，采用微服务架构设计，支持对话管理、知识库检索增强生成（RAG）、用户认证、监控告警等核心功能。

### 整体架构图

```mermaid
graph TB
    subgraph "客户端层"
        Web[Web 前端]
        Mobile[移动端]
        API_Client[API 客户端]
    end

    subgraph "API 网关层"
        Nginx[Nginx 反向代理]
        RateLimit[限流中间件]
        Metrics[Prometheus 监控]
    end

    subgraph "应用层"
        FastAPI[FastAPI 应用]
        WebSocket[WebSocket 服务]
        Tasks[Celery 任务队列]
    end

    subgraph "业务服务层"
        AuthService[认证服务]
        UserService[用户服务]
        ConversationService[对话服务]
        KnowledgeService[知识库服务]
        ConsultingService[咨询服务]
        AIService[AI 服务]
        RAGService[RAG 服务]
        CacheService[缓存服务]
    end

    subgraph "数据存储层"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis 缓存)]
        Milvus[(Milvus 向量库)]
        MinIO[MinIO 对象存储]
    end

    subgraph "监控层"
        Prometheus[Prometheus]
        Grafana[Grafana]
        Loki[Loki 日志]
        Promtail[Promtail 采集]
    end

    subgraph "外部服务"
        ZhipuAI[智谱 AI]
        Pinecone[Pinecone 可选]
    end

    Web --> Nginx
    Mobile --> Nginx
    API_Client --> Nginx
    Nginx --> RateLimit
    RateLimit --> FastAPI
    RateLimit --> WebSocket
    WebSocket --> FastAPI

    FastAPI --> AuthService
    FastAPI --> UserService
    FastAPI --> ConversationService
    FastAPI --> KnowledgeService
    FastAPI --> ConsultingService
    FastAPI --> Tasks

    ConversationService --> AIService
    ConversationService --> RAGService
    KnowledgeService --> RAGService

    AuthService --> PostgreSQL
    UserService --> PostgreSQL
    ConversationService --> PostgreSQL
    KnowledgeService --> PostgreSQL
    ConsultingService --> PostgreSQL
    AIService --> CacheService
    RAGService --> CacheService

    CacheService --> Redis
    RAGService --> Milvus
    KnowledgeService --> MinIO

    Tasks --> AIService
    Tasks --> RAGService

    FastAPI --> Metrics
    WebSocket --> Metrics
    Metrics --> Prometheus
    Prometheus --> Grafana

    FastAPI --> Loki
    WebSocket --> Loki
    Loki --> Promtail

    AIService --> ZhipuAI
    RAGService --> ZhipuAI
    RAGService --> Pinecone
```

---

## 技术栈

### 后端框架

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 主要开发语言 |
| FastAPI | 0.104.1 | Web 框架 |
| Uvicorn | 0.24.0 | ASGI 服务器 |
| Pydantic | 2.5.0 | 数据验证 |
| Celery | 5.3.6 | 异步任务队列 |

### 数据库

| 技术 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 15 | 主数据库 |
| SQLAlchemy | 2.0.23 | ORM 框架 |
| Alembic | 1.12.1 | 数据库迁移 |
| Redis | 7 | 缓存和会话存储 |
| Milvus | 2.3+ | 向量数据库 |
| Pinecone | - | 可选向量数据库 |

### AI & ML

| 技术 | 版本 | 用途 |
|------|------|------|
| Zhipu AI | 4.0.0 | GLM-4 模型 API |
| LangChain | 0.1.0 | AI 应用框架 |
| Sentence-Transformers | 2.2.2 | 文本嵌入 |

### 监控 & 日志

| 技术 | 版本 | 用途 |
|------|------|------|
| Prometheus | - | 指标收集 |
| Grafana | - | 可视化监控 |
| Loki | - | 日志聚合 |
| Promtail | - | 日志采集 |

---

## 核心组件

### 1. API 网关层

#### Nginx 反向代理
- 负载均衡
- SSL 终止
- 静态文件服务
- 请求路由

#### 限流中间件
- 基于 Token Bucket 算法
- 支持 IP、用户、API 多维度限流
- 配置化限流策略

```mermaid
sequenceDiagram
    participant Client
    participant RateLimit
    participant FastAPI
    participant Redis

    Client->>RateLimit: API 请求
    RateLimit->>Redis: 检查配额
    Redis-->>RateLimit: 返回当前计数
    alt 未超限
        RateLimit->>FastAPI: 转发请求
        RateLimit->>Redis: 增加计数
    else 超限
        RateLimit-->>Client: 429 Too Many Requests
    end
```

### 2. 应用服务层

#### 认证服务 (AuthService)
- JWT Token 生成和验证
- 用户注册和登录
- 密码加密和验证
- 权限管理

#### 对话服务 (ConversationService)
- 对话 CRUD 操作
- 消息管理
- AI 响应生成
- 对话历史管理

#### 知识库服务 (KnowledgeService)
- 知识库管理
- 文档上传和解析
- 向量索引
- 语义搜索

#### RAG 服务 (RAGService)
- 文档分块
- 向量嵌入
- 相似度检索
- 上下文增强生成

### 3. 异步任务层

#### Celery 任务队列
- 异步 AI 响应生成
- 文档异步索引
- 数据清理任务
- 定时任务调度

```mermaid
graph LR
    FastAPI[FastAPI] -->|发布任务| CeleryBroker[Redis Broker]
    CeleryBroker --> CeleryWorker[Celery Worker]
    CeleryWorker --> AIService[AI 服务]
    CeleryWorker --> RAGService[RAG 服务]
    CeleryWorker --> CeleryResult[Redis Result Backend]
```

---

## 数据流

### 1. 用户登录流程

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant AuthService
    participant PostgreSQL
    participant Redis

    User->>FastAPI: POST /api/v1/auth/login
    FastAPI->>AuthService: 验证用户
    AuthService->>PostgreSQL: 查询用户
    PostgreSQL-->>AuthService: 返回用户信息
    AuthService->>AuthService: 验证密码
    AuthService->>AuthService: 生成 JWT Token
    AuthService->>Redis: 存储 Token（可选）
    AuthService-->>FastAPI: 返回 Token
    FastAPI-->>User: 返回 Token
```

### 2. 对话创建流程

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant ConversationService
    participant PostgreSQL
    participant AIService
    participant Redis

    User->>FastAPI: POST /api/v1/conversations
    FastAPI->>ConversationService: 创建对话
    ConversationService->>PostgreSQL: 插入对话记录
    PostgreSQL-->>ConversationService: 返回对话 ID
    ConversationService-->>FastAPI: 返回对话信息
    FastAPI-->>User: 返回对话信息
```

### 3. AI 对话流程

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant ConversationService
    participant Celery
    participant AIService
    participant RAGService
    participant ZhipuAI
    participant PostgreSQL

    User->>FastAPI: POST /api/v1/conversations/{id}/chat
    FastAPI->>ConversationService: 发送消息
    ConversationService->>PostgreSQL: 存储用户消息
    ConversationService->>Celery: 提交异步任务
    Celery->>AIService: 准备生成响应
    AIService->>RAGService: 检索相关文档
    RAGService-->>AIService: 返回上下文
    AIService->>ZhipuAI: 调用 GLM-4 API
    ZhipuAI-->>AIService: 返回响应
    AIService->>PostgreSQL: 存储助手消息
    AIService-->>FastAPI: 返回响应
    FastAPI-->>User: 返回响应
```

### 4. 知识库文档索引流程

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant KnowledgeService
    participant Celery
    participant RAGService
    participant Milvus
    participant PostgreSQL

    User->>FastAPI: 上传文档
    FastAPI->>KnowledgeService: 创建文档记录
    KnowledgeService->>PostgreSQL: 存储文档元数据
    KnowledgeService->>Celery: 提交索引任务
    Celery->>RAGService: 处理文档
    RAGService->>RAGService: 文本分块
    RAGService->>RAGService: 生成向量嵌入
    RAGService->>Milvus: 存储向量
    Milvus-->>RAGService: 确认存储
    RAGService->>PostgreSQL: 更新文档状态
    RAGService-->>FastAPI: 索引完成
    FastAPI-->>User: 返回结果
```

### 5. RAG 查询流程

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant RAGService
    participant Milvus
    participant Redis
    participant ZhipuAI

    User->>FastAPI: 提出问题
    FastAPI->>RAGService: RAG 查询
    RAGService->>Redis: 检查缓存
    alt 缓存命中
        Redis-->>RAGService: 返回缓存结果
        RAGService-->>FastAPI: 返回答案
    else 缓存未命中
        RAGService->>RAGService: 生成查询向量
        RAGService->>Milvus: 向量检索
        Milvus-->>RAGService: 返回相关文档
        RAGService->>ZhipuAI: 带上下文生成答案
        ZhipuAI-->>RAGService: 返回答案
        RAGService->>Redis: 缓存结果
        RAGService-->>FastAPI: 返回答案
    end
    FastAPI-->>User: 返回答案
```

---

## 部署架构

### 生产环境部署架构

```mermaid
graph TB
    subgraph "负载均衡层"
        LB[负载均衡器]
    end

    subgraph "Web 服务集群"
        Web1[Web 服务器 1]
        Web2[Web 服务器 2]
        Web3[Web 服务器 N]
    end

    subgraph "应用服务集群"
        App1[FastAPI 实例 1]
        App2[FastAPI 实例 2]
        App3[FastAPI 实例 N]
    end

    subgraph "Worker 集群"
        Worker1[Celery Worker 1]
        Worker2[Celery Worker 2]
        Worker3[Celery Worker N]
    end

    subgraph "数据层"
        PG_Master[PostgreSQL 主库]
        PG_Replica1[PostgreSQL 从库 1]
        PG_Replica2[PostgreSQL 从库 2]
        Redis_Cluster[Redis 集群]
        Milvus_Cluster[Milvus 集群]
    end

    subgraph "监控层"
        Prometheus_Server[Prometheus]
        Grafana_Server[Grafana]
        AlertManager[Alert Manager]
    end

    LB --> Web1
    LB --> Web2
    LB --> Web3

    Web1 --> App1
    Web2 --> App2
    Web3 --> App3

    App1 --> PG_Master
    App2 --> PG_Master
    App3 --> PG_Master

    PG_Master --> PG_Replica1
    PG_Master --> PG_Replica2

    App1 --> Redis_Cluster
    App2 --> Redis_Cluster
    App3 --> Redis_Cluster

    Worker1 --> PG_Master
    Worker2 --> PG_Master
    Worker3 --> PG_Master

    Worker1 --> Milvus_Cluster
    Worker2 --> Milvus_Cluster
    Worker3 --> Milvus_Cluster

    App1 --> Prometheus_Server
    App2 --> Prometheus_Server
    App3 --> Prometheus_Server

    Worker1 --> Prometheus_Server
    Worker2 --> Prometheus_Server
    Worker3 --> Prometheus_Server

    Prometheus_Server --> Grafana_Server
    Prometheus_Server --> AlertManager
```

### Docker Compose 部署架构

```mermaid
graph TB
    subgraph "Docker 网络"
        Nginx[Nginx 容器]
        FastAPI[FastAPI 容器]
        CeleryWorker[Celery Worker 容器]
        CeleryBeat[Celery Beat 容器]
        PostgreSQL[PostgreSQL 容器]
        Redis[Redis 容器]
        Milvus[Milvus 容器]
        MinIO[MinIO 容器]
        Prometheus[Prometheus 容器]
        Grafana[Grafana 容器]
        Loki[Loki 容器]
        Promtail[Promtail 容器]
    end

    Nginx --> FastAPI
    Nginx --> Prometheus
    Nginx --> Grafana

    FastAPI --> PostgreSQL
    FastAPI --> Redis
    FastAPI --> Milvus
    FastAPI --> Loki

    CeleryWorker --> PostgreSQL
    CeleryWorker --> Redis
    CeleryWorker --> Milvus
    CeleryWorker --> MinIO
    CeleryWorker --> Loki

    CeleryBeat --> Redis

    Prometheus --> FastAPI
    Prometheus --> CeleryWorker

    Loki --> Promtail

    Grafana --> Prometheus
    Grafana --> Loki
```

---

## 扩展性设计

### 1. 水平扩展

#### FastAPI 应用实例
- 无状态设计，支持水平扩展
- 通过 Nginx 负载均衡分发请求
- 共享 Redis 缓存和会话

#### Celery Worker
- 支持多 Worker 并行处理
- 任务队列分区提高吞吐量
- 动态扩缩容

### 2. 数据库扩展

#### PostgreSQL 读写分离
- 主库处理写操作
- 从库处理读操作
- 通过 ORM 配置实现自动路由

#### Redis 集群
- 数据分片
- 主从复制
- 自动故障转移

#### Milvus 分布式部署
- 协调节点
- 数据节点
- 查询节点
- 索引节点

### 3. 缓存策略

#### 多级缓存
```mermaid
graph LR
    A[应用] --> B[本地缓存 L1]
    B --> C[Redis 缓存 L2]
    C --> D[数据库]

    style B fill:#e1f5e1
    style C fill:#fff4e1
    style D fill:#ffe1e1
```

- L1: 内存缓存（Python dict）
- L2: Redis 缓存
- L3: 数据库

#### 缓存失效策略
- TTL 过期
- 主动更新
- 延迟双删

---

## 安全架构

### 1. 认证与授权

```mermaid
graph TB
    Client[客户端] -->|1. 提交凭证| Login[登录接口]
    Login -->|2. 验证凭证| Auth[认证服务]
    Auth -->|3. 查询用户| DB[数据库]
    DB -->|4. 返回用户| Auth
    Auth -->|5. 生成 Token| JWT[JWT 生成器]
    JWT -->|6. 返回 Token| Login
    Login -->|7. 返回 Token| Client

    Client -->|8. 携带 Token| API[受保护的 API]
    API -->|9. 验证 Token| Verify[JWT 验证器]
    Verify -->|10. 验证通过| Handler[业务处理器]
    Verify -->|11. 验证失败| Error[错误响应]
    Handler -->|12. 返回数据| Client
    Error -->|13. 返回错误| Client
```

### 2. 数据安全

- 密码使用 bcrypt 加密
- 敏感数据传输使用 HTTPS
- SQL 注入防护（ORM 参数化查询）
- XSS 防护（输入验证和输出编码）

### 3. API 安全

- CORS 配置
- 限流和防刷
- 请求签名验证（可选）
- API Key 管理（可选）

---

## 性能优化

### 1. 数据库优化
- 索引优化
- 查询优化
- 连接池管理
- 读写分离

### 2. 缓存优化
- 热点数据缓存
- 查询结果缓存
- 会话缓存
- 分布式缓存

### 3. 异步处理
- Celery 异步任务
- WebSocket 实时通信
- 异步 I/O 操作

### 4. CDN 加速
- 静态资源 CDN
- API 响应缓存

---

## 监控与告警

### 监控指标

```mermaid
graph TB
    subgraph "应用指标"
        QPS[QPS]
        Latency[延迟]
        ErrorRate[错误率]
        ActiveUsers[活跃用户]
    end

    subgraph "系统指标"
        CPU[CPU 使用率]
        Memory[内存使用率]
        DiskIO[磁盘 I/O]
        NetworkIO[网络 I/O]
    end

    subgraph "数据库指标"
        DBConnections[连接数]
        QueryTime[查询时间]
        SlowQueries[慢查询]
        CacheHitRate[缓存命中率]
    end

    subgraph "业务指标"
        ConversationCount[对话数]
        MessageCount[消息数]
        TokenUsage[Token 使用量]
        Cost[成本]
    end
```

### 告警策略
- P0: 服务不可用（立即告警）
- P1: 性能严重下降（5 分钟告警）
- P2: 性能轻微下降（30 分钟告警）
- P3: 潜在问题（1 小时告警）

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2024-02-14 | 初始版本 |

---

*最后更新：2024-02-14*
