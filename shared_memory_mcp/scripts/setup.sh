#!/bin/bash
set -e

echo "🧠 Setting up Shared Memory MCP with Graphiti..."

# Check for Docker
command -v docker >/dev/null 2>&1 || { echo "Docker is required. Please install Docker first." >&2; exit 1; }

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p config data logs

# Create Neo4j configuration
echo "⚙️ Creating Neo4j configuration..."
cat > config/neo4j.conf << 'EOF'
# Neo4j configuration for Graphiti
dbms.memory.heap.initial_size=512m
dbms.memory.heap.max_size=1G
dbms.memory.pagecache.size=512m

# Enable APOC procedures
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*

# Network settings
dbms.connector.bolt.listen_address=0.0.0.0:7687
dbms.connector.http.listen_address=0.0.0.0:7474

# Logging
dbms.logs.query.enabled=true
dbms.logs.query.time_logging_enabled=true
dbms.logs.query.threshold=100ms
EOF

# Start services
echo "🚀 Starting Neo4j and Redis..."
docker-compose up -d

# Wait for Neo4j
echo "⏳ Waiting for Neo4j to initialize..."
sleep 20

# Check Neo4j health
until curl -s http://localhost:7474 > /dev/null; do
  echo "Waiting for Neo4j..."
  sleep 5
done
echo "✅ Neo4j is ready!"

# Create Python environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Initialize sample memories
echo "💭 Creating sample memories..."
python3 << 'EOF'
import json

sample_memories = [
    {
        "content": "Nike Air Max shows 25% higher sales in Metro Manila vs provinces",
        "memory_type": "insight",
        "source_agent": "scout_edge",
        "tags": ["nike", "metro_manila", "sales"],
        "metadata": {"confidence": 0.89, "sample_size": 2500}
    },
    {
        "content": "Minimalist design campaigns have 40% better engagement",
        "memory_type": "fact",
        "source_agent": "creative_rag",
        "tags": ["design", "engagement", "campaign"],
        "metadata": {"measured_period": "Q4 2023"}
    },
    {
        "content": "Increase social media budget by 30% for Q2",
        "memory_type": "decision",
        "source_agent": "financial_analyst",
        "tags": ["budget", "social_media", "q2"],
        "metadata": {"approved_by": "CMO", "date": "2024-01-15"}
    },
    {
        "content": "Customer sentiment positive for eco-friendly products",
        "memory_type": "insight",
        "source_agent": "voice_agent",
        "tags": ["sentiment", "eco_friendly", "customer"],
        "metadata": {"sentiment_score": 0.78, "call_volume": 450}
    }
]

with open('data/sample_memories.json', 'w') as f:
    json.dump(sample_memories, f, indent=2)

print("✅ Sample memories created")
EOF

echo "✅ Setup complete!"
echo ""
echo "🌐 Access Points:"
echo "  - Shared Memory API: http://localhost:5700"
echo "  - Neo4j Browser: http://localhost:7474"
echo "    Username: neo4j"
echo "    Password: graphiti123"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/memory_server.py"
echo ""
echo "To view the graph:"
echo "  1. Open http://localhost:7474"
echo "  2. Run: MATCH (n) RETURN n LIMIT 50"