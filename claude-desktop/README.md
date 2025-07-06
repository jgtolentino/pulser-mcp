# Pulser MCP Bridge for Claude Desktop

This bridge enables Claude Desktop to interact with your Pulser MCP ecosystem through the Model Context Protocol (MCP).

## 🚀 Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Add to Claude Desktop config
# See INSTALLATION.md for detailed steps

# 3. Restart Claude Desktop
```

## 🛠️ Available Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `scout_analytics` | Query retail analytics data | "Show me sales trends for the last week" |
| `creative_search` | Search creative assets | "Find summer campaign materials" |
| `financial_forecast` | Generate KPI forecasts | "Forecast revenue for next month" |
| `sync_status` | Check data synchronization | "Is the data synced with cloud?" |
| `mcp_health` | Service health monitoring | "Check if all services are running" |

## 📋 How It Works

```
Claude Desktop ←→ MCP Protocol ←→ Pulser Bridge ←→ Pulser Services
```

The bridge:
1. Receives tool calls from Claude Desktop via MCP
2. Authenticates with Pulser services using JWT
3. Routes requests to appropriate MCP endpoints
4. Returns formatted responses to Claude

## 🔧 Configuration

Edit environment variables in Claude Desktop config:

```json
{
  "env": {
    "PULSER_URL": "http://localhost:8000",
    "PULSER_JWT_SECRET": "your-secret-key"
  }
}
```

## 🧪 Testing

Test the connection:
1. Open Claude Desktop
2. Look for "pulser-mcp" in the MCP indicator
3. Try: "Check MCP health status"

## 📚 Documentation

- [Installation Guide](INSTALLATION.md)
- [Pulser MCP Documentation](../README.md)
- [MCP Protocol Spec](https://modelcontextprotocol.io)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Test with Claude Desktop
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](../LICENSE) file.