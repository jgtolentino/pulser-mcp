#!/bin/bash

# Complete MCP Server - One-Click Installation
# This script sets up everything needed for the MCP server

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="/Users/tbwa/Documents/GitHub/mcp-complete-setup"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Banner
echo "================================================================"
echo "🚀 COMPLETE MCP SERVER - ONE-CLICK INSTALLATION"
echo "================================================================"
echo "This will:"
echo "✅ Install all dependencies"
echo "✅ Set up the MCP server and CORS proxy"
echo "✅ Configure for Claude Web App"
echo "✅ Run comprehensive tests"
echo "✅ Integrate with existing MCP setup"
echo "================================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    log_error "Please run this script from the mcp-complete-setup directory"
    exit 1
fi

log_step "Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

NODE_VER=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VER" -lt "18" ]; then
    log_error "Node.js version $NODE_VER is too old. Need version 18 or newer."
    exit 1
fi

log_info "Node.js $(node -v) ✓"

# Check npm
if ! command -v npm &> /dev/null; then
    log_error "npm is not installed"
    exit 1
fi

log_info "npm $(npm -v) ✓"

log_step "Installing dependencies..."

# Install dependencies
if ! npm install; then
    log_error "Failed to install dependencies"
    exit 1
fi

log_info "Dependencies installed ✓"

log_step "Setting up permissions..."

# Make scripts executable
chmod +x scripts/*.sh
chmod +x setup.sh

log_info "Permissions set ✓"

log_step "Creating environment configuration..."

# Copy environment example if .env doesn't exist
if [ ! -f ".env" ]; then
    cp config/.env.example .env
    log_info "Environment file created ✓"
else
    log_info "Environment file already exists ✓"
fi

log_step "Starting servers..."

# Start the servers
./scripts/start.sh

log_step "Running tests..."

# Give servers time to start
sleep 5

# Run tests
if npm test; then
    log_info "All tests passed ✓"
else
    log_warn "Some tests failed, but server is running"
fi

log_step "Integrating with existing MCP setup..."

# Run integration
node scripts/integrate-existing.js

echo ""
echo "================================================================"
echo "🎉 INSTALLATION COMPLETE!"
echo "================================================================"
echo "📍 Servers running:"
echo "   Main MCP Server: http://localhost:8000"
echo "   CORS Proxy: http://localhost:8001"
echo ""
echo "🌐 Claude Web App Configuration:"
echo "   1. Go to Claude Settings → Integrations"
echo "   2. Add New Integration:"
echo "      - Name: Complete MCP Server"
echo "      - URL: http://localhost:8000 (or http://localhost:8001 for CORS)"
echo "      - Type: HTTP"
echo ""
echo "🔧 Management Commands:"
echo "   Start: ./scripts/start.sh"
echo "   Stop: ./scripts/stop.sh"
echo "   Status: ./scripts/status.sh"
echo "   Test: npm test"
echo ""
echo "📚 Documentation: See README.md"
echo "📋 Configuration: config/claude-webapp-config.json"
echo "================================================================"

# Final health check
log_step "Final health check..."

if curl -s http://localhost:8000/health > /dev/null; then
    log_info "Main server is healthy ✓"
else
    log_warn "Main server health check failed"
fi

if curl -s http://localhost:8001/health > /dev/null; then
    log_info "CORS proxy is healthy ✓"
else
    log_warn "CORS proxy health check failed"
fi

echo ""
echo "🎯 Ready to use with Claude Web App!"
echo "📄 Check logs: tail -f logs/*.log"
echo "🛑 Stop anytime: ./scripts/stop.sh"
