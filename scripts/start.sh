#!/bin/bash

# 后端快速启动脚本
# 用于快速启动 CLAW.AI 后端服务

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================"
echo "CLAW.AI 后端快速启动"
echo "======================================"
echo ""

# 检查 Python
echo "检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 未安装${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python 版本: $PYTHON_VERSION"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env 文件不存在，从 .env.example 复制...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠ 请编辑 .env 文件，配置以下关键参数：${NC}"
    echo "   - DATABASE_URL (PostgreSQL 连接字符串)"
    echo "   - REDIS_URL (Redis 连接字符串)"
    echo "   - ZHIPUAI_API_KEY (智谱 AI API 密钥)"
    echo ""
    read -p "按 Enter 继续，或 Ctrl+C 取消..."
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} 虚拟环境创建完成"
    echo ""
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} 虚拟环境已激活"
echo ""

# 安装依赖
echo "检查并安装依赖..."
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}✗ requirements.txt 文件不存在${NC}"
    exit 1
fi

pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} 依赖安装完成"
echo ""

# 检查数据库连接
echo "检查数据库连接..."
if grep -q "postgresql://postgres:password@localhost:5432/claw_ai" .env; then
    echo -e "${YELLOW}⚠ 使用默认数据库配置，请确保 PostgreSQL 已启动${NC}"
fi
echo ""

# 检查 Redis 连接
echo "检查 Redis 连接..."
if grep -q "redis://localhost:6379/0" .env; then
    echo -e "${YELLOW}⚠ 使用默认 Redis 配置，请确保 Redis 已启动${NC}"
fi
echo ""

# 检查 Qdrant 连接
echo "检查 Qdrant 连接..."
if grep -q "localhost:6333" .env; then
    echo -e "${YELLOW}⚠ 使用默认 Qdrant 配置，请确保 Qdrant 已启动${NC}"
    echo ""
    echo "启动 Qdrant（Docker）："
    echo "  docker run -d -p 6333:6333 qdrant/qdrant:latest"
fi
echo ""

# 创建日志目录
echo "创建日志目录..."
mkdir -p logs
echo -e "${GREEN}✓${NC} 日志目录创建完成"
echo ""

# 创建上传目录
echo "创建上传目录..."
mkdir -p uploads
echo -e "${GREEN}✓${NC} 上传目录创建完成"
echo ""

# 数据库迁移
echo "运行数据库迁移..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
    echo -e "${GREEN}✓${NC} 数据库迁移完成"
else
    echo -e "${YELLOW}⚠ alembic 未安装，跳过数据库迁移${NC}"
fi
echo ""

# 启动服务
echo "======================================"
echo -e "${BLUE}启动后端服务...${NC}"
echo "======================================"
echo ""
echo "服务地址:"
echo "  - API: http://localhost:8000"
echo "  - 文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
