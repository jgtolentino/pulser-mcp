#!/bin/bash

# Quick Start Script for MCP Complete Server
# Run this to get everything up and running quickly

echo "🚀 MCP Complete Server - Quick Start"
echo "====================================="

# Make scripts executable
chmod +x scripts/*.sh install.sh setup.sh

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start servers
echo "🌟 Starting servers..."
./scripts/start.sh

# Wait a moment
sleep 3

# Run a quick test
echo "🧪 Running quick test..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Server is running and healthy!"
    echo ""
    echo "🌐 Claude Web App URLs:"
    echo "   Direct: http://localhost:8000"
    echo "   CORS Proxy: http://localhost:8001"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Add integration in Claude Web App settings"
    echo "   2. Use URL: http://localhost:8000"
    echo "   3. Run 'npm test' for full testing"
    echo "   4. Check 'README.md' for detailed instructions"
else
    echo "❌ Server failed to start"
    echo "📋 Check logs: tail -f logs/server.log"
fi
