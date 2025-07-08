#!/bin/bash

echo "🛑 Stopping MCP Server..."

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Read PIDs from files
if [ -f logs/server.pid ]; then
    SERVER_PID=$(cat logs/server.pid)
    if ps -p $SERVER_PID > /dev/null; then
        kill $SERVER_PID
        echo "✅ Main server stopped (PID: $SERVER_PID)"
    fi
    rm -f logs/server.pid
fi

if [ -f logs/cors-proxy.pid ]; then
    PROXY_PID=$(cat logs/cors-proxy.pid)
    if ps -p $PROXY_PID > /dev/null; then
        kill $PROXY_PID
        echo "✅ CORS proxy stopped (PID: $PROXY_PID)"
    fi
    rm -f logs/cors-proxy.pid
fi

# Fallback: kill by pattern
pkill -f "node.*src/server.js" || true
pkill -f "node.*src/cors-proxy.js" || true

echo "🔄 All MCP server processes stopped"
