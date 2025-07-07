# Pulser MCP Remote Bridge

This bridge enables Claude.ai to connect to your Pulser MCP ecosystem via Server-Sent Events (SSE).

## 🌐 Overview

The Remote MCP Bridge provides:
- **SSE endpoint** at `https://pulser-ai.com/sse` for Claude Remote MCP
- **TLS termination** with nginx and Let's Encrypt
- **JWT authentication** to secure internal services
- **Real-time events** from all 12 MCP services
- **Health monitoring** and service discovery

## 🚀 Quick Deploy

```bash
# Run as root on your server
cd /path/to/pulser-mcp-server/remote-mcp
sudo ./deploy.sh
```

## 🔧 Manual Setup

### 1. Install Dependencies

```bash
cd /opt/pulser-mcp-bridge
npm install
```

### 2. Configure Environment

Create `/opt/pulser-mcp-bridge/.env`:
```env
NODE_ENV=production
PORT=3001
PULSER_URL=http://localhost:8000
PULSER_JWT_SECRET=your-secret-key-here
```

### 3. Install Systemd Service

```bash
sudo cp pulser-mcp-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pulser-mcp-bridge
```

### 4. Configure Nginx

```bash
sudo cp nginx.conf /etc/nginx/sites-available/pulser-ai.com
sudo ln -sf /etc/nginx/sites-available/pulser-ai.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 5. Set Up SSL

```bash
sudo certbot certonly --nginx -d pulser-ai.com
```

## 📡 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sse` | GET | Server-Sent Events stream |
| `/mcp/command` | POST | Execute MCP commands |
| `/mcp/services` | GET | List available services |
| `/mcp/sync-status` | GET | Check sync status |
| `/health` | GET | Health check |

## 🔗 Claude.ai Integration

1. Go to [Claude.ai](https://claude.ai) settings
2. Navigate to "Remote MCP" integrations
3. Add new integration:
   - **Name**: Pulser MCP
   - **URL**: `https://pulser-ai.com/sse`
   - **Description**: Pulser AI ecosystem integration

## 📊 SSE Event Types

The SSE stream emits these event types:

```javascript
// Initial connection
event: init
data: {"connected": true, "timestamp": "2024-01-07T..."}

// Health updates (every 10s)
event: health
data: {"services": {...}, "timestamp": "..."}

// Keep-alive ping (every 30s)
event: ping
data: {"timestamp": "..."}

// Error notifications
event: error
data: {"message": "...", "error": "..."}
```

## 🔍 Monitoring

### View Logs
```bash
# Service logs
sudo journalctl -u pulser-mcp-bridge -f

# Nginx access logs
sudo tail -f /var/log/nginx/pulser-ai.com.access.log

# Nginx error logs
sudo tail -f /var/log/nginx/pulser-ai.com.error.log
```

### Check Status
```bash
# Service status
sudo systemctl status pulser-mcp-bridge

# Test endpoints
curl https://pulser-ai.com/health
curl https://pulser-ai.com/mcp/services
```

## 🛡️ Security

- **JWT Authentication**: All internal requests use JWT tokens
- **TLS 1.3**: Modern encryption with Let's Encrypt
- **CORS**: Configured for Claude.ai domains
- **Rate Limiting**: Nginx can add rate limits if needed
- **Resource Limits**: Systemd enforces memory/CPU quotas

## 🐛 Troubleshooting

### SSE Connection Drops
- Check nginx timeout settings
- Verify keep-alive is working
- Look for proxy buffering issues

### Authentication Errors
- Ensure JWT_SECRET matches between services
- Check token expiration (1 hour default)
- Verify Authorization header format

### SSL Certificate Issues
- Run `sudo certbot renew` to refresh
- Check DNS A record for pulser-ai.com
- Verify port 443 is open in firewall

## 📚 Architecture

```
Claude.ai → HTTPS → Nginx → Node.js Bridge → Pulser MCP Services
                      ↓
                   SSL/TLS
                 (Let's Encrypt)
```

The bridge acts as a secure gateway between Claude's Remote MCP and your internal Pulser services.