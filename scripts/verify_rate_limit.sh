#!/bin/bash

# CLAW.AI 限流系统验证脚本

echo "=================================="
echo "CLAW.AI 限流系统验证"
echo "=================================="
echo ""

# 配置
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test_admin_token}"
USER_TOKEN="${USER_TOKEN:-test_user_token}"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试计数器
TOTAL=0
PASSED=0
FAILED=0

# 测试函数
test_api() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    local method="${4:-GET}"
    local data="$5"

    TOTAL=$((TOTAL + 1))
    echo -n "测试 $TOTAL: $name ... "

    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$url" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $ADMIN_TOKEN" \
            -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" \
            -H "Authorization: Bearer $ADMIN_TOKEN")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ 通过${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ 失败${NC}"
        echo "  期望状态码: $expected_status, 实际: $http_code"
        echo "  响应: $body"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "1. 检查应用健康状态"
echo "-------------------"
test_api "健康检查" "/health" "200"
echo ""

echo "2. 检查限流配置"
echo "-------------------"
test_api "获取限流配置" "/api/v1/rate-limit/config" "200"
echo ""

echo "3. 白名单管理"
echo "-------------------"
# 添加 IP 到白名单
test_api "添加 IP 到白名单" "/api/v1/rate-limit/whitelist" "200" "POST" '{"type":"ip","value":"192.168.1.100"}'

# 获取白名单
test_api "获取白名单" "/api/v1/rate-limit/whitelist" "200"

# 从白名单移除
test_api "从白名单移除 IP" "/api/v1/rate-limit/whitelist" "200" "DELETE" '{"type":"ip","value":"192.168.1.100"}'
echo ""

echo "4. 黑名单管理"
echo "-------------------"
# 添加 IP 到黑名单
test_api "添加 IP 到黑名单" "/api/v1/rate-limit/blacklist" "200" "POST" '{"type":"ip","value":"192.168.1.200"}'

# 获取黑名单
test_api "获取黑名单" "/api/v1/rate-limit/blacklist" "200"

# 从黑名单移除
test_api "从黑名单移除 IP" "/api/v1/rate-limit/blacklist" "200" "DELETE" '{"type":"ip","value":"192.168.1.200"}'
echo ""

echo "5. 限流状态查询"
echo "-------------------"
test_api "获取限流状态" "/api/v1/rate-limit/status" "200"
echo ""

echo "6. 限流测试"
echo "-------------------"
test_api "限流测试端点" "/api/v1/rate-limit/test" "200"
echo ""

echo "7. 监控数据"
echo "-------------------"
test_api "获取监控数据" "/api/v1/rate-limit/monitor" "200"
echo ""

echo "8. 重置限流"
echo "-------------------"
test_api "重置用户限流" "/api/v1/rate-limit/reset" "200" "POST" '{"type":"user","identifier":"test_user"}'
test_api "重置 IP 限流" "/api/v1/rate-limit/reset" "200" "POST" '{"type":"ip","identifier":"192.168.1.100"}'
echo ""

echo "=================================="
echo "测试总结"
echo "=================================="
echo -e "总计: $TOTAL"
echo -e "${GREEN}通过: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}失败: $FAILED${NC}"
    echo ""
    echo "⚠️  部分测试失败，请检查应用日志"
    exit 1
else
    echo -e "${GREEN}所有测试通过！✓${NC}"
    echo ""
    echo "✅ 限流系统已正确安装和配置"
    exit 0
fi
