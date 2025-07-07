# Pulser MCP Complete Deployment Guide

**Contact**: jake.tolentino@insightpulseai.com

## Prerequisites

1. **Local Machine**:
   - Docker & Docker Compose installed
   - Node.js 18+ installed
   - Python 3.8+ installed
   - Git configured

2. **Remote Server**:
   - Ubuntu 20.04+ or similar
   - Root access via SSH
   - Domain pointing to server (pulser-ai.com)
   - Ports 80, 443 open

## Step 1: Configure Environment

1. Copy the production environment template:
   ```bash
   cp .env.production .env
   ```

2. Edit `.env` and update:
   - Generate secure JWT secret: `openssl rand -hex 32`
   - Set strong database passwords
   - Add your Supabase credentials (if using)
   - Add monitoring webhooks (Slack, etc.)

## Step 2: Update Deployment Script

Edit `deploy-all.sh` and set:
```bash
SERVER_IP="your-actual-server-ip"  # Replace with your server's IP
```

## Step 3: Run Complete Deployment

```bash
./deploy-all.sh
```

This will:
1. Start all local MCP services via Docker
2. Deploy Remote MCP bridge to your server
3. Configure SSL with Let's Encrypt
4. Setup monitoring and health checks
5. Test all endpoints

## Step 4: Configure Claude.ai

1. Go to [Claude.ai](https://claude.ai) settings
2. Navigate to "Integrations" or "MCP"
3. Add new Remote MCP:
   - **Name**: Pulser MCP
   - **URL**: `https://pulser-ai.com/sse`
   - **Description**: InsightPulseAI MCP Services

## Step 5: Verify Integration

In Claude, test these commands:
```
Check monitoring summary
Show me Scout analytics for last week
Search creative assets for "summer campaign"
```

## Monitoring & Maintenance

### View Logs
```bash
# Local services
docker-compose logs -f

# Remote bridge (on server)
ssh root@your-server "journalctl -u pulser-mcp-bridge -f"
```

### Check Health
```bash
# All services
curl https://pulser-ai.com/health

# Monitor summary
curl -X POST https://pulser-ai.com/mcp/command \
  -H "Content-Type: application/json" \
  -d '{"service": "monitor_summary", "method": "run", "params": {}}'
```

### Grafana Dashboards
- Local: http://localhost:3000 (admin/admin)
- Import dashboard from `monitoring/grafana-dashboard.json`

## Troubleshooting

### Services Won't Start
```bash
# Check Docker
docker ps -a
docker-compose logs service_name

# Check ports
netstat -tlnp | grep -E '(8000|8001|8002)'
```

### SSL Certificate Issues
```bash
# On server
sudo certbot renew
sudo systemctl reload nginx
```

### Remote MCP Not Accessible
```bash
# Check nginx
sudo nginx -t
sudo systemctl status nginx

# Check bridge service
sudo systemctl status pulser-mcp-bridge
sudo journalctl -u pulser-mcp-bridge -n 100
```

## Security Checklist

- [ ] Changed all default passwords in `.env`
- [ ] Generated secure JWT secret
- [ ] Configured firewall (ufw) on server
- [ ] SSL certificate active and auto-renewing
- [ ] Monitoring alerts configured
- [ ] Backup strategy in place

## Support

- Email: jake.tolentino@insightpulseai.com
- GitHub: https://github.com/jgtolentino/pulser-mcp
- Issues: https://github.com/jgtolentino/pulser-mcp/issues