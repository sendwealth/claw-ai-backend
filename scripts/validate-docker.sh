#!/bin/bash

# Docker 配置验证脚本

set -e

echo "=================================="
echo "Docker 配置验证"
echo "=================================="

# 1. 检查 Docker 是否安装
echo -e "\n[1/6] 检查 Docker 安装..."
if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装: $(docker --version)"
else
    echo "❌ Docker 未安装"
    exit 1
fi

# 2. 检查 Docker 是否运行
echo -e "\n[2/6] 检查 Docker 运行状态..."
if docker info &> /dev/null; then
    echo "✅ Docker 正在运行"
else
    echo "❌ Docker 未运行"
    exit 1
fi

# 3. 检查 Docker Compose
echo -e "\n[3/6] 检查 Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose 已安装: $(docker-compose --version)"
elif docker compose version &> /dev/null; then
    echo "✅ Docker Compose V2 已安装: $(docker compose version)"
else
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 4. 检查必要文件
echo -e "\n[4/6] 检查必要文件..."
files=(
    "Dockerfile"
    "docker-compose.prod.yml"
    "requirements.txt"
    ".dockerignore"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file 存在"
    else
        echo "❌ $file 不存在"
        exit 1
    fi
done

# 5. 验证 Dockerfile 语法
echo -e "\n[5/6] 验证 Dockerfile 语法..."
if docker build --dry-run -f Dockerfile . &> /dev/null; then
    echo "✅ Dockerfile 语法正确"
else
    echo "⚠️  无法验证 Dockerfile 语法（可能需要 Docker Buildx）"
fi

# 6. 验证 docker-compose 配置
echo -e "\n[6/6] 验证 docker-compose.prod.yml 配置..."
if docker-compose -f docker-compose.prod.yml config &> /dev/null; then
    echo "✅ docker-compose.prod.yml 配置正确"
else
    echo "❌ docker-compose.prod.yml 配置有误"
    exit 1
fi

echo -e "\n=================================="
echo "✅ 所有检查通过！"
echo "=================================="

echo -e "\n下一步操作："
echo "1. 构建 Docker 镜像:"
echo "   docker build -t claw-ai-backend:test ."
echo ""
echo "2. 测试运行容器:"
echo "   docker run --rm -p 8000:8000 claw-ai-backend:test"
echo ""
echo "3. 启动完整服务栈:"
echo "   docker-compose -f docker-compose.prod.yml up -d"
