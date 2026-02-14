#!/bin/bash

# CLAW.AI Celery 系统文件验证脚本

set -e

echo "======================================"
echo "CLAW.AI Celery 系统文件验证"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "1. 检查任务模块文件"
echo "   ------------------"

TASK_FILES=(
    "app/tasks/__init__.py"
    "app/tasks/celery_app.py"
    "app/tasks/ai_tasks.py"
    "app/tasks/knowledge_tasks.py"
)

for file in "${TASK_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✅${NC} $file ($size)"
    else
        echo -e "${RED}❌${NC} $file"
    fi
done
echo ""

echo "2. 检查 API 文件"
echo "   ------------------"

if [ -f "app/api/tasks.py" ]; then
    size=$(du -h "app/api/tasks.py" | cut -f1)
    # 统计 API 端点数量
    endpoints=$(grep -c '@router\.' app/api/tasks.py || echo 0)
    echo -e "${GREEN}✅${NC} app/api/tasks.py ($size, $endpoints 个 API 端点)"
else
    echo -e "${RED}❌${NC} app/api/tasks.py"
fi
echo ""

echo "3. 检查配置文件更新"
echo "   ------------------"

if grep -q "CELERY_BROKER_URL" "app/core/config.py"; then
    echo -e "${GREEN}✅${NC} app/core/config.py - Celery 配置已添加"
else
    echo -e "${RED}❌${NC} app/core/config.py - Celery 配置未添加"
fi

if grep -q "tasks.router" "app/main.py"; then
    echo -e "${GREEN}✅${NC} app/main.py - 任务路由已注册"
else
    echo -e "${RED}❌${NC} app/main.py - 任务路由未注册"
fi
echo ""

echo "4. 检查 Docker Compose 配置"
echo "   ------------------"

if grep -q "celery-worker" "docker-compose.prod.yml"; then
    worker_lines=$(grep -A 30 "celery-worker:" docker-compose.prod.yml | wc -l)
    echo -e "${GREEN}✅${NC} docker-compose.prod.yml - Celery Worker 已配置 ($worker_lines 行)"
else
    echo -e "${RED}❌${NC} docker-compose.prod.yml - Celery Worker 未配置"
fi

if grep -q "celery-beat" "docker-compose.prod.yml"; then
    beat_lines=$(grep -A 20 "celery-beat:" docker-compose.prod.yml | wc -l)
    echo -e "${GREEN}✅${NC} docker-compose.prod.yml - Celery Beat 已配置 ($beat_lines 行)"
else
    echo -e "${RED}❌${NC} docker-compose.prod.yml - Celery Beat 未配置"
fi

if grep -q "celery-flower" "docker-compose.prod.yml"; then
    flower_lines=$(grep -A 25 "celery-flower:" docker-compose.prod.yml | wc -l)
    echo -e "${GREEN}✅${NC} docker-compose.prod.yml - Flower 已配置 ($flower_lines 行)"
else
    echo -e "${RED}❌${NC} docker-compose.prod.yml - Flower 未配置"
fi
echo ""

echo "5. 检查依赖文件"
echo "   ------------------"

if grep -q "celery==" "requirements.txt"; then
    celery_version=$(grep "celery==" requirements.txt)
    echo -e "${GREEN}✅${NC} requirements.txt - $celery_version"
else
    echo -e "${RED}❌${NC} requirements.txt - Celery 未添加"
fi

if grep -q "flower==" "requirements.txt"; then
    flower_version=$(grep "flower==" requirements.txt)
    echo -e "${GREEN}✅${NC} requirements.txt - $flower_version"
else
    echo -e "${RED}❌${NC} requirements.txt - Flower 未添加"
fi

if grep -q "celery-redbeat==" "requirements.txt"; then
    redbeat_version=$(grep "celery-redbeat==" requirements.txt)
    echo -e "${GREEN}✅${NC} requirements.txt - $redbeat_version"
else
    echo -e "${RED}❌${NC} requirements.txt - RedBeat 未添加"
fi
echo ""

echo "6. 检查文档文件"
echo "   ------------------"

DOC_FILES=(
    "docs/celery-usage.md"
    "docs/celery.md"
    "docs/celery-async-conversation-example.py"
    "docs/CELERY_IMPLEMENTATION_SUMMARY.md"
)

for file in "${DOC_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo -e "${GREEN}✅${NC} $file ($size)"
    else
        echo -e "${RED}❌${NC} $file"
    fi
done
echo ""

echo "7. 任务统计"
echo "   ------------------"

# 统计 AI 任务数量
ai_tasks=$(grep -c "@celery_app.task" app/tasks/ai_tasks.py || echo 0)
echo -e "${GREEN}✅${NC} AI 任务数量: $ai_tasks"

# 统计知识库任务数量
kb_tasks=$(grep -c "@celery_app.task" app/tasks/knowledge_tasks.py || echo 0)
echo -e "${GREEN}✅${NC} 知识库任务数量: $kb_tasks"

# 总任务数量
total_tasks=$((ai_tasks + kb_tasks))
echo -e "${GREEN}✅${NC} 总任务数量: $total_tasks"
echo ""

echo "8. Celery 配置统计"
echo "   ------------------"

# 任务队列数量
queues=$(grep -c '"queue":' app/tasks/celery_app.py || echo 0)
echo -e "${GREEN}✅${NC} 任务队列数量: $queues"

# 定时任务数量
scheduled=$(grep -A 2 "beat_schedule" app/tasks/celery_app.py | grep -c 'task:' || echo 0)
echo -e "${GREEN}✅${NC} 定时任务数量: $scheduled"
echo ""

echo "======================================"
echo "验证完成！"
echo "======================================"
echo ""
echo "📋 快速启动："
echo "   1. docker-compose -f docker-compose.prod.yml up -d"
echo "   2. docker-compose -f docker-compose.prod.yml ps"
echo "   3. 访问 Flower: http://localhost:5555"
echo ""
echo "📚 详细文档："
echo "   - docs/celery-usage.md"
echo "   - docs/CELERY_IMPLEMENTATION_SUMMARY.md"
echo ""
