#!/bin/bash
set -e

echo "🎙️ Setting up Audio Analysis MCP Server..."

# Check for Python
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }

# Check for system audio dependencies
echo "🔧 Checking system dependencies..."

# Check for portaudio (required for pyaudio)
if ! pkg-config --exists portaudio-2.0; then
    echo "⚠️ PortAudio not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew >/dev/null 2>&1; then
            brew install portaudio
        else
            echo "Please install Homebrew and run: brew install portaudio"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-pyaudio
    else
        echo "Please install PortAudio for your system"
        exit 1
    fi
fi

# Check for FFmpeg (useful for audio processing)
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "⚠️ FFmpeg not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew >/dev/null 2>&1; then
            brew install ffmpeg
        else
            echo "Please install Homebrew and run: brew install ffmpeg"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y ffmpeg
    fi
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install build tools
echo "🔨 Setting up build environment..."
pip install --upgrade pip setuptools wheel

# Install system-specific dependencies first
echo "📚 Installing audio processing dependencies..."

# Install PyAudio (can be tricky)
echo "🎧 Installing PyAudio..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - use pip with proper flags
    pip install pyaudio
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - install from apt first
    pip install pyaudio
else
    echo "Manual PyAudio installation may be required for your system"
    pip install pyaudio || echo "PyAudio installation failed - continuing without it"
fi

# Install remaining dependencies
echo "📦 Installing Python packages..."
pip install -r requirements.txt

# Download NLTK data for text processing
echo "📊 Downloading NLTK data..."
python -c "
import nltk
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    print('NLTK data downloaded successfully')
except Exception as e:
    print(f'NLTK download error: {e}')
"

# Download sentence transformer model
echo "🧠 Downloading AI models..."
python -c "
from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings('ignore')

print('Downloading text encoder...')
encoder = SentenceTransformer('all-MiniLM-L6-v2')
print('Text encoder downloaded successfully!')
"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/{audio,processed,reports,models} logs output

# Create sample call centre configuration
echo "⚙️ Creating sample configuration..."
cat > data/call_centre_config.json << 'EOF'
{
  "quality_standards": {
    "audio_quality": {
      "minimum_clarity_score": 70,
      "maximum_background_noise_db": 40,
      "target_volume_range": [10, 80],
      "interruption_limit": 3
    },
    "speech_quality": {
      "minimum_transcription_confidence": 0.8,
      "maximum_filler_word_percentage": 8,
      "target_words_per_minute": [120, 180],
      "maximum_response_time_seconds": 5
    },
    "customer_satisfaction": {
      "minimum_sentiment_score": 0.2,
      "target_satisfaction_score": 75,
      "escalation_risk_threshold": 30,
      "resolution_indicator_target": 2
    }
  },
  "agent_guidelines": {
    "greeting_requirements": {
      "required_phrases": ["thank you for calling", "how can I help"],
      "maximum_greeting_time": 30
    },
    "professional_standards": {
      "prohibited_words": ["um", "uh", "like", "basically"],
      "required_closing": ["thank you", "have a great day"],
      "escalation_triggers": ["manager", "supervisor", "complaint"]
    },
    "performance_metrics": {
      "target_call_resolution_rate": 85,
      "maximum_average_handling_time": 360,
      "minimum_customer_satisfaction": 4.0,
      "maximum_escalation_rate": 10
    }
  },
  "departments": {
    "customer_support": {
      "specialization": "technical support and troubleshooting",
      "avg_call_duration": 240,
      "quality_focus": ["problem_resolution", "technical_accuracy"]
    },
    "sales": {
      "specialization": "product sales and upselling",
      "avg_call_duration": 180,
      "quality_focus": ["conversion_rate", "customer_engagement"]
    },
    "billing": {
      "specialization": "billing inquiries and disputes",
      "avg_call_duration": 150,
      "quality_focus": ["accuracy", "dispute_resolution"]
    },
    "retention": {
      "specialization": "customer retention and loyalty",
      "avg_call_duration": 300,
      "quality_focus": ["customer_satisfaction", "retention_rate"]
    }
  }
}
EOF

# Create sample quality assessment template
echo "📋 Creating quality assessment template..."
cat > data/quality_assessment_template.json << 'EOF'
{
  "assessment_criteria": {
    "opening": {
      "weight": 15,
      "criteria": [
        "Professional greeting within 30 seconds",
        "Clear identification of agent and company",
        "Appropriate tone and enthusiasm"
      ]
    },
    "information_gathering": {
      "weight": 20,
      "criteria": [
        "Asked relevant questions to understand issue",
        "Actively listened to customer responses",
        "Clarified complex information when needed"
      ]
    },
    "problem_resolution": {
      "weight": 25,
      "criteria": [
        "Demonstrated product/service knowledge",
        "Provided accurate and complete solutions",
        "Followed proper procedures and protocols"
      ]
    },
    "communication_skills": {
      "weight": 20,
      "criteria": [
        "Clear and professional speech",
        "Appropriate pace and volume",
        "Minimal use of filler words"
      ]
    },
    "customer_service": {
      "weight": 15,
      "criteria": [
        "Empathetic and patient approach",
        "Professional closing and next steps",
        "Customer satisfaction achieved"
      ]
    },
    "compliance": {
      "weight": 5,
      "criteria": [
        "Followed security and privacy protocols",
        "Adhered to company policies",
        "Completed required documentation"
      ]
    }
  },
  "scoring": {
    "excellent": {"range": [90, 100], "description": "Exceeds expectations"},
    "good": {"range": [80, 89], "description": "Meets expectations"},
    "satisfactory": {"range": [70, 79], "description": "Acceptable performance"},
    "needs_improvement": {"range": [60, 69], "description": "Below expectations"},
    "unsatisfactory": {"range": [0, 59], "description": "Requires immediate coaching"}
  }
}
EOF

mkdir -p data/templates

# Create test script
echo "🧪 Creating test script..."
cat > scripts/test_audio_analysis.py << 'EOF'
#!/usr/bin/env python3
import requests
import json
import time
import os

def test_health():
    """Test server health"""
    print("🏥 Testing server health...")
    try:
        response = requests.get("http://localhost:8009/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Server healthy - Audio files analyzed: {result.get('audio_files_analyzed', 0)}")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_audio_analysis():
    """Test audio analysis with sample audio"""
    # Note: User would replace with actual audio file
    test_audio_path = "/path/to/sample/call.wav"
    
    payload = {
        "audio_path": test_audio_path,
        "analysis_type": "comprehensive",
        "speaker_detection": True,
        "language": "en-US",
        "metadata": {
            "agent_id": "AGENT_001",
            "customer_id": "CUST_12345",
            "call_type": "support",
            "department": "customer_support",
            "date": "2024-01-15"
        }
    }
    
    print("🎙️ Testing audio analysis...")
    print(f"Note: Update test_audio_path to a real audio file: {test_audio_path}")
    
    try:
        response = requests.post(
            "http://localhost:8009/mcp/tools/analyze_audio",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Audio analysis completed: {result.get('audio_id')}")
                return result
            else:
                print(f"❌ Analysis failed: {result.get('error')}")
                return None
        else:
            print(f"❌ Analysis request failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return None

def test_quality_assessment():
    """Test call quality assessment"""
    # This requires an audio_id from previous analysis
    sample_guidelines = {
        "clarity_threshold": 75,
        "pace_target": 150,
        "interruption_limit": 2,
        "sentiment_target": 0.3
    }
    
    payload = {
        "audio_id": "sample_audio_id",
        "quality_metrics": ["clarity", "volume", "background_noise", "interruptions", "pace"],
        "agent_guidelines": sample_guidelines
    }
    
    print("📊 Testing quality assessment...")
    print("Note: This requires a valid audio_id from previous analysis")
    
    try:
        response = requests.post(
            "http://localhost:8009/mcp/tools/assess_quality",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                assessment = result.get("quality_assessment", {})
                score = assessment.get("overall_score", 0)
                print(f"✅ Quality assessment completed - Score: {score:.1f}")
                return result
            else:
                print(f"❌ Quality assessment failed: {result.get('error')}")
                return None
        else:
            print(f"❌ Assessment request failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Assessment error: {e}")
        return None

def test_sentiment_analysis():
    """Test sentiment analysis"""
    payload = {
        "audio_id": "sample_audio_id",
        "analysis_segments": True,
        "customer_satisfaction_focus": True
    }
    
    print("😊 Testing sentiment analysis...")
    
    try:
        response = requests.post(
            "http://localhost:8009/mcp/tools/analyze_sentiment",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                sentiment = result.get("sentiment_analysis", {})
                overall_sentiment = sentiment.get("overall_sentiment", {})
                print(f"✅ Sentiment analysis completed - Polarity: {overall_sentiment.get('polarity', 0):.2f}")
                return result
            else:
                print(f"❌ Sentiment analysis failed: {result.get('error')}")
                return None
        else:
            print(f"❌ Sentiment request failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Sentiment error: {e}")
        return None

def test_audio_search():
    """Test audio search functionality"""
    payload = {
        "query": "customer complaint resolution satisfaction",
        "search_type": "semantic",
        "filters": {
            "call_type": "support",
            "quality_score_min": 70
        },
        "limit": 5
    }
    
    print("🔍 Testing audio search...")
    
    try:
        response = requests.post(
            "http://localhost:8009/mcp/tools/search_audio",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                results = result.get("results", [])
                print(f"✅ Search completed - Found {len(results)} audio files")
                return result
            else:
                print(f"❌ Search failed: {result.get('error')}")
                return None
        else:
            print(f"❌ Search request failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("Audio Analysis MCP Test Suite")
    print("=" * 60)
    
    # Test server health first
    if not test_health():
        print("❌ Server is not running. Start it first with:")
        print("  python src/audio_server.py")
        exit(1)
    
    print()
    
    # Test audio analysis (requires actual audio file)
    test_audio_analysis()
    print()
    
    # Test quality assessment
    test_quality_assessment()
    print()
    
    # Test sentiment analysis
    test_sentiment_analysis()
    print()
    
    # Test audio search
    test_audio_search()
    
    print("\n🎉 All tests completed!")
    print("\nTo analyze real call recordings:")
    print("1. Place audio files in the data/audio/ directory")
    print("2. Update the test_audio_path in test_audio_analysis()")
    print("3. Run the analysis with: python scripts/test_audio_analysis.py")
    print("\nSupported audio formats: WAV, MP3, M4A, FLAC")
EOF

chmod +x scripts/test_audio_analysis.py

# Create sample data directory structure
echo "📂 Creating sample data structure..."
cat > data/README.md << 'EOF'
# Audio Analysis Data Directory

## Structure

- `audio/` - Place call recordings here for analysis
- `processed/` - Processed audio data and analysis results
- `reports/` - Generated quality assessment reports
- `models/` - AI models and training data
- `call_centre_config.json` - Call centre configuration and standards
- `quality_assessment_template.json` - Quality assessment criteria

## Supported Audio Formats

- WAV (recommended for best quality)
- MP3 (compressed, good for storage)
- M4A (Apple audio format)
- FLAC (lossless compression)

## Usage

1. Copy call recordings to the `audio/` directory
2. Start the server: `python src/audio_server.py`
3. Use the API endpoints or test script to analyze calls
4. Check the `processed/` directory for results

## Quality Standards

Customize `call_centre_config.json` with your organization's:
- Audio quality thresholds
- Speech quality standards
- Customer satisfaction targets
- Agent performance guidelines

## Analysis Types

- **comprehensive**: Full analysis including quality, sentiment, and transcription
- **quality_only**: Focus on audio and speech quality metrics
- **sentiment_only**: Customer satisfaction and emotional analysis
- **transcription_only**: Speech-to-text conversion only
EOF

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/audio_server.py"
echo ""
echo "Server will be available at: http://localhost:8009"
echo ""
echo "To test audio analysis capabilities:"
echo "  python scripts/test_audio_analysis.py"
echo ""
echo "📝 Next steps:"
echo "1. Place call recordings in data/audio/"
echo "2. Customize data/call_centre_config.json"
echo "3. Start analyzing call quality!"
echo ""
echo "📊 For best results:"
echo "- Use WAV format for highest quality analysis"
echo "- Ensure recordings are clear with minimal background noise"
echo "- Include metadata (agent ID, call type, etc.) for better insights"