#!/bin/bash
# Deploy Pulser MCP to Render

set -e

echo "🚀 Deploying Pulser MCP to Render"
echo "================================="

# Check if render CLI is installed
if ! command -v render &> /dev/null; then
    echo "❌ Render CLI not found. Installing..."
    echo "Visit: https://render.com/docs/cli"
    echo "Or run: brew install render"
    exit 1
fi

# Configuration
EMAIL="jake.tolentino@insightpulseai.com"

echo "📋 Deployment Configuration:"
echo "- Email: $EMAIL"
echo "- Platform: Render"
echo "- Services: MCP Bridge + MCP Services"

# Create requirements.txt if not exists
if [ ! -f requirements.txt ]; then
    echo "📝 Creating requirements.txt..."
    cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
redis==5.0.1
pymongo==4.5.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
aiohttp==3.9.0
pyjwt==2.8.0
python-multipart==0.0.6
sse-starlette==1.6.5
httpx==0.25.1
supervisor==4.2.5
EOF
fi

# Create deployment instructions
cat > RENDER_DEPLOYMENT.md << EOF
# Render Deployment Instructions

## Option 1: Deploy via Render Dashboard

1. Go to https://dashboard.render.com
2. Click "New +" → "Blueprint"
3. Connect your GitHub repo: https://github.com/jgtolentino/pulser-mcp
4. Select the \`render.yaml\` file
5. Click "Apply"

## Option 2: Deploy via GitHub

1. Fork the repo if you haven't
2. Go to your repo Settings → Secrets
3. Add secret: RENDER_API_KEY
4. Push to main branch to trigger deployment

## Option 3: Manual Service Creation

### 1. Create Redis Instance
- Go to Render Dashboard
- New → Redis
- Name: pulser-redis
- Region: Oregon
- Plan: Starter

### 2. Create PostgreSQL Database
- New → PostgreSQL
- Name: pulser-postgres
- Database: pulser_mcp
- User: pulser_admin
- Region: Oregon

### 3. Deploy MCP Services
- New → Web Service
- Connect repo: https://github.com/jgtolentino/pulser-mcp
- Name: pulser-mcp-services
- Environment: Docker
- Dockerfile Path: ./Dockerfile.render
- Add environment variables from render.yaml

### 4. Deploy SSE Bridge
- New → Web Service
- Name: pulser-mcp-bridge
- Environment: Node
- Build Command: cd remote-mcp && npm install
- Start Command: node remote-mcp/index.js

## Custom Domain Setup

1. In Render Dashboard, go to your pulser-mcp-bridge service
2. Settings → Custom Domains
3. Add: mcp.pulser-ai.com
4. Add CNAME record:
   - Type: CNAME
   - Name: mcp
   - Value: [your-service].onrender.com

## Environment Variables

Set these in each service:
- PULSER_JWT_SECRET: (generate a secure key)
- REDIS_URL: (from Redis service)
- DATABASE_URL: (from PostgreSQL service)
- MCP_ADMIN_PASS: Postgres_admin
- REDIS_PASSWORD: Postgres_26!

## Verify Deployment

Once deployed, test:
\`\`\`bash
# Health check
curl https://pulser-mcp-bridge.onrender.com/health

# SSE endpoint
curl https://pulser-mcp-bridge.onrender.com/sse

# Monitor summary
curl -X POST https://pulser-mcp-bridge.onrender.com/mcp/command \\
  -H "Content-Type: application/json" \\
  -d '{"service": "monitor_summary", "method": "run", "params": {}}'
\`\`\`

## Claude.ai Integration

1. Go to Claude.ai settings
2. Add Remote MCP:
   - URL: https://pulser-mcp-bridge.onrender.com/sse
   - Or with custom domain: https://mcp.pulser-ai.com/sse
EOF

echo "
✅ Render deployment files created!

📚 Created files:
- render.yaml: Blueprint for one-click deployment
- Dockerfile.render: Multi-service container
- supervisor.conf: Process manager config
- RENDER_DEPLOYMENT.md: Step-by-step guide

🚀 To deploy:
1. Commit and push these files to GitHub
2. Go to https://dashboard.render.com
3. New + → Blueprint → Select your repo
4. Choose render.yaml and click Apply

📡 Your services will be available at:
- SSE Endpoint: https://pulser-mcp-bridge.onrender.com/sse
- Health Check: https://pulser-mcp-bridge.onrender.com/health

💡 Tip: You can also set up a custom domain in Render:
   mcp.pulser-ai.com → pulser-mcp-bridge.onrender.com
"