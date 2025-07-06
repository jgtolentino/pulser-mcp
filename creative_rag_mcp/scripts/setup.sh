#!/bin/bash
set -e

echo "🚀 Setting up Creative RAG MCP Server..."

# Check for Docker (required for Qdrant)
command -v docker >/dev/null 2>&1 || { echo "Docker is required for Qdrant. Please install Docker first." >&2; exit 1; }

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Start Qdrant using Docker
echo "🗄️ Starting Qdrant vector database..."
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/data/qdrant:/qdrant/storage \
  qdrant/qdrant:latest \
  2>/dev/null || echo "Qdrant container already exists"

# Wait for Qdrant to be ready
echo "⏳ Waiting for Qdrant to initialize..."
sleep 10

# Check Qdrant health
until curl -s http://localhost:6333/health > /dev/null; do
  echo "Waiting for Qdrant..."
  sleep 2
done
echo "✅ Qdrant is ready!"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs data/qdrant

# Download sample ColPali model (mock for now)
echo "🧠 Preparing embedding model..."
cat > data/colpali_config.json << 'EOF'
{
  "model_name": "colpali-mock",
  "embedding_dim": 768,
  "model_type": "vision-language",
  "supported_formats": ["jpg", "png", "pdf"]
}
EOF

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/rag_server.py"
echo ""
echo "Server will be available at: http://localhost:8001"
echo "Qdrant UI available at: http://localhost:6333/dashboard"
echo "MCP endpoint: http://localhost:8001/mcp"