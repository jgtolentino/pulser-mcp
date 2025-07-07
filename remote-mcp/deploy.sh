#!/bin/bash
# Deploy script for Pulser MCP Remote Bridge

set -e

echo "🚀 Deploying Pulser MCP Remote Bridge..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# 1. Create directory and copy files
echo "📁 Setting up application directory..."
mkdir -p /opt/pulser-mcp-bridge
cp package.json index.js /opt/pulser-mcp-bridge/
chown -R www-data:www-data /opt/pulser-mcp-bridge

# 2. Install dependencies
echo "📦 Installing dependencies..."
cd /opt/pulser-mcp-bridge
sudo -u www-data npm install --production

# 3. Install systemd service
echo "⚙️  Installing systemd service..."
cp /path/to/pulser-mcp-bridge.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable pulser-mcp-bridge.service

# 4. Configure nginx
echo "🔧 Configuring nginx..."
cp nginx.conf /etc/nginx/sites-available/pulser-ai.com
ln -sf /etc/nginx/sites-available/pulser-ai.com /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

# 5. Set up SSL with Let's Encrypt
echo "🔒 Setting up SSL certificate..."
if ! [ -d "/etc/letsencrypt/live/pulser-ai.com" ]; then
    certbot certonly --nginx \
        -d pulser-ai.com \
        --non-interactive \
        --agree-tos \
        -m admin@pulser-ai.com
else
    echo "SSL certificate already exists"
fi

# 6. Create environment file
echo "🔐 Creating environment configuration..."
cat > /opt/pulser-mcp-bridge/.env << EOF
NODE_ENV=production
PORT=3001
PULSER_URL=http://localhost:8000
PULSER_JWT_SECRET=$(openssl rand -hex 32)
EOF
chown www-data:www-data /opt/pulser-mcp-bridge/.env
chmod 600 /opt/pulser-mcp-bridge/.env

# 7. Start services
echo "🚀 Starting services..."
systemctl start pulser-mcp-bridge
systemctl reload nginx

# 8. Verify deployment
echo "✅ Verifying deployment..."
sleep 5

# Check if service is running
if systemctl is-active --quiet pulser-mcp-bridge; then
    echo "✅ Pulser MCP Bridge is running"
else
    echo "❌ Pulser MCP Bridge failed to start"
    journalctl -u pulser-mcp-bridge -n 50
    exit 1
fi

# Check health endpoint
if curl -f http://localhost:3001/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Check nginx
if curl -f https://pulser-ai.com/health > /dev/null 2>&1; then
    echo "✅ HTTPS endpoint is accessible"
else
    echo "⚠️  HTTPS endpoint not accessible (DNS may need to propagate)"
fi

echo "
🎉 Deployment complete!

Your Pulser MCP Remote endpoints are:
- SSE: https://pulser-ai.com/sse
- Command: https://pulser-ai.com/mcp/command
- Services: https://pulser-ai.com/mcp/services
- Health: https://pulser-ai.com/health

To view logs:
- Service: journalctl -u pulser-mcp-bridge -f
- Nginx: tail -f /var/log/nginx/pulser-ai.com.*.log

To configure Claude Remote MCP:
1. Go to Claude.ai settings
2. Add Remote MCP integration
3. Set URL: https://pulser-ai.com/sse
"