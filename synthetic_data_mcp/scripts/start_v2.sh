#!/bin/bash
set -e

echo "🏪 Starting Synthetic Data Generator V2 with Accurate Market Share..."
echo ""
echo "📊 Market Share Configuration:"
echo "   - TBWA Total Share: 55%"
echo "   - Category-based distribution (Dairy, Snacks, etc.)"
echo "   - Economic weighting by region/city"
echo "   - Coverage-first generation"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Running setup first..."
    ./scripts/setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Start the V2 server
echo "🚀 Starting server on http://localhost:8005..."
python src/synthetic_server_v2.py