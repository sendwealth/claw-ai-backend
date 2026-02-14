#!/bin/bash

# CLAW.AI Celery 系统快速测试脚本

set -e

echo "======================================"
echo "CLAW.AI Celery 系统快速测试"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅${NC} $1 已安装"
        return 0
    else
        echo -e "${RED}❌${NC} $1 未安装"
        return 1
    fi
}

# 检查 Python 依赖
check_python_package() {
    python3 -c "import $1" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅${NC} Python 包 $1 已安装"
        return 0
    else
        echo -e "${RED}❌${NC} Python 包 $1 未安装"
        return 1
    fi
}

echo "1. 检查系统依赖"
echo "   ------------------"
check_command "docker"
check_command "docker-compose"
check_command "python3"
echo ""

echo "2. 检查 Python 依赖"
echo "   ------------------"
check_python_package "celery"
check_python_package "redis"
check_python_package "fastapi"
echo ""

echo "3. 检查项目文件"
echo "   ------------------"

FILES=(
    "app/tasks/__init__.py"
    "app/tasks/celery_app.py"
    "app/tasks/ai_tasks.py"
    "app/tasks/knowledge_tasks.py"
    "app/api/tasks.py"
    "docs/celery-usage.md"
    "docs/celery.md"
    "docs/celery-async-conversation-example.py"
    "docs/CELERY_IMPLEMENTATION_SUMMARY.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file"
    fi
done
echo ""

echo "4. 检查配置文件"
echo "   ------------------"

# 检查 config.py
if grep -q "CELERY_BROKER_URL" "app/core/config.py"; then
    echo -e "${GREEN}✅${NC} app/core/config.py 已添加 Celery 配置"
else
    echo -e "${RED}❌${NC} app/core/config.py 未添加 Celery 配置"
fi

# 检查 main.py
if grep -q "tasks.router" "app/main.py"; then
    echo -e "${GREEN}✅${NC} app/main.py 已注册任务路由"
else
    echo -e "${RED}❌${NC} app/main.py 未注册任务路由"
fi

# 检查 docker-compose.prod.yml
if grep -q "celery-worker" "docker-compose.prod.yml"; then
    echo -e "${GREEN}✅${NC} docker-compose.prod.yml 已添加 Celery 服务"
else
    echo -e "${RED}❌${NC} docker-compose.prod.yml 未添加 Celery 服务"
fi

# 检查 requirements.txt
if grep -q "celery==" "requirements.txt"; then
    echo -e "${GREEN}✅${NC} requirements.txt 已添加 Celery 依赖"
else
    echo -e "${RED}❌${NC} requirements.txt 未添加 Celery 依赖"
fi
echo ""

echo "5. 检查 Celery 配置"
echo "   ------------------"

# 尝试导入 Celery 应用
python3 -c "from app.tasks.celery_app import celery_app; print(f'✅ Celery 应用名称: {celery_app.main}')" 2>/dev/null || {
    echo -e "${RED}❌${NC} Celery 应用导入失败"
    echo "   可能原因："
    echo "   - Python 环境未正确配置"
    echo "   - 依赖未安装"
    echo ""
}
echo ""

echo "6. 启动建议"
echo "   ------------------"
echo -e "${YELLOW}📋${NC} 启动步骤："
echo ""
echo "1. 确保 .env 文件已配置："
echo "   cat .env | grep -E 'REDIS_URL|ZHIPUAI_API_KEY'"
echo ""
echo "2. 启动所有服务："
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "3. 查看服务状态："
echo "   docker-compose -f docker-compose.prod.yml ps"
echo ""
echo "4. 查看 Worker 日志："
echo "   docker-compose -f docker-compose.prod.yml logs -f celery-worker"
echo ""
echo "5. 访问 Flower 监控面板："
echo "   URL: http://localhost:5555"
echo "   默认用户名/密码: admin/admin"
echo ""
echo "6. 测试 API："
echo "   # 提交任务"
echo '   curl -X POST "http://localhost:8000/api/v1/tasks/ai/generate" \\'
echo '     -H "Content-Type: application/json" \\'
echo '     -d "{\"conversation_id\": \"test\", \"user_message\": \"你好\"}"'
echo ""
echo "   # 查询任务状态"
echo '   curl "http://localhost:8000/api/v1/tasks/status/{task_id}"'
echo ""

echo "======================================"
echo "测试完成！"
echo "======================================"
echo ""
echo -e "${GREEN}📚${NC} 详细文档："
echo "   - docs/celery-usage.md (完整使用指南)"
echo "   - docs/celery.md (快速入门)"
echo "   - docs/CELERY_IMPLEMENTATION_SUMMARY.md (实现总结)"
echo ""
