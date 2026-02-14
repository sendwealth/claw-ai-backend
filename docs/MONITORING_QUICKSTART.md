# CLAW.AI 监控系统 - 快速开始

## 🎯 5 分钟快速部署

### 步骤 1：准备环境

```bash
cd /home/wuying/clawd/claw-ai-backend
cp .env.prod.example .env.prod
```

### 步骤 2：编辑环境变量

```bash
vim .env.prod
```

添加以下配置：

```bash
# Grafana 配置
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password_here
GRAFANA_ROOT_URL=https://openspark.online/grafana
```

### 步骤 3：启动监控服务

```bash
# 启动所有服务（包括监控）
docker-compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤 4：验证部署

```bash
# 检查服务健康状态
curl http://localhost:9090/-/healthy   # Prometheus
curl http://localhost:3000/api/health   # Grafana
curl http://localhost:3100/ready        # Loki
```

### 步骤 5：访问监控面板

- **Grafana**：http://localhost:3000 (admin / your_secure_password_here)
- **Prometheus**：http://localhost:9090
- **Loki**：http://localhost:3100

## 📊 查看预置仪表板

登录 Grafana 后：

1. 左侧菜单 → Dashboards
2. 找到 "CLAW.AI" 文件夹
3. 选择要查看的仪表板：
   - **CLAW.AI 系统概览** - 整体健康状态
   - **CLAW.AI 性能监控** - API 性能指标
   - **CLAW.AI 资源监控** - 系统资源使用

## 🔍 快速查询示例

### Prometheus 查询

在 Prometheus 或 Grafana 中执行：

```promql
# 当前请求速率
rate(claw_ai_http_requests_total[5m])

# 平均响应时间
rate(claw_ai_http_request_duration_seconds_sum[5m]) / rate(claw_ai_http_request_duration_seconds_count[5m])

# P95 响应时间
histogram_quantile(0.95, rate(claw_ai_http_request_duration_seconds_bucket[5m]))

# 错误率
rate(claw_ai_http_requests_total{status=~"5.."}[5m]) / rate(claw_ai_http_requests_total[5m])
```

### Loki 日志查询

在 Grafana "Explore" → 选择 "Loki" 数据源：

```logql
{service="claw-ai-backend"} |= "error"

{service="nginx"} |= "500"

{app="claw-ai-backend"} |~ "Exception"

# 统计错误数量
count_over_time({service="claw-ai-backend"} |= "error" [5m])
```

## 🛠️ 常用命令

```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 停止所有服务
docker-compose -f docker-compose.prod.yml down

# 重启监控服务
docker-compose -f docker-compose.prod.yml restart prometheus grafana loki promtail

# 查看服务日志
docker-compose -f docker-compose.prod.yml logs -f [service]

# 查看所有服务状态
docker-compose -f docker-compose.prod.yml ps

# 清理所有数据（谨慎使用！）
docker-compose -f docker-compose.prod.yml down -v
```

## 📝 下一步

- 阅读完整部署文档：`docs/MONITORING_DEPLOYMENT.md`
- 自定义仪表板配置
- 配置告警规则（AlertManager）
- 设置定期备份

## ⚠️ 注意事项

1. **生产环境**：务必修改默认密码
2. **防火墙**：配置防火墙规则限制端口访问
3. **备份**：定期备份 Grafana 配置和仪表板
4. **资源**：监控服务会消耗额外资源，确保服务器有足够容量

---

**需要帮助？** 查看 `docs/MONITORING_DEPLOYMENT.md` 获取完整文档。
