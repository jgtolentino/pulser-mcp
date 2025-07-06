# Installing Pulser MCP in Claude Desktop

## Prerequisites

1. Claude Desktop app installed
2. Node.js 18+ installed
3. Pulser MCP services running locally

## Installation Steps

### 1. Install Dependencies

```bash
cd /Users/tbwa/Documents/GitHub/pulser-mcp-server/claude-desktop
npm install
```

### 2. Configure Claude Desktop

Add the Pulser MCP server to your Claude Desktop configuration:

**On macOS:**
```bash
# Open Claude Desktop config
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**On Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

Add this configuration:

```json
{
  "mcpServers": {
    "pulser-mcp": {
      "command": "node",
      "args": ["/Users/tbwa/Documents/GitHub/pulser-mcp-server/claude-desktop/pulser-mcp-bridge.js"],
      "env": {
        "PULSER_URL": "http://localhost:8000",
        "PULSER_JWT_SECRET": "your-secret-jwt-key-change-this-in-production"
      }
    }
  }
}
```

### 3. Start Pulser Services

Make sure your Pulser MCP services are running:

```bash
cd /Users/tbwa/Documents/GitHub/pulser-mcp-server
docker-compose up -d
```

### 4. Restart Claude Desktop

Quit and restart Claude Desktop to load the new MCP server.

## Available Tools in Claude

Once installed, you can use these tools in Claude Desktop:

### 📊 Scout Analytics
```
Use the scout_analytics tool to query retail data for the last 7 days
```

### 🎨 Creative Search
```
Search for marketing assets about "summer campaign" using creative_search
```

### 📈 Financial Forecast
```
Generate a 30-day forecast for revenue using financial_forecast
```

### 🔄 Sync Status
```
Check the sync status of all services with sync_status
```

### 🏥 Health Check
```
Check if all MCP services are healthy using mcp_health
```

## Troubleshooting

### Check MCP Connection
In Claude Desktop, you should see "pulser-mcp" in the MCP indicator at the bottom of the chat window.

### View Logs
```bash
# Claude Desktop logs (macOS)
tail -f ~/Library/Logs/Claude/mcp.log

# Pulser services logs
docker-compose logs -f
```

### Common Issues

1. **"Connection refused"**: Make sure Pulser services are running
2. **"Unauthorized"**: Check JWT_SECRET matches in both configs
3. **"Tool not found"**: Restart Claude Desktop after config changes

## Advanced Configuration

### Custom Environment Variables

Create a `.env` file in the claude-desktop directory:

```bash
PULSER_URL=https://mcp.yourdomain.com
PULSER_JWT_SECRET=your-production-secret
PULSER_TIMEOUT=30000
```

### SSL/TLS Support

For production deployments with HTTPS:

```json
{
  "mcpServers": {
    "pulser-mcp": {
      "command": "node",
      "args": ["pulser-mcp-bridge.js"],
      "env": {
        "PULSER_URL": "https://mcp.yourdomain.com",
        "NODE_TLS_REJECT_UNAUTHORIZED": "1"
      }
    }
  }
}
```