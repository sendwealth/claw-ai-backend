#!/bin/bash

# API 测试脚本
# 测试后端 API 的连通性和基本功能

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API 基础 URL
API_BASE="${API_BASE_URL:-http://localhost:8000/api/v1}"

echo "======================================"
echo "CLAW.AI API 测试脚本"
echo "======================================"
echo ""
echo "API 基础 URL: $API_BASE"
echo ""

# 测试函数
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local token="$5"

    echo -n "测试 $name ... "

    local curl_cmd="curl -s -w '\n%{http_code}' -X $method '$API_BASE$endpoint'"

    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi

    if [ -n "$token" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $token'"
    fi

    local response=$(eval $curl_cmd)
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓${NC} ($http_code)"
        return 0
    else
        echo -e "${RED}✗${NC} ($http_code)"
        echo "  响应: $body"
        return 1
    fi
}

# 1. 健康检查
echo "1. 健康检查"
test_endpoint "健康检查" "GET" "/../health"
echo ""

# 2. 注册用户
echo "2. 用户注册"
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"Test123!","email":"test@example.com"}')

echo "注册响应: $REGISTER_RESPONSE"
echo ""

# 3. 登录用户
echo "3. 用户登录"
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"Test123!"}')

echo "登录响应: $LOGIN_RESPONSE"

# 提取 token
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ 登录失败，无法获取 token${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 登录成功，获取到 token${NC}"
echo ""

# 4. 获取当前用户信息
echo "4. 获取当前用户信息"
test_endpoint "获取用户信息" "GET" "/users/me" "" "$TOKEN"
echo ""

# 5. 创建知识库
echo "5. 创建知识库"
KB_RESPONSE=$(curl -s -X POST "$API_BASE/knowledge" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"name":"测试知识库","description":"这是一个测试知识库"}')

echo "创建知识库响应: $KB_RESPONSE"

# 提取知识库 ID
KB_ID=$(echo $KB_RESPONSE | grep -o '"id":[0-9]*' | head -n1 | cut -d':' -f2)

if [ -z "$KB_ID" ]; then
    echo -e "${RED}✗ 创建知识库失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 知识库创建成功，ID: $KB_ID${NC}"
echo ""

# 6. 获取知识库列表
echo "6. 获取知识库列表"
test_endpoint "获取知识库列表" "GET" "/knowledge" "" "$TOKEN"
echo ""

# 7. 创建文档
echo "7. 创建文档"
DOC_RESPONSE=$(curl -s -X POST "$API_BASE/knowledge/$KB_ID/documents" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"title":"测试文档","content":"这是一个测试文档的内容。","file_type":"txt"}')

echo "创建文档响应: $DOC_RESPONSE"
echo ""

# 8. 获取文档列表
echo "8. 获取文档列表"
test_endpoint "获取文档列表" "GET" "/knowledge/$KB_ID/documents" "" "$TOKEN"
echo ""

# 9. RAG 查询
echo "9. RAG 查询"
RAG_RESPONSE=$(curl -s -X POST "$API_BASE/knowledge/$KB_ID/query?question=测试问题&top_k=5" \
    -H "Authorization: Bearer $TOKEN")

echo "RAG 查询响应: $RAG_RESPONSE"
echo ""

# 10. 创建对话
echo "10. 创建对话"
CONV_RESPONSE=$(curl -s -X POST "$API_BASE/conversations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"title":"测试对话"}')

echo "创建对话响应: $CONV_RESPONSE"

# 提取对话 ID
CONV_ID=$(echo $CONV_RESPONSE | grep -o '"id":"[^"]*"' | head -n1 | cut -d'"' -f4)

if [ -z "$CONV_ID" ]; then
    echo -e "${RED}✗ 创建对话失败${NC}"
else
    echo -e "${GREEN}✓ 对话创建成功，ID: $CONV_ID${NC}"
fi
echo ""

# 11. 获取对话列表
echo "11. 获取对话列表"
test_endpoint "获取对话列表" "GET" "/conversations" "" "$TOKEN"
echo ""

echo "======================================"
echo -e "${GREEN}API 测试完成！${NC}"
echo "======================================"
