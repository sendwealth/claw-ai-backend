#!/bin/bash

# CLAW.AI Backend Deployment Script
# 部署后端到生产服务器

set -e

echo "========================================="
echo "  CLAW.AI Backend 部署"
echo "========================================="
echo ""

# 配置
APP_DIR="/root/claw-ai-backend"
REPO_URL="https://github.com/sendwealth/claw-ai-backend.git"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="claw-ai-backend"

# 检查是否在服务器上
if [ ! -d "/root" ]; then
    echo "❌ 错误：此脚本必须在服务器上运行"
    exit 1
fi

echo "📂 1. 克隆代码..."
if [ -d "$APP_DIR" ]; then
    echo "ℹ️  代码已存在，更新代码..."
    cd "$APP_DIR"
    git pull origin master
else
    echo "ℹ️  克隆新代码..."
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi
echo "✅ 代码克隆完成"
echo ""

echo "🐍 2. 创建虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "✅ 虚拟环境创建完成"
else
    echo "ℹ️  虚拟环境已存在"
fi
echo ""

echo "📦 3. 安装依赖..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ 依赖安装完成"
echo ""

echo "⚙️  4. 配置环境变量..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "ℹ️  创建 .env 文件..."
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "⚠️  请编辑 .env 文件并配置必要的变量："
    echo "   - ZHIPUAI_API_KEY"
    echo "   - DATABASE_URL"
    echo "   - REDIS_URL"
    echo ""
    echo "   编辑命令：nano $APP_DIR/.env"
    echo ""
    echo "   配置完成后，重新运行此脚本或手动启动服务"
    exit 0
else
    echo "ℹ️  .env 文件已存在"
fi
echo ""

echo "🗄️  5. 初始化数据库..."
python -c "from app.db import engine; from app.db.base import Base; import app.models; Base.metadata.create_all(bind=engine); print('✅ 数据库初始化完成')" || echo "⚠️  数据库初始化可能失败，请检查配置"
echo ""

echo "👤 6. 创建默认用户..."
python scripts/init_db.py || echo "⚠️  初始化用户可能失败"
echo ""

echo "🧪 7. 测试配置..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 测试健康检查
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "📱 访问地址："
    echo "   - API: http://111.229.40.25:8000"
    echo "   - 文档: http://111.229.40.25:8000/docs"
    echo "   - 健康检查: http://111.229.40.25:8000/health"
    echo ""
    echo "🔥 测试命令："
    echo "   curl http://localhost:8000/health"
else
    echo "❌ 服务启动失败，请检查日志"
fi

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
