#!/bin/bash
# Master startup script for all MCP servers
# Generated by Pulser Bootstrap

set -e

echo "🚀 Starting all MCP servers..."

# Function to start server in background
start_server() {
    local server_name=$1
    local script_path=$2
    
    echo "📦 Starting $server_name..."
    nohup ./$script_path > logs/${server_name}.log 2>&1 &
    local pid=$!
    echo "$pid" > "pids/${server_name}.pid"
    echo "   ✅ Started $server_name (PID: $pid)"
}

# Create directories
mkdir -p logs pids

# Start servers in order of priority
start_server "shared_memory_mcp" "start_shared_memory_mcp.sh"
sleep 2
start_server "creative_rag_mcp" "start_creative_rag_mcp.sh"
sleep 2
start_server "voice_agent_mcp" "start_voice_agent_mcp.sh"
sleep 2
start_server "briefvault_rag_mcp" "start_briefvault_rag_mcp.sh"
sleep 2
start_server "scout_local_mcp" "start_scout_local_mcp.sh"
sleep 2
start_server "video_rag_mcp" "start_video_rag_mcp.sh"
sleep 2
start_server "slideforge_mcp" "start_slideforge_mcp.sh"
sleep 1
start_server "unified_mcp" "start_unified_mcp.sh"
sleep 1
start_server "deep_researcher_mcp" "start_deep_researcher_mcp.sh"
sleep 1
start_server "financial_analyst_mcp" "start_financial_analyst_mcp.sh"
sleep 1
start_server "synthetic_data_mcp" "start_synthetic_data_mcp.sh"
sleep 1
start_server "audio_analysis_mcp" "start_audio_analysis_mcp.sh"
sleep 1

echo "⏱️ Waiting for servers to start..."
sleep 10

echo "🏥 Checking server health..."
python pulser_bootstrap.py --health-check

echo "✅ All servers started!"
echo "📊 Check logs/ directory for individual server logs"
echo "🔍 Use 'python pulser_bootstrap.py --status' to check status"
