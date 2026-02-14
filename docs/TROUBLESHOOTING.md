# CLAW.AI 故障排查指南

本指南帮助您诊断和解决 CLAW.AI 使用过程中可能遇到的常见问题。

---

## 目录

- [快速诊断](#快速诊断)
- [安装问题](#安装问题)
- [数据库问题](#数据库问题)
- [Redis 问题](#redis-问题)
- [认证问题](#认证问题)
- [API 调用问题](#api-调用问题)
- [AI 服务问题](#ai-服务问题)
- [性能问题](#性能问题)
- [部署问题](#部署问题)
- [监控与日志](#监控与日志)
- [获取支持](#获取支持)

---

## 快速诊断

### 健康检查

首先检查服务是否正常运行：

```bash
# 检查 API 服务
curl http://localhost:8000/health

# 预期响应
{
  "status": "healthy",
  "app": "CLAW.AI",
  "version": "1.0.0"
}
```

### 检查依赖服务

```bash
# 检查 PostgreSQL
psql -U postgres -h localhost -c "SELECT version();"

# 检查 Redis
redis-cli ping

# 检查 Milvus（如果使用）
# 访问 http://localhost:19530/healthz
```

### 查看日志

```bash
# 应用日志
tail -f logs/app.log

# Docker 日志
docker-compose logs -f app

# 系统日志
journalctl -u claw-ai -f
```

---

## 安装问题

### 问题 1: Python 版本不兼容

**症状**：

```
ERROR: This package requires a different Python version...
```

**解决方案**：

```bash
# 检查 Python 版本
python --version

# 如果版本低于 3.11，安装 Python 3.11+
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# macOS
brew install python@3.11

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate
```

---

### 问题 2: 依赖安装失败

**症状**：

```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案**：

```bash
# 更新 pip
pip install --upgrade pip

# 清理缓存
pip cache purge

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 单独安装失败的包
pip install package-name==version
```

---

### 问题 3: 编译错误

**症状**：

```
error: command 'gcc' failed
```

**解决方案**：

```bash
# 安装编译依赖
# Ubuntu/Debian
sudo apt install build-essential python3-dev

# macOS
xcode-select --install

# CentOS/RHEL
sudo yum install gcc python3-devel
```

---

## 数据库问题

### 问题 1: 数据库连接失败

**症状**：

```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**解决方案**：

```bash
# 1. 检查 PostgreSQL 是否运行
sudo systemctl status postgresql

# 2. 启动 PostgreSQL
sudo systemctl start postgresql

# 3. 检查连接配置
# 查看 .env 中的 DATABASE_URL
# 格式: postgresql://user:password@host:port/database

# 4. 测试连接
psql -U postgres -h localhost -d claw_ai

# 5. 检查防火墙
sudo ufw allow 5432
```

---

### 问题 2: 数据库不存在

**症状**：

```
FATAL: database "claw_ai" does not exist
```

**解决方案**：

```bash
# 创建数据库
sudo -u postgres psql
CREATE DATABASE claw_ai;
CREATE USER claw_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE claw_ai TO claw_user;
\q
```

---

### 问题 3: 数据库迁移失败

**症状**：

```
alembic.util.exc.CommandError: Target database is not up to date
```

**解决方案**：

```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 强制同步到指定版本
alembic stamp head

# 重置迁移（慎用！）
alembic downgrade base
alembic upgrade head
```

---

### 问题 4: 慢查询问题

**症状**：

API 响应很慢，数据库查询时间长。

**解决方案**：

```bash
# 1. 查看慢查询日志
# 编辑 postgresql.conf
log_min_duration_statement = 1000  # 记录超过 1 秒的查询

# 2. 分析查询计划
EXPLAIN ANALYZE SELECT * FROM conversations WHERE user_id = 123;

# 3. 添加索引
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

# 4. 使用连接池
# 在数据库 URL 中配置
DATABASE_URL=postgresql://user:password@host:port/database?pool_size=10&max_overflow=20
```

---

## Redis 问题

### 问题 1: Redis 连接失败

**症状**：

```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```

**解决方案**：

```bash
# 1. 检查 Redis 是否运行
sudo systemctl status redis
# 或
ps aux | grep redis

# 2. 启动 Redis
sudo systemctl start redis

# 3. 测试连接
redis-cli ping

# 4. 检查配置
# 查看 .env 中的 REDIS_URL
# 格式: redis://host:port/db
```

---

### 问题 2: Redis 内存不足

**症状**：

```
OOM command not allowed when used memory > 'maxmemory'
```

**解决方案**：

```bash
# 1. 查看内存使用情况
redis-cli INFO memory

# 2. 设置最大内存
redis-cli CONFIG SET maxmemory 1gb

# 3. 设置内存回收策略
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# 4. 永久配置
# 编辑 /etc/redis/redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru

# 5. 重启 Redis
sudo systemctl restart redis
```

---

### 问题 3: Redis 连接数过多

**症状**：

```
ERR max number of clients reached
```

**解决方案**：

```bash
# 1. 查看当前连接数
redis-cli INFO clients

# 2. 增加最大连接数
redis-cli CONFIG SET maxclients 10000

# 3. 查找并关闭空闲连接
redis-cli CLIENT LIST
redis-cli CLIENT KILL <id>
```

---

## 认证问题

### 问题 1: Token 无效

**症状**：

```
401 Unauthorized: Invalid or expired token
```

**解决方案**：

```bash
# 1. 检查 Token 是否过期
# Token 有效期为 60 分钟

# 2. 使用 Refresh Token 获取新的 Access Token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'

# 3. 重新登录获取新 Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

---

### 问题 2: 密码错误

**症状**：

```
401 Unauthorized: 邮箱或密码错误
```

**解决方案**：

```bash
# 1. 确认邮箱和密码是否正确
# 2. 检查数据库中的用户记录
psql -U postgres -d claw_ai -c "SELECT id, email FROM users WHERE email = 'user@example.com';"

# 3. 如果忘记密码，需要重置
# 可以通过数据库直接更新
psql -U postgres -d claw_ai
UPDATE users
SET password_hash = '$2b$12$...'  # 使用 bcrypt 生成新密码哈希
WHERE email = 'user@example.com';
```

---

### 问题 3: CORS 错误

**症状**：

浏览器控制台显示 CORS 错误。

**解决方案**：

```python
# 检查 app/main.py 中的 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保前端域名在 CORS_ORIGINS 中
# .env
CORS_ORIGINS=["http://localhost:3000","http://your-frontend-domain.com"]
```

---

## API 调用问题

### 问题 1: 404 Not Found

**症状**：

```
404 Not Found: Resource does not exist
```

**解决方案**：

```bash
# 1. 检查 API 路径是否正确
# 所有 API 路径都以 /api/v1 开头

# 2. 检查资源 ID 是否存在
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/conversations/123

# 3. 确认资源所有权
# 确保该资源属于当前用户
```

---

### 问题 2: 429 Too Many Requests

**症状**：

```
429 Too Many Requests: Rate limit exceeded
```

**解决方案**：

```bash
# 1. 查看限流配置
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/rate-limit/config

# 2. 查看当前配额
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/rate-limit/quota

# 3. 等待限流重置
# 或联系管理员调整限流配置
```

---

### 问题 3: 请求超时

**症状**：

请求长时间没有响应。

**解决方案**：

```bash
# 1. 检查 AI 服务响应时间
# 如果使用外部 AI API，可能网络较慢

# 2. 增加超时时间
# 在客户端配置超时
timeout = 60  # 秒

# 3. 使用异步任务
# 对于长时间运行的任务，使用 Celery 异步处理
```

---

## AI 服务问题

### 问题 1: Zhipu AI API 调用失败

**症状**：

```
zhipuai.core._errors.APIError: 401 Unauthorized
```

**解决方案**：

```bash
# 1. 检查 API Key 是否正确
# 查看 .env 中的 ZHIPUAI_API_KEY

# 2. 确认 API Key 是否有效
# 访问 https://open.bigmodel.cn/ 检查账户状态

# 3. 检查账户余额
# 如果余额不足，需要充值
```

---

### 问题 2: AI 响应为空

**症状**：

AI 返回的内容为空或异常。

**解决方案**：

```python
# 1. 检查 API 调用日志
# 查看 app.log 中的详细错误信息

# 2. 检查请求参数
# 确保 system_prompt、user_message 等参数正确

# 3. 尝试使用不同的模型
# glm-4 更强大但可能较慢
# glm-3-turbo 更快但可能效果稍差

# 4. 检查内容安全策略
# 某些内容可能被 AI 服务过滤
```

---

### 问题 3: 向量嵌入失败

**症状**：

```
Error generating embeddings: Connection timeout
```

**解决方案**：

```bash
# 1. 检查网络连接
# 确保可以访问嵌入模型 API

# 2. 检查 Milvus 连接
# 查看 Milvus 服务状态

# 3. 减小文档大小
# 大文档可以分段处理

# 4. 使用异步任务
# 通过 Celery 异步生成嵌入
```

---

## 性能问题

### 问题 1: API 响应慢

**症状**：

API 请求响应时间超过预期。

**解决方案**：

```bash
# 1. 启用缓存
# 热点数据使用 Redis 缓存

# 2. 优化数据库查询
# 添加索引，避免 N+1 查询

# 3. 使用异步任务
# 耗时操作使用 Celery 异步处理

# 4. 启用压缩
# 在 Nginx 配置中启用 gzip 压缩

# 5. 使用 CDN
# 静态资源使用 CDN 加速
```

---

### 问题 2: 内存使用过高

**症状**：

服务器内存占用过高。

**解决方案**：

```bash
# 1. 查看内存使用情况
top
htop

# 2. 检查缓存大小
redis-cli INFO memory

# 3. 限制 Uvicorn Worker 数量
# 生产环境使用多个 Worker 但不要太多
uvicorn app.main:app --workers 4

# 4. 清理无用数据
# 定期清理过期的缓存和日志
```

---

### 问题 3: CPU 使用率高

**症状**：

服务器 CPU 占用率高。

**解决方案**：

```bash
# 1. 查看进程
top -p $(pgrep -f uvicorn)

# 2. 分析慢日志
# 查找耗时的操作

# 3. 使用异步 I/O
# 避免阻塞操作

# 4. 水平扩展
# 使用多个应用实例分担负载
```

---

## 部署问题

### 问题 1: Docker 容器启动失败

**症状**：

```
ERROR: for app  Cannot start service app: ...
```

**解决方案**：

```bash
# 1. 查看容器日志
docker-compose logs app

# 2. 检查配置文件
# 确保 docker-compose.yml 配置正确

# 3. 重新构建镜像
docker-compose build --no-cache

# 4. 检查端口占用
lsof -i :8000

# 5. 清理并重启
docker-compose down
docker-compose up -d
```

---

### 问题 2: Nginx 配置错误

**症状**：

502 Bad Gateway

**解决方案**：

```nginx
# 检查 Nginx 配置
# /etc/nginx/sites-available/claw-ai

server {
    listen 80;
    server_name api.claw.ai;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

---

### 问题 3: SSL 证书问题

**症状**：

HTTPS 访问失败，证书错误。

**解决方案**：

```bash
# 1. 使用 Let's Encrypt 获取免费证书
sudo apt install certbot python3-certbot-nginx

# 2. 获取证书
sudo certbot --nginx -d api.claw.ai

# 3. 自动续期
sudo certbot renew --dry-run

# 4. 检查证书
sudo certbot certificates
```

---

## 监控与日志

### 查看应用日志

```bash
# 实时日志
tail -f logs/app.log

# 错误日志
tail -f logs/error.log

# Docker 日志
docker-compose logs -f app

# 查看特定时间范围的日志
sed -n '/2024-02-14 10:00/,/2024-02-14 11:00/p' logs/app.log
```

### 使用 Prometheus 监控

访问 Grafana 仪表板：

- URL: http://localhost:3000
- 默认用户名: admin
- 默认密码: admin

监控指标：

- QPS (Queries Per Second)
- 响应时间 (Latency)
- 错误率 (Error Rate)
- CPU 使用率
- 内存使用率
- 数据库连接数
- Redis 命中率

### 设置告警

配置 Prometheus 告警规则：

```yaml
# prometheus/alerts.yml
groups:
  - name: claw_ai_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "High latency detected"
```

---

## 获取支持

如果您无法解决问题，请按照以下步骤获取帮助：

### 1. 收集诊断信息

```bash
# 系统信息
uname -a
python --version
pip list

# 服务状态
systemctl status claw-ai
systemctl status postgresql
systemctl status redis

# 日志
tail -n 100 logs/app.log

# 错误信息
# 保存完整的错误堆栈
```

### 2. 搜索已知问题

- 📖 查看 [常见问题](FAQ.md)
- 🔍 搜索 GitHub Issues
- 📚 查看项目文档

### 3. 联系技术支持

如果以上方法都无法解决问题，请联系：

- 📧 Email: support@openspark.online
- 💬 企业微信：OpenSpark 智能科技
- 📱 电话：400-XXX-XXXX

### 4. 提交 Issue

如果这是 Bug，请提交 GitHub Issue：

1. 详细的 Bug 描述
2. 重现步骤
3. 预期行为
4. 实际行为
5. 环境信息
6. 错误日志

---

## 诊断清单

在报告问题前，请确保已完成以下检查：

- [ ] 检查服务状态：`curl http://localhost:8000/health`
- [ ] 检查数据库连接：`psql -U postgres -d claw_ai`
- [ ] 检查 Redis 连接：`redis-cli ping`
- [ ] 查看应用日志：`tail -f logs/app.log`
- [ ] 检查配置文件：`.env` 和配置目录
- [ ] 查看错误堆栈信息
- [ ] 搜索已知问题和解决方案

---

**希望本指南能帮助您解决问题！如有需要，请随时联系技术支持。**

*最后更新：2024-02-14*
