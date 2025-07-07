#!/bin/bash
# Test the monitor_summary tool locally

echo "🧪 Testing monitor_summary tool..."

# Set environment variables for testing
export PULSER_URL="http://localhost:8000"
export PULSER_JWT_SECRET="your-secret-jwt-key-change-this-in-production"
export GRAFANA_URL="http://localhost:3000"
export GRAFANA_API_KEY=""  # Add if available

# Run the tool
echo "Running monitor_summary.py..."
python3 monitor_summary.py

echo -e "\n📊 Testing in Claude Desktop..."
echo "1. Restart Claude Desktop to load the updated bridge"
echo "2. In Claude, type: 'Use monitor_summary to check system health'"
echo "3. Or directly: 'Run the monitor_summary tool'"

echo -e "\n🌐 Testing via Remote MCP..."
echo "Testing endpoint at https://pulser-ai.com/mcp/command"
curl -X POST https://pulser-ai.com/mcp/command \
  -H "Content-Type: application/json" \
  -d '{"service": "monitor_summary", "method": "run", "params": {}}'