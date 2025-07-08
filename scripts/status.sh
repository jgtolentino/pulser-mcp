#!/bin/bash

echo "📊 MCP Server Status"
echo "==================="

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Check main server
if [ -f logs/server.pid ] && ps -p $(cat logs/server.pid) > /dev/null; then
    echo "✅ Main Server: Running (PID: $(cat logs/server.pid))"
    curl -s http://localhost:8000/health > /dev/null && echo "   Health check: OK" || echo "   Health check: FAILED"
else
    echo "❌ Main Server: Not running"
fi

# Check CORS proxy
if [ -f logs/cors-proxy.pid ] && ps -p $(cat logs/cors-proxy.pid) > /dev/null; then
    echo "✅ CORS Proxy: Running (PID: $(cat logs/cors-proxy.pid))"
    curl -s http://localhost:8001/health > /dev/null && echo "   Health check: OK" || echo "   Health check: FAILED"
else
    echo "❌ CORS Proxy: Not running"
fi

# Port usage
echo ""
echo "📡 Port Usage:"
lsof -i :8000 2>/dev/null | grep LISTEN && echo "   Port 8000: In use" || echo "   Port 8000: Available"
lsof -i :8001 2>/dev/null | grep LISTEN && echo "   Port 8001: In use" || echo "   Port 8001: Available"

# Recent logs
echo ""
echo "📄 Recent Logs (last 5 lines):"
if [ -f logs/server.log ]; then
    echo "Main Server:"
    tail -5 logs/server.log
else
    echo "No server logs found"
fi
