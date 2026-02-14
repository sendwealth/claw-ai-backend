# CLAW.AI 监控指标参考文档

## 📊 指标分类

### 1. HTTP 请求指标

| 指标名称 | 类型 | 标签 | 描述 |
|---------|------|------|------|
| `claw_ai_http_requests_total` | Counter | method, endpoint, status | HTTP 请求总数 |
| `claw_ai_http_request_duration_seconds` | Histogram | method, endpoint | 请求持续时间 |
| `claw_ai_http_response_size_bytes` | Histogram | method, endpoint | 响应体大小 |
| `claw_ai_http_active_connections` | Gauge | - | 当前活跃连接数 |

**查询示例**：

```promql
# 每秒请求数 (RPS)
rate(claw_ai_http_requests_total[5m])

# 按端点分组
sum(rate(claw_ai_http_requests_total[5m])) by (endpoint)

# P95 响应时间
histogram_quantile(0.95, rate(claw_ai_http_request_duration_seconds_bucket[5m]))

# 平均响应时间
rate(claw_ai_http_request_duration_seconds_sum[5m]) / rate(claw_ai_http_request_duration_seconds_count[5m])

# 错误率
rate(claw_ai_http_requests_total{status=~"5.."}[5m]) / rate(claw_ai_http_requests_total[5m])
```

---

### 2. 业务指标

| 指标名称 | 类型 | 标签 | 描述 |
|---------|------|------|------|
| `claw_ai_conversations_total` | Counter | status | 对话总数 |
| `claw_ai_messages_total` | Counter | role | 消息总数 |

**查询示例**：

```promql
# 对话创建速率
rate(claw_ai_conversations_total{status="created"}[5m])

# 用户消息速率
rate(claw_ai_messages_total{role="user"}[5m])

# AI 响应速率
rate(claw_ai_messages_total{role="assistant"}[5m])
```

---

### 3. AI 响应指标

| 指标名称 | 类型 | 标签 | 描述 |
|---------|------|------|------|
| `claw_ai_ai_response_duration_seconds` | Histogram | model | AI 响应时间 |

**查询示例**：

```promql
# AI 响应时间 P95
histogram_quantile(0.95, rate(claw_ai_ai_response_duration_seconds_bucket{model="glm-4"}[5m]))

# 按模型分组的响应时间
rate(claw_ai_ai_response_duration_seconds_sum[5m]) by (model) / rate(claw_ai_ai_response_duration_seconds_count[5m]) by (model)
```

---

### 4. 数据库操作指标

| 指标名称 | 类型 | 标签 | 描述 |
|---------|------|------|------|
| `claw_ai_vector_db_operation_duration_seconds` | Histogram | operation | 向量数据库操作时间 |
| `claw_ai_db_pool_connections` | Gauge | state | 数据库连接池状态 |

**查询示例**：

```promql
# 向量查询时间 P95
histogram_quantile(0.95, rate(claw_ai_vector_db_operation_duration_seconds_bucket{operation="query"}[5m]))

# 数据库连接池使用率
claw_ai_db_pool_connections{state="active"} / (claw_ai_db_pool_connections{state="active"} + claw_ai_db_pool_connections{state="idle"})
```

---

### 5. 缓存操作指标

| 指标名称 | 类型 | 标签 | 描述 |
|---------|------|------|------|
| `claw_ai_redis_operation_duration_seconds` | Histogram | operation | Redis 操作时间 |

**查询示例**：

```promql
# Redis 操作时间
rate(claw_ai_redis_operation_duration_seconds_sum[5m]) / rate(claw_ai_redis_operation_duration_seconds_count[5m])

# 按操作类型分组
rate(claw_ai_redis_operation_duration_seconds_sum[5m]) by (operation) / rate(claw_ai_redis_operation_duration_seconds_count[5m]) by (operation)
```

---

### 6. 系统资源指标（需要 Node Exporter）

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `node_cpu_seconds_total` | Counter | CPU 时间 |
| `node_memory_*` | Gauge | 内存使用情况 |
| `node_filesystem_*` | Gauge | 文件系统使用情况 |
| `node_network_*` | Counter | 网络流量 |
| `node_load1` / `node_load5` / `node_load15` | Gauge | 系统负载 |

**查询示例**：

```promql
# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 内存使用率
100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100)

# 磁盘使用率
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# 网络流量
rate(node_network_receive_bytes_total[5m])
rate(node_network_transmit_bytes_total[5m])
```

---

### 7. PostgreSQL 指标（需要 PostgreSQL Exporter）

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `pg_stat_database_*` | Gauge | 数据库统计 |
| `pg_stat_activity_count` | Gauge | 活跃连接数 |
| `pg_replication_lag` | Gauge | 复制延迟 |

**查询示例**：

```promql
# 数据库连接数
pg_stat_activity_count{datname="claw_ai"}

# 慢查询数量
rate(pg_stat_statements_calls_total[5m]) > 0.1

# 数据库大小
pg_database_size_bytes{datname="claw_ai"}
```

---

### 8. Redis 指标（需要 Redis Exporter）

| 指标名称 | 类型 | 描述 |
|---------|------|------|
| `redis_up` | Gauge | Redis 是否在线 |
| `redis_connected_clients` | Gauge | 连接客户端数 |
| `redis_memory_used_bytes` | Gauge | 内存使用量 |
| `redis_keyspace_*` | Gauge | 键空间信息 |

**查询示例**：

```promql
# Redis 连接数
redis_connected_clients

# Redis 内存使用
redis_memory_used_bytes

# 缓存命中率
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))
```

---

## 🎯 常用查询场景

### 1. 性能监控

```promql
# API 性能摘要
rate(claw_ai_http_requests_total[5m]) as rps,
histogram_quantile(0.95, rate(claw_ai_http_request_duration_seconds_bucket[5m])) as p95_latency
```

### 2. 错误追踪

```promql
# 5xx 错误率
rate(claw_ai_http_requests_total{status=~"5.."}[5m]) / rate(claw_ai_http_requests_total[5m])

# 4xx 错误率
rate(claw_ai_http_requests_total{status=~"4.."}[5m]) / rate(claw_ai_http_requests_total[5m])
```

### 3. 资源使用

```promql
# 综合资源概览
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) as cpu_usage,
100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100) as memory_usage
```

### 4. 业务健康

```promql
# 对话成功率
rate(claw_ai_conversations_total{status="success"}[5m]) / rate(claw_ai_conversations_total[5m])

# AI 响应可用性
rate(claw_ai_messages_total{role="assistant"}[5m]) / rate(claw_ai_messages_total{role="user"}[5m])
```

---

## 📏 指标阈值参考

### 建议告警阈值

| 指标 | 警告 | 严重 |
|------|------|------|
| API 响应时间 (P95) | > 500ms | > 1000ms |
| API 错误率 | > 1% | > 5% |
| CPU 使用率 | > 70% | > 90% |
| 内存使用率 | > 80% | > 95% |
| 磁盘使用率 | > 80% | > 95% |
| AI 响应时间 (P95) | > 3000ms | > 5000ms |
| 数据库连接池使用率 | > 80% | > 95% |
| Redis 内存使用率 | > 80% | > 95% |

---

## 🎨 Grafana 查询技巧

### 1. 使用变量

创建仪表板变量以增强灵活性：

```
# 时间范围变量
$__range
$__range_s

# 实例变量
$instance

# 标签变量
label_values(up, job)
```

### 2. 聚合函数

```promql
# 按标签聚合
sum(rate(claw_ai_http_requests_total[5m])) by (method)

# 求平均值
avg(rate(claw_ai_http_request_duration_seconds_sum[5m]) / rate(claw_ai_http_request_duration_seconds_count[5m]))

# 求最大值
max(rate(claw_ai_http_requests_total[5m]))

# 求最小值
min(rate(claw_ai_http_requests_total[5m]))
```

### 3. 时间范围

```promql
# 最近 5 分钟
rate(claw_ai_http_requests_total[5m])

# 最近 1 小时
rate(claw_ai_http_requests_total[1h])

# 最近 1 天
rate(claw_ai_http_requests_total[1d])

# 使用仪表板时间范围
rate(claw_ai_http_requests_total[$__range])
```

---

## 🔍 高级查询技巧

### 1. 预测分析

```promql
# 预测未来趋势
predict_linear(claw_ai_http_requests_total[1h], 3600)
```

### 2. 异常检测

```promql
# 检测异常值
rate(claw_ai_http_requests_total[5m]) > (avg(rate(claw_ai_http_requests_total[5m])) * 2)
```

### 3. 百分位计算

```promql
# 计算多个百分位
histogram_quantile(0.50, rate(claw_ai_http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.90, rate(claw_ai_http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(claw_ai_http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(claw_ai_http_request_duration_seconds_bucket[5m]))
```

---

## 📚 参考资料

- [Prometheus 查询语言文档](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana 变量语法](https://grafana.com/docs/grafana/latest/variables/variable-syntax/)
- [PromQL 最佳实践](https://prometheus.io/docs/practices/naming/)

---

**版本**：1.0.0
**更新日期**：2024-02-14
