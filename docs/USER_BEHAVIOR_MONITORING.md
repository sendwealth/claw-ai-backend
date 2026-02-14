# CLAW.AI 用户行为监控配置

**文档版本:** v1.0
**创建日期:** 2026-02-14
**适用环境:** 生产环境

---

## 1. 概述

本文档定义了 CLAW.AI 产品的用户行为监控配置，包括埋点事件规范、数据采集规则、指标计算方法等。

### 1.1 监控目标

- **用户获取监控**：追踪用户注册来源和转化
- **用户活跃监控**：追踪用户使用频率和时长
- **用户留存监控**：追踪用户留存和流失
- **功能使用监控**：追踪各功能模块的使用情况
- **用户路径监控**：追踪用户在产品中的行为路径

### 1.2 技术架构

```
用户端 → 埋点 SDK → Kafka → Flink → ClickHouse
                                            ↓
                                     数据分析平台
```

---

## 2. 埋点事件定义

### 2.1 事件命名规范

格式：`{模块}_{动作}_{对象}`

**模块前缀：**
- `user` - 用户相关
- `auth` - 认证相关
- `dialog` - AI 对话相关
- `kb` - 知识库相关
- `dashboard` - 看板相关
- `setting` - 设置相关
- `billing` - 计费相关

**动作类型：**
- `view` - 查看
- `click` - 点击
- `submit` - 提交
- `start` - 开始
- `end` - 结束
- `success` - 成功
- `fail` - 失败
- `cancel` - 取消
- `delete` - 删除
- `edit` - 编辑
- `search` - 搜索
- `filter` - 筛选

---

## 3. 用户获取监控

### 3.1 用户注册事件

#### 3.1.1 注册页面浏览

**事件名称:** `auth_register_view`

**事件描述:** 用户访问注册页面

**触发时机:** 用户打开注册页面时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| source | string | 是 | 来源渠道（direct/referral/seo/social/email） |
| campaign | string | 否 | 营销活动 ID |
| referrer | string | 否 | 来源 URL |
| platform | string | 是 | 平台（web/mobile） |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

**事件示例:**
```json
{
  "event_id": "evt_20260214_001",
  "event_name": "auth_register_view",
  "user_id": "",
  "session_id": "sess_abc123",
  "timestamp": 1739496000000,
  "platform": "web",
  "device_id": "dev_xyz789",
  "properties": {
    "source": "referral",
    "campaign": "INV2024",
    "referrer": "https://example.com"
  }
}
```

---

#### 3.1.2 注册提交

**事件名称:** `auth_register_submit`

**事件描述:** 用户提交注册表单

**触发时机:** 用户点击注册按钮时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| source | string | 是 | 来源渠道 |
| campaign | string | 否 | 营销活动 ID |
| referrer | string | 否 | 来源 URL |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

#### 3.1.3 注册成功

**事件名称:** `auth_register_success`

**事件描述:** 用户注册成功

**触发时机:** 注册成功后

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| source | string | 是 | 来源渠道 |
| campaign | string | 否 | 营销活动 ID |
| referrer | string | 否 | 来源 URL |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |
| user_type | string | 是 | 用户类型（free/premium） |

---

#### 3.1.4 注册失败

**事件名称:** `auth_register_fail`

**事件描述:** 用户注册失败

**触发时机:** 注册失败后

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| source | string | 是 | 来源渠道 |
| error_code | string | 是 | 错误码 |
| error_message | string | 是 | 错误信息 |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

### 3.2 监控指标

#### 3.2.1 注册数

**计算方式:**

```sql
-- 日注册数
SELECT
  DATE(created_at) AS date,
  COUNT(*) AS daily_registrations
FROM users
WHERE DATE(created_at) = CURRENT_DATE - 1
GROUP BY DATE(created_at);

-- 周注册数
SELECT
  DATE_TRUNC('week', created_at) AS week,
  COUNT(*) AS weekly_registrations
FROM users
WHERE DATE_TRUNC('week', created_at) = DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 week')
GROUP BY DATE_TRUNC('week', created_at);

-- 月注册数
SELECT
  DATE_TRUNC('month', created_at) AS month,
  COUNT(*) AS monthly_registrations
FROM users
WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
GROUP BY DATE_TRUNC('month', created_at);
```

#### 3.2.2 注册来源分析

**计算方式:**

```sql
-- 注册来源分布
SELECT
  properties.source AS source,
  COUNT(*) AS count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS percentage
FROM user_events
WHERE event_name = 'auth_register_success'
  AND DATE(timestamp) = CURRENT_DATE - 1
GROUP BY properties.source
ORDER BY count DESC;
```

#### 3.2.3 注册转化率

**计算方式:**

```sql
-- 注册转化率（注册成功 / 注册页面浏览）
SELECT
  DATE(timestamp) AS date,
  SUM(CASE WHEN event_name = 'auth_register_success' THEN 1 ELSE 0 END) AS registrations,
  SUM(CASE WHEN event_name = 'auth_register_view' THEN 1 ELSE 0 END) AS views,
  SUM(CASE WHEN event_name = 'auth_register_success' THEN 1 ELSE 0 END) * 100.0 /
    SUM(CASE WHEN event_name = 'auth_register_view' THEN 1 ELSE 0 END) AS conversion_rate
FROM user_events
WHERE DATE(timestamp) = CURRENT_DATE - 1
  AND event_name IN ('auth_register_view', 'auth_register_success')
GROUP BY DATE(timestamp);
```

---

## 4. 用户活跃监控

### 4.1 登录事件

#### 4.1.1 登录成功

**事件名称:** `auth_login_success`

**事件描述:** 用户登录成功

**触发时机:** 用户登录成功后

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| login_method | string | 是 | 登录方式（password/email/sso） |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

#### 4.1.2 登出

**事件名称:** `auth_logout`

**事件描述:** 用户登出

**触发时机:** 用户点击登出按钮或会话过期时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| logout_type | string | 是 | 登出类型（manual/timeout） |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

### 4.2 活跃度指标

#### 4.2.1 DAU (日活跃用户)

**计算方式:**

```sql
-- DAU
SELECT
  DATE(timestamp) AS date,
  COUNT(DISTINCT user_id) AS dau
FROM user_events
WHERE DATE(timestamp) = CURRENT_DATE - 1
  AND user_id IS NOT NULL
GROUP BY DATE(timestamp);

-- DAU 按平台
SELECT
  DATE(timestamp) AS date,
  properties.platform AS platform,
  COUNT(DISTINCT user_id) AS dau
FROM user_events
WHERE DATE(timestamp) = CURRENT_DATE - 1
  AND user_id IS NOT NULL
GROUP BY DATE(timestamp), properties.platform;
```

#### 4.2.2 MAU (月活跃用户)

**计算方式:**

```sql
-- MAU
SELECT
  DATE_TRUNC('month', timestamp) AS month,
  COUNT(DISTINCT user_id) AS mau
FROM user_events
WHERE DATE_TRUNC('month', timestamp) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND user_id IS NOT NULL
GROUP BY DATE_TRUNC('month', timestamp);
```

#### 4.2.3 DAU/MAU 比率

**计算方式:**

```sql
-- DAU/MAU
WITH daily AS (
  SELECT
    DATE(timestamp) AS date,
    COUNT(DISTINCT user_id) AS dau
  FROM user_events
  WHERE DATE(timestamp) = CURRENT_DATE - 1
    AND user_id IS NOT NULL
  GROUP BY DATE(timestamp)
),
monthly AS (
  SELECT
    COUNT(DISTINCT user_id) AS mau
  FROM user_events
  WHERE DATE(timestamp) >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
    AND user_id IS NOT NULL
)
SELECT
  d.date,
  d.dau,
  m.mau,
  d.dau * 100.0 / m.mau AS dau_mau_ratio
FROM daily d
CROSS JOIN monthly m;
```

#### 4.2.4 用户在线时长

**计算方式:**

```sql
-- 平均在线时长
SELECT
  DATE(timestamp) AS date,
  AVG(duration_seconds) AS avg_session_duration
FROM (
  SELECT
    user_id,
    session_id,
    MIN(timestamp) AS session_start,
    MAX(timestamp) AS session_end,
    EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp))) AS duration_seconds
  FROM user_events
  WHERE DATE(timestamp) = CURRENT_DATE - 1
    AND user_id IS NOT NULL
  GROUP BY user_id, session_id
) t
GROUP BY DATE(timestamp);
```

---

## 5. 用户留存监控

### 5.1 留存率计算

#### 5.1.1 次日留存率

**计算方式:**

```sql
-- 次日留存率
WITH cohort_users AS (
  SELECT user_id, DATE(created_at) AS cohort_date
  FROM users
  WHERE DATE(created_at) = CURRENT_DATE - 2
),
retained_users AS (
  SELECT DISTINCT e.user_id
  FROM user_events e
  INNER JOIN cohort_users c ON e.user_id = c.user_id
  WHERE DATE(e.timestamp) = c.cohort_date + INTERVAL '1 day'
),
retention_rates AS (
  SELECT
    cohort_date,
    (SELECT COUNT(*) FROM retained_users) AS retained_count,
    (SELECT COUNT(*) FROM cohort_users) AS cohort_size
  FROM cohort_users
  LIMIT 1
)
SELECT
  cohort_date,
  cohort_size,
  retained_count,
  retained_count * 100.0 / cohort_size AS retention_d1_rate
FROM retention_rates;
```

#### 5.1.2 7 日留存率

**计算方式:**

```sql
-- 7 日留存率
WITH cohort_users AS (
  SELECT user_id, DATE(created_at) AS cohort_date
  FROM users
  WHERE DATE(created_at) = CURRENT_DATE - 8
),
retained_users AS (
  SELECT DISTINCT e.user_id
  FROM user_events e
  INNER JOIN cohort_users c ON e.user_id = c.user_id
  WHERE DATE(e.timestamp) >= c.cohort_date + INTERVAL '7 days'
    AND DATE(e.timestamp) < c.cohort_date + INTERVAL '8 days'
),
retention_rates AS (
  SELECT
    cohort_date,
    (SELECT COUNT(*) FROM retained_users) AS retained_count,
    (SELECT COUNT(*) FROM cohort_users) AS cohort_size
  FROM cohort_users
  LIMIT 1
)
SELECT
  cohort_date,
  cohort_size,
  retained_count,
  retained_count * 100.0 / cohort_size AS retention_d7_rate
FROM retention_rates;
```

#### 5.1.3 30 日留存率

**计算方式:**

```sql
-- 30 日留存率
WITH cohort_users AS (
  SELECT user_id, DATE(created_at) AS cohort_date
  FROM users
  WHERE DATE(created_at) = CURRENT_DATE - 31
),
retained_users AS (
  SELECT DISTINCT e.user_id
  FROM user_events e
  INNER JOIN cohort_users c ON e.user_id = c.user_id
  WHERE DATE(e.timestamp) >= c.cohort_date + INTERVAL '30 days'
    AND DATE(e.timestamp) < c.cohort_date + INTERVAL '31 days'
),
retention_rates AS (
  SELECT
    cohort_date,
    (SELECT COUNT(*) FROM retained_users) AS retained_count,
    (SELECT COUNT(*) FROM cohort_users) AS cohort_size
  FROM cohort_users
  LIMIT 1
)
SELECT
  cohort_date,
  cohort_size,
  retained_count,
  retained_count * 100.0 / cohort_size AS retention_d30_rate
FROM retention_rates;
```

---

## 6. 功能使用监控

### 6.1 AI 对话功能

#### 6.1.1 对话开始

**事件名称:** `dialog_start`

**事件描述:** 用户开始 AI 对话

**触发时机:** 用户发送第一条消息时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| dialog_id | string | 是 | 对话 ID |
| message | string | 是 | 用户消息内容 |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

#### 6.1.2 对话结束

**事件名称:** `dialog_end`

**事件描述:** AI 对话结束

**触发时机:** 对话会话结束时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| dialog_id | string | 是 | 对话 ID |
| message_count | int | 是 | 消息总数 |
| duration_seconds | int | 是 | 对话时长（秒） |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

#### 6.1.3 功能使用统计

**计算方式:**

```sql
-- 对话数统计
SELECT
  DATE(timestamp) AS date,
  COUNT(DISTINCT dialog_id) AS daily_dialogs,
  COUNT(DISTINCT user_id) AS active_users,
  COUNT(DISTINCT dialog_id) * 1.0 / COUNT(DISTINCT user_id) AS dialogs_per_user
FROM user_events
WHERE event_name = 'dialog_start'
  AND DATE(timestamp) = CURRENT_DATE - 1
GROUP BY DATE(timestamp);

-- 对话时长分布
SELECT
  date,
  AVG(properties.duration_seconds) AS avg_duration,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY properties.duration_seconds) AS p50_duration,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY properties.duration_seconds) AS p95_duration,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY properties.duration_seconds) AS p99_duration
FROM user_events
WHERE event_name = 'dialog_end'
  AND DATE(timestamp) = CURRENT_DATE - 1
GROUP BY date;
```

---

### 6.2 知识库功能

#### 6.2.1 知识库浏览

**事件名称:** `kb_view`

**事件描述:** 用户浏览知识库

**触发时机:** 用户打开知识库页面时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| kb_id | string | 是 | 知识库 ID |
| category | string | 是 | 知识库分类 |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

#### 6.2.2 知识库搜索

**事件名称:** `kb_search`

**事件描述:** 用户搜索知识库

**触发时机:** 用户执行搜索时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| search_query | string | 是 | 搜索关键词 |
| result_count | int | 是 | 结果数量 |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

### 6.3 看板功能

#### 6.3.1 看板浏览

**事件名称:** `dashboard_view`

**事件描述:** 用户浏览看板

**触发时机:** 用户打开看板页面时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| dashboard_id | string | 是 | 看板 ID |
| dashboard_name | string | 是 | 看板名称 |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

#### 6.3.2 看板交互

**事件名称:** `dashboard_interact`

**事件描述:** 用户在看板上执行交互操作

**触发时机:** 用户点击、筛选、导出等操作时

**事件属性:**

| 属性名 | 类型 | 是否必填 | 说明 |
|--------|------|---------|------|
| dashboard_id | string | 是 | 看板 ID |
| action_type | string | 是 | 操作类型（click/filter/export/share） |
| widget_id | string | 否 | 组件 ID |
| platform | string | 是 | 平台 |
| device_id | string | 是 | 设备 ID |
| session_id | string | 是 | 会话 ID |

---

### 6.4 功能使用率统计

**计算方式:**

```sql
-- 功能使用率
SELECT
  DATE(timestamp) AS date,
  'ai_dialog' AS feature_name,
  COUNT(DISTINCT user_id) AS feature_users,
  (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE DATE(timestamp) = DATE(e.timestamp)) AS total_users,
  COUNT(DISTINCT user_id) * 100.0 / (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE DATE(timestamp) = DATE(e.timestamp)) AS usage_rate
FROM user_events e
WHERE event_name = 'dialog_start'
  AND DATE(timestamp) = CURRENT_DATE - 1
GROUP BY DATE(timestamp)

UNION ALL

SELECT
  DATE(timestamp) AS date,
  'knowledge_base' AS feature_name,
  COUNT(DISTINCT user_id) AS feature_users,
  (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE DATE(timestamp) = DATE(e.timestamp)) AS total_users,
  COUNT(DISTINCT user_id) * 100.0 / (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE DATE(timestamp) = DATE(e.timestamp)) AS usage_rate
FROM user_events e
WHERE event_name = 'kb_view'
  AND DATE(timestamp) = CURRENT_DATE - 1
GROUP BY DATE(timestamp)

UNION ALL

SELECT
  DATE(timestamp) AS date,
  'dashboard' AS feature_name,
  COUNT(DISTINCT user_id) AS feature_users,
  (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE DATE(timestamp) = DATE(e.timestamp)) AS total_users,
  COUNT(DISTINCT user_id) * 100.0 / (SELECT COUNT(DISTINCT user_id) FROM user_events WHERE DATE(timestamp) = DATE(e.timestamp)) AS usage_rate
FROM user_events e
WHERE event_name = 'dashboard_view'
  AND DATE(timestamp) = CURRENT_DATE - 1
GROUP BY DATE(timestamp);
```

---

## 7. 用户路径分析

### 7.1 用户会话定义

**会话规则：**
- 同一用户在同一设备上，连续操作间隔不超过 30 分钟
- 超过 30 分钟无操作，会话自动结束

### 7.2 关键路径转化率

#### 7.2.1 注册 → 首次对话转化率

**计算方式:**

```sql
-- 注册后 7 天内首次对话转化率
WITH registered_users AS (
  SELECT user_id, created_at
  FROM users
  WHERE DATE(created_at) BETWEEN CURRENT_DATE - 8 AND CURRENT_DATE - 2
),
first_dialog_users AS (
  SELECT
    r.user_id,
    MIN(e.timestamp) AS first_dialog_time
  FROM registered_users r
  INNER JOIN user_events e ON r.user_id = e.user_id
  WHERE e.event_name = 'dialog_start'
    AND e.timestamp BETWEEN r.created_at AND r.created_at + INTERVAL '7 days'
  GROUP BY r.user_id
)
SELECT
  DATE(r.created_at) AS registration_date,
  COUNT(*) AS registered_count,
  COUNT(f.user_id) AS first_dialog_count,
  COUNT(f.user_id) * 100.0 / COUNT(*) AS conversion_rate
FROM registered_users r
LEFT JOIN first_dialog_users f ON r.user_id = f.user_id
GROUP BY DATE(r.created_at)
ORDER BY registration_date DESC;
```

#### 7.2.2 免费用户 → 付费用户转化率

**计算方式:**

```sql
-- 免费 → 付费转化率
WITH free_users AS (
  SELECT user_id, created_at
  FROM users
  WHERE subscription_type = 'free'
    AND DATE(created_at) BETWEEN CURRENT_DATE - 31 AND CURRENT_DATE - 1
),
paid_users AS (
  SELECT
    f.user_id,
    MIN(s.created_at) AS first_payment_time
  FROM free_users f
  INNER JOIN subscriptions s ON f.user_id = s.user_id
  WHERE s.plan_type IN ('premium', 'enterprise')
    AND s.created_at BETWEEN f.created_at AND f.created_at + INTERVAL '30 days'
  GROUP BY f.user_id
)
SELECT
  DATE(f.created_at) AS registration_date,
  COUNT(*) AS free_user_count,
  COUNT(p.user_id) AS paid_user_count,
  COUNT(p.user_id) * 100.0 / COUNT(*) AS conversion_rate
FROM free_users f
LEFT JOIN paid_users p ON f.user_id = p.user_id
GROUP BY DATE(f.created_at)
ORDER BY registration_date DESC;
```

### 7.3 用户流失路径分析

**计算方式:**

```sql
-- 用户流失前的最后操作路径
WITH churned_users AS (
  SELECT DISTINCT user_id
  FROM users
  WHERE subscription_status = 'cancelled'
    AND last_active_at < CURRENT_DATE - INTERVAL '30 days'
),
user_events_ordered AS (
  SELECT
    user_id,
    event_name,
    timestamp,
    LAG(event_name) OVER (PARTITION BY user_id ORDER BY timestamp) AS prev_event,
    LEAD(event_name) OVER (PARTITION BY user_id ORDER BY timestamp) AS next_event,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY timestamp DESC) AS rn
  FROM user_events
  WHERE user_id IN (SELECT user_id FROM churned_users)
    AND timestamp >= CURRENT_DATE - INTERVAL '60 days'
),
last_events AS (
  SELECT user_id, event_name, prev_event
  FROM user_events_ordered
  WHERE rn = 1
)
SELECT
  prev_event,
  event_name,
  COUNT(*) AS churn_count,
  COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS percentage
FROM last_events
GROUP BY prev_event, event_name
ORDER BY churn_count DESC
LIMIT 20;
```

---

## 8. 数据采集配置

### 8.1 数据采集频率

| 数据类型 | 采集频率 | 聚合粒度 |
|---------|---------|---------|
| 用户行为事件 | 实时 | 原始事件保留 30 天 |
| DAU/MAU | 实时 | 按天聚合 |
| 留存率 | 每日计算 | 按天聚合 |
| 功能使用率 | 实时 | 按天聚合 |

### 8.2 数据保留策略

| 数据类型 | 保留时长 |
|---------|---------|
| 原始事件数据 | 30 天 |
| 日聚合数据 | 1 年 |
| 月聚合数据 | 永久保留 |

### 8.3 数据质量控制

**数据校验规则：**

1. **必填字段校验**
   - 所有事件的必填字段不能为空

2. **数据类型校验**
   - 时间戳必须是有效时间戳
   - 用户 ID 必须符合 UUID 格式

3. **数据完整性校验**
   - 事件序列不能乱序（允许 5 分钟误差）

4. **数据去重**
   - 相同 event_id 的事件去重保留最新

---

## 9. 告警配置

### 9.1 用户行为告警

#### 9.1.1 DAU 下降告警

**告警名称:** `user_behavior_dau_drop`

**告警级别:** P2

**触发条件:**
```
DAU 环比下降 > 20%
```

**检测 SQL:**
```sql
WITH yesterday_dau AS (
  SELECT COUNT(DISTINCT user_id) AS dau
  FROM user_events
  WHERE DATE(timestamp) = CURRENT_DATE - 1
    AND user_id IS NOT NULL
),
two_days_ago_dau AS (
  SELECT COUNT(DISTINCT user_id) AS dau
  FROM user_events
  WHERE DATE(timestamp) = CURRENT_DATE - 2
    AND user_id IS NOT NULL
)
SELECT
  y.dau AS today_dau,
  t.dau AS yesterday_dau,
  (y.dau - t.dau) * 100.0 / t.dau AS drop_rate
FROM yesterday_dau y
CROSS JOIN two_days_ago_dau t
HAVING (y.dau - t.dau) * 100.0 / t.dau < -20;
```

---

#### 9.1.2 留存率下降告警

**告警名称:** `user_behavior_retention_drop`

**告警级别:** P3

**触发条件:**
```
次日留存率 < 20% 或 环比下降 > 30%
```

---

#### 9.1.3 功能使用率下降告警

**告警名称:** `user_behavior_feature_usage_drop`

**告警级别:** P3

**触发条件:**
```
核心功能使用率环比下降 > 15%
```

---

## 10. 附录

### 10.1 埋点 SDK 集成指南

**Web 端集成:**

```javascript
// 初始化埋点 SDK
const tracker = new ClawTracker({
  appId: 'claw-ai-web',
  apiEndpoint: 'https://api.claw.ai/events',
  autoTrack: true,
  userId: 'user_123',
  sessionId: 'sess_456'
});

// 埋点示例
tracker.track('auth_register_success', {
  source: 'referral',
  campaign: 'INV2024',
  platform: 'web'
});
```

**移动端集成:**

```swift
// iOS Swift 示例
import ClawTrackerSDK

ClawTracker.initialize(appId: "claw-ai-mobile")
ClawTracker.setUserId("user_123")
ClawTracker.track("auth_register_success", properties: [
  "source": "referral",
  "campaign": "INV2024",
  "platform": "ios"
])
```

---

### 10.2 数据分析看板

| 看板名称 | URL | 负责人 |
|---------|-----|-------|
| 用户获取看板 | /dashboard/user-acquisition | 产品团队 |
| 用户活跃看板 | /dashboard/user-engagement | 产品团队 |
| 用户留存看板 | /dashboard/user-retention | 产品团队 |
| 功能使用看板 | /dashboard/feature-usage | 产品团队 |

---

**文档结束**
