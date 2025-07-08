# Complete MCP Server

A comprehensive SQLite-based Model Context Protocol (MCP) server designed for seamless integration with Claude Web App.

## 🚀 Features

- **SQLite Database**: Persistent storage with key-value operations
- **CORS Proxy**: Bypasses browser restrictions for Claude Web App
- **WebSocket Support**: Real-time communication
- **Comprehensive Logging**: Full activity logging with Winston
- **Security**: Helmet.js protection and input validation
- **Testing Suite**: Complete test coverage
- **Easy Integration**: Works with existing MCP setups

## 📋 Quick Start

### Installation

```bash
# Clone or download to your desired location
cd /Users/tbwa/Documents/GitHub/mcp-complete-setup

# Install dependencies
npm install

# Start the server
./scripts/start.sh

# Run tests
npm test

# Check status
./scripts/status.sh
```

### Claude Web App Configuration

1. **Open Claude Web App Settings**
2. **Go to Integrations**
3. **Add New Integration:**
   - **Name:** Complete MCP Server
   - **URL:** `http://localhost:8000` (or `http://localhost:8001` for CORS proxy)
   - **Type:** HTTP

## 🔧 Available Tools

### Core Operations
- `sqlite_get` - Retrieve value by key
- `sqlite_set` - Store key-value pair
- `sqlite_delete` - Delete key
- `sqlite_list` - List keys with pattern matching
- `sqlite_query` - Execute SQL queries
- `get_logs` - Retrieve system logs

### Example Usage

```javascript
// Set a value
{
  "tool": "sqlite_set",
  "parameters": {
    "key": "user_name",
    "value": "John Doe",
    "type": "string"
  }
}

// Get a value
{
  "tool": "sqlite_get",
  "parameters": {
    "key": "user_name"
  }
}

// Query data
{
  "tool": "sqlite_query",
  "parameters": {
    "query": "SELECT * FROM mcp_data WHERE key LIKE ?",
    "params": ["%user_%"]
  }
}
```

## 🌐 Server Endpoints

- `GET /health` - Health check
- `GET /capabilities` - List available tools
- `GET /status` - Server status
- `POST /mcp/call` - Execute MCP tools
- `WebSocket /` - Real-time communication

## 📁 Project Structure

```
mcp-complete-setup/
├── src/
│   ├── server.js          # Main MCP server
│   └── cors-proxy.js      # CORS proxy server
├── scripts/
│   ├── start.sh           # Start servers
│   ├── stop.sh            # Stop servers
│   ├── status.sh          # Check status
│   └── integrate-existing.js # Integration script
├── tests/
│   └── test-suite.js      # Test suite
├── config/
│   ├── .env.example       # Environment variables
│   └── claude-webapp-config.json # Claude config
├── data/                  # SQLite database
├── logs/                  # Log files
└── package.json
```

## 🔗 Integration with Existing MCP Setup

To integrate with your existing MCP infrastructure:

```bash
node scripts/integrate-existing.js
```

This will:
- Create a symlink in your existing MCP directory
- Update the MCP registry
- Create startup scripts for easy management

## 🧪 Testing

Run the complete test suite:

```bash
npm test
```

Individual tests:
- Health endpoint
- Capabilities endpoint
- SQLite operations
- WebSocket connection
- CORS proxy

## 📊 Monitoring

### Check Status
```bash
./scripts/status.sh
```

### View Logs
```bash
# Server logs
tail -f logs/server.log

# CORS proxy logs
tail -f logs/cors-proxy.log

# All logs
tail -f logs/*.log
```

## 🛑 Stopping the Server

```bash
./scripts/stop.sh
```

## 🔧 Configuration

### Environment Variables

Copy `config/.env.example` to `.env` and modify:

```bash
MCP_PORT=8000
CORS_PORT=8001
DB_PATH=./data/mcp.db
LOG_LEVEL=info
```

### Production Deployment

For production use:
1. Set `NODE_ENV=production`
2. Configure proper logging
3. Set up process monitoring (PM2)
4. Configure firewall rules

## 🔒 Security

- Input validation on all endpoints
- SQL injection protection
- CORS configuration
- Helmet.js security headers
- Request logging

## 🆘 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   ./scripts/stop.sh
   ./scripts/start.sh
   ```

2. **CORS issues in Claude Web App**
   - Use the proxy URL: `http://localhost:8001`

3. **Database locked**
   - Check if another process is using the database
   - Restart the server

4. **Tests failing**
   - Ensure servers are running
   - Check port availability
   - Review logs for errors

### Getting Help

1. Check the logs: `tail -f logs/*.log`
2. Run the test suite: `npm test`
3. Check status: `./scripts/status.sh`

## 📈 Performance

- Lightweight SQLite database
- Efficient connection pooling
- Compression middleware
- Memory monitoring
- Request/response logging

## 🔄 Updates

To update the server:
1. Pull latest changes
2. Run `npm install`
3. Restart: `./scripts/stop.sh && ./scripts/start.sh`

## 📝 License

MIT License - see LICENSE file for details.
