# CLAW.AI 生产环境部署文档

## 目录

- [概述](#概述)
- [系统架构](#系统架构)
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [SSL 证书配置](#ssl-证书配置)
- [服务配置](#服务配置)
- [监控与日志](#监控与日志)
- [备份与恢复](#备份与恢复)
- [回滚操作](#回滚操作)
- [性能优化](#性能优化)
- [安全加固](#安全加固)
- [故障排查](#故障排查)
- [日常运维](#日常运维)

---

## 概述

CLAW.AI 是一个基于 FastAPI 的智能对话和知识管理系统，采用微服务架构设计。

### 核心服务

| 服务 | 用途 | 端口 |
|------|------|------|
| claw-ai-backend | 后端 API 服务 | 8000 |
| PostgreSQL | 关系型数据库 | 5432 |
| Redis | 缓存和消息队列 | 6379 |
| Milvus | 向量数据库 | 19530 |
| Celery Worker | 异步任务执行 | - |
| Celery Beat | 定时任务调度 | - |
| Flower | Celery 监控面板 | 5555 |
| Nginx | 反向代理和负载均衡 | 80, 443 |
| Prometheus | 指标收集 | 9090 |
| Grafana | 可视化仪表板 | 3000 |
| Loki | 日志聚合 | 3100 |

---

## 系统架构

```
                    ┌─────────────┐
                    │   用户请求  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Nginx     │ (SSL 终止, 反向代理)
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐      ┌─────▼─────┐
   │  API    │       │ Flower  │      │  Grafana  │
   │ Server  │       │  (Celery)│      │  Monitor  │
   └────┬────┘       └─────────┘      └───────────┘
        │
        ├──────────────┬──────────────┐
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌─────▼─────┐
   │PostgreSQL│  │  Redis  │   │  Milvus   │
   └─────────┘   └─────────┘   └───────────┘
        │              │              │
   ┌────▼────┐   ┌────▼────┐   ┌─────▼─────┐
   │  数据   │   │  缓存   │   │  向量数据 │
   └─────────┘   └─────────┘   └───────────┘

        ┌─────────────────────────────┐
        │      Celery Worker           │
        │  (异步任务: 邮件, 向量化等)  │
        └─────────────────────────────┘
```

---

## 前置要求

### 硬件要求

**最小配置：**
- CPU: 2 核
- 内存: 4GB
- 存储: 50GB SSD

**推荐配置：**
- CPU: 4 核或更多
- 内存: 8GB 或更多
- 存储: 100GB SSD 或更多

### 软件要求

- **操作系统**: Ubuntu 22.04 LTS 或更高版本
- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本
- **Git**: 2.0 或更高版本
- **Certbot**: 1.0 或更高版本（用于 SSL 证书）

### 网络要求

- 公网 IP 地址
- 域名（如 claw-ai.com）已解析到服务器 IP
- 开放端口: 80, 443 (HTTP/HTTPS)

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/claw-ai-backend.git
cd claw-ai-backend
```

### 2. 配置环境变量

```bash
cp .env.prod.example .env.prod
vim .env.prod
```

**必须修改的配置：**
- `POSTGRES_PASSWORD`: PostgreSQL 密码
- `REDIS_PASSWORD`: Redis 密码
- `SECRET_KEY`: JWT 密钥（使用 `openssl rand -hex 32` 生成）
- `ZHIPUAI_API_KEY`: 智谱 AI API Key
- `PINECONE_API_KEY`: Pinecone API Key

### 3. 运行部署脚本

```bash
chmod +x scripts/deploy.sh
sudo bash scripts/deploy.sh
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 检查健康状态
curl https://claw-ai.com/health

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 详细部署步骤

### 步骤 1: 系统初始化

```bash
# 更新系统
sudo apt-get update
sudo apt-get upgrade -y

# 安装基础工具
sudo apt-get install -y curl git vim htop net-tools unzip

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 步骤 2: 配置防火墙

```bash
# 安装 UFW
sudo apt-get install -y ufw

# 配置规则
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable
sudo ufw status
```

### 步骤 3: 配置系统参数

```bash
# 编辑 /etc/sysctl.conf
sudo vim /etc/sysctl.conf
```

添加以下配置：
```conf
# 网络优化
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# 文件描述符限制
fs.file-max = 100000

# 共享内存
kernel.shmmax = 68719476736
kernel.shmall = 4294967296
```

应用配置：
```bash
sudo sysctl -p
```

### 步骤 4: 创建必要的目录

```bash
sudo mkdir -p /var/log/claw-ai
sudo mkdir -p /var/lib/claw-ai/backups
sudo mkdir -p /var/lib/claw-ai/uploads
sudo mkdir -p /var/lib/claw-ai/ssl
sudo chown -R $USER:$USER /var/log/claw-ai
sudo chown -R $USER:$USER /var/lib/claw-ai
```

### 步骤 5: 配置 SSL 证书

```bash
# 安装 Certbot
sudo apt-get install -y certbot

# 申请证书（确保域名已解析）
sudo certbot certonly --standalone \
    --email admin@claw-ai.com \
    --agree-tos \
    -d claw-ai.com \
    -d www.claw-ai.com

# 复制证书到项目目录
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/claw-ai.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/claw-ai.com/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/*.pem
```

### 步骤 6: 创建环境配置文件

```bash
# 生成安全密钥
openssl rand -hex 32 > .secret_key
openssl rand -hex 32 > .postgres_password
openssl rand -hex 32 > .redis_password

# 编辑配置文件
vim .env.prod
```

### 步骤 7: 构建和启动服务

```bash
# 拉取镜像
docker-compose -f docker-compose.prod.yml pull

# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤 8: 运行数据库迁移

```bash
# 执行迁移
chmod +x scripts/migrate.sh
bash scripts/migrate.sh

# 验证迁移
bash scripts/migrate.sh --status
```

### 步骤 9: 配置自动备份

```bash
# 设置定时任务
crontab -e
```

添加以下内容：
```cron
# 每天凌晨 2 点执行备份
0 2 * * * cd /path/to/claw-ai-backend && bash scripts/backup.sh >> logs/backup.log 2>&1
```

---

## SSL 证书配置

### 证书申请

使用 Certbot 申请 Let's Encrypt 证书：

```bash
sudo certbot certonly --standalone \
    --email admin@claw-ai.com \
    --agree-tos \
    -d claw-ai.com \
    -d www.claw-ai.com
```

### 自动续期

设置证书自动续期：

```bash
# 添加续期脚本
sudo vim /etc/letsencrypt/renewal-hooks/post/renew-claw-ai.sh
```

脚本内容：
```bash
#!/bin/bash
cp /etc/letsencrypt/live/claw-ai.com/fullchain.pem /path/to/claw-ai-backend/nginx/ssl/
cp /etc/letsencrypt/live/claw-ai.com/privkey.pem /path/to/claw-ai-backend/nginx/ssl/
cd /path/to/claw-ai-backend
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

添加执行权限：
```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/renew-claw-ai.sh
```

测试续期：
```bash
sudo certbot renew --dry-run
```

---

## 服务配置

### PostgreSQL

**连接字符串：**
```
postgresql://claw_ai:password@postgres:5432/claw_ai
```

**常用操作：**
```bash
# 进入容器
docker exec -it claw_ai_postgres psql -U claw_ai -d claw_ai

# 备份数据库
docker exec claw_ai_postgres pg_dump -U claw_ai claw_ai > backup.sql

# 恢复数据库
cat backup.sql | docker exec -i claw_ai_postgres psql -U claw_ai claw_ai
```

### Redis

**连接字符串：**
```
redis://:password@redis:6379/0
```

**常用操作：**
```bash
# 进入容器
docker exec -it claw_ai_redis redis-cli -a password

# 查看所有键
docker exec claw_ai_redis redis-cli -a password KEYS '*'

# 清空缓存
docker exec claw_ai_redis redis-cli -a password FLUSHALL
```

### Milvus

**连接配置：**
```
host: milvus-standalone
port: 19530
```

**管理界面：**
- MinIO Web UI: http://claw-ai.com:9002
  - 用户名: minioadmin
  - 密码: minioadmin

---

## 监控与日志

### Prometheus

访问地址: http://claw-ai.com:9090

**配置文件位置：** `prometheus/prometheus.yml`

**添加新的监控目标：**
```yaml
scrape_configs:
  - job_name: 'custom-service'
    static_configs:
      - targets: ['service:port']
```

### Grafana

访问地址: https://claw-ai.com/grafana

**默认凭据：**
- 用户名: admin
- 密码: admin（首次登录后修改）

**添加 Prometheus 数据源：**
1. Configuration → Data Sources → Add data source
2. 选择 Prometheus
3. URL: http://prometheus:9090
4. 点击 Save & Test

### Loki

访问地址: http://claw-ai.com:3100

**查询示例：**
```logql
{service="claw-ai-backend"} |= "error"
{service="claw-ai-backend"} |~ "Exception.*"
{service="claw-ai-backend"} | line_format "{{.message}}" | json | status >= 500
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f claw-ai-backend

# 查看最近 100 行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 claw-ai-backend

# 查看日志统计
docker-compose -f docker-compose.prod.yml logs --tail=0 --follow | grep --line-buffered -E "ERROR|WARN"
```

---

## 备份与恢复

### 备份

**手动备份：**
```bash
bash scripts/backup.sh
```

**备份内容：**
- PostgreSQL 数据库
- Redis 数据
- Milvus 数据（etcd + MinIO）
- 上传文件
- 配置文件

**备份位置：** `backups/daily/YYYYMMDD-HHMMSS/`

### 恢复

**从备份恢复：**
```bash
bash scripts/backup.sh --restore backups/daily/20240215-020000
```

**仅恢复数据库：**
```bash
gunzip < backups/daily/20240215-020000/postgres-claw_ai.sql.gz | \
    docker exec -i claw_ai_postgres psql -U claw_ai claw_ai
```

### 备份策略

- **每日备份**: 保留 7 天
- **每周备份**: 每周一创建，保留 30 天
- **每月备份**: 每月第一天创建，保留 365 天

---

## 回滚操作

### 查看可用备份

```bash
bash scripts/rollback.sh --list
```

### 回滚到指定备份

```bash
# 交互式回滚
bash scripts/rollback.sh

# 使用备份编号
bash scripts/rollback.sh 1

# 使用备份目录
bash scripts/rollback.sh --backup ./backups/daily/20240215-020000

# 自动确认回滚
bash scripts/rollback.sh 1 -y
```

### 部分回滚

```bash
# 仅回滚数据库
bash scripts/rollback.sh 1 --skip-redis --skip-milvus --skip-uploads

# 仅回滚配置
bash scripts/rollback.sh 1 --skip-db --skip-redis --skip-milvus --skip-uploads
```

---

## 性能优化

### Docker 资源限制

编辑 `docker-compose.prod.yml`，为每个服务添加资源限制：

```yaml
services:
  claw-ai-backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Nginx 优化

1. **启用 Gzip 压缩**（已配置）
2. **启用缓存**
3. **调整 Worker 进程数**（已自动配置）
4. **启用 HTTP/2**（已配置）

### PostgreSQL 优化

编辑 `docker-compose.prod.yml` 中的 PostgreSQL 配置：

```yaml
command:
  - "postgres"
  - "-c"
  - "max_connections=200"
  - "-c"
  - "shared_buffers=256MB"
  - "-c"
  - "effective_cache_size=1GB"
  - "-c"
  - "maintenance_work_mem=64MB"
  - "-c"
  - "checkpoint_completion_target=0.9"
  - "-c"
  - "wal_buffers=16MB"
  - "-c"
  - "default_statistics_target=100"
  - "-c"
  - "random_page_cost=1.1"
  - "-c"
  - "effective_io_concurrency=200"
  - "-c"
  - "work_mem=1310kB"
  - "-c"
  - "min_wal_size=1GB"
  - "-c"
  - "max_wal_size=4GB"
```

### Redis 优化

编辑 `docker-compose.prod.yml` 中的 Redis 配置：

```yaml
command: redis-server --appendonly yes --requirepass password --maxmemory 512mb --maxmemory-policy allkeys-lru
```

---

## 安全加固

### 1. 使用强密码

所有密码都应使用 `openssl rand -hex 32` 生成。

### 2. 限制网络访问

使用防火墙限制访问：

```bash
sudo ufw allow from 192.168.1.0/24 to any port 22
sudo ufw allow from 192.168.1.0/24 to any port 5432
```

### 3. 启用 SELinux（可选）

```bash
sudo apt-get install -y selinux-basics
sudo selinux-activate
sudo selinux-config-enforcing
```

### 4. 定期更新

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 5. 配置日志审计

```bash
sudo auditctl -w /etc/passwd -p wa -k passwd_changes
sudo auditctl -w /etc/shadow -p wa -k shadow_changes
sudo auditctl -w /var/log/claw-ai -p wa -k claw_ai_logs
```

---

## 故障排查

### 服务无法启动

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs [service_name]

# 检查端口占用
netstat -tlnp | grep :[port]

# 检查磁盘空间
df -h
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 状态
docker exec claw_ai_postgres pg_isready

# 测试连接
docker exec -it claw_ai_postgres psql -U claw_ai -d claw_ai

# 检查日志
docker-compose -f docker-compose.prod.yml logs postgres
```

### SSL 证书问题

```bash
# 检查证书状态
sudo certbot certificates

# 测试续期
sudo certbot renew --dry-run

# 查看证书有效期
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates
```

### 内存不足

```bash
# 查看内存使用
free -h

# 查看容器资源使用
docker stats

# 清理未使用的资源
docker system prune -a --volumes
```

### 性能问题

```bash
# 查看系统负载
htop

# 查看数据库连接
docker exec claw_ai_postgres psql -U claw_ai -d claw_ai -c "SELECT * FROM pg_stat_activity;"

# 查看 Redis 慢查询
docker exec claw_ai_redis redis-cli -a password --latency
```

---

## 日常运维

### 每日检查

```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 检查日志错误
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

### 每周检查

```bash
# 检查备份完整性
ls -lh backups/daily/

# 检查 SSL 证书有效期
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates

# 检查系统更新
sudo apt-get update
sudo apt-get upgrade -y
```

### 每月检查

```bash
# 审查日志
docker-compose -f docker-compose.prod.yml logs --since 1m > monthly-review.log

# 审查监控数据（Grafana）

# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理旧备份
find backups/ -type d -mtime +180 -exec rm -rf {} + 2>/dev/null || true
```

---

## 常用命令速查

```bash
# 服务管理
docker-compose -f docker-compose.prod.yml up -d           # 启动服务
docker-compose -f docker-compose.prod.yml down           # 停止服务
docker-compose -f docker-compose.prod.yml restart        # 重启服务
docker-compose -f docker-compose.prod.yml ps              # 查看状态
docker-compose -f docker-compose.prod.yml logs -f        # 查看日志

# 备份和恢复
bash scripts/backup.sh                                    # 备份
bash scripts/backup.sh --restore <backup_dir>            # 恢复
bash scripts/rollback.sh --list                           # 列出备份
bash scripts/rollback.sh 1 -y                             # 回滚

# 数据库
bash scripts/migrate.sh                                   # 迁移
bash scripts/migrate.sh --status                          # 查看状态

# 监控
docker stats                                              # 资源使用
docker-compose -f docker-compose.prod.yml exec claw_ai_backend top
```

---

## 附录

### A. 端口映射

| 服务 | 容器端口 | 宿主机端口 | 用途 |
|------|----------|------------|------|
| Nginx | 80, 443 | 80, 443 | HTTP/HTTPS |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存 |
| Milvus | 19530, 9091 | 19530, 9091 | 向量数据库 |
| MinIO | 9000, 9001 | 9001, 9002 | 对象存储 |
| Flower | 5555 | 5555 | Celery 监控 |
| Prometheus | 9090 | 9090 | 指标收集 |
| Grafana | 3000 | 3000 | 可视化 |
| Loki | 3100 | 3100 | 日志聚合 |

### B. 目录结构

```
claw-ai-backend/
├── nginx/
│   ├── nginx.conf          # Nginx 配置
│   └── ssl/                # SSL 证书
├── scripts/
│   ├── deploy.sh           # 部署脚本
│   ├── backup.sh           # 备份脚本
│   ├── rollback.sh         # 回滚脚本
│   └── migrate.sh          # 迁移脚本
├── backups/
│   ├── daily/              # 每日备份
│   ├── weekly/             # 每周备份
│   └── monthly/            # 每月备份
├── logs/                   # 应用日志
├── uploads/                # 上传文件
├── docker-compose.prod.yml # 生产环境编排
├── .env.prod               # 生产环境变量
└── Dockerfile              # 镜像构建
```

### C. 联系方式

- **技术支持**: support@claw-ai.com
- **文档**: https://docs.claw-ai.com
- **GitHub**: https://github.com/your-org/claw-ai-backend

---

**文档版本**: 1.0.0
**最后更新**: 2024-02-15
