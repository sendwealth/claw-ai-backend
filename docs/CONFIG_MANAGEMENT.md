# 配置管理文档

## 概述

CLAW.AI 项目现已支持配置持久化，所有配置项都可以通过数据库进行管理，支持完整的 CRUD 操作、历史记录、回滚和审计日志。

## 架构设计

### 数据库表结构

#### 1. configs 表
存储所有配置项的主表。

**字段说明：**
- `id`: 主键
- `key`: 配置键（唯一索引）
- `value`: 配置值（TEXT 类型，支持长文本）
- `description`: 配置描述
- `is_sensitive`: 是否敏感信息（布尔值）
- `is_public`: 是否公开访问（布尔值）
- `version`: 版本号（每次更新自增）
- `updated_by`: 更新者用户 ID（外键关联 users 表）
- `created_at`: 创建时间（继承自 Base）
- `updated_at`: 更新时间（继承自 Base）

**索引：**
- `ix_configs_key`: 唯一索引，用于快速查找配置
- `idx_config_key_public`: 组合索引，优化公开配置查询

#### 2. config_history 表
记录所有配置变更历史，支持审计和回滚。

**字段说明：**
- `id`: 主键
- `config_id`: 关联配置 ID（外键关联 configs 表）
- `key`: 配置键（冗余字段，便于查询）
- `old_value`: 变更前的值
- `new_value`: 变更后的值
- `changed_by`: 变更者用户 ID（外键关联 users 表）
- `changed_at`: 变更时间
- `version`: 版本号
- `created_at`: 创建时间（继承自 Base）
- `updated_at`: 更新时间（继承自 Base）

**索引：**
- `idx_config_history_config_id`: 配置 ID 索引
- `idx_config_history_key`: 配置键索引
- `idx_config_history_changed_at`: 变更时间索引

### 服务层设计

`ConfigService` 提供以下功能：

1. **基础 CRUD 操作**
   - `get_all()`: 获取所有配置
   - `get_by_key()`: 根据键获取配置
   - `create()`: 创建新配置
   - `update()`: 更新配置
   - `delete()`: 删除配置

2. **历史记录管理**
   - `get_history()`: 获取配置变更历史
   - `rollback()`: 回滚配置到指定历史版本

3. **批量操作**
   - `export_configs()`: 导出所有配置
   - `import_configs()`: 导入配置

4. **审计日志**
   - `get_audit_log()`: 获取配置变更审计日志

### 敏感信息保护

系统自动对敏感配置进行脱敏处理：

- 敏感配置在列表视图和公开接口中显示为 `******`
- 历史记录中的敏感值也会自动脱敏
- 管理员可通过 `include_sensitive=true` 参数查看明文

脱敏规则：
- 长度 ≤ 4: 显示为 `******`
- 长度 > 4: 显示 `前2位` + `* (n-4)` + `后2位`

## API 接口说明

### 基础路径
`/api/v1/configs`

### 认证要求
- 大部分接口需要管理员权限
- `GET /public` 端点无需认证，返回公开配置

### 端点列表

#### 1. 获取所有配置
```http
GET /api/v1/configs/
```

**查询参数：**
- `include_sensitive`: 是否包含敏感信息（默认 false）

**权限：** 管理员

**响应：**
```json
[
  {
    "id": 1,
    "key": "DATABASE_URL",
    "value": "postgresql://...",
    "description": "数据库连接字符串",
    "is_sensitive": true,
    "is_public": false,
    "version": 3,
    "created_at": "2025-02-15T10:00:00",
    "updated_at": "2025-02-15T11:30:00"
  }
]
```

#### 2. 获取公开配置
```http
GET /api/v1/configs/public
```

**权限：** 无需认证

**响应：** 同上，仅返回 `is_public=true` 的配置

#### 3. 获取单个配置
```http
GET /api/v1/configs/{key}
```

**路径参数：**
- `key`: 配置键

**查询参数：**
- `include_sensitive`: 是否显示敏感信息（默认 false）

**权限：** 管理员

#### 4. 创建配置
```http
POST /api/v1/configs/
```

**请求体：**
```json
{
  "key": "NEW_CONFIG",
  "value": "config_value",
  "description": "新配置描述",
  "is_sensitive": false,
  "is_public": true
}
```

**权限：** 管理员

**响应：** 创建的配置对象（HTTP 201）

#### 5. 更新配置
```http
PUT /api/v1/configs/{key}
```

**路径参数：**
- `key`: 配置键

**请求体：**
```json
{
  "value": "new_value"
}
```

**权限：** 管理员

**说明：**
- 更新会自动增加版本号
- 自动记录到历史表
- 自动更新 `updated_at` 和 `updated_by` 字段

#### 6. 删除配置
```http
DELETE /api/v1/configs/{key}
```

**权限：** 管理员

**响应：** HTTP 204 No Content

#### 7. 获取配置历史
```http
GET /api/v1/configs/{key}/history
```

**路径参数：**
- `key`: 配置键

**查询参数：**
- `limit`: 返回记录数限制（默认 100，最大 1000）
- `include_sensitive`: 是否包含敏感信息明文（默认 false）

**权限：** 管理员

**响应：**
```json
[
  {
    "id": 123,
    "config_id": 1,
    "key": "DATABASE_URL",
    "old_value": "postgresql://old_value",
    "new_value": "postgresql://new_value",
    "changed_at": "2025-02-15T11:30:00",
    "version": 3
  }
]
```

#### 8. 回滚配置
```http
POST /api/v1/configs/{key}/rollback
```

**路径参数：**
- `key`: 配置键

**请求体：**
```json
{
  "history_id": 123
}
```

**权限：** 管理员

**说明：**
- 将配置回滚到指定历史记录的值
- 会创建新的历史记录记录回滚操作
- 版本号自动递增

#### 9. 获取审计日志
```http
GET /api/v1/configs/audit/log
```

**查询参数：**
- `key`: 配置键过滤（可选）
- `start_time`: 开始时间（可选，ISO 8601 格式）
- `end_time`: 结束时间（可选，ISO 8601 格式）
- `limit`: 返回记录数限制（默认 100，最大 1000）

**权限：** 管理员

#### 10. 重新加载配置
```http
POST /api/v1/configs/reload
```

**权限：** 管理员

**响应：**
```json
{
  "success": true,
  "message": "配置已重新加载（共 15 个配置项）",
  "timestamp": "2025-02-15T12:00:00"
}
```

#### 11. 导出配置
```http
POST /api/v1/configs/export
```

**查询参数：**
- `include_sensitive`: 是否包含敏感信息（默认 false）

**权限：** 管理员

**响应：**
```json
{
  "exported_at": "2025-02-15T12:00:00",
  "total": 15,
  "configs": [...]
}
```

#### 12. 导入配置
```http
POST /api/v1/configs/import
```

**请求体：**
```json
[
  {
    "key": "CONFIG_1",
    "value": "value1",
    "description": "描述",
    "is_sensitive": false,
    "is_public": true
  }
]
```

**查询参数：**
- `overwrite`: 是否覆盖已存在的配置（默认 false）

**权限：** 管理员

**响应：**
```json
{
  "imported_at": "2025-02-15T12:00:00",
  "created": 5,
  "updated": 3,
  "skipped": 2,
  "errors": []
}
```

## 使用示例

### Python 客户端示例

```python
import requests
from datetime import datetime

# 配置 API 基础 URL
BASE_URL = "http://localhost:8000/api/v1/configs"
TOKEN = "your_admin_token"  # 从登录接口获取

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. 创建新配置
new_config = {
    "key": "API_TIMEOUT",
    "value": "30",
    "description": "API 超时时间（秒）",
    "is_sensitive": False,
    "is_public": True
}
response = requests.post(f"{BASE_URL}/", json=new_config, headers=headers)
print(f"创建配置: {response.json()}")

# 2. 更新配置
update_data = {"value": "60"}
response = requests.put(f"{BASE_URL}/API_TIMEOUT", json=update_data, headers=headers)
print(f"更新配置: {response.json()}")

# 3. 查看历史
response = requests.get(f"{BASE_URL}/API_TIMEOUT/history", headers=headers)
history = response.json()
print(f"历史记录: {history}")

# 4. 回滚到上一个版本
if len(history) > 1:
    rollback_data = {"history_id": history[1]["id"]}
    response = requests.post(f"{BASE_URL}/API_TIMEOUT/rollback", json=rollback_data, headers=headers)
    print(f"回滚结果: {response.json()}")

# 5. 导出配置
response = requests.post(f"{BASE_URL}/export", headers=headers)
export_data = response.json()
print(f"导出 {export_data['total']} 个配置")

# 6. 导入配置
configs_to_import = [
    {
        "key": "NEW_CONFIG_1",
        "value": "value1",
        "description": "新配置 1",
        "is_sensitive": False,
        "is_public": True
    }
]
response = requests.post(f"{BASE_URL}/import", json=configs_to_import, headers=headers)
print(f"导入结果: {response.json()}")
```

### cURL 示例

```bash
# 获取所有配置
curl -X GET "http://localhost:8000/api/v1/configs/" \
  -H "Authorization: Bearer $TOKEN"

# 创建配置
curl -X POST "http://localhost:8000/api/v1/configs/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "MAX_UPLOAD_SIZE",
    "value": "10485760",
    "description": "最大上传大小（字节）",
    "is_sensitive": false,
    "is_public": true
  }'

# 更新配置
curl -X PUT "http://localhost:8000/api/v1/configs/MAX_UPLOAD_SIZE" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "20971520"}'

# 查看历史
curl -X GET "http://localhost:8000/api/v1/configs/MAX_UPLOAD_SIZE/history" \
  -H "Authorization: Bearer $TOKEN"

# 回滚
curl -X POST "http://localhost:8000/api/v1/configs/MAX_UPLOAD_SIZE/rollback" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"history_id": 123}'
```

## 数据库迁移

### 执行迁移

```bash
# 进入项目目录
cd /home/wuying/clawd/claw-ai-backend

# 执行迁移
python -m alembic upgrade head
```

### 回滚迁移

```bash
# 回滚到上一个版本
python -m alembic downgrade -1

# 回滚到指定版本
python -m alembic downgrade add_indexes
```

### 查看迁移状态

```bash
# 查看当前版本
python -m alembic current

# 查看迁移历史
python -m alembic history
```

## 安全建议

1. **敏感配置保护**
   - 标记所有敏感配置为 `is_sensitive=true`
   - 避免在日志中打印敏感配置
   - 定期轮换敏感凭证（API Key、密钥等）

2. **访问控制**
   - 严格限制配置管理 API 的访问权限
   - 记录所有配置变更操作
   - 定期审计配置变更日志

3. **备份策略**
   - 定期导出配置进行备份
   - 在重大变更前创建配置快照
   - 保留至少 30 天的历史记录

4. **环境隔离**
   - 不同环境使用不同的数据库
   - 生产环境配置需要双重确认
   - 定期同步开发/测试/生产配置

## 最佳实践

1. **命名规范**
   - 配置键使用大写字母和下划线（UPPER_CASE）
   - 配置键要清晰表达用途（如 `DATABASE_URL`、`API_TIMEOUT`）
   - 避免使用保留字和特殊字符

2. **文档化**
   - 为每个配置提供清晰的描述
   - 标记配置的敏感性和公开性
   - 记录配置的默认值和取值范围

3. **版本管理**
   - 重要配置变更前先导出备份
   - 使用历史记录功能追踪变更
   - 回滚时确认历史记录的有效性

4. **监控告警**
   - 监控配置变更频率
   - 对敏感配置变更发送告警
   - 定期检查配置一致性

## 故障排查

### 常见问题

1. **配置未生效**
   - 检查是否调用了 `/reload` 接口
   - 确认应用是否从数据库读取配置
   - 检查缓存是否已清除

2. **历史记录丢失**
   - 确认 `config_history` 表数据完整性
   - 检查外键约束是否正确
   - 查看数据库日志

3. **回滚失败**
   - 确认历史记录 ID 有效
   - 检查配置是否存在
   - 验证用户权限

4. **导出导入错误**
   - 检查 JSON 格式是否正确
   - 确认必填字段完整
   - 查看错误消息详情

## 扩展功能

### 未来可能的功能

1. **配置分组**
   - 支持按模块/服务分组配置
   - 批量操作配置组

2. **配置验证**
   - 添加配置值格式验证
   - 支持自定义验证规则

3. **配置加密**
   - 对敏感配置进行加密存储
   - 支持加密算法配置

4. **多环境管理**
   - 支持多环境配置切换
   - 环境间配置同步

5. **配置模板**
   - 预定义配置模板
   - 快速部署新环境

## 支持

如有问题或建议，请联系：
- 技术支持邮箱：support@claw.ai
- 项目文档：https://docs.claw.ai
- GitHub Issues：https://github.com/claw-ai/claw-ai-backend/issues
