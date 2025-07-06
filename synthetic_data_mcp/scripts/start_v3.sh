#!/bin/bash
set -e

echo "🏪 Starting Synthetic Data Generator V3 with Realistic Market Share..."
echo ""
echo "📊 Market Reality Configuration:"
echo "   - Total TBWA Share: ~22% (realistic penetration)" 
echo "   - 177 brands (39 TBWA + 138 competitors)"
echo "   - 17 sari-sari categories with authentic weights"
echo "   - 1200+ SKUs with realistic pack sizes"
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

# Check if extended data files exist
if [ ! -f "data/brands_extended.csv" ]; then
    echo "⚠️  Extended brand data not found. Please ensure:"
    echo "     - data/brands_extended.csv exists (177 brands)"
    echo "     - data/sku_catalog_extended.csv exists (1200+ SKUs)"
    echo ""
    echo "   Falling back to basic data files..."
fi

# Start the V3 server
echo "🚀 Starting V3 server on http://localhost:8005..."
echo "   Expected TBWA share: ~22%"
echo "   To generate data: python scripts/generate_realistic_data.py"
echo ""
python src/synthetic_server_v3.py