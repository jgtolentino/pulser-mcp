#!/bin/bash

# Complete MCP Server Setup Script
set -e

echo "🚀 Setting up Complete MCP Server..."

# Configuration
MCP_DIR="$HOME/mcp-complete-server"
PORT=8000
CORS_PORT=8001

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed"
    exit 1
fi

log_info "Node.js $(node -v) found"

# Create directory
if [ -d "$MCP_DIR" ]; then
    log_warn "Backing up existing directory"
    mv "$MCP_DIR" "$MCP_DIR.backup.$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$MCP_DIR"/{src,data,logs,scripts,config,tests}
cd "$MCP_DIR"

log_info "Created project structure at $MCP_DIR"

echo "✅ Setup script created. Run from the main directory to continue."
