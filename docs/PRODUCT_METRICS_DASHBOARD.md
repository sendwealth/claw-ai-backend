# CLAW.AI 产品指标看板

**文档版本:** v1.0
**创建日期:** 2026-02-14
**看板平台:** Grafana + 自研可视化

---

## 1. 概述

本文档定义了 CLAW.AI 产品的数据看板配置，包括看板结构、指标定义、可视化配置等。

### 1.1 看板分类

| 看板类别 | 看板名称 | 目标受众 | 更新频率 |
|---------|---------|---------|---------|
| 业务监控 | 产品概览 | 产品团队、管理层 | 实时 |
| 业务监控 | 用户行为分析 | 产品团队、运营团队 | 每日 |
| 业务监控 | AI 质量监控 | AI 团队 | 实时 |
| 业务监控 | 订阅分析 | 产品团队、运营团队 | 每日 |
| 技术监控 | 系统健康 | 技术团队、运维团队 | 实时 |
| 技术监控 | API 性能 | 后端团队 | 实时 |
| 技术监控 | 数据库监控 | DBA | 实时 |

---

## 2. 产品概览看板

### 2.1 看板配置

**看板 ID:** `product-overview`
**看板名称:** 产品概览
**刷新间隔:** 5 分钟

### 2.2 看板组件

#### 2.2.1 核心指标卡

**组件 1: 今日 DAU**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(DISTINCT user_id) AS value
FROM user_events
WHERE DATE(timestamp) = CURRENT_DATE
  AND user_id IS NOT NULL;
```

**显示配置:**
- 标题: "今日 DAU"
- 单位: "用户"
- 趋势: 环比昨日
- 颜色阈值:
  - 绿色: >= 环比增长 5%
  - 黄色: 环比下降 5-20%
  - 红色: 环比下降 > 20%

---

**组件 2: 今日新增用户**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(*) AS value
FROM users
WHERE DATE(created_at) = CURRENT_DATE;
```

**显示配置:**
- 标题: "今日新增用户"
- 单位: "用户"
- 趋势: 环比昨日
- 颜色阈值:
  - 绿色: >= 环比增长 10%
  - 黄色: 环比下降 10-30%
  - 红色: 环比下降 > 30%

---

**组件 3: 活跃对话数**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(DISTINCT dialog_id) AS value
FROM user_events
WHERE event_name = 'dialog_start'
  AND DATE(timestamp) = CURRENT_DATE;
```

**显示配置:**
- 标题: "活跃对话数"
- 单位: "对话"
- 趋势: 环比昨日
- 颜色阈值:
  - 绿色: >= 环比增长 5%
  - 黄色: 环比下降 5-15%
  - 红色: 环比下降 > 15%

---

**组件 4: AI 对话成功率**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) AS value
FROM ai_dialog_metrics
WHERE DATE(timestamp) = CURRENT_DATE;
```

**显示配置:**
- 标题: "AI 对话成功率"
- 单位: "%"
- 趋势: 环比昨日
- 颜色阈值:
  - 绿色: >= 98%
  - 黄色: 95-98%
  - 红色: < 95%

---

**组件 5: 客户满意度评分**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  AVG(rating) AS value
FROM user_feedback
WHERE DATE(created_at) = CURRENT_DATE;
```

**显示配置:**
- 标题: "客户满意度"
- 单位: "星"
- 范围: 1-5
- 颜色阈值:
  - 绿色: >= 4.5
  - 黄色: 4.0-4.5
  - 红色: < 4.0

---

**组件 6: 今日营收**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COALESCE(SUM(amount), 0) AS value
FROM payments
WHERE DATE(created_at) = CURRENT_DATE
  AND status = 'success';
```

**显示配置:**
- 标题: "今日营收"
- 单位: "元"
- 趋势: 环比昨日
- 颜色阈值:
  - 绿色: >= 环比增长 10%
  - 黄色: 环比下降 10-20%
  - 红色: 环比下降 > 20%

---

#### 2.2.2 趋势图表

**组件 7: DAU 趋势 (7 天)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE(timestamp) AS time,
  COUNT(DISTINCT user_id) AS value
FROM user_events
WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '7 days'
  AND user_id IS NOT NULL
GROUP BY DATE(timestamp)
ORDER BY time;
```

**显示配置:**
- 标题: "DAU 趋势 (7 天)"
- Y 轴标签: "用户数"
- 线条颜色: #3274D9 (蓝色)
- 显示数值标记

---

**组件 8: 用户注册趋势 (30 天)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE(created_at) AS time,
  COUNT(*) AS value
FROM users
WHERE DATE(created_at) >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY time;
```

**显示配置:**
- 标题: "用户注册趋势 (30 天)"
- Y 轴标签: "注册数"
- 线条颜色: #26A69A (绿色)
- 显示数值标记

---

**组件 9: AI 对话成功率趋势 (24 小时)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE_TRUNC('hour', timestamp) AS time,
  COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) AS value
FROM ai_dialog_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY time;
```

**显示配置:**
- 标题: "AI 对话成功率趋势 (24 小时)"
- Y 轴标签: "成功率 (%)"
- 线条颜色: #AB47BC (紫色)
- Y 轴范围: 80-100

---

#### 2.2.3 对比图表

**组件 10: 用户留存率对比**

**可视化类型:** Bar Chart (柱状图)

**查询:**
```sql
SELECT
  cohort_date,
  retention_d1,
  retention_d7,
  retention_d30
FROM user_retention_metrics
WHERE cohort_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY cohort_date;
```

**显示配置:**
- 标题: "用户留存率对比 (近 30 天)"
- X 轴标签: "注册日期"
- Y 轴标签: "留存率 (%)"
- 颜色:
  - 次日留存: #EF5350 (红色)
  - 7 日留存: #FFA726 (橙色)
  - 30 日留存: #66BB6A (绿色)
- 显示图例

---

**组件 11: 功能使用率对比**

**可视化类型:** Bar Chart (柱状图)

**查询:**
```sql
SELECT
  feature_name,
  usage_rate
FROM feature_usage_metrics
WHERE date = CURRENT_DATE
ORDER BY usage_rate DESC;
```

**显示配置:**
- 标题: "功能使用率 (今日)"
- X 轴标签: "功能名称"
- Y 轴标签: "使用率 (%)"
- 颜色: #42A5F5 (蓝色)
- 水平方向

---

#### 2.2.4 饼图/环形图

**组件 12: 用户来源分布**

**可视化类型:** Pie Chart (饼图)

**查询:**
```sql
SELECT
  properties.source AS metric,
  COUNT(*) AS value
FROM user_events
WHERE event_name = 'auth_register_success'
  AND DATE(timestamp) = CURRENT_DATE - INTERVAL '30 days'
GROUP BY properties.source
ORDER BY value DESC;
```

**显示配置:**
- 标题: "用户来源分布 (近 30 天)"
- 显示百分比
- 颜色方案: Tableau 10

---

**组件 13: 订阅类型分布**

**可视化类型:** Pie Chart (饼图)

**查询:**
```sql
SELECT
  plan_type AS metric,
  COUNT(*) AS value
FROM subscriptions
WHERE status = 'active'
GROUP BY plan_type
ORDER BY value DESC;
```

**显示配置:**
- 标题: "订阅类型分布"
- 显示百分比
- 颜色方案: Tableau 10

---

#### 2.2.5 表格组件

**组件 14: Top 10 活跃用户**

**可视化类型:** Table (表格)

**查询:**
```sql
SELECT
  user_id,
  COUNT(DISTINCT DATE(timestamp)) AS active_days,
  COUNT(DISTINCT dialog_id) AS dialog_count,
  AVG(rating) AS avg_rating
FROM user_events e
LEFT JOIN ai_dialog_metrics d ON e.dialog_id = d.dialog_id
WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '7 days'
  AND e.user_id IS NOT NULL
GROUP BY user_id
ORDER BY dialog_count DESC
LIMIT 10;
```

**显示配置:**
- 标题: "Top 10 活跃用户 (近 7 天)"
- 列:
  - 用户 ID
  - 活跃天数
  - 对话次数
  - 平均评分
- 分页: 禁用

---

## 3. 用户行为分析看板

### 3.1 看板配置

**看板 ID:** `user-behavior-analysis`
**看板名称:** 用户行为分析
**刷新间隔:** 1 小时

### 3.2 看板组件

#### 3.2.1 用户漏斗分析

**组件 15: 用户转化漏斗**

**可视化类型:** Bar Chart (柱状图) - 水平

**查询:**
```sql
SELECT
  '页面浏览' AS stage,
  COUNT(DISTINCT session_id) AS value
FROM user_events
WHERE DATE(timestamp) = CURRENT_DATE - 1

UNION ALL

SELECT
  '注册页面',
  COUNT(DISTINCT session_id)
FROM user_events
WHERE event_name = 'auth_register_view'
  AND DATE(timestamp) = CURRENT_DATE - 1

UNION ALL

SELECT
  '注册成功',
  COUNT(DISTINCT user_id)
FROM users
WHERE DATE(created_at) = CURRENT_DATE - 1

UNION ALL

SELECT
  '首次对话',
  COUNT(DISTINCT user_id)
FROM user_events
WHERE event_name = 'dialog_start'
  AND user_id IN (SELECT user_id FROM users WHERE DATE(created_at) = CURRENT_DATE - 1)
  AND DATE(timestamp) BETWEEN CURRENT_DATE - 1 AND CURRENT_DATE + 6;
```

**显示配置:**
- 标题: "用户转化漏斗"
- X 轴标签: "转化阶段"
- Y 轴标签: "用户数"
- 颜色: 渐变色 (从蓝到绿)
- 显示转化率标签

---

#### 3.2.2 用户活跃度分析

**组件 16: 用户活跃时间段分布**

**可视化类型:** Heatmap (热力图)

**查询:**
```sql
SELECT
  EXTRACT(DOW FROM timestamp) AS day_of_week,
  EXTRACT(HOUR FROM timestamp) AS hour_of_day,
  COUNT(DISTINCT user_id) AS value
FROM user_events
WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '7 days'
  AND user_id IS NOT NULL
GROUP BY EXTRACT(DOW FROM timestamp), EXTRACT(HOUR FROM timestamp)
ORDER BY day_of_week, hour_of_day;
```

**显示配置:**
- 标题: "用户活跃时间段分布 (近 7 天)"
- X 轴标签: "小时 (0-23)"
- Y 轴标签: "星期 (0=周日, 6=周六)"
- 颜色方案: YlOrRd (黄橙红)

---

**组件 17: 用户使用时长分布**

**可视化类型:** Histogram (直方图)

**查询:**
```sql
SELECT
  CASE
    WHEN duration_seconds < 60 THEN '< 1 分钟'
    WHEN duration_seconds < 300 THEN '1-5 分钟'
    WHEN duration_seconds < 600 THEN '5-10 分钟'
    WHEN duration_seconds < 1800 THEN '10-30 分钟'
    WHEN duration_seconds < 3600 THEN '30-60 分钟'
    ELSE '> 60 分钟'
  END AS duration_range,
  COUNT(*) AS value
FROM (
  SELECT
    user_id,
    session_id,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) AS duration_seconds
  FROM user_events
  WHERE DATE(timestamp) = CURRENT_DATE - 1
    AND user_id IS NOT NULL
  GROUP BY user_id, session_id
) t
GROUP BY duration_range
ORDER BY MIN(duration_seconds);
```

**显示配置:**
- 标题: "用户使用时长分布 (昨日)"
- X 轴标签: "使用时长"
- Y 轴标签: "用户数"
- 颜色: #29B6F6 (浅蓝)

---

#### 3.2.3 用户留存分析

**组件 18: 留存率热力图**

**可视化类型:** Heatmap (热力图)

**查询:**
```sql
SELECT
  cohort_date,
  day_number,
  retention_rate
FROM user_retention_heatmap
WHERE cohort_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY cohort_date, day_number;
```

**显示配置:**
- 标题: "用户留存热力图 (近 90 天)"
- X 轴标签: "留存天数"
- Y 轴标签: "注册日期"
- 颜色方案: RdYlGn (红黄绿)
- 数值格式: 百分比

---

#### 3.2.4 用户分群分析

**组件 19: 用户分群概览**

**可视化类型:** Stat Group (统计卡片组)

**查询:**

```sql
-- 活跃用户
SELECT
  '活跃用户' AS label,
  COUNT(DISTINCT user_id) AS value
FROM user_events
WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '7 days'
  AND user_id IS NOT NULL

UNION ALL

-- 沉睡用户 (7-30 天未登录)
SELECT
  '沉睡用户',
  COUNT(DISTINCT user_id)
FROM users
WHERE last_active_at BETWEEN CURRENT_DATE - INTERVAL '30 days' AND CURRENT_DATE - INTERVAL '7 days'

UNION ALL

-- 流失用户 (>30 天未登录)
SELECT
  '流失用户',
  COUNT(DISTINCT user_id)
FROM users
WHERE last_active_at < CURRENT_DATE - INTERVAL '30 days';
```

**显示配置:**
- 标题: "用户分群概览"
- 布局: 水平排列

---

## 4. AI 质量监控看板

### 4.1 看板配置

**看板 ID:** `ai-quality-monitoring`
**看板名称:** AI 质量监控
**刷新间隔:** 1 分钟

### 4.2 看板组件

#### 4.2.1 核心质量指标

**组件 20: AI 对话成功率 (实时)**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) AS value
FROM ai_dialog_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour';
```

**显示配置:**
- 标题: "AI 对话成功率 (近 1 小时)"
- 单位: "%"
- 阈值指示器

---

**组件 21: AI 响应时间分布**

**可视化类型:** Gauge (仪表盘)

**查询:**
```sql
SELECT
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds) AS value
FROM ai_dialog_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 hour';
```

**显示配置:**
- 标题: "AI P95 响应时间"
- 单位: "秒"
- 最小值: 0
- 最大值: 10
- 颜色阈值:
  - 绿色: 0-2
  - 黄色: 2-3
  - 红色: > 3

---

**组件 22: 知识库覆盖率**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(CASE WHEN answer_source = 'knowledge_base' THEN 1 END) * 100.0 / COUNT(*) AS value
FROM ai_dialog_metrics
WHERE DATE(timestamp) = CURRENT_DATE;
```

**显示配置:**
- 标题: "知识库覆盖率 (今日)"
- 单位: "%"
- 趋势: 环比昨日

---

**组件 23: 问题解决率**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(CASE WHEN user_feedback = 'solved' THEN 1 END) * 100.0 / COUNT(*) AS value
FROM ai_dialog_metrics
WHERE DATE(timestamp) = CURRENT_DATE
  AND user_feedback IS NOT NULL;
```

**显示配置:**
- 标题: "问题解决率 (今日)"
- 单位: "%"

---

#### 4.2.2 AI 性能趋势

**组件 24: AI 响应时间趋势 (24 小时)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE_TRUNC('hour', timestamp) AS time,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_seconds) AS p50,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_seconds) AS p95,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_seconds) AS p99
FROM ai_dialog_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY time;
```

**显示配置:**
- 标题: "AI 响应时间趋势 (24 小时)"
- Y 轴标签: "响应时间 (秒)"
- 系列:
  - P50: 绿色 (#66BB6A)
  - P95: 橙色 (#FFA726)
  - P99: 红色 (#EF5350)
- 显示图例

---

**组件 25: AI 对话成功率趋势 (7 天)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE(timestamp) AS time,
  COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) AS value
FROM ai_dialog_metrics
WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY time;
```

**显示配置:**
- 标题: "AI 对话成功率趋势 (7 天)"
- Y 轴标签: "成功率 (%)"
- 线条颜色: #26A69A (绿色)
- Y 轴范围: 80-100

---

#### 4.2.3 AI 失败原因分析

**组件 26: AI 失败原因分布**

**可视化类型:** Pie Chart (饼图)

**查询:**
```sql
SELECT
  failure_reason AS metric,
  COUNT(*) AS value
FROM ai_dialog_metrics
WHERE status = 'failed'
  AND DATE(timestamp) = CURRENT_DATE
GROUP BY failure_reason
ORDER BY value DESC
LIMIT 10;
```

**显示配置:**
- 标题: "AI 失败原因分布 (今日)"
- 显示百分比
- 颜色方案: Tableau 10

---

#### 4.2.4 客户满意度分析

**组件 27: 评分分布**

**可视化类型:** Bar Chart (柱状图)

**查询:**
```sql
SELECT
  rating AS metric,
  COUNT(*) AS value
FROM user_feedback
WHERE DATE(created_at) = CURRENT_DATE
GROUP BY rating
ORDER BY rating DESC;
```

**显示配置:**
- 标题: "客户满意度评分分布 (今日)"
- X 轴标签: "评分 (星)"
- Y 轴标签: "数量"
- 颜色: 根据评分显示 (5星=绿, 1星=红)

---

**组件 28: 差评原因分析**

**可视化类型:** Table (表格)

**查询:**
```sql
SELECT
  rating,
  feedback_text,
  dialog_id,
  user_id,
  created_at
FROM user_feedback
WHERE DATE(created_at) = CURRENT_DATE
  AND rating <= 2
ORDER BY created_at DESC
LIMIT 20;
```

**显示配置:**
- 标题: "差评反馈 (今日)"
- 列:
  - 评分
  - 反馈内容
  - 对话 ID
  - 用户 ID
  - 时间
- 分页: 启用

---

## 5. 订阅分析看板

### 5.1 看板配置

**看板 ID:** `subscription-analysis`
**看板名称:** 订阅分析
**刷新间隔:** 1 小时

### 5.2 看板组件

#### 5.2.1 订阅概览

**组件 29: 活跃订阅数**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(*) AS value
FROM subscriptions
WHERE status = 'active';
```

**显示配置:**
- 标题: "活跃订阅数"
- 单位: "订阅"
- 趋势: 环比上月

---

**组件 30: 月度经常性收入 (MRR)**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  SUM(monthly_price) AS value
FROM subscriptions
WHERE status = 'active';
```

**显示配置:**
- 标题: "月度经常性收入 (MRR)"
- 单位: "元"
- 趋势: 环比上月

---

**组件 31: 续费率**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(CASE WHEN renewed = true THEN 1 END) * 100.0 / COUNT(*) AS value
FROM subscription_renewals
WHERE renewal_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND renewal_date < DATE_TRUNC('month', CURRENT_DATE);
```

**显示配置:**
- 标题: "上月续费率"
- 单位: "%"

---

**组件 32: 客户流失率 (Churn Rate)**

**可视化类型:** Stat (统计卡片)

**查询:**
```sql
SELECT
  COUNT(*) * 100.0 / (SELECT COUNT(*) FROM subscriptions WHERE DATE(created_at) < DATE_TRUNC('month', CURRENT_DATE)) AS value
FROM subscriptions
WHERE status = 'cancelled'
  AND DATE(cancelled_at) >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND DATE(cancelled_at) < DATE_TRUNC('month', CURRENT_DATE);
```

**显示配置:**
- 标题: "上月客户流失率"
- 单位: "%"

---

#### 5.2.2 订阅趋势

**组件 33: 新增订阅趋势 (30 天)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE(created_at) AS time,
  COUNT(*) AS value
FROM subscriptions
WHERE DATE(created_at) >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY time;
```

**显示配置:**
- 标题: "新增订阅趋势 (30 天)"
- Y 轴标签: "订阅数"
- 线条颜色: #42A5F5 (蓝色)

---

**组件 34: 取消订阅趋势 (30 天)**

**可视化类型:** Time Series (时间序列)

**查询:**
```sql
SELECT
  DATE(cancelled_at) AS time,
  COUNT(*) AS value
FROM subscriptions
WHERE DATE(cancelled_at) >= CURRENT_DATE - INTERVAL '30 days'
  AND status = 'cancelled'
GROUP BY DATE(cancelled_at)
ORDER BY time;
```

**显示配置:**
- 标题: "取消订阅趋势 (30 天)"
- Y 轴标签: "订阅数"
- 线条颜色: #EF5350 (红色)

---

#### 5.2.3 订阅类型分析

**组件 35: 订阅类型分布**

**可视化类型:** Pie Chart (饼图)

**查询:**
```sql
SELECT
  plan_type AS metric,
  COUNT(*) AS value
FROM subscriptions
WHERE status = 'active'
GROUP BY plan_type
ORDER BY value DESC;
```

**显示配置:**
- 标题: "活跃订阅类型分布"
- 显示百分比
- 颜色方案: Tableau 10

---

**组件 36: 各类型续费率对比**

**可视化类型:** Bar Chart (柱状图)

**查询:**
```sql
SELECT
  s.plan_type,
  COUNT(CASE WHEN r.renewed = true THEN 1 END) * 100.0 / COUNT(*) AS renewal_rate
FROM subscriptions s
INNER JOIN subscription_renewals r ON s.id = r.subscription_id
WHERE r.renewal_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')
GROUP BY s.plan_type
ORDER BY renewal_rate DESC;
```

**显示配置:**
- 标题: "各订阅类型续费率 (近 3 个月)"
- X 轴标签: "订阅类型"
- Y 轴标签: "续费率 (%)"
- 颜色: #26A69A (绿色)
- 显示数值标记

---

#### 5.2.4 取消原因分析

**组件 37: 取消原因分布**

**可视化类型:** Bar Chart (柱状图)

**查询:**
```sql
SELECT
  cancellation_reason AS metric,
  COUNT(*) AS value
FROM subscriptions
WHERE status = 'cancelled'
  AND DATE(cancelled_at) >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY cancellation_reason
ORDER BY value DESC
LIMIT 10;
```

**显示配置:**
- 标题: "取消原因分布 (近 30 天)"
- X 轴标签: "取消原因"
- Y 轴标签: "数量"
- 颜色: #EF5350 (红色)
- 水平方向

---

## 6. 看板权限配置

### 6.1 角色权限

| 角色 | 可访问看板 |
|------|-----------|
| 管理层 | 所有看板 |
| 产品团队 | 产品概览、用户行为分析、订阅分析 |
| 运营团队 | 用户行为分析、订阅分析 |
| AI 团队 | AI 质量监控 |
| 后端团队 | 产品概览、系统健康、API 性能 |
| 运维团队 | 系统健康、API 性能、数据库监控 |
| DBA | 数据库监控 |

### 6.2 访问方式

**Web 访问:**
- URL: `https://monitoring.claw.ai`
- 认证方式: SSO (单点登录)

**API 访问:**
```bash
# 获取看板数据
GET /api/v1/dashboards/{dashboard_id}?from={start_time}&to={end_time}
```

---

## 7. 看板最佳实践

### 7.1 设计原则

1. **简洁明了**
   - 每个看板聚焦一个主题
   - 避免信息过载
   - 使用清晰的标题和说明

2. **层次分明**
   - 关键指标突出显示
   - 使用颜色区分重要程度
   - 合理使用图表类型

3. **实时性**
   - 关键指标实时更新
   - 历史数据定时更新
   - 标注更新时间

### 7.2 颜色使用规范

| 颜色 | 含义 | 使用场景 |
|------|------|---------|
| 绿色 | 正常/增长/优秀 | 达标指标、正向增长 |
| 蓝色 | 中性 | 一般数据、趋势线 |
| 黄色 | 警告 | 接近阈值、轻微下降 |
| 橙色 | 注意 | 需要关注、中等下降 |
| 红色 | 严重/下降 | 未达标、严重问题 |

### 7.3 告警集成

在看板上集成告警指示器：

1. **指标卡告警**
   - 当指标超过阈值时显示告警图标
   - 点击图标跳转到告警详情

2. **图表告警**
   - 异常数据点用特殊颜色标记
   - 显示告警提示信息

3. **告警统计**
   - 在看板顶部显示当前告警数量
   - 按级别分组显示

---

## 8. 附录

### 8.1 看板导出

支持导出格式：
- PDF (包含完整看板)
- PNG (单个图表)
- CSV (表格数据)
- JSON (原始数据)

### 8.2 看板分享

- **公开链接**: 可生成临时访问链接（有效期可配置）
- **团队分享**: 支持按团队分享看板
- **嵌入**: 支持嵌入到其他系统

### 8.3 联系人

| 看板类别 | 负责人 | 邮箱 |
|---------|-------|------|
| 产品概览 | 产品负责人 | product@claw.ai |
| 用户行为分析 | 产品负责人 | product@claw.ai |
| AI 质量监控 | AI 负责人 | ai-team@claw.ai |
| 订阅分析 | 产品负责人 | product@claw.ai |
| 系统健康 | 运维负责人 | ops@claw.ai |
| API 性能 | 后端负责人 | backend@claw.ai |
| 数据库监控 | DBA | dba@claw.ai |

---

**文档结束**
