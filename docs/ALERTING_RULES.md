# CLAW.AI 告警规则文档

**文档版本:** v1.0
**创建日期:** 2026-02-14
**适用环境:** 生产环境

---

## 1. 告警级别定义

| 级别 | 名称 | 响应时间 | 通知方式 | 影响范围 |
|------|------|---------|---------|---------|
| P0 | 紧急 | 30 分钟 | 飞书 + 邮件 + 短信 + 电话 | 系统完全不可用 |
| P1 | 严重 | 1 小时 | 飞书 + 邮件 + 短信 | 核心功能不可用 |
| P2 | 中等 | 4 小时 | 飞书 + 邮件 | 性能下降、部分功能异常 |
| P3 | 轻微 | 24 小时 | 飞书 | 业务指标异常、趋势预警 |

---

## 2. P0 - 紧急告警

### 2.1 系统宕机

**告警名称:** `system_down`

**告警描述:** 系统完全宕机，所有服务不可用

**触发条件:**
```
所有健康检查端点连续失败 >= 5 次（5分钟）
```

**检测表达式:**
```promql
up{job="claw-ai-backend"} == 0 for 5m
```

**通知配置:**
- 飞书群：@技术团队全员
- 邮件：tech-team@claw.ai
- 短信：技术负责人手机号
- 电话：技术负责人手机号（连续 P0 告警）

**处理步骤:**
1. 立即检查服务器状态
2. 查看系统日志定位问题
3. 尝试重启服务
4. 如无法解决，上报技术负责人

**恢复条件:**
```
所有健康检查端点连续成功 >= 3 次（3分钟）
```

---

### 2.2 API 完全不可用

**告警名称:** `api_unavailable`

**告警描述:** API 服务完全不可用，所有请求失败

**触发条件:**
```
API 请求失败率 == 100% 且持续时间 >= 5 分钟
```

**检测表达式:**
```promql
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) == 1 for 5m
```

**通知配置:**
- 飞书群：@后端团队 @运维团队
- 邮件：backend-team@claw.ai, ops-team@claw.ai
- 短信：后端负责人手机号
- 电话：后端负责人手机号

**处理步骤:**
1. 检查 API 服务进程状态
2. 查看应用日志和错误信息
3. 检查依赖服务状态（数据库、Redis 等）
4. 尝试重启 API 服务

**恢复条件:**
```
API 请求成功率 >= 99% 且持续时间 >= 3 分钟
```

---

### 2.3 数据库连接失败

**告警名称:** `database_connection_failed`

**告警描述:** 数据库连接失败，无法访问数据

**触发条件:**
```
数据库连接失败次数 >= 10 次/分钟 且持续时间 >= 3 分钟
```

**检测表达式:**
```promql
rate(db_connection_errors_total[5m]) >= 10 for 3m
```

**通知配置:**
- 飞书群：@后端团队 @DBA
- 邮件：backend-team@claw.ai
- 短信：DBA 手机号
- 电话：DBA 手机号

**处理步骤:**
1. 检查数据库服务状态
2. 验证数据库连接配置
3. 检查数据库连接数是否达到上限
4. 检查网络连通性

**恢复条件:**
```
数据库连接失败次数 = 0 且持续时间 >= 3 分钟
```

---

## 3. P1 - 严重告警

### 3.1 AI 响应失败率过高

**告警名称:** `ai_response_failure_rate_high`

**告警描述:** AI 对话失败率超过阈值

**触发条件:**
```
AI 响应失败率 > 10% 且持续时间 >= 10 分钟
```

**检测表达式:**
```promql
rate(ai_dialog_total{status="failed"}[10m]) / rate(ai_dialog_total[10m]) > 0.1 for 10m
```

**通知配置:**
- 飞书群：@AI团队 @后端团队
- 邮件：ai-team@claw.ai, backend-team@claw.ai
- 短信：AI 负责人手机号

**处理步骤:**
1. 检查 AI 模型服务状态
2. 查看失败原因日志
3. 检查知识库服务状态
4. 检查 API 限流配置

**恢复条件:**
```
AI 响应失败率 <= 5% 且持续时间 >= 10 分钟
```

---

### 3.2 API 响应时间过长

**告警名称:** `api_response_time_slow`

**告警描述:** API 响应时间超过阈值，严重影响用户体验

**触发条件:**
```
API P95 响应时间 > 5 秒 且持续时间 >= 10 分钟
```

**检测表达式:**
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[10m])) by (le)) > 5 for 10m
```

**通知配置:**
- 飞书群：@后端团队 @运维团队
- 邮件：backend-team@claw.ai
- 短信：后端负责人手机号

**处理步骤:**
1. 检查 API 请求日志，定位慢接口
2. 检查数据库慢查询
3. 检查外部依赖服务响应时间
4. 检查服务器资源使用情况

**恢复条件:**
```
API P95 响应时间 <= 3 秒 且持续时间 >= 10 分钟
```

---

### 3.3 数据库慢查询

**告警名称:** `database_slow_query`

**告警描述:** 数据库存在大量慢查询，影响性能

**触发条件:**
```
慢查询数量 >= 50 次/分钟 且持续时间 >= 10 分钟
```

**检测表达式:**
```promql
rate(db_slow_queries_total[10m]) >= 50 for 10m
```

**通知配置:**
- 飞书群：@后端团队 @DBA
- 邮件：backend-team@claw.ai
- 短信：DBA 手机号

**处理步骤:**
1. 获取慢查询日志
2. 分析慢查询 SQL
3. 添加或优化索引
4. 优化查询语句

**恢复条件:**
```
慢查询数量 <= 10 次/分钟 且持续时间 >= 10 分钟
```

---

## 4. P2 - 中等告警

### 4.1 AI 响应时间过长

**告警名称:** `ai_response_time_slow`

**告警描述:** AI 响应时间超过阈值，影响用户体验

**触发条件:**
```
AI P95 响应时间 > 3 秒 且持续时间 >= 15 分钟
```

**检测表达式:**
```promql
histogram_quantile(0.95, sum(rate(ai_dialog_duration_seconds_bucket[15m])) by (le)) > 3 for 15m
```

**通知配置:**
- 飞书群：@AI团队 @后端团队
- 邮件：ai-team@claw.ai

**处理步骤:**
1. 检查 AI 模型响应时间
2. 检查知识库查询时间
3. 检查网络延迟
4. 考虑启用缓存优化

**恢复条件:**
```
AI P95 响应时间 <= 2 秒 且持续时间 >= 15 分钟
```

---

### 4.2 错误率过高

**告警名称:** `error_rate_high`

**告警描述:** 系统错误率超过阈值

**触发条件:**
```
HTTP 5xx 错误率 > 5% 且持续时间 >= 15 分钟
```

**检测表达式:**
```promql
rate(http_requests_total{status=~"5.."}[15m]) / rate(http_requests_total[15m]) > 0.05 for 15m
```

**通知配置:**
- 飞书群：@后端团队
- 邮件：backend-team@claw.ai

**处理步骤:**
1. 查看错误日志
2. 统计错误类型分布
3. 优先处理高频错误
4. 更新错误监控规则

**恢复条件:**
```
HTTP 5xx 错误率 <= 2% 且持续时间 >= 15 分钟
```

---

### 4.3 Redis 命中率过低

**告警名称:** `redis_hit_rate_low`

**告警描述:** Redis 缓存命中率过低，影响性能

**触发条件:**
```
Redis 命中率 < 60% 且持续时间 >= 20 分钟
```

**检测表达式:**
```promql
redis_hits / (redis_hits + redis_misses) < 0.6 for 20m
```

**通知配置:**
- 飞书群：@后端团队 @运维团队
- 邮件：backend-team@claw.ai

**处理步骤:**
1. 检查 Redis 缓存策略
2. 检查缓存过期时间设置
3. 分析缓存未命中原因
4. 考虑增加缓存容量

**恢复条件:**
```
Redis 命中率 >= 70% 且持续时间 >= 20 分钟
```

---

### 4.4 数据库连接数过高

**告警名称:** `database_connection_high`

**告警描述:** 数据库连接数接近上限，存在连接池耗尽风险

**触发条件:**
```
数据库活跃连接数 > 80% 最大连接数 且持续时间 >= 15 分钟
```

**检测表达式:**
```promql
db_connections_active / db_connections_max > 0.8 for 15m
```

**通知配置:**
- 飞书群：@后端团队 @DBA
- 邮件：backend-team@claw.ai

**处理步骤:**
1. 检查连接池配置
2. 检查是否有长连接未释放
3. 优化连接池大小
4. 考虑增加数据库连接数上限

**恢复条件:**
```
数据库活跃连接数 <= 70% 最大连接数 且持续时间 >= 15 分钟
```

---

### 4.5 服务器 CPU 使用率过高

**告警名称:** `server_cpu_high`

**告警描述:** 服务器 CPU 使用率过高

**触发条件:**
```
CPU 使用率 > 90% 且持续时间 >= 10 分钟
```

**检测表达式:**
```promql
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 90 for 10m
```

**通知配置:**
- 飞书群：@运维团队
- 邮件：ops-team@claw.ai

**处理步骤:**
1. 检查高 CPU 进程
2. 分析是否有异常任务
3. 检查是否有死循环代码
4. 考虑扩容

**恢复条件:**
```
CPU 使用率 <= 80% 且持续时间 >= 10 分钟
```

---

### 4.6 服务器内存使用率过高

**告警名称:** `server_memory_high`

**告警描述:** 服务器内存使用率过高

**触发条件:**
```
内存使用率 > 90% 且持续时间 >= 15 分钟
```

**检测表达式:**
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90 for 15m
```

**通知配置:**
- 飞书群：@运维团队
- 邮件：ops-team@claw.ai

**处理步骤:**
1. 检查内存使用分布
2. 检查是否有内存泄漏
3. 优化内存使用
4. 考虑扩容

**恢复条件:**
```
内存使用率 <= 80% 且持续时间 >= 15 分钟
```

---

## 5. P3 - 轻微告警

### 5.1 用户留存率下降

**告警名称:** `user_retention_drop`

**告警描述:** 用户留存率环比下降超过阈值

**触发条件:**
```
次日留存率 环比下降 > 30%
```

**检测表达式:**
```sql
-- 每日计算的 SQL
SELECT
  date,
  retention_d1,
  LAG(retention_d1) OVER (ORDER BY date) AS prev_retention_d1,
  (retention_d1 - LAG(retention_d1) OVER (ORDER BY date)) / LAG(retention_d1) OVER (ORDER BY date) AS drop_rate
FROM user_retention_metrics
WHERE date = CURRENT_DATE - 1
HAVING drop_rate < -0.3
```

**通知配置:**
- 飞书群：@产品团队 @运营团队
- 邮件：product-team@claw.ai

**处理步骤:**
1. 分析留存率下降原因
2. 检查是否有产品功能变更
3. 分析用户流失路径
4. 制定改进方案

**恢复条件:**
```
次日留存率 环比下降 <= 10%
```

---

### 5.2 功能使用率下降

**告警名称:** `feature_usage_drop`

**告警描述:** 核心功能使用率环比下降超过阈值

**触发条件:**
```
核心功能使用率 环比下降 > 15%
```

**检测表达式:**
```sql
-- 每日计算的 SQL
SELECT
  date,
  feature_name,
  usage_rate,
  LAG(usage_rate) OVER (PARTITION BY feature_name ORDER BY date) AS prev_usage_rate,
  (usage_rate - LAG(usage_rate) OVER (PARTITION BY feature_name ORDER BY date)) / LAG(usage_rate) OVER (PARTITION BY feature_name ORDER BY date) AS drop_rate
FROM feature_usage_metrics
WHERE date = CURRENT_DATE - 1
  AND feature_name IN ('ai_dialog', 'knowledge_base', 'dashboard')
HAVING drop_rate < -0.15
```

**通知配置:**
- 飞书群：@产品团队
- 邮件：product-team@claw.ai

**处理步骤:**
1. 分析哪个功能使用率下降
2. 检查功能是否有 bug
3. 分析用户反馈
4. 优化功能体验

**恢复条件:**
```
功能使用率 环比下降 <= 5%
```

---

### 5.3 客户满意度下降

**告警名称:** `customer_satisfaction_drop`

**告警描述:** 客户满意度评分低于阈值或下降

**触发条件:**
```
平均满意度评分 < 4.0 或 环比下降 > 10%
```

**检测表达式:**
```sql
-- 每日计算的 SQL
SELECT
  date,
  AVG(rating) AS avg_rating,
  LAG(AVG(rating)) OVER (ORDER BY date) AS prev_avg_rating
FROM user_feedback
WHERE date = CURRENT_DATE - 1
GROUP BY date
HAVING AVG(rating) < 4.0
   OR (AVG(rating) - LAG(AVG(rating)) OVER (ORDER BY date)) / LAG(AVG(rating)) OVER (ORDER BY date) < -0.1
```

**通知配置:**
- 飞书群：@产品团队 @AI团队 @客服团队
- 邮件：product-team@claw.ai, ai-team@claw.ai, cs-team@claw.ai

**处理步骤:**
1. 查看差评内容
2. 分析主要问题类型
3. 制定改进措施
4. 回复用户反馈

**恢复条件:**
```
平均满意度评分 >= 4.2 且 环比下降 <= 5%
```

---

### 5.4 DAU 下降

**告警名称:** `dau_drop`

**告警描述:** 日活跃用户数下降超过阈值

**触发条件:**
```
DAU 环比下降 > 20%
```

**检测表达式:**
```sql
-- 每日计算的 SQL
SELECT
  date,
  dau,
  LAG(dau) OVER (ORDER BY date) AS prev_dau,
  (dau - LAG(dau) OVER (ORDER BY date)) / LAG(dau) OVER (ORDER BY date) AS drop_rate
FROM user_activity_metrics
WHERE date = CURRENT_DATE - 1
HAVING drop_rate < -0.2
```

**通知配置:**
- 飞书群：@产品团队 @运营团队
- 邮件：product-team@claw.ai

**处理步骤:**
1. 分析 DAU 下降原因
2. 检查是否有运营活动影响
3. 分析用户访问来源
4. 制定拉新/促活方案

**恢复条件:**
```
DAU 环比下降 <= 10%
```

---

### 5.5 AI 对话成功率下降

**告警名称:** `ai_success_rate_drop`

**告警描述:** AI 对话成功率下降超过阈值

**触发条件:**
```
AI 对话成功率 < 95% 或 环比下降 > 5%
```

**检测表达式:**
```sql
-- 每小时计算的 SQL
SELECT
  date,
  hour,
  success_count / total_count AS success_rate,
  LAG(success_count / total_count) OVER (ORDER BY date, hour) AS prev_success_rate
FROM ai_dialog_metrics
WHERE date = CURRENT_DATE AND hour = EXTRACT(HOUR FROM CURRENT_TIMESTAMP)
HAVING success_count / total_count < 0.95
   OR (success_count / total_count - LAG(success_count / total_count) OVER (ORDER BY date, hour)) / LAG(success_count / total_count) OVER (ORDER BY date, hour) < -0.05
```

**通知配置:**
- 飞书群：@AI团队
- 邮件：ai-team@claw.ai

**处理步骤:**
1. 分析失败原因
2. 检查知识库覆盖度
3. 检查 AI 模型状态
4. 优化回答质量

**恢复条件:**
```
AI 对话成功率 >= 97% 且 环比下降 <= 3%
```

---

### 5.6 续费率下降

**告警名称:** `renewal_rate_drop`

**告警描述:** 订阅续费率下降超过阈值

**触发条件:**
```
月度续费率 < 80% 或 环比下降 > 10%
```

**检测表达式:**
```sql
-- 每月计算的 SQL
SELECT
  month,
  renewal_count / expire_count AS renewal_rate,
  LAG(renewal_count / expire_count) OVER (ORDER BY month) AS prev_renewal_rate
FROM subscription_metrics
WHERE month = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
HAVING renewal_count / expire_count < 0.8
   OR (renewal_count / expire_count - LAG(renewal_count / expire_count) OVER (ORDER BY month)) / LAG(renewal_count / expire_count) OVER (ORDER BY month) < -0.1
```

**通知配置:**
- 飞书群：@产品团队 @运营团队 @客服团队
- 邮件：product-team@claw.ai

**处理步骤:**
1. 分析用户取消原因
2. 检查产品功能是否满足需求
3. 分析竞品情况
4. 优化续费激励方案

**恢复条件:**
```
月度续费率 >= 85% 且 环比下降 <= 5%
```

---

## 6. 告警抑制和静默

### 6.1 告警抑制规则

为了避免告警风暴，配置以下抑制规则：

1. **服务不可用时抑制下游告警**
   - 当 `system_down` 触发时，抑制所有其他告警

2. **数据库不可用时抑制相关告警**
   - 当 `database_connection_failed` 触发时，抑制 `database_slow_query`、`database_connection_high`

3. **AI 服务不可用时抑制相关告警**
   - 当 `ai_response_failure_rate_high` 触发时，抑制 `ai_response_time_slow`、`ai_success_rate_drop`

### 6.2 告警静默策略

以下情况可以临时静默告警：

1. **计划内维护**
   - 维护开始前 15 分钟创建静默规则
   - 维护结束后 30 分钟自动解除静默

2. **已知问题**
   - 已知问题正在修复中，可以临时静默相关告警
   - 静默时长不超过 24 小时

3. **误报**
   - 确认为误报的告警，可以临时静默
   - 需同时创建工单优化告警规则

---

## 7. 告警测试

### 7.1 测试计划

| 告警类型 | 测试频率 | 负责人 |
|---------|---------|-------|
| P0 告警 | 每月一次 | 运维团队 |
| P1 告警 | 每月一次 | 后端团队 |
| P2 告警 | 每季度一次 | 后端团队 |
| P3 告警 | 每半年一次 | 产品团队 |

### 7.2 测试流程

1. 准备测试环境
2. 模拟告警触发条件
3. 验证告警通知发送
4. 验证告警信息准确性
5. 记录测试结果
6. 优化告警规则

---

## 8. 告警优化

### 8.1 告警质量指标

- **误报率**：< 5%
- **漏报率**：< 1%
- **平均响应时间**：P0 < 10 分钟，P1 < 30 分钟，P2 < 2 小时，P3 < 12 小时
- **告警收敛率**：> 90%（避免告警风暴）

### 8.2 持续优化

1. **每周告警复盘**
   - 统计告警数量和级别分布
   - 分析误报原因
   - 优化告警规则

2. **每月告警评审**
   - 评估告警有效性
   - 调整告警阈值
   - 新增/删除告警规则

3. **每季度告警体系评估**
   - 评估整体告警体系效果
   - 调整告警级别定义
   - 优化通知方式

---

## 9. 附录

### 9.1 联系人信息

| 角色 | 负责人 | 飞书 | 手机 | 邮箱 |
|------|-------|------|------|------|
| 技术负责人 | [待填写] | @xxx | 138xxxx | xxx@claw.ai |
| 后端负责人 | [待填写] | @xxx | 139xxxx | xxx@claw.ai |
| AI 负责人 | [待填写] | @xxx | 137xxxx | xxx@claw.ai |
| DBA | [待填写] | @xxx | 136xxxx | xxx@claw.ai |
| 运维负责人 | [待填写] | @xxx | 135xxxx | xxx@claw.ai |
| 产品负责人 | [待填写] | @xxx | 134xxxx | xxx@claw.ai |

### 9.2 相关文档

- [产品监控体系文档](/home/wuying/clawd/claw-intelligence/reports/product-monitoring-strategy-2026-02-14.md)
- [问题诊断流程](/home/wuying/clawd/claw-ai-backend/docs/INCIDENT_MANAGEMENT.md)
- [告警通知配置](/home/wuying/clawd/claw-ai-backend/config/alerting.yaml)

---

**文档结束**
