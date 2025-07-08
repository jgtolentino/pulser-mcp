#!/bin/bash

# Render deployment script
echo "🚀 Deploying MCP Server to Render..."

# Export required environment variables
export RENDER_API_KEY="${RENDER_API_KEY:-}"

if [ -z "$RENDER_API_KEY" ]; then
    echo "❌ RENDER_API_KEY not set. Please set it first:"
    echo "export RENDER_API_KEY=your-api-key"
    exit 1
fi

# Create service via API
echo "📦 Creating/updating service..."

curl -X POST https://api.render.com/v1/services \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "web_service",
    "name": "pulser-mcp-simple",
    "ownerId": "'"$RENDER_OWNER_ID"'",
    "repo": "https://github.com/jgtolentino/pulser-mcp",
    "branch": "claude-mcp-simple",
    "autoDeploy": "yes",
    "envVars": [
      {"key": "NODE_ENV", "value": "production"},
      {"key": "PORT", "value": "10000"},
      {"key": "DB_PATH", "value": "/mnt/data/mcp.db"},
      {"key": "LOG_LEVEL", "value": "info"}
    ],
    "serviceDetails": {
      "env": "node",
      "buildCommand": "npm install",
      "startCommand": "node src/server.js",
      "plan": "free",
      "region": "oregon",
      "healthCheckPath": "/health",
      "disk": {
        "name": "mcp-storage",
        "mountPath": "/mnt/data",
        "sizeGB": 1
      }
    }
  }'

echo ""
echo "✅ Deployment initiated!"
echo "📊 Check status at: https://dashboard.render.com"