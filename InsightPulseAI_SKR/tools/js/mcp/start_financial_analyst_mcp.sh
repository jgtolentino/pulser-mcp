#!/bin/bash
# Startup script for financial_analyst_mcp
# Generated by Pulser Bootstrap

set -e

echo "🚀 Starting financial_analyst_mcp..."

# Navigate to server directory
cd "/Users/tbwa/Documents/GitHub/InsightPulseAI_SKR/tools/js/mcp/financial_analyst_mcp"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo "▶️ Starting server on port 8002..."
python /Users/tbwa/Documents/GitHub/InsightPulseAI_SKR/tools/js/mcp/financial_analyst_mcp/src/financial_server.py
