#!/bin/bash
set -e

echo "🔍 Setting up Deep Researcher MCP Server..."

# Check for Python
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Download NLTK data for text processing
echo "📊 Downloading NLTK data..."
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('vader_lexicon')"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/{research,reports,cache,monitoring} logs output

# Create sample research configuration
echo "⚙️ Creating sample configuration..."
cat > data/research_config.json << 'EOF'
{
  "default_sources": ["web", "news", "social"],
  "research_depth": {
    "quick": {
      "max_sources": 10,
      "time_limit_minutes": 5
    },
    "standard": {
      "max_sources": 25,
      "time_limit_minutes": 15
    },
    "deep": {
      "max_sources": 50,
      "time_limit_minutes": 30
    }
  },
  "monitoring_intervals": {
    "hourly": 3600,
    "daily": 86400,
    "weekly": 604800
  },
  "quality_thresholds": {
    "min_relevance_score": 0.7,
    "max_duplicate_percentage": 0.1,
    "min_source_credibility": 0.6
  }
}
EOF

# Create sample competitive analysis template
echo "📋 Creating analysis templates..."
cat > data/templates/competitive_analysis_template.json << 'EOF'
{
  "analysis_framework": {
    "market_position": {
      "factors": ["market_share", "brand_recognition", "product_quality", "pricing_strategy"],
      "scoring": "1-5 scale"
    },
    "competitive_strengths": {
      "categories": ["product", "marketing", "distribution", "technology", "brand"],
      "assessment": "qualitative description"
    },
    "competitive_threats": {
      "threat_level": ["low", "medium", "high", "critical"],
      "impact_areas": ["market_share", "pricing_pressure", "innovation_lag"]
    },
    "strategic_recommendations": {
      "timeframe": ["immediate", "short_term", "medium_term", "long_term"],
      "priority": ["high", "medium", "low"],
      "effort": ["low", "medium", "high"]
    }
  }
}
EOF

mkdir -p data/templates

# Create test script
echo "🧪 Creating test script..."
cat > scripts/test_research.py << 'EOF'
#!/usr/bin/env python3
import requests
import json
import time

def test_research():
    """Test basic research functionality"""
    payload = {
        "topic": "AI marketing automation tools",
        "research_type": "competitive_analysis",
        "depth": "standard",
        "sources": ["web", "news"]
    }
    
    print("🔍 Testing research automation...")
    response = requests.post(
        "http://localhost:8007/mcp/tools/conduct_research",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Research completed: {result.get('research_id')}")
        return result
    else:
        print(f"❌ Research failed: {response.text}")
        return None

def test_competitor_analysis():
    """Test competitive analysis"""
    payload = {
        "brand": "TechCorp",
        "competitors": ["InnovateAI", "MarketBot", "AutoFlow"],
        "analysis_areas": ["pricing", "products", "marketing"],
        "time_range": "30d"
    }
    
    print("🏆 Testing competitive analysis...")
    response = requests.post(
        "http://localhost:8007/mcp/tools/analyze_competitors",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Analysis completed: {result.get('analysis_id')}")
        return result
    else:
        print(f"❌ Analysis failed: {response.text}")
        return None

def test_trend_analysis():
    """Test trend analysis"""
    payload = {
        "industry": "digital marketing",
        "keywords": ["AI automation", "personalization", "omnichannel"],
        "time_range": "90d",
        "geo_focus": "Philippines"
    }
    
    print("📈 Testing trend analysis...")
    response = requests.post(
        "http://localhost:8007/mcp/tools/analyze_trends",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Trend analysis completed: {result.get('trends_id')}")
        return result
    else:
        print(f"❌ Trend analysis failed: {response.text}")
        return None

def test_monitoring_setup():
    """Test monitoring setup"""
    payload = {
        "entities": ["TechCorp", "AI automation", "marketing tools"],
        "monitoring_type": "brand_mentions",
        "frequency": "daily"
    }
    
    print("📡 Testing monitoring setup...")
    response = requests.post(
        "http://localhost:8007/mcp/tools/setup_monitoring",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Monitoring setup: {result.get('monitor_id')}")
        return result
    else:
        print(f"❌ Monitoring setup failed: {response.text}")
        return None

if __name__ == "__main__":
    print("=" * 50)
    print("Deep Researcher MCP Test Suite")
    print("=" * 50)
    
    # Test all capabilities
    test_research()
    print()
    test_competitor_analysis()
    print()
    test_trend_analysis()
    print()
    test_monitoring_setup()
    
    print("\n🎉 All tests completed!")
EOF

chmod +x scripts/test_research.py

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/researcher_server.py"
echo ""
echo "Server will be available at: http://localhost:8007"
echo ""
echo "To test research capabilities:"
echo "  python scripts/test_research.py"