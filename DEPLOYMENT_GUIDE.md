# MCP Server Deployment Guide

## 🚀 Quick Start - Choose Your Path

### Option 1: Cloud Deployment (Recommended for Claude Web App)

#### Deploy to Render (Free Tier)
```bash
# 1. Push to GitHub
git add .
git commit -m "Deploy MCP server"
git push origin main

# 2. Go to render.com
# 3. New > Web Service > Connect GitHub repo
# 4. Use existing render.yaml configuration
# 5. Deploy!

# Your URL will be: https://mcp-cloud-server.onrender.com
```

#### Deploy to Vercel
```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Deploy
cd deployment/cloud
vercel --prod

# Your URL will be: https://mcp-server-xxx.vercel.app
```

### Option 2: Local Development Only

#### For Claude Desktop
```bash
# Just run locally - no ngrok needed!
./scripts/start.sh

# Claude Desktop can access localhost:8000 directly
```

#### For Claude Web App (Testing)
```bash
# Only if you MUST test locally with Claude Web App
./scripts/start-with-ngrok.sh

# Use the ngrok URL in Claude settings
```

## 📋 Decision Matrix

| Your Situation | What You Need | Command |
|----------------|---------------|---------|
| Production use with Claude Web App | Render/Vercel | `git push` → Deploy |
| Team collaboration | Render/Vercel | Share the public URL |
| Local dev with Claude Desktop | Local server only | `./scripts/start.sh` |
| Local testing with Claude Web App | Local + ngrok | `./scripts/start-with-ngrok.sh` |

## 🌐 Claude Web App Configuration

### For Cloud Deployment (Render/Vercel)
```
Name: MCP Server
URL: https://your-mcp.onrender.com
Type: HTTP
Auth: None (or use API key if configured)
```

### For Local Development (Claude Desktop)
```
Name: MCP Server (Local)
URL: http://localhost:8000
Type: HTTP
Auth: None
```

## ✅ No ngrok Needed When:
- ✅ Using Render (automatic HTTPS + CORS)
- ✅ Using Vercel (automatic HTTPS + CORS)
- ✅ Using Claude Desktop with local server
- ✅ Any production deployment

## 🚨 ngrok Only Needed When:
- 🧪 Testing local server with Claude Web App
- 🔧 Debugging cloud-like behavior locally
- 📱 Sharing local dev server temporarily

## 🎯 Best Practice
**Deploy to Render/Vercel for any real usage.** Keep ngrok only as a development convenience tool.