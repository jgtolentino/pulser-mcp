#!/bin/bash
set -e

echo "📄 Setting up BriefVault RAG MCP Server..."

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

# Install Tesseract for OCR (macOS)
if command -v brew >/dev/null 2>&1; then
    echo "🔍 Installing Tesseract OCR..."
    brew install tesseract || echo "Tesseract may already be installed"
else
    echo "⚠️  Homebrew not found. Please install Tesseract manually for OCR functionality"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/documents data/processed logs output

# Create sample documents directory
mkdir -p data/samples

# Create sample brief for testing
echo "📝 Creating sample brief..."
cat > data/samples/sample_brief.txt << 'EOF'
CREATIVE BRIEF

Client: TechCorp Inc.
Campaign: Q1 Product Launch
Date: January 15, 2024

OBJECTIVES:
- Increase brand awareness among millennials by 25%
- Drive 10,000 app downloads in first month
- Generate 500 qualified leads

TARGET AUDIENCE:
- Demographics: Ages 25-35, urban professionals
- Income: $50,000-$100,000 annually
- Psychographics: Tech-savvy early adopters who value innovation
- Behaviors: Heavy social media users, online shoppers

KEY MESSAGES:
- Innovation meets simplicity
- Transform your daily workflow
- Join the productivity revolution

CREATIVE REQUIREMENTS:
- 30-second video ad for social media
- Static display ads (300x250, 728x90)
- App store screenshots and description
- Landing page with conversion form

SUCCESS METRICS:
- Click-through rate > 2%
- Cost per acquisition < $50
- App store rating > 4.0 stars

TIMELINE:
- Creative concepts: January 25
- Final assets: February 10
- Campaign launch: February 15

BRAND GUIDELINES:
- Use primary brand colors: #FF6B35, #F7931E
- Include logo prominently
- Maintain friendly, approachable tone
EOF

echo "🧪 Creating test script..."
cat > scripts/test_ingestion.py << 'EOF'
#!/usr/bin/env python3
import requests
import json

# Test document ingestion
def test_ingest():
    payload = {
        "file_path": "data/samples/sample_brief.txt",
        "document_type": "creative_brief",
        "metadata": {
            "client": "TechCorp Inc.",
            "campaign": "Q1 Product Launch",
            "date": "2024-01-15",
            "author": "Creative Team"
        }
    }
    
    response = requests.post(
        "http://localhost:8006/mcp/tools/ingest_document",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Document ingested: {result}")
        return result.get("document_id")
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_search():
    payload = {
        "query": "target audience demographics millennials",
        "limit": 5
    }
    
    response = requests.post(
        "http://localhost:8006/mcp/tools/search_briefs",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Search results: {result}")
    else:
        print(f"❌ Search error: {response.text}")

if __name__ == "__main__":
    print("Testing BriefVault RAG MCP...")
    doc_id = test_ingest()
    if doc_id:
        test_search()
EOF

chmod +x scripts/test_ingestion.py

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/briefvault_server.py"
echo ""
echo "Server will be available at: http://localhost:8006"
echo ""
echo "To test document processing:"
echo "  python scripts/test_ingestion.py"