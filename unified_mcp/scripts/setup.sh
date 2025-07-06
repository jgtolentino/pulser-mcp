#!/bin/bash
set -e

echo "🔮 Setting up Unified MCP Server with MindsDB..."

# Check for Docker
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Please install Docker first." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required. Please install it first." >&2; exit 1; }

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p config data logs scripts

# Start MindsDB and dependencies
echo "🚀 Starting MindsDB and supporting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 30

# Check MindsDB health
echo "🏥 Checking MindsDB health..."
until curl -s http://localhost:47334/api/util/ping > /dev/null; do
  echo "Waiting for MindsDB API..."
  sleep 5
done
echo "✅ MindsDB API is ready!"

# Check PostgreSQL
echo "🐘 Checking PostgreSQL..."
until docker exec unified-postgres pg_isready -U mindsdb > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL..."
  sleep 3
done
echo "✅ PostgreSQL is ready!"

# Create Python environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Configure integrations
echo "🔗 Configuring data source integrations..."
cat > data/integrations_config.json << 'EOF'
{
  "slack": {
    "enabled": false,
    "bot_token": "xoxb-your-bot-token",
    "app_token": "xapp-your-app-token"
  },
  "gmail": {
    "enabled": false,
    "credentials_file": "path/to/credentials.json",
    "token_file": "path/to/token.json"
  },
  "github": {
    "enabled": false,
    "access_token": "ghp_your_github_token",
    "org": "InsightPulseAI"
  },
  "hackernews": {
    "enabled": true,
    "poll_interval": 3600
  }
}
EOF

# Create sample queries
echo "📝 Creating sample queries..."
cat > data/sample_queries.json << 'EOF'
{
  "unified_queries": [
    {
      "name": "Agent Performance Overview",
      "query": "Show me performance metrics for all agents in the last 24 hours",
      "sources": ["scout_metrics", "creative_insights", "voice_analytics", "financial_kpis"]
    },
    {
      "name": "Cross-Agent Correlations",
      "query": "Find correlations between Scout sales data and Creative campaign performance",
      "sources": ["scout_metrics", "creative_insights"]
    },
    {
      "name": "Predictive Revenue Model",
      "query": "Create a model to predict next week revenue based on current metrics",
      "sources": ["financial_kpis", "scout_metrics"]
    }
  ]
}
EOF

echo "✅ Setup complete!"
echo ""
echo "📊 Access Points:"
echo "  - MindsDB Studio: http://localhost:8891"
echo "  - MindsDB API: http://localhost:47334"
echo "  - Unified MCP: http://localhost:8004"
echo "  - PostgreSQL: localhost:5432 (user: mindsdb, pass: mindsdb123)"
echo ""
echo "To start the Unified MCP server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/unified_server.py"
echo ""
echo "To access MindsDB SQL interface:"
echo "  mysql -h 127.0.0.1 -P 47335 -u mindsdb -p"
echo "  Password: mindsdb123"