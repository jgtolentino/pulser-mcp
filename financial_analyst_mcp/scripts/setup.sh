#!/bin/bash
set -e

echo "📊 Setting up Financial Analyst MCP Server..."

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠️  Docker is recommended for sandboxed execution. Continue anyway? (y/n)" >&2; read -r response; [[ "$response" != "y" ]] && exit 1; }

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Pull Docker sandbox image if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Pulling Docker sandbox image..."
    docker pull python:3.11-slim || echo "⚠️  Failed to pull Docker image"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/plots data/datasets logs notebooks

# Create sample dataset
echo "📈 Creating sample marketing KPI dataset..."
cat > data/datasets/sample_kpis.csv << 'EOF'
date,brand,revenue,engagement,conversion,spend
2024-01-01,Nike,125000,0.045,0.023,15000
2024-01-02,Nike,132000,0.048,0.025,15500
2024-01-03,Nike,128000,0.044,0.022,15200
2024-01-01,Adidas,98000,0.042,0.021,12000
2024-01-02,Adidas,102000,0.043,0.022,12300
2024-01-03,Adidas,105000,0.046,0.024,12500
2024-01-01,Puma,75000,0.041,0.020,9000
2024-01-02,Puma,78000,0.042,0.021,9200
2024-01-03,Puma,77000,0.040,0.019,9100
EOF

# Create sample notebook
echo "📓 Creating sample analysis notebook..."
cat > notebooks/marketing_kpi_analysis.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Marketing KPI Analysis Template\n",
    "Use this notebook to analyze marketing performance metrics"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "\n",
    "# Load sample data\n",
    "df = pd.read_csv('../data/datasets/sample_kpis.csv')\n",
    "df['date'] = pd.to_datetime(df['date'])\n",
    "df.head()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Calculate ROI\n",
    "df['roi'] = (df['revenue'] - df['spend']) / df['spend'] * 100\n",
    "\n",
    "# Plot ROI by brand\n",
    "plt.figure(figsize=(10, 6))\n",
    "for brand in df['brand'].unique():\n",
    "    brand_data = df[df['brand'] == brand]\n",
    "    plt.plot(brand_data['date'], brand_data['roi'], marker='o', label=brand)\n",
    "\n",
    "plt.title('ROI by Brand Over Time')\n",
    "plt.xlabel('Date')\n",
    "plt.ylabel('ROI (%)')\n",
    "plt.legend()\n",
    "plt.grid(True)\n",
    "plt.show()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  cd $(pwd)"
echo "  source venv/bin/activate"
echo "  python src/financial_server.py"
echo ""
echo "Server will be available at: http://localhost:8002"
echo "MCP endpoint: http://localhost:8002/mcp"
echo ""
echo "Try the sample notebook:"
echo "  jupyter notebook notebooks/marketing_kpi_analysis.ipynb"