# CLAW.AI 数据库优化 - 快速参考指南

## 🚀 快速开始

### 1. 执行数据库迁移

```bash
cd /home/wuying/clawd/claw-ai-backend

# 查看待执行的迁移
alembic current
alembic history

# 执行迁移
alembic upgrade head

# 回滚迁移（如需要）
alembic downgrade -1
```

### 2. 运行性能测试

```bash
# 运行所有性能测试
pytest tests/test_db_performance.py -v -s

# 运行特定测试
pytest tests/test_db_performance.py::TestDBPerformance::test_index_performance_conversations -v -s
```

### 3. 监控数据库

```bash
# 查看连接池状态
python scripts/monitor_db.py --pool

# 查看索引使用情况
python scripts/monitor_db.py --index-usage

# 生成完整报告
python scripts/monitor_db.py --report
```

---

## 📊 索引概览

### 已创建的索引

| 表名 | 索引类型 | 列 | 用途 |
|------|----------|-----|------|
| conversations | 单列 | created_at | 时间排序 |
| conversations | 组合 | (user_id, created_at) | 用户对话列表 |
| messages | 单列 | created_at | 时间排序 |
| messages | 组合 | (conversation_id, created_at) | 消息历史 |
| documents | 单列 | created_at | 时间排序 |
| documents | 组合 | (knowledge_base_id, created_at) | 文档列表 |

### 验证索引

```sql
-- 查看所有索引
SELECT * FROM pg_indexes WHERE schemaname = 'public';

-- 查看索引大小
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## 🔧 代码示例

### 使用连接池监控

```python
from app.db.database import get_db_pool_status

# 获取连接池状态
status = get_db_pool_status()

print(f"连接池状态: {status['status']}")
print(f"已借出连接: {status['checked_out']}")
print(f"利用率: {status['checked_out'] / (status['pool_size'] + status['max_overflow']) * 100:.1f}%")
```

### 优化查询示例

```python
from app.db.database import get_db
from app.models import Conversation

# ✅ 推荐：使用索引字段 + 排序
with get_db() as db:
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.created_at.desc()).limit(20).all()

# ✅ 推荐：只查询需要的列
with get_db() as db:
    conversations = db.query(
        Conversation.id,
        Conversation.title,
        Conversation.created_at
    ).filter(Conversation.user_id == user_id).all()

# ❌ 不推荐：使用 SELECT *
conversations = db.query(Conversation).filter(
    Conversation.user_id == user_id
).all()
```

---

## 📈 性能基准

| 查询类型 | 目标时间 | 说明 |
|----------|----------|------|
| 简单查询 | < 50ms | 主键/外键查询 |
| 排序查询 | < 100ms | 带排序的查询 |
| 分页查询 | < 100ms | offset/limit |
| 复杂连接 | < 200ms | 多表 JOIN |

---

## 🔍 故障排查

### 慢查询问题

```sql
-- 查看慢查询
SELECT query, calls, mean_time, max_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;

-- 分析查询计划
EXPLAIN ANALYZE
SELECT * FROM conversations
WHERE user_id = 1
ORDER BY created_at DESC;
```

### 连接池问题

```bash
# 查看连接池状态
python scripts/monitor_db.py --pool

# 如果连接池利用率过高（>80%）：
# 1. 增加 pool_size
# 2. 检查是否有连接泄漏
# 3. 优化查询减少查询时间
```

### 索引问题

```bash
# 查看未使用的索引
python scripts/monitor_db.py --index-usage

# 如果发现未使用的索引：
# 1. 确认索引是否仍需要
# 2. 如不需要，可以删除以减少写入开销
```

---

## 📚 文档链接

- 完整优化文档：[DATABASE_OPTIMIZATION.md](./DATABASE_OPTIMIZATION.md)
- 优化总结：[DATABASE_OPTIMIZATION_SUMMARY.md](./DATABASE_OPTIMIZATION_SUMMARY.md)
- 迁移脚本：`alembic/versions/20250214_add_indexes.py`
- 性能测试：`tests/test_db_performance.py`
- 监控脚本：`scripts/monitor_db.py`

---

## ⚡ 快速命令

```bash
# 执行迁移
alembic upgrade head

# 运行测试
pytest tests/test_db_performance.py -v

# 查看报告
python scripts/monitor_db.py --report

# 重启应用（应用新配置）
# systemctl restart claw-ai-backend  # 或使用你的部署方式
```

---

**版本：** 1.0
**最后更新：** 2025-02-14
