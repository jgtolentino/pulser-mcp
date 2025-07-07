#!/bin/bash
# Deploy monitor_summary tool to Remote MCP server

set -e

echo "🚀 Deploying monitor_summary to Remote MCP..."

# Copy the tool to server
echo "📦 Copying monitor_summary.py to server..."
scp ../tools/monitor_summary.py root@pulser-ai.com:/opt/pulser-mcp-bridge/

# Update the Remote MCP bridge
echo "🔄 Updating Remote MCP bridge..."
scp index.js root@pulser-ai.com:/opt/pulser-mcp-bridge/

# Install Python dependencies on server
echo "📚 Installing dependencies..."
ssh root@pulser-ai.com << 'EOF'
cd /opt/pulser-mcp-bridge
pip3 install pyjwt requests
chown www-data:www-data monitor_summary.py
chmod +x monitor_summary.py
EOF

# Restart the service
echo "🔄 Restarting Remote MCP bridge..."
ssh root@pulser-ai.com "systemctl restart pulser-mcp-bridge"

# Wait for service to start
sleep 5

# Test the deployment
echo "🧪 Testing deployment..."
response=$(curl -s -X POST https://pulser-ai.com/mcp/command \
  -H "Content-Type: application/json" \
  -d '{"service": "monitor_summary", "method": "run", "params": {}}')

if echo "$response" | jq -e '.summary' > /dev/null 2>&1; then
  echo "✅ Monitor summary deployed successfully!"
  echo "Response preview:"
  echo "$response" | jq -r '.summary' | head -n 5
else
  echo "❌ Deployment test failed"
  echo "Response: $response"
  exit 1
fi

echo "
🎉 Deployment complete!

Test in Claude.ai:
1. Go to Claude.ai
2. Type: 'Check the monitoring summary'
3. Or: 'Run monitor_summary to see system health'

The tool will return:
- Service health status (X/12 healthy)
- Sync lag information
- Active alerts summary
- Recent incidents (if any)
"