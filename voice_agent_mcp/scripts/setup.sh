#!/bin/bash
set -e

echo "🎤 Setting up Voice Agent MCP Server..."

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required for LiveKit. Please install Docker first." >&2; exit 1; }

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip

# Install portaudio for pyaudio (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Installing portaudio for macOS..."
    brew install portaudio || echo "⚠️  Please install portaudio manually"
fi

pip install -r requirements.txt

# Start LiveKit server using Docker
echo "📞 Starting LiveKit server..."
docker run -d \
  --name livekit-server \
  -p 7880:7880 \
  -p 7881:7881 \
  -p 7882:7882/udp \
  -e LIVEKIT_KEYS="devkey: secret" \
  livekit/livekit-server \
  --dev \
  2>/dev/null || echo "LiveKit container already exists"

# Wait for LiveKit
echo "⏳ Waiting for LiveKit to initialize..."
sleep 10

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data recordings logs

# Create environment template
echo "🔐 Creating environment template..."
cat > .env.example << 'EOF'
# LiveKit Configuration
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY=your_assemblyai_key_here

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here

# Firecrawl Configuration
FIRECRAWL_API_KEY=your_firecrawl_key_here

# Voice Settings
ELEVENLABS_API_KEY=your_elevenlabs_key_here
EOF

# Create sample call script
echo "📝 Creating sample call script..."
cat > data/sample_call_script.json << 'EOF'
{
  "greeting": "Hi, this is Arkie from InsightPulse. I'm calling regarding your interest in our analytics platform.",
  "discovery_questions": [
    "What analytics challenges is your team currently facing?",
    "How are you measuring marketing performance today?",
    "What would an ideal solution look like for you?"
  ],
  "value_props": [
    "Real-time insights across all channels",
    "AI-powered predictive analytics",
    "Seamless integration with existing tools"
  ],
  "objection_handlers": {
    "too_expensive": "I understand budget is important. Let's discuss the ROI our clients typically see...",
    "not_interested": "I appreciate your time. Before we end, may I ask what your current solution is?",
    "need_more_info": "Absolutely! What specific information would be most helpful for you?"
  },
  "closing": "Based on what you've shared, I think a 30-minute demo would be valuable. Are you available next Tuesday or Wednesday?"
}
EOF

# Create test audio file
echo "🎵 Creating test audio..."
python3 << 'EOF'
import numpy as np
import wave

# Generate a test tone
sample_rate = 16000
duration = 3  # seconds
frequency = 440  # A4 note

t = np.linspace(0, duration, int(sample_rate * duration))
audio = np.sin(2 * np.pi * frequency * t) * 0.3

# Save as WAV
with wave.open('recordings/test_audio.wav', 'w') as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    wav_file.writeframes((audio * 32767).astype(np.int16).tobytes())

print("Test audio created: recordings/test_audio.wav")
EOF

echo "✅ Setup complete!"
echo ""
echo "⚠️  Important: Configure your API keys in .env file"
echo "  cp .env.example .env"
echo "  # Edit .env with your actual API keys"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/voice_server.py"
echo ""
echo "Server will be available at: http://localhost:8003"
echo "LiveKit dashboard: http://localhost:7880"
echo "WebSocket endpoint: ws://localhost:8003/ws/voice/{session_id}"