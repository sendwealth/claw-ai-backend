# CLAW.AI 监控系统部署指南

## 📋 目录

- [架构概览](#架构概览)
- [组件说明](#组件说明)
- [快速部署](#快速部署)
- [配置说明](#配置说明)
- [访问监控面板](#访问监控面板)
- [常用操作](#常用操作)
- [故障排查](#故障排查)

---

## 🏗️ 架构概览

CLAW.AI 监控系统采用企业级监控架构，包含以下核心组件：

```
┌─────────────────────────────────────────────────────────────┐
│                       监控系统架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Grafana    │◄────────┤  Prometheus   │                 │
│  │  可视化      │         │  指标收集     │                 │
│  │   :3000      │         │   :9090      │                 │
│  └──────┬───────┘         └──────┬───────┘                 │
│         │                        │                          │
│         │                        │                          │
│         │                 ┌──────┴───────┐                  │
│         │                 │  Exporters   │                  │
│         │                 ├──────────────┤                  │
│         │                 │ - FastAPI    │                  │
│         │                 │ - PostgreSQL  │                  │
│         │                 │ - Redis       │                  │
│         │                 │ - Node (可选) │                  │
│         │                 └──────────────┘                  │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │     Loki     │◄────────┤   Promtail   │                 │
│  │  日志聚合    │         │  日志采集     │                 │
│  │   :3100      │         │    :9080     │                 │
│  └──────────────┘         └──────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 组件说明

### 1. Prometheus
- **功能**：指标收集和存储
- **端口**：9090
- **数据保留**：30 天
- **采集间隔**：15 秒（默认）

### 2. Grafana
- **功能**：数据可视化和仪表板
- **端口**：3000
- **默认账号**：admin / admin
- **预置仪表板**：
  - CLAW.AI 系统概览
  - CLAW.AI 性能监控
  - CLAW.AI 资源监控

### 3. Loki
- **功能**：日志聚合和存储
- **端口**：3100
- **数据保留**：30 天

### 4. Promtail
- **功能**：日志采集和转发
- **端口**：9080
- **采集源**：
  - Docker 容器日志
  - FastAPI 应用日志
  - Nginx 访问日志

### 5. Exporters
- **PostgreSQL Exporter** (9187)
- **Redis Exporter** (9121)
- **FastAPI 内置指标** (/metrics)

---

## 🚀 快速部署

### 前置条件

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 部署步骤

#### 1. 克隆项目（如未完成）

```bash
cd /home/wuying/clawd/claw-ai-backend
```

#### 2. 配置环境变量

编辑 `.env.prod` 文件（从 `.env.prod.example` 复制）：

```bash
cp .env.prod.example .env.prod
```

添加监控相关配置：

```bash
# Grafana 配置
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password
GRAFANA_ROOT_URL=https://openspark.online/grafana

# 其他配置保持不变...
```

#### 3. 更新 Prometheus 配置（可选）

如果需要修改采集目标，编辑：

```bash
vim prometheus/prometheus.yml
```

#### 4. 启动监控服务

```bash
# 启动所有服务（包括监控）
docker-compose -f docker-compose.prod.yml up -d

# 仅启动监控服务
docker-compose -f docker-compose.prod.yml up -d prometheus grafana loki promtail postgres-exporter redis-exporter

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

#### 5. 验证部署

检查服务是否正常运行：

```bash
# 检查 Prometheus
curl http://localhost:9090/-/healthy

# 检查 Grafana
curl http://localhost:3000/api/health

# 检查 Loki
curl http://localhost:3100/ready

# 检查 Promtail
curl http://localhost:9080/ready
```

---

## ⚙️ 配置说明

### Prometheus 配置文件

位置：`prometheus/prometheus.yml`

**关键配置项**：

```yaml
global:
  scrape_interval: 15s        # 采集间隔
  evaluation_interval: 15s    # 规则评估间隔

scrape_configs:
  - job_name: 'claw-ai-backend'
    static_configs:
      - targets: ['claw-ai-backend:8000']
    metrics_path: '/metrics'   # 指标端点
```

### Grafana 仪表板

位置：`grafana/dashboards/`

**可用仪表板**：

| 仪表板 | UID | 描述 |
|--------|-----|------|
| 系统概览 | `claw-ai-overview` | 整体系统健康状态 |
| 性能监控 | `claw-ai-performance` | API 性能指标 |
| 资源监控 | `claw-ai-resources` | 系统资源使用情况 |

### Loki 配置文件

位置：`loki/loki-config.yml`

**关键配置项**：

```yaml
limits_config:
  retention_period: 30d    # 日志保留时间
  ingestion_rate_mb: 10    # 速率限制
```

### Promtail 配置文件

位置：`promtail/promtail-config.yml`

**采集配置**：

```yaml
scrape_configs:
  - job_name: docker      # Docker 容器日志
  - job_name: fastapi     # FastAPI 应用日志
  - job_name: nginx       # Nginx 访问日志
```

---

## 🔗 访问监控面板

### Grafana

- **URL**：`http://localhost:3000` 或 `https://your-domain/grafana`
- **默认账号**：`admin / admin`
- **首次登录**：系统会要求修改密码

### Prometheus

- **URL**：`http://localhost:9090`
- **查询界面**：直接访问主页
- **状态**：`http://localhost:9090/status`

### Loki

- **URL**：`http://localhost:3100`
- **日志查询**：通过 Grafana Loki 数据源查询

---

## 🛠️ 常用操作

### 查看 Prometheus 指标

1. 访问 `http://localhost:9090`
2. 在查询框输入指标名称
3. 点击 "Execute" 查询

**常用查询示例**：

```promql
# 请求速率
rate(claw_ai_http_requests_total[5m])

# 响应时间 P95
histogram_quantile(0.95, rate(claw_ai_http_request_duration_seconds_bucket[5m]))

# 错误率
rate(claw_ai_http_requests_total{status=~"5.."}[5m]) / rate(claw_ai_http_requests_total[5m])
```

### Grafana 仪表板管理

1. **添加新仪表板**：
   - 点击 "+" → "Import"
   - 上传 JSON 文件或输入 Dashboard ID

2. **编辑仪表板**：
   - 打开仪表板
   - 点击右上角 "设置" 图标
   - 修改配置后保存

3. **导出仪表板**：
   - 点击 "设置" → "JSON Model"
   - 复制 JSON 保存

### 日志查询

在 Grafana 中：

1. 切换到 "Explore" 模式
2. 选择 "Loki" 数据源
3. 输入查询语句：

```logql
{service="claw-ai-backend"} |= "error"
{service="nginx"} |= "500"
{app="claw-ai-backend"} |~ "Exception"
```

### 导出数据

```bash
# 导出 Prometheus 数据（需要 curl 或 wget）
curl http://localhost:9090/federate?match[]={__name__=~".+"} > metrics.txt

# 导出 Grafana 仪表板
# 通过 UI 导出为 JSON 文件
```

---

## 📊 使用示例

### 添加自定义指标

在 FastAPI 应用中：

```python
from app.core import metrics

# 追踪 AI 响应
@metrics.track_ai_response(model="glm-4")
async def generate_response(prompt: str):
    # 业务逻辑
    return response

# 追踪数据库操作
@metrics.track_vector_db_operation(operation="query")
async def query_vectors(embedding: list):
    # 业务逻辑
    return results

# 手动记录指标
metrics.track_conversation(status="created")
metrics.track_message(role="user")
```

### 添加业务监控

```python
from app.core.metrics import (
    conversations_total,
    messages_total
)

# 在对话创建时
conversations_total.labels(status="created").inc()

# 在消息发送时
messages_total.labels(role="user").inc()
messages_total.labels(role="assistant").inc()
```

---

## 🔧 故障排查

### Prometheus 无法启动

**症状**：容器启动失败

**排查步骤**：

```bash
# 查看日志
docker-compose -f docker-compose.prod.yml logs prometheus

# 检查配置文件语法
docker run --rm -v $(pwd)/prometheus:/etc/prometheus \
  prom/prometheus:v2.48.0 \
  promtool check config /etc/prometheus/prometheus.yml
```

**常见问题**：
- 配置文件语法错误
- 端口冲突
- 权限问题

### Grafana 无法连接 Prometheus

**症状**：仪表板无数据

**排查步骤**：

1. 检查 Prometheus 是否正常运行
2. 检查数据源配置
3. 查看连接测试日志

```bash
# 测试 Prometheus 可达性
curl http://prometheus:9090/api/v1/targets
```

### 指标未采集

**症状**：指标为 0 或无数据

**排查步骤**：

1. 检查应用是否暴露 `/metrics` 端点
2. 检查 Prometheus 配置中的 targets
3. 查看采集日志

```bash
# 查看采集目标状态
curl http://localhost:9090/api/v1/targets | jq
```

### 日志未采集

**症状**：Loki 中无日志

**排查步骤**：

1. 检查 Promtail 日志
2. 检查配置文件中的路径
3. 验证 Docker 标签

```bash
# 查看 Promtail 日志
docker-compose -f docker-compose.prod.yml logs promtail

# 测试 Promtail 配置
docker run --rm -v $(pwd)/promtail:/etc/promtail \
  grafana/promtail:2.9.4 \
  --config.file=/etc/promtail/config.yml --dry-run
```

### 磁盘空间不足

**症状**：服务运行缓慢或停止

**解决方案**：

```bash
# 检查磁盘使用
df -h

# 清理 Prometheus 数据（谨慎操作）
docker-compose -f docker-compose.prod.yml stop prometheus
docker volume rm claw-ai-backend_prometheus_data
docker-compose -f docker-compose.prod.yml up -d prometheus
```

---

## 📈 性能优化

### Prometheus 优化

1. **调整采集间隔**：根据需求调整 `scrape_interval`
2. **数据保留时间**：修改 `storage.tsdb.retention.time`
3. **压缩数据**：使用 `--storage.tsdb.retention.size` 限制大小

### Grafana 优化

1. **缓存查询结果**：启用查询缓存
2. **减少刷新频率**：仪表板刷新间隔不宜过短
3. **使用变量**：避免硬编码大量查询

### Loki 优化

1. **调整保留策略**：根据需求修改 `retention_period`
2. **限制速率**：设置 `ingestion_rate_mb` 防止过载
3. **索引策略**：优化索引配置以减少存储

---

## 🔒 安全建议

### 生产环境注意事项

1. **修改默认密码**：
   - Grafana 管理员密码
   - Redis 密码
   - 数据库密码

2. **限制访问**：
   - 使用防火墙限制端口访问
   - 配置 Nginx 反向代理
   - 启用 HTTPS

3. **数据备份**：
   - 定期备份 Grafana 数据卷
   - 备份 Prometheus 配置文件
   - 导出重要仪表板配置

4. **监控告警**：
   - 配置 AlertManager
   - 设置关键指标告警
   - 配置通知渠道（邮件、Slack 等）

### Nginx 反向代理配置示例

```nginx
# Grafana
location /grafana/ {
    proxy_pass http://grafana:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Prometheus
location /prometheus/ {
    proxy_pass http://prometheus:9090/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

---

## 📚 参考资料

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [Loki 官方文档](https://grafana.com/docs/loki/latest/)
- [Promtail 官方文档](https://grafana.com/docs/loki/latest/send-data/promtail/)
- [FastAPI Prometheus 集成](https://fastapi.tiangolo.com/advanced/sub-applications/#using-the-fastapi-prometheus-middleware)

---

## 📞 支持

如有问题，请：

1. 查看本文档的故障排查部分
2. 检查容器日志：`docker-compose -f docker-compose.prod.yml logs [service]`
3. 查看相关组件的官方文档

---

**版本**：1.0.0
**更新日期**：2024-02-14
**维护者**：CLAW.AI Team
