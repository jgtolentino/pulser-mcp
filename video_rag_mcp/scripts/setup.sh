#!/bin/bash
set -e

echo "🎬 Setting up Video RAG MCP Server..."

# Check for Python
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }

# Check for FFmpeg (required for moviepy)
command -v ffmpeg >/dev/null 2>&1 || { echo "⚠️ FFmpeg is recommended for optimal video processing." >&2; }

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip

# Install system dependencies first
echo "🔧 Installing system-level dependencies..."
pip install wheel setuptools

# Install PyTorch (CPU version for compatibility)
echo "🤖 Installing PyTorch..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
pip install -r requirements.txt

# Download pre-trained models
echo "🧠 Downloading AI models..."
python -c "
from sentence_transformers import SentenceTransformer
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch

print('Downloading text encoder...')
text_encoder = SentenceTransformer('all-MiniLM-L6-v2')

print('Downloading image captioning model...')
blip_processor = BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-base')
blip_model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base')

print('Models downloaded successfully!')
"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/{videos,processed,frames,audio} logs output

# Create sample brand guidelines configuration
echo "⚙️ Creating sample brand guidelines..."
cat > data/brand_guidelines_sample.json << 'EOF'
{
  "brand_name": "Sample Brand",
  "logo_placement": {
    "minimum_size": "64x64",
    "preferred_positions": ["bottom-right", "top-right"],
    "clear_space": "2x logo height",
    "background_requirements": "high contrast"
  },
  "brand_colors": {
    "approved_colors": ["#FF6B35", "#2E86AB", "#A23B72", "#F18F01", "#C73E1D"],
    "primary_color": "#FF6B35",
    "secondary_colors": ["#2E86AB", "#F18F01"],
    "avoid_colors": ["#FF0000", "#00FF00", "#0000FF"]
  },
  "messaging_guidelines": {
    "required_phrases": ["Powered by innovation", "Your trusted partner"],
    "prohibited_phrases": ["cheap", "discount", "limited time"],
    "tone": "professional and approachable",
    "voice": "confident and trustworthy"
  },
  "audio_guidelines": {
    "minimum_clarity_score": 0.8,
    "maximum_background_noise": 0.2,
    "speech_pace": "moderate",
    "music_volume_limit": 0.6
  }
}
EOF

# Create sample video analysis configuration
echo "📋 Creating analysis configuration..."
cat > data/video_analysis_config.json << 'EOF'
{
  "default_settings": {
    "frame_sampling_rate": 30,
    "extract_audio": true,
    "analysis_depth": "comprehensive",
    "quality_thresholds": {
      "min_resolution": "720p",
      "max_duration_minutes": 60,
      "min_audio_quality": 0.7
    }
  },
  "analysis_types": {
    "comprehensive": {
      "include_frames": true,
      "include_audio": true,
      "include_compliance": true,
      "include_performance": true
    },
    "brand_compliance": {
      "include_frames": true,
      "include_audio": true,
      "include_compliance": true,
      "include_performance": false
    },
    "performance_analysis": {
      "include_frames": true,
      "include_audio": false,
      "include_compliance": false,
      "include_performance": true
    },
    "content_summary": {
      "include_frames": true,
      "include_audio": true,
      "include_compliance": false,
      "include_performance": false
    }
  },
  "output_formats": {
    "json": true,
    "html_report": true,
    "csv_summary": true
  }
}
EOF

mkdir -p data/templates

# Create test script
echo "🧪 Creating test script..."
cat > scripts/test_video_analysis.py << 'EOF'
#!/usr/bin/env python3
import requests
import json
import time
import os

def test_health():
    """Test server health"""
    print("🏥 Testing server health...")
    try:
        response = requests.get("http://localhost:8008/health")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Server healthy - Videos analyzed: {result.get('videos_analyzed', 0)}")
            return True
        else:
            print(f"❌ Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_video_analysis():
    """Test video analysis with sample video"""
    # Create a simple test video path (user would replace with actual video)
    test_video_path = "/path/to/sample/video.mp4"
    
    payload = {
        "video_path": test_video_path,
        "analysis_type": "comprehensive",
        "extract_audio": True,
        "frame_sampling_rate": 60,
        "metadata": {
            "campaign": "Test Campaign",
            "brand": "Sample Brand",
            "format": "digital"
        }
    }
    
    print("🎬 Testing video analysis...")
    print(f"Note: Update test_video_path to a real video file: {test_video_path}")
    
    try:
        response = requests.post(
            "http://localhost:8008/mcp/tools/analyze_video",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ Video analysis completed: {result.get('video_id')}")
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

def test_compliance_check():
    """Test brand compliance checking"""
    # This requires a video_id from previous analysis
    sample_guidelines = {
        "logo_placement": {
            "minimum_size": "64x64",
            "preferred_positions": ["bottom-right"]
        },
        "brand_colors": {
            "approved_colors": ["#FF6B35", "#2E86AB", "#A23B72"]
        },
        "messaging_guidelines": {
            "required_phrases": ["innovation"],
            "prohibited_phrases": ["cheap"]
        }
    }
    
    payload = {
        "video_id": "sample_video_id",
        "brand_guidelines": sample_guidelines,
        "check_areas": ["logo_placement", "color_compliance", "messaging"]
    }
    
    print("🔍 Testing compliance check...")
    print("Note: This requires a valid video_id from previous analysis")
    
    try:
        response = requests.post(
            "http://localhost:8008/mcp/tools/check_compliance",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                compliance = result.get("compliance_report", {})
                score = compliance.get("overall_score", 0)
                print(f"✅ Compliance check completed - Score: {score:.2f}")
                return result
            else:
                print(f"❌ Compliance check failed: {result.get('error')}")
                return None
        else:
            print(f"❌ Compliance request failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Compliance error: {e}")
        return None

def test_video_search():
    """Test video search functionality"""
    payload = {
        "query": "brand logo innovation",
        "search_type": "semantic",
        "filters": {
            "brand": "Sample Brand"
        },
        "limit": 5
    }
    
    print("🔍 Testing video search...")
    
    try:
        response = requests.post(
            "http://localhost:8008/mcp/tools/search_videos",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                results = result.get("results", [])
                print(f"✅ Search completed - Found {len(results)} videos")
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
    print("Video RAG MCP Test Suite")
    print("=" * 60)
    
    # Test server health first
    if not test_health():
        print("❌ Server is not running. Start it first with:")
        print("  python src/video_server.py")
        exit(1)
    
    print()
    
    # Test video analysis (requires actual video file)
    test_video_analysis()
    print()
    
    # Test compliance checking
    test_compliance_check()
    print()
    
    # Test video search
    test_video_search()
    
    print("\n🎉 All tests completed!")
    print("\nTo analyze real videos:")
    print("1. Place video files in the data/videos/ directory")
    print("2. Update the test_video_path in test_video_analysis()")
    print("3. Run the analysis with: python scripts/test_video_analysis.py")
EOF

chmod +x scripts/test_video_analysis.py

# Create sample data directory structure
echo "📂 Creating sample data structure..."
cat > data/README.md << 'EOF'
# Video RAG Data Directory

## Structure

- `videos/` - Place video files here for analysis
- `processed/` - Processed video data and analysis results
- `frames/` - Extracted frames from videos
- `audio/` - Extracted audio files
- `brand_guidelines_sample.json` - Example brand guidelines
- `video_analysis_config.json` - Analysis configuration

## Supported Video Formats

- MP4 (recommended)
- AVI
- MOV
- WMV
- FLV
- WebM

## Usage

1. Copy video files to the `videos/` directory
2. Start the server: `python src/video_server.py`
3. Use the API endpoints or test script to analyze videos
4. Check the `processed/` directory for results

## Brand Guidelines

Customize `brand_guidelines_sample.json` with your brand's:
- Logo placement requirements
- Approved color palette
- Messaging guidelines
- Audio quality standards
EOF

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/video_server.py"
echo ""
echo "Server will be available at: http://localhost:8008"
echo ""
echo "To test video analysis capabilities:"
echo "  python scripts/test_video_analysis.py"
echo ""
echo "📝 Next steps:"
echo "1. Place video files in data/videos/"
echo "2. Customize data/brand_guidelines_sample.json"
echo "3. Start analyzing videos!"