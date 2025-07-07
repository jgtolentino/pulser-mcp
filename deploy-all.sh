#!/bin/bash
# Complete deployment script for Pulser MCP infrastructure
# Including Remote MCP bridge and monitor_summary

set -e

# Configuration
EMAIL="jake.tolentino@insightpulseai.com"
DOMAIN="pulser-ai.com"
SERVER_IP="your-server-ip"  # Update with actual server IP
MCP_ADMIN_PASS="Postgres_admin"
REDIS_PASSWORD="Postgres_26!"

echo "🚀 Deploying Pulser MCP Infrastructure"
echo "Email: $EMAIL"
echo "Domain: $DOMAIN"
echo ""

# Check if we have server IP
if [ "$SERVER_IP" = "your-server-ip" ]; then
    echo "❌ Please update SERVER_IP in this script with your actual server IP"
    exit 1
fi

# 1. Deploy Docker services locally
echo "📦 Starting local MCP services..."
cd /Users/tbwa/Documents/GitHub/pulser-mcp-server
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Verify local services
echo "✅ Verifying local services..."
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 5700; do
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        echo "✅ Port $port: UP"
    else
        echo "❌ Port $port: DOWN"
    fi
done

# 2. Deploy Remote MCP bridge to server
echo -e "\n🌐 Deploying Remote MCP bridge to $DOMAIN..."

# Create deployment package
echo "📦 Creating deployment package..."
cd remote-mcp
tar -czf pulser-mcp-remote.tar.gz \
    index.js \
    package.json \
    nginx.conf \
    pulser-mcp-bridge.service \
    ../tools/monitor_summary.py

# Copy to server
echo "📤 Copying files to server..."
scp pulser-mcp-remote.tar.gz root@$SERVER_IP:/tmp/
scp deploy.sh root@$SERVER_IP:/tmp/

# Execute deployment on server
echo "🔧 Running deployment on server..."
ssh root@$SERVER_IP << EOF
set -e

# Extract files
cd /tmp
tar -xzf pulser-mcp-remote.tar.gz

# Create directories
mkdir -p /opt/pulser-mcp-bridge
cp index.js package.json monitor_summary.py /opt/pulser-mcp-bridge/
cd /opt/pulser-mcp-bridge

# Install Node.js dependencies
npm install --production

# Install Python dependencies
pip3 install pyjwt requests aiohttp pyyaml

# Set permissions
chown -R www-data:www-data /opt/pulser-mcp-bridge
chmod +x monitor_summary.py

# Install systemd service
cp /tmp/pulser-mcp-bridge.service /etc/systemd/system/
systemctl daemon-reload

# Configure nginx
cp /tmp/nginx.conf /etc/nginx/sites-available/$DOMAIN

# Create symlink if not exists
if [ ! -L /etc/nginx/sites-enabled/$DOMAIN ]; then
    ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
fi

# Test nginx config
nginx -t

# Generate JWT secret
JWT_SECRET=\$(openssl rand -hex 32)

# Create environment file
cat > /opt/pulser-mcp-bridge/.env << EOL
NODE_ENV=production
PORT=3001
PULSER_URL=http://localhost:8000
PULSER_JWT_SECRET=\$JWT_SECRET
EMAIL=$EMAIL
MCP_ADMIN_PASS=$MCP_ADMIN_PASS
REDIS_PASSWORD=$REDIS_PASSWORD
EOL

chmod 600 /opt/pulser-mcp-bridge/.env

# Setup SSL with Let's Encrypt
if ! [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "🔒 Setting up SSL certificate..."
    certbot certonly --nginx \
        -d $DOMAIN \
        --non-interactive \
        --agree-tos \
        -m $EMAIL
else
    echo "✅ SSL certificate already exists"
fi

# Start services
systemctl enable pulser-mcp-bridge
systemctl start pulser-mcp-bridge
systemctl reload nginx

echo "✅ Remote deployment complete"
EOF

# Clean up
rm pulser-mcp-remote.tar.gz

# 3. Setup monitoring
echo -e "\n📊 Setting up monitoring..."
cd ../monitoring
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    echo "Setting up Slack alerts..."
    # Update systemd service with webhook
    ssh root@$SERVER_IP "sed -i 's|# Environment=\"ALERT_WEBHOOK=.*\"|Environment=\"ALERT_WEBHOOK=$SLACK_WEBHOOK_URL\"|' /etc/systemd/system/mcp-health-monitor.service"
fi

# 4. Verify deployment
echo -e "\n🧪 Verifying deployment..."
sleep 10

# Test health endpoint
if curl -f https://$DOMAIN/health > /dev/null 2>&1; then
    echo "✅ HTTPS health endpoint is accessible"
else
    echo "❌ HTTPS health endpoint failed"
fi

# Test SSE endpoint
if curl -f -H "Accept: text/event-stream" --max-time 5 https://$DOMAIN/sse > /dev/null 2>&1; then
    echo "✅ SSE endpoint is accessible"
else
    echo "⚠️  SSE endpoint check timed out (this may be normal)"
fi

# Test monitor_summary
echo "🧪 Testing monitor_summary..."
response=$(curl -s -X POST https://$DOMAIN/mcp/command \
  -H "Content-Type: application/json" \
  -d '{"service": "monitor_summary", "method": "run", "params": {}}')

if echo "$response" | jq -e '.summary' > /dev/null 2>&1; then
    echo "✅ Monitor summary is working!"
    echo "Preview:"
    echo "$response" | jq -r '.summary' | head -n 5
else
    echo "❌ Monitor summary test failed"
fi

echo "
🎉 Deployment Complete!

Local Services: http://localhost:8000-8009
Remote MCP: https://$DOMAIN/sse
Monitor: https://$DOMAIN/mcp/command

Next Steps:
1. Add to Claude.ai Remote MCP:
   - URL: https://$DOMAIN/sse
   - Name: Pulser MCP
   
2. Test in Claude:
   - 'Check monitoring summary'
   - 'Show me Scout analytics'
   
3. Setup GitHub Actions:
   - Push to trigger health checks
   - Monitor via Issues tab

Documentation:
- Incident Runbook: docs/INCIDENT_RUNBOOK.md
- Example Prompts: docs/CLAUDE_PROMPTS.md
"