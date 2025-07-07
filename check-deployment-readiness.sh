#!/bin/bash
# Check deployment readiness for Pulser MCP

echo "🔍 Checking Deployment Readiness..."
echo "=================================="

# Check domain DNS
echo -e "\n📡 DNS Configuration:"
echo "Current DNS for pulser-ai.com:"
dig pulser-ai.com +short

echo -e "\n💡 Options for deployment:"
echo "1. Use subdomain: mcp.pulser-ai.com → Your Server IP"
echo "2. Use main domain: pulser-ai.com → Your Server IP"
echo "3. Use different domain for MCP services"

echo -e "\n🔧 To use a subdomain (recommended):"
echo "1. Add A record: mcp.pulser-ai.com → YOUR_SERVER_IP"
echo "2. Update deploy-all.sh:"
echo "   DOMAIN=\"mcp.pulser-ai.com\""
echo "   SERVER_IP=\"YOUR_SERVER_IP\""

echo -e "\n📋 Pre-deployment checklist:"
echo "[ ] Server provisioned (Ubuntu 20.04+)"
echo "[ ] SSH key added: ssh-copy-id root@YOUR_SERVER_IP"
echo "[ ] Firewall allows ports: 22, 80, 443"
echo "[ ] DNS configured (A record pointing to server)"
echo "[ ] Docker installed on server"

echo -e "\n🚀 Quick server setup (run on new server):"
echo "curl -fsSL https://get.docker.com | sh"
echo "apt update && apt install -y nginx certbot python3-certbot-nginx"
echo "ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp"
echo "ufw --force enable"

echo -e "\n✅ When ready, update deploy-all.sh with:"
echo "SERVER_IP=\"$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')\""
echo "DOMAIN=\"mcp.pulser-ai.com\"  # or your chosen domain"