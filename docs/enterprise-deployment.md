# 企业级部署文档

**版本：** v1.0
**更新日期：** 2026-02-14
**公司：** OpenSpark 智能科技

---

## 📋 部署架构

### 架构概览

```
                    ┌─────────────┐
                    │   用户      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Nginx      │
                    │  (HTTPS)    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐     ┌─────▼─────┐    ┌───▼────┐
   │ Backend  │     │ PostgreSQL │    │ Redis  │
   │ (FastAPI)│     │ (Database)│    │ (Cache)│
   └─────────┘     └───────────┘    └────────┘
        │
        │
   ┌────▼─────┐
   │ Zhipu AI │
   │ (API)    │
   └──────────┘
```

### 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 反向代理 | Nginx | Alpine |
| 后端框架 | FastAPI | 0.104.1 |
| 数据库 | PostgreSQL | 15 |
| 缓存 | Redis | 7 |
| 容器化 | Docker Compose | 2.0+ |
| AI 服务 | Zhipu AI | GLM-4 |
| 向量数据库 | Pinecone | - |

---

## 🔧 系统要求

### 最低配置
- **CPU：** 2 核心
- **内存：** 4 GB
- **存储：** 20 GB SSD
- **操作系统：** Linux (Ubuntu 20.04+ 或 CentOS 7+)

### 推荐配置
- **CPU：** 4 核心
- **内存：** 8 GB
- **存储：** 50 GB SSD
- **网络：** 10 Mbps+

---

## 🚀 快速部署

### 步骤 1：安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 步骤 2：克隆代码

```bash
git clone https://github.com/sendwealth/claw-ai-backend.git /opt/claw-ai
cd /opt/claw-ai
```

### 步骤 3：配置环境变量

```bash
# 复制环境变量模板
cp .env.prod.example .env

# 编辑环境变量
nano .env
```

**必须配置的变量：**
- `ZHIPUAI_API_KEY` - 智谱 AI API Key
- `PINECONE_API_KEY` - Pinecone API Key

**生成安全的密钥：**
```bash
# 生成 SECRET_KEY
openssl rand -hex 32

# 生成 POSTGRES_PASSWORD
openssl rand -hex 16

# 生成 REDIS_PASSWORD
openssl rand -hex 16
```

### 步骤 4：配置 SSL 证书

```bash
# 创建 SSL 目录
mkdir -p nginx/ssl

# 上传 SSL 证书文件到 nginx/ssl/
# 需要：
#   - fullchain.pem
#   - privkey.pem
```

**如果没有 SSL 证书：**
1. 使用 Let's Encrypt（免费）
2. 或购买商业 SSL 证书
3. 或使用 Cloudflare SSL

### 步骤 5：一键部署

```bash
# 给部署脚本执行权限
chmod +x deploy.sh

# 安装并启动所有服务
./deploy.sh install
```

---

## 📊 服务管理

### 启动服务

```bash
./deploy.sh start
```

### 停止服务

```bash
./deploy.sh stop
```

### 重启服务

```bash
./deploy.sh restart
```

### 查看状态

```bash
./deploy.sh status
```

### 查看日志

```bash
# 查看所有服务日志
./deploy.sh logs

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f claw-ai-backend
docker-compose -f docker-compose.prod.yml logs -f postgres
docker-compose -f docker-compose.prod.yml logs -f redis
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### 健康检查

```bash
./deploy.sh health
```

---

## 💾 数据备份

### 自动备份（Cron）

```bash
# 编辑 crontab
crontab -e

# 添加每日凌晨 2 点备份
0 2 * * * cd /opt/claw-ai && ./deploy.sh backup
```

### 手动备份

```bash
./deploy.sh backup
```

### 恢复备份

```bash
# 解压备份文件
gunzip postgres_backup_20260214_020000.sql.gz

# 恢复数据库
docker exec -i claw_ai_postgres psql -U claw_ai -d claw_ai < postgres_backup_20260214_020000.sql
```

---

## 🔄 更新部署

### 更新代码

```bash
# 更新到最新版本
./deploy.sh update
```

### 回滚版本

```bash
cd /opt/claw-ai
git log --oneline  # 查看提交历史
git reset --hard <commit-hash>  # 回滚到指定版本
./deploy.sh restart
```

---

## 🔒 安全配置

### 防火墙配置

```bash
# 开放必要端口
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw enable
```

### 数据库安全

- ✅ 使用强密码
- ✅ 限制数据库访问（仅内部网络）
- ✅ 定期备份
- ✅ 启用日志

### API 安全

- ✅ JWT 认证
- ✅ CORS 限制
- ✅ 速率限制（Nginx）
- ✅ HTTPS 强制
- ✅ 安全头设置

---

## 📱 访问地址

### 生产环境

- **API（HTTP）：** http://111.229.40.25
- **API（HTTPS）：** https://openspark.online
- **API 文档：** https://openspark.online/docs
- **健康检查：** https://openspark.online/health
- **WebSocket：** wss://openspark.online/api/v1/ws

### 测试环境

- **API：** http://localhost:8000
- **API 文档：** http://localhost:8000/docs
- **健康检查：** http://localhost:8000/health

---

## 🔍 监控和日志

### 日志位置

- **应用日志：** `/opt/claw-ai/logs/`
- **Nginx 日志：** `/opt/claw-ai/nginx/logs/`
- **Docker 日志：** `docker-compose logs`

### 日志查看

```bash
# 实时查看
tail -f /opt/claw-ai/logs/app.log

# 搜索错误
grep "ERROR" /opt/claw-ai/logs/app.log
```

---

## ❓ 故障排查

### 服务启动失败

```bash
# 查看服务状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 检查环境变量
cat .env
```

### 数据库连接失败

```bash
# 测试数据库连接
docker exec -it claw_ai_postgres psql -U claw_ai -d claw_ai

# 检查数据库日志
docker logs claw_ai_postgres
```

### API 无响应

```bash
# 检查 API 日志
docker logs claw_ai_backend

# 测试健康检查
curl http://localhost:8000/health
```

---

## 📞 技术支持

- **CTO：** OpenClaw
- **文档：** https://github.com/sendwealth/claw-ai-backend
- **问题报告：** 在 GitHub 提交 Issue

---

## 📋 部署清单

- [ ] 系统要求满足
- [ ] Docker 已安装
- [ ] Docker Compose 已安装
- [ ] 代码已克隆
- [ ] 环境变量已配置
- [ ] SSL 证书已配置
- [ ] 数据库密码已修改
- [ ] 服务已启动
- [ ] 健康检查通过
- [ ] API 访问正常
- [ ] WebSocket 连接正常
- [ ] 备份任务已配置
- [ ] 监控已配置

---

*企业级部署文档 v1.0 - OpenSpark 智能科技*
