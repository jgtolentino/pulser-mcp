#!/bin/bash
# Simple deployment to use existing gagambi-backend

echo "🚀 Configuring Pulser MCP to use gagambi-backend:8000"
echo "===================================================="

# Update all configuration files
echo "📝 Updating configuration files..."

# Update .env
cat > .env << EOF
# MCP Configuration for Gagambi Backend
PULSER_URL=http://gagambi-backend:8000
PULSER_JWT_SECRET=$(openssl rand -hex 32)
MCP_ADMIN_USER=admin
MCP_ADMIN_PASS=Postgres_admin
REDIS_PASSWORD=Postgres_26!
NEO4J_PASSWORD=Postgres_26!
EMAIL=jake.tolentino@insightpulseai.com
EOF

echo "✅ Configuration updated to use gagambi-backend:8000"

# For Claude Desktop
echo -e "\n💻 For Claude Desktop:"
echo "1. Update ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "2. Set PULSER_URL to: http://gagambi-backend:8000"
echo "3. Restart Claude Desktop"

# For Remote MCP (if using)
echo -e "\n🌐 For Remote MCP:"
echo "1. Deploy only the SSE bridge component"
echo "2. Point it to gagambi-backend:8000"

echo -e "\n📋 Next Steps:"
echo "1. Ensure gagambi-backend is running on port 8000"
echo "2. Update Claude Desktop config"
echo "3. Test with: 'Check monitoring summary'"

# Test connection
echo -e "\n🧪 Testing connection to gagambi-backend..."
if curl -f http://gagambi-backend:8000/health > /dev/null 2>&1; then
    echo "✅ Successfully connected to gagambi-backend:8000"
else
    echo "⚠️  Could not connect to gagambi-backend:8000"
    echo "   Make sure the service is running and accessible"
fi