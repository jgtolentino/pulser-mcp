#!/bin/bash

# MCP Server Endpoint Test Script
# Tests local, ngrok, and cloud endpoints

set -e

echo "🧪 MCP Server Endpoint Testing Suite"
echo "===================================="

# Configuration
LOCAL_URL="http://localhost:8000"
NGROK_URL="${NGROK_URL:-}"
CLOUD_URL="${CLOUD_URL:-}"
API_KEY="${API_KEY:-}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local endpoint=$3
    local expected_status=$4
    local api_key=$5
    
    echo -n "Testing $name $endpoint... "
    
    if [ -n "$api_key" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $api_key" "$url$endpoint" 2>/dev/null || echo "000")
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url$endpoint" 2>/dev/null || echo "000")
    fi
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✅ Pass ($response)${NC}"
        return 0
    else
        echo -e "${RED}❌ Fail (got $response, expected $expected_status)${NC}"
        return 1
    fi
}

# Test MCP discovery
test_mcp_discovery() {
    local name=$1
    local url=$2
    local api_key=$3
    
    echo -n "Testing $name MCP Discovery... "
    
    if [ -n "$api_key" ]; then
        response=$(curl -s -H "X-API-Key: $api_key" "$url/.well-known/mcp" 2>/dev/null)
    else
        response=$(curl -s "$url/.well-known/mcp" 2>/dev/null)
    fi
    
    if echo "$response" | jq -e '.mcp_version' >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Valid MCP response${NC}"
        return 0
    else
        echo -e "${RED}❌ Invalid MCP response${NC}"
        return 1
    fi
}

# Test MCP tool call
test_mcp_tool() {
    local name=$1
    local url=$2
    local api_key=$3
    
    echo -n "Testing $name MCP Tool (sqlite_set)... "
    
    if [ -n "$api_key" ]; then
        response=$(curl -s -X POST -H "Content-Type: application/json" -H "X-API-Key: $api_key" \
            -d '{"tool":"sqlite_set","parameters":{"key":"test_key","value":"test_value"}}' \
            "$url/mcp/call" 2>/dev/null)
    else
        response=$(curl -s -X POST -H "Content-Type: application/json" \
            -d '{"tool":"sqlite_set","parameters":{"key":"test_key","value":"test_value"}}' \
            "$url/mcp/call" 2>/dev/null)
    fi
    
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Tool call successful${NC}"
        return 0
    else
        echo -e "${RED}❌ Tool call failed${NC}"
        return 1
    fi
}

# Main testing
echo "1. Testing Local Server"
echo "-----------------------"
if curl -s "$LOCAL_URL/health" >/dev/null 2>&1; then
    test_endpoint "Local" "$LOCAL_URL" "/health" "200"
    test_endpoint "Local" "$LOCAL_URL" "/capabilities" "200"
    test_mcp_discovery "Local" "$LOCAL_URL"
    test_mcp_tool "Local" "$LOCAL_URL"
else
    echo -e "${YELLOW}⚠️  Local server not running${NC}"
fi

echo ""

# Test ngrok if URL provided
if [ -n "$NGROK_URL" ]; then
    echo "2. Testing Ngrok Tunnel"
    echo "-----------------------"
    test_endpoint "Ngrok" "$NGROK_URL" "/health" "200"
    test_endpoint "Ngrok" "$NGROK_URL" "/capabilities" "200"
    test_mcp_discovery "Ngrok" "$NGROK_URL"
    test_mcp_tool "Ngrok" "$NGROK_URL"
else
    echo "2. Ngrok Testing"
    echo "----------------"
    echo -e "${YELLOW}⚠️  No NGROK_URL provided. Skipping ngrok tests.${NC}"
    echo "   Run with: NGROK_URL=https://your-url.ngrok.io ./test-endpoints.sh"
fi

echo ""

# Test cloud if URL provided
if [ -n "$CLOUD_URL" ]; then
    echo "3. Testing Cloud Deployment"
    echo "---------------------------"
    test_endpoint "Cloud" "$CLOUD_URL" "/health" "200" "$API_KEY"
    test_endpoint "Cloud" "$CLOUD_URL" "/capabilities" "200" "$API_KEY"
    test_mcp_discovery "Cloud" "$CLOUD_URL" "$API_KEY"
    test_mcp_tool "Cloud" "$CLOUD_URL" "$API_KEY"
else
    echo "3. Cloud Testing"
    echo "----------------"
    echo -e "${YELLOW}⚠️  No CLOUD_URL provided. Skipping cloud tests.${NC}"
    echo "   Run with: CLOUD_URL=https://your-app.onrender.com API_KEY=your-key ./test-endpoints.sh"
fi

echo ""
echo "===================================="
echo "🎯 Test Summary"
echo ""
echo "To test all environments, run:"
echo "NGROK_URL=https://xxx.ngrok.io CLOUD_URL=https://mcp.onrender.com API_KEY=key ./test-endpoints.sh"