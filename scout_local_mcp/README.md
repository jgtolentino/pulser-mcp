# Scout Local MCP - 100% Offline Analytics

A fully offline-capable MCP server for Scout field agents, providing local SQLite-based analytics and transcription management without internet connectivity.

## Features

- **100% Offline Operation**: Works without internet connection
- **Local SQLite Storage**: Fast, reliable local database
- **Smart Caching**: Intelligent data caching for performance
- **Opportunistic Sync**: Syncs when connection available
- **Edge Device Support**: Runs on Raspberry Pi, tablets, laptops

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/scout_local_mcp
   ./scripts/setup.sh
   ```

2. **Start Server**:
   ```bash
   source venv/bin/activate
   python src/server.py
   ```

3. **Test Local Endpoint**:
   ```bash
   curl -X GET http://localhost:8000/mcp/metadata
   ```

## Available Tools

### add_transcription
Store sales transcriptions locally:
```json
{
  "tool": "add_transcription",
  "params": {
    "store_id": "SM-NCR-001",
    "region": "NCR",
    "brand": "Nike",
    "transcript": "Customer inquired about Air Max availability...",
    "metadata": {
      "agent_id": "field_001",
      "device_id": "tablet_42"
    }
  }
}
```

### fetch_transcriptions
Query stored transcriptions:
```json
{
  "tool": "fetch_transcriptions",
  "params": {
    "query": "Get Nike transcriptions from NCR",
    "params": {
      "region": "NCR",
      "brand": "Nike"
    }
  }
}
```

### analyze_trends
Get offline analytics:
```json
{
  "tool": "analyze_trends",
  "params": {}
}
```

## Integration with Pulser

Add to your `.pulser/settings/mcp_servers.json`:
```json
{
  "scout_local": {
    "url": "http://localhost:8000/mcp",
    "description": "Local Scout Analytics",
    "offline_capable": true
  }
}
```

## Edge Deployment

### Raspberry Pi
```bash
# Install on Raspberry Pi
sudo apt-get update
sudo apt-get install python3-pip sqlite3
./scripts/setup.sh
```

### Android Tablet (Termux)
```bash
pkg install python sqlite
pip install -r requirements.txt
python src/server.py
```

## Use Cases

1. **Field Sales Analytics**: Analyze transcriptions without internet
2. **Offline Brand Performance**: Track brand mentions locally
3. **Regional Insights**: Generate reports per region offline
4. **Cache-First Architecture**: Speed up field operations

## Architecture

```
┌─────────────────┐
│  Field Agent    │
│    Tablet       │
└────────┬────────┘
         │
    ┌────▼────┐
    │  Scout  │
    │  Local  │
    │   MCP   │
    └────┬────┘
         │
    ┌────▼────┐
    │ SQLite  │
    │   DB    │
    └─────────┘
```

## Troubleshooting

- **Database Lock**: Ensure only one instance running
- **Sync Issues**: Check `logs/sync.log` for errors
- **Performance**: Run `VACUUM` on SQLite periodically

## License

Part of InsightPulseAI SKR - Proprietary