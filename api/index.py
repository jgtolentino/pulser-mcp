"""
Vercel serverless function handler for MCP Server
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import FastAPI app
from src.main import app

# Create handler for Vercel
handler = app