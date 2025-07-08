#!/bin/bash

echo "🚀 Starting Complete MCP Server..."

# Configuration
MCP_PORT=8000
CORS_PORT=8001

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Kill any existing processes
echo "🔄 Stopping existing processes..."
pkill -f "node.*src/server.js" || true
pkill -f "node.*src/cors-proxy.js" || true
sleep 2

# Check if ports are free
if lsof -i :$MCP_PORT &>/dev/null; then
    echo "❌ Port $MCP_PORT is still in use"
    exit 1
fi

if lsof -i :$CORS_PORT &>/dev/null; then
    echo "❌ Port $CORS_PORT is still in use"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Start main server
echo "🌟 Starting main MCP server on port $MCP_PORT..."
nohup node src/server.js > logs/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > logs/server.pid

# Start CORS proxy
echo "🌐 Starting CORS proxy on port $CORS_PORT..."
nohup node src/cors-proxy.js > logs/cors-proxy.log 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > logs/cors-proxy.pid

# Wait for servers to start
sleep 3

# Check if servers are running
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Main server started (PID: $SERVER_PID)"
else
    echo "❌ Main server failed to start"
    cat logs/server.log
    exit 1
fi

if ps -p $PROXY_PID > /dev/null; then
    echo "✅ CORS proxy started (PID: $PROXY_PID)"
else
    echo "❌ CORS proxy failed to start"
    cat logs/cors-proxy.log
    exit 1
fi

echo ""
echo "🎉 MCP Complete Server is running!"
echo "======================================="
echo "📍 Main Server: http://localhost:$MCP_PORT"
echo "🌐 CORS Proxy: http://localhost:$CORS_PORT"
echo "🏥 Health Check: curl http://localhost:$MCP_PORT/health"
echo "🧪 Run Tests: npm test"
echo "📋 View Logs: tail -f logs/server.log"
echo "🛑 Stop Server: ./scripts/stop.sh"
echo ""
echo "Claude Web App Configuration:"
echo "- Direct URL: http://localhost:$MCP_PORT"
echo "- Proxy URL: http://localhost:$CORS_PORT"
echo "======================================="
