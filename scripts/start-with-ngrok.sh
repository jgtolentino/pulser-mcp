#!/bin/bash

# Start MCP server with ngrok tunnel
set -e

echo "🚀 Starting MCP Server with ngrok tunnel..."
echo "========================================="

# Start the main server if not running
if ! lsof -ti:8000 > /dev/null 2>&1; then
    echo "📦 Starting MCP server..."
    ./scripts/start.sh
    sleep 2
fi

# Kill any existing ngrok process
echo "🔄 Stopping any existing ngrok tunnels..."
pkill -f "ngrok http 8000" 2>/dev/null || true
sleep 1

# Start ngrok in background
echo "🌐 Starting ngrok tunnel..."
ngrok http 8000 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
echo "✅ Ngrok started (PID: $NGROK_PID)"

# Wait for ngrok to start
echo "⏳ Waiting for tunnel to establish..."
sleep 3

# Get the public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url' 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL. Check /tmp/ngrok.log for details"
    exit 1
fi

echo ""
echo "🎉 MCP Server is accessible via ngrok!"
echo "======================================="
echo "🌍 Public URL: $NGROK_URL"
echo "🏥 Health Check: $NGROK_URL/health"
echo "🔧 Capabilities: $NGROK_URL/capabilities"
echo ""
echo "📋 Claude Web App Configuration:"
echo "   Name: MCP Server (Ngrok)"
echo "   URL: $NGROK_URL"
echo "   Type: HTTP"
echo "   Auth: None"
echo ""
echo "🛑 To stop: pkill ngrok && ./scripts/stop.sh"
echo "======================================="

# Test the connection
echo "🧪 Testing connection..."
if curl -s "$NGROK_URL/health" | jq '.status' | grep -q "healthy"; then
    echo "✅ Server is accessible via ngrok!"
else
    echo "⚠️ Server test failed. Check logs."
fi