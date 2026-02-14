# CLAW.AI 生产环境部署检查清单

本文档提供了 CLAW.AI 生产环境部署的完整检查清单，确保每个步骤都正确执行。

---

## 📋 部署前检查

### 1. 服务器准备

- [ ] **操作系统**: Ubuntu 22.04 LTS 或更高版本
- [ ] **CPU**: 至少 2 核（推荐 4 核或更多）
- [ ] **内存**: 至少 4GB（推荐 8GB 或更多）
- [ ] **存储**: 至少 50GB SSD（推荐 100GB 或更多）
- [ ] **网络**: 公网 IP 地址
- [ ] **SSH**: 已配置 SSH 访问

### 2. 域名和 DNS

- [ ] **域名**: 已注册域名（如 claw-ai.com）
- [ ] **DNS 解析**: A 记录指向服务器 IP
- [ ] **WWW 子域**: www.claw-ai.com 也已解析
- [ ] **DNS 传播**: 已等待 DNS 完全传播（使用 `dig` 或 `nslookup` 验证）

```bash
# 验证 DNS 解析
dig +short claw-ai.com
dig +short www.claw-ai.com
```

### 3. 网络端口

- [ ] **端口 80**: 已开放（HTTP）
- [ ] **端口 443**: 已开放（HTTPS）
- [ ] **端口 22**: 已开放（SSH，建议限制 IP）
- [ ] **防火墙**: 已配置 UFW 或 iptables

```bash
# 检查防火墙状态
sudo ufw status
```

### 4. 软件依赖

- [ ] **Docker**: 已安装（版本 20.10+）
- [ ] **Docker Compose**: 已安装（版本 2.0+）
- [ ] **Git**: 已安装（版本 2.0+）
- [ ] **Certbot**: 已安装（版本 1.0+）
- [ ] **基础工具**: curl, vim, htop, net-tools

```bash
# 验证安装
docker --version
docker-compose --version
git --version
certbot --version
```

---

## 🔧 系统配置检查

### 5. 系统参数优化

- [ ] **TCP 参数**: 已优化 `/etc/sysctl.conf`
- [ ] **文件描述符**: 已提高 `fs.file-max`
- [ ] **共享内存**: 已配置 `shmmax` 和 `shmall`

```bash
# 查看当前配置
sysctl -a | grep -E "somaxconn|tcp_max_syn_backlog|file-max"
```

### 6. 目录结构

- [ ] **日志目录**: `/var/log/claw-ai` 已创建
- [ ] **备份目录**: `/var/lib/claw-ai/backups` 已创建
- [ ] **上传目录**: `/var/lib/claw-ai/uploads` 已创建
- [ ] **SSL 目录**: `/var/lib/claw-ai/ssl` 已创建
- [ ] **权限**: 所有目录已正确设置权限

```bash
# 验证目录和权限
ls -la /var/log/claw-ai
ls -la /var/lib/claw-ai
```

### 7. 时间同步

- [ ] **NTP 服务**: 已配置并运行
- [ ] **时区**: 已设置为正确的时区

```bash
# 检查时间同步
timedatectl status
```

---

## 🔐 安全配置检查

### 8. SSL 证书

- [ ] **证书申请**: 已成功申请 Let's Encrypt 证书
- [ ] **证书位置**: 已复制到 `nginx/ssl/` 目录
- [ ] **证书权限**: 正确设置（644）
- [ ] **证书有效期**: 检查证书未过期
- [ ] **自动续期**: 已配置 cron 任务

```bash
# 验证证书
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates

# 测试续期
sudo certbot renew --dry-run
```

### 9. 环境变量

- [ ] **配置文件**: `.env.prod` 已创建
- [ ] **数据库密码**: 已修改为强密码
- [ ] **Redis 密码**: 已修改为强密码
- [ ] **JWT 密钥**: 已生成（`openssl rand -hex 32`）
- [ ] **API Keys**: 已配置 Zhipu AI 和 Pinecone
- [ ] **敏感信息**: 无默认密码残留

```bash
# 检查是否有默认密码
grep -r "your_secure_password_here" .env.prod
```

### 10. 防火墙规则

- [ ] **SSH**: 已配置来源 IP 限制（推荐）
- [ ] **HTTP/HTTPS**: 已允许
- [ ] **数据库端口**: 已禁止外网访问
- [ ] **默认策略**: 已设置为拒绝入站

```bash
# 查看防火墙规则
sudo ufw status numbered
```

---

## 🚀 部署过程检查

### 11. 项目代码

- [ ] **代码拉取**: 已从 Git 仓库拉取最新代码
- [ ] **权限设置**: 脚本文件已设置可执行权限
- [ ] **配置文件**: 所有配置文件已准备

```bash
# 设置脚本权限
chmod +x scripts/*.sh
```

### 12. Docker 镜像

- [ ] **镜像拉取**: 所有镜像已成功拉取
- [ ] **镜像构建**: 自定义镜像已成功构建
- [ ] **镜像标签**: 镜像版本正确

```bash
# 查看镜像
docker images | grep claw
```

### 13. 服务启动

- [ ] **容器创建**: 所有容器已成功创建
- [ ] **容器启动**: 所有容器已成功启动
- [ ] **健康检查**: 所有服务健康检查通过
- [ ] **日志检查**: 无严重错误日志

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看健康状态
docker-compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}"
```

### 14. 数据库迁移

- [ ] **迁移执行**: 数据库迁移已成功执行
- [ ] **表创建**: 所有表已创建
- [ ] **索引创建**: 所有索引已创建
- [ ] **种子数据**: 种子数据已导入（如有）

```bash
# 运行迁移
bash scripts/migrate.sh

# 查看迁移状态
bash scripts/migrate.sh --status
```

---

## ✅ 功能验证检查

### 15. API 服务

- [ ] **健康检查**: `/health` 端点返回 200
- [ ] **认证**: 登录接口正常工作
- [ ] **API 响应**: 主要 API 接口正常响应
- [ ] **错误处理**: 错误接口返回正确的错误信息

```bash
# 健康检查
curl -f https://claw-ai.com/health

# API 测试
curl -X POST https://claw-ai.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

### 16. 数据库连接

- [ ] **PostgreSQL**: 连接正常
- [ ] **Redis**: 连接正常
- [ ] **Milvus**: 连接正常

```bash
# 测试 PostgreSQL
docker exec claw_ai_postgres pg_isready

# 测试 Redis
docker exec claw_ai_redis redis-cli -a $REDIS_PASSWORD ping

# 测试 Milvus
curl http://localhost:19530/healthz
```

### 17. 文件上传

- [ ] **上传目录**: 可写权限已配置
- [ ] **上传测试**: 文件上传功能正常
- [ ] **文件访问**: 上传的文件可通过 URL 访问

### 18. 监控服务

- [ ] **Prometheus**: 访问正常（http://claw-ai.com:9090）
- [ ] **Grafana**: 访问正常（https://claw-ai.com/grafana）
- [ ] **Flower**: 访问正常（https://claw-ai.com/flower）
- [ ] **数据源**: Prometheus 数据源已配置
- [ ] **仪表板**: 仪表板已导入

### 19. 日志收集

- [ ] **Loki**: 日志聚合正常
- [ ] **Promtail**: 日志采集正常
- [ ] **日志查询**: 可在 Grafana 中查询日志

```bash
# 测试日志查询
curl -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query={service="claw-ai-backend"}'
```

---

## 🔄 运维配置检查

### 20. 备份配置

- [ ] **备份脚本**: 已设置可执行权限
- [ ] **定时任务**: Cron 任务已配置
- [ ] **备份测试**: 备份功能已测试
- [ ] **备份验证**: 备份文件完整性已验证

```bash
# 测试备份
bash scripts/backup.sh

# 验证备份文件
ls -lh backups/daily/
```

### 21. SSL 自动续期

- [ ] **续期脚本**: 已创建并设置权限
- [ ] **Cron 任务**: 自动续期任务已配置
- [ ] **续期测试**: 干跑测试成功

```bash
# 测试续期
sudo certbot renew --dry-run

# 检查 crontab
crontab -l | grep certbot
```

### 22. 日志轮转

- [ ] **日志轮转**: 已配置 logrotate
- [ ] **日志保留**: 保留策略已设置
- [ ] **日志清理**: 旧日志自动清理

```bash
# 查看 logrotate 配置
cat /etc/logrotate.d/claw-ai
```

### 23. 资源监控

- [ ] **Prometheus 导出器**: 已配置（PostgreSQL、Redis）
- [ ] **节点导出器**: 已配置（可选）
- [ ] **告警规则**: 告警规则已配置（可选）

---

## 🧪 压力测试检查

### 24. 性能测试

- [ ] **负载测试**: 已使用工具测试（如 Apache Bench）
- [ ] **并发测试**: 已测试并发请求
- [ ] **响应时间**: API 响应时间在可接受范围内

```bash
# 负载测试
ab -n 1000 -c 100 https://claw-ai.com/health
```

### 25. 容错测试

- [ ] **容器重启**: 服务容器可自动重启
- [ ] **数据库重连**: 数据库连接断开后可自动重连
- [ ] **故障转移**: 主节点故障时可切换

---

## 📊 最终验收检查

### 26. 完整性检查

- [ ] **所有服务**: 所有服务正常运行
- [ ] **无错误日志**: 最近 1 小时内无严重错误
- [ ] **资源使用**: CPU、内存使用正常
- [ ] **磁盘空间**: 磁盘空间充足（> 20%）

```bash
# 检查资源使用
docker stats --no-stream

# 检查磁盘空间
df -h
```

### 27. 文档更新

- [ ] **部署文档**: 已更新部署日志
- [ ] **密码记录**: 已安全保存密码
- [ ] **访问凭证**: 已记录所有访问地址和凭据
- [ ] **联系方式**: 已提供技术支持联系方式

### 28. 交接检查

- [ ] **访问权限**: 已移交必要权限
- [ ] **文档交付**: 已交付完整文档
- [ ] **培训完成**: 运维人员已培训
- [ ] **演练完成**: 已进行故障演练

---

## 📝 部署后维护清单

### 每日检查

- [ ] 检查服务状态（`docker-compose ps`）
- [ ] 检查错误日志
- [ ] 检查磁盘空间
- [ ] 检查备份是否完成

### 每周检查

- [ ] 检查备份完整性
- [ ] 检查 SSL 证书有效期
- [ ] 检查系统更新
- [ ] 审查安全日志

### 每月检查

- [ ] 审查性能指标
- [ ] 清理旧日志和备份
- [ ] 更新依赖版本
- [ ] 进行灾难恢复演练

---

## 🔍 问题排查清单

### 服务无法启动

- [ ] 检查端口占用
- [ ] 检查磁盘空间
- [ ] 检查 Docker 守护进程
- [ ] 检查配置文件语法

### 数据库连接失败

- [ ] 检查数据库容器状态
- [ ] 检查连接字符串
- [ ] 检查防火墙规则
- [ ] 检查数据库日志

### SSL 证书问题

- [ ] 检查证书文件权限
- [ ] 检查证书有效期
- [ ] 检查域名解析
- [ ] 检查 Nginx 配置

### 性能问题

- [ ] 检查资源使用（`docker stats`）
- [ ] 检查慢查询日志
- [ ] 检查网络连接
- [ ] 检查应用日志

---

## 📞 应急联系信息

**技术支持**: support@claw-ai.com
**紧急联系**: +86-xxx-xxxx-xxxx
**文档地址**: https://docs.claw-ai.com

---

## ✍️ 部署记录

| 项目 | 内容 |
|------|------|
| 部署日期 | |
| 部署人员 | |
| 服务器 IP | |
| 域名 | |
| 数据库密码 | (保存到密码管理器) |
| Redis 密码 | (保存到密码管理器) |
| JWT 密钥 | (保存到密码管理器) |
| 备注事项 | |

---

**检查清单版本**: 1.0.0
**最后更新**: 2024-02-15
