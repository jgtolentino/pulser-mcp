#!/bin/bash
set -e

echo "🏪 Setting up Synthetic Data Generator MCP Server..."

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

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data output logs

# Verify master data files
echo "✅ Verifying master data..."
if [ -f "data/brands.csv" ] && [ -f "data/sku_catalog.csv" ]; then
    echo "  ✓ Brand catalog loaded"
    echo "  ✓ SKU catalog loaded"
else
    echo "  ⚠️  Missing master data files. Please ensure brands.csv and sku_catalog.csv are in the data/ directory"
fi

# Create sample generation script
echo "📝 Creating sample generation script..."
cat > scripts/generate_sample.py << 'EOF'
#!/usr/bin/env python3
import requests
import json

# Generate 10,000 sample transactions
payload = {
    "dataset_type": "transactions",
    "num_records": 10000,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "client_weight": 0.55,
    "tobacco_share": 0.18,
    "output_format": "csv"
}

response = requests.post(
    "http://localhost:8005/mcp/tools/generate_data",
    json=payload
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Generated {result['records_generated']} records")
    print(f"📄 Output: {result['output_path']}")
    print(f"📊 TBWA Client Share: {result['summary']['tbwa_client_share']:.1%}")
    print(f"🚬 Tobacco Share: {result['summary']['tobacco_share']:.1%}")
else:
    print(f"❌ Error: {response.text}")
EOF

chmod +x scripts/generate_sample.py

# Create validation script
echo "🔍 Creating validation script..."
cat > scripts/validate_data.py << 'EOF'
#!/usr/bin/env python3
import requests
import sys

if len(sys.argv) < 2:
    print("Usage: validate_data.py <dataset_path>")
    sys.exit(1)

payload = {
    "dataset_path": sys.argv[1],
    "validation_rules": ["completeness", "distribution", "outliers"]
}

response = requests.post(
    "http://localhost:8005/mcp/tools/validate_quality",
    json=payload
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Validated {result['total_records']} records")
    print(f"📊 Completeness Score: {result['validation_results']['completeness']['completeness_score']:.1%}")
    print(f"🎯 Outliers: {result['validation_results']['outliers']['outlier_percentage']:.1%}")
else:
    print(f"❌ Error: {response.text}")
EOF

chmod +x scripts/validate_data.py

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/synthetic_server.py"
echo ""
echo "Server will be available at: http://localhost:8005"
echo ""
echo "To generate sample data:"
echo "  python scripts/generate_sample.py"
echo ""
echo "To validate generated data:"
echo "  python scripts/validate_data.py output/<filename>"