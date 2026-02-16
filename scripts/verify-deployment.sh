#!/bin/bash

# 部署验证脚本
# 用于在服务器上验证部署是否成功

set -e

echo "=================================="
echo "部署验证脚本"
echo "=================================="

# 配置
API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-10}"

echo -e "\n配置信息:"
echo "API URL: $API_URL"
echo "Timeout: ${TIMEOUT}s"

# 1. 检查容器状态
echo -e "\n[1/7] 检查容器状态..."
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ 容器正在运行"
    docker-compose -f docker-compose.prod.yml ps
else
    echo "❌ 容器未运行"
    exit 1
fi

# 2. 检查 FastAPI 健康状态
echo -e "\n[2/7] 检查 FastAPI 健康状态..."
HEALTH_RESPONSE=$(curl -s --max-time $TIMEOUT "$API_URL/health" || echo "failed")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo "✅ FastAPI 健康检查通过"
    echo "   响应: $HEALTH_RESPONSE"
else
    echo "❌ FastAPI 健康检查失败"
    echo "   响应: $HEALTH_RESPONSE"
    exit 1
fi

# 3. 检查 PostgreSQL 连接
echo -e "\n[3/7] 检查 PostgreSQL 连接..."
if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U claw_ai | grep -q "accepting connections"; then
    echo "✅ PostgreSQL 连接正常"
else
    echo "❌ PostgreSQL 连接失败"
    exit 1
fi

# 4. 检查 Redis 连接
echo -e "\n[4/7] 检查 Redis 连接..."
if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli -a "${REDIS_PASSWORD}" ping | grep -q "PONG"; then
    echo "✅ Redis 连接正常"
else
    echo "❌ Redis 连接失败"
    exit 1
fi

# 5. 检查 Milvus 连接
echo -e "\n[5/7] 检查 Milvus 连接..."
if curl -s --max-time $TIMEOUT http://localhost:9091/healthz | grep -q "ok"; then
    echo "✅ Milvus 连接正常"
else
    echo "⚠️  Milvus 健康检查失败（可能还在启动中）"
fi

# 6. 检查 Prometheus 指标
echo -e "\n[6/7] 检查 Prometheus 指标..."
if curl -s --max-time $TIMEOUT "$API_URL/metrics" | grep -q "http_requests_total"; then
    echo "✅ Prometheus 指标端点正常"
else
    echo "⚠️  Prometheus 指标端点异常"
fi

# 7. 检查容器资源使用
echo -e "\n[7/7] 检查容器资源使用..."
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo -e "\n=================================="
echo "✅ 部署验证完成！"
echo "=================================="

echo -e "\n监控面板:"
echo "- Grafana:   https://openspark.online/grafana"
echo "- Prometheus: https://openspark.online/prometheus"
echo "- Flower:    https://openspark.online/flower"
echo "- API Docs:  https://openspark.online/docs"

echo -e "\n查看日志:"
echo "docker-compose -f docker-compose.prod.yml logs -f"

echo -e "\n重启服务:"
echo "docker-compose -f docker-compose.prod.yml restart"
