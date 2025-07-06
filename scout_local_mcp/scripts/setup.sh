#!/bin/bash
set -e

echo "🚀 Setting up Scout Local MCP Server..."

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "pip3 is required but not installed. Aborting." >&2; exit 1; }

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Ollama if not present (for local LLM)
if ! command -v ollama &> /dev/null; then
    echo "🤖 Installing Ollama for local LLM..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ollama
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "⚠️  Please install Ollama manually from https://ollama.ai"
    fi
fi

# Pull DeepSeek model for local inference
echo "🧠 Pulling DeepSeek model..."
ollama pull deepseek:latest || echo "⚠️  Failed to pull model. Please run 'ollama pull deepseek:latest' manually."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Initialize database
echo "🗄️ Initializing database..."
python3 src/server.py &
SERVER_PID=$!
sleep 5
kill $SERVER_PID 2>/dev/null || true

# Create system prompt file
echo "📝 Creating system prompt..."
cat > system_prompt.txt << 'EOF'
You are Scout Local Analytics Assistant, operating in offline mode.
Focus on providing actionable insights from local transcription data.
Prioritize speed and relevance for field agents.
When data is limited, provide best estimates with clear disclaimers.
EOF

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/server.py"
echo ""
echo "Server will be available at: http://localhost:8000"
echo "MCP endpoint: http://localhost:8000/mcp"