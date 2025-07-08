#!/bin/bash

# Desktop Application Build Script

set -e

echo "🏗️  Building MCP Complete Desktop Application..."

# Configuration
BUILD_DIR="deployment/desktop-dxt"
DIST_DIR="$BUILD_DIR/dist"

# Ensure we're in the right directory
cd "$(dirname "$0")/../.."

# Check if desktop build directory exists
if [ ! -d "$BUILD_DIR" ]; then
    echo "❌ Desktop build directory not found: $BUILD_DIR"
    exit 1
fi

cd "$BUILD_DIR"

echo "📦 Installing desktop dependencies..."
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "Dependencies already installed"
fi

echo "🧹 Cleaning previous builds..."
rm -rf dist/

echo "📋 Preparing build..."

# Create necessary directories
mkdir -p server/src
mkdir -p server/scripts
mkdir -p server/config

# Copy server files
echo "📁 Copying server files..."
cp -r ../../src/* server/src/
cp -r ../../scripts/* server/scripts/
cp -r ../../config/* server/config/
cp ../../package.json server/

# Update server package.json for desktop
echo "⚙️  Updating server configuration for desktop..."
cat > server/package.json << EOF
{
  "name": "mcp-server-embedded",
  "version": "1.0.0",
  "main": "src/server.js",
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "sqlite3": "^5.1.6",
    "ws": "^8.13.0",
    "winston": "^3.10.0",
    "compression": "^1.7.4",
    "helmet": "^7.0.0"
  }
}
EOF

echo "🔧 Building application..."

# Build for current platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Building for macOS..."
    npm run build-mac
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Building for Linux..."
    npm run build-linux
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "🪟 Building for Windows..."
    npm run build-win
else
    echo "🌍 Building for all platforms..."
    npm run build
fi

echo "✅ Build completed!"

# Show build results
if [ -d "dist" ]; then
    echo ""
    echo "📦 Build artifacts:"
    ls -la dist/
    echo ""
    echo "📍 Build location: $(pwd)/dist/"
    
    # Calculate sizes
    echo "📊 Package sizes:"
    du -sh dist/* 2>/dev/null || echo "No packages found"
else
    echo "❌ Build failed - no dist directory found"
    exit 1
fi

echo ""
echo "🎉 Desktop application build completed successfully!"
echo ""
echo "📱 Installation:"
echo "   macOS: Open the .dmg file and drag to Applications"
echo "   Windows: Run the .exe installer"
echo "   Linux: Install the .deb package or run the AppImage"
echo ""
echo "🚀 The desktop app includes:"
echo "   ✅ MCP Server with SQLite database"
echo "   ✅ CORS Proxy for browser access"
echo "   ✅ System tray integration"
echo "   ✅ Auto-start capability"
echo "   ✅ Settings management"
echo "   ✅ Real-time monitoring"
