#!/bin/bash

# RAG 系统快速启动脚本

set -e

echo "🚀 启动 RAG 系统依赖服务..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 启动依赖服务
echo "📦 启动 Qdrant、PostgreSQL 和 Redis..."
docker-compose -f docker-compose.rag.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务健康状态
echo "🔍 检查服务状态..."

# 检查 Qdrant
if curl -f http://localhost:6333/health > /dev/null 2>&1; then
    echo "✅ Qdrant 运行正常"
else
    echo "⚠️  Qdrant 可能未完全启动，请稍后手动检查"
fi

# 检查 Redis
if docker exec claw-ai-redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis 运行正常"
else
    echo "⚠️  Redis 可能未完全启动，请稍后手动检查"
fi

# 检查 PostgreSQL
if docker exec claw-ai-postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL 运行正常"
else
    echo "⚠️  PostgreSQL 可能未完全启动，请稍后手动检查"
fi

# 运行数据库迁移
echo ""
echo "📊 运行数据库迁移..."
if [ -f "alembic.ini" ]; then
    alembic upgrade head
    echo "✅ 数据库迁移完成"
else
    echo "⚠️  未找到 alembic.ini，跳过数据库迁移"
fi

# 创建上传目录
echo ""
echo "📁 创建上传目录..."
mkdir -p uploads
echo "✅ 上传目录创建完成"

# 检查环境变量
echo ""
echo "🔧 检查环境变量..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    echo "✅ .env 文件已创建，请编辑配置后重新运行"
    echo ""
    echo "📝 重要：请在 .env 文件中配置以下变量："
    echo "   - ZHIPUAI_API_KEY: 智谱 AI API 密钥"
    echo "   - DATABASE_URL: PostgreSQL 连接字符串"
    echo "   - REDIS_URL: Redis 连接字符串"
    exit 0
else
    echo "✅ .env 文件已存在"
fi

# 启动 FastAPI 应用
echo ""
echo "🌟 启动 FastAPI 应用..."
echo "📖 API 文档: http://localhost:8000/docs"
echo "🔍 健康检查: http://localhost:8000/health"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
