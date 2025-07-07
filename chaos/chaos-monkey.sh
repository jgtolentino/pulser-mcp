#!/bin/bash
# Chaos Monkey for Pulser MCP
# Simulates failures to test resilience and alerting

set -e

# Configuration
CHAOS_MODE=${1:-"random"}  # random, network, service, database
DURATION=${2:-"60"}        # Duration in seconds
LOG_FILE="/var/log/pulser-chaos.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] CHAOS: $1" | tee -a "$LOG_FILE"
}

# Ensure we're running with proper permissions
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root for chaos testing"
    exit 1
fi

log "Starting Chaos Monkey - Mode: $CHAOS_MODE, Duration: ${DURATION}s"

# Function to kill random MCP service
chaos_kill_service() {
    SERVICES=(
        "scout_local_mcp"
        "creative_rag_mcp"
        "financial_analyst_mcp"
        "voice_agent_mcp"
        "unified_mcp"
        "shared_memory_mcp"
    )
    
    SERVICE=${SERVICES[$RANDOM % ${#SERVICES[@]}]}
    log "Killing service: $SERVICE"
    
    docker stop $SERVICE 2>/dev/null || true
    sleep $DURATION
    
    log "Restarting service: $SERVICE"
    docker start $SERVICE
}

# Function to simulate network partition
chaos_network_partition() {
    log "Creating network partition between services"
    
    # Block traffic between random services
    iptables -I DOCKER-USER -s 172.20.0.0/16 -d 172.20.0.0/16 -j DROP
    
    sleep $DURATION
    
    log "Removing network partition"
    iptables -D DOCKER-USER -s 172.20.0.0/16 -d 172.20.0.0/16 -j DROP
}

# Function to exhaust resources
chaos_resource_exhaustion() {
    log "Simulating resource exhaustion"
    
    # CPU stress
    docker run -d --name chaos-cpu --rm alpine/stress:latest \
        --cpu 8 --timeout ${DURATION}s
    
    # Memory stress (be careful!)
    docker run -d --name chaos-memory --rm alpine/stress:latest \
        --vm 2 --vm-bytes 512M --timeout ${DURATION}s
    
    sleep $DURATION
    
    # Cleanup
    docker stop chaos-cpu chaos-memory 2>/dev/null || true
}

# Function to corrupt database (safely)
chaos_database_failure() {
    log "Simulating database issues"
    
    # Pause Redis (simulates connection issues)
    docker pause redis
    
    sleep $((DURATION / 2))
    
    log "Resuming Redis"
    docker unpause redis
    
    # Restart Neo4j (simulates crash)
    log "Restarting Neo4j"
    docker restart neo4j
}

# Function to kill SSE bridge
chaos_sse_bridge() {
    log "Stopping SSE bridge"
    
    systemctl stop pulser-mcp-bridge
    
    sleep $DURATION
    
    log "Starting SSE bridge"
    systemctl start pulser-mcp-bridge
}

# Function to simulate disk pressure
chaos_disk_pressure() {
    log "Creating disk pressure"
    
    # Create large file
    dd if=/dev/zero of=/tmp/chaos-disk bs=1M count=1000 2>/dev/null
    
    sleep $DURATION
    
    log "Removing disk pressure"
    rm -f /tmp/chaos-disk
}

# Function to drop random API calls
chaos_api_failures() {
    log "Injecting API failures with iptables"
    
    # Drop 50% of packets to API port
    iptables -I INPUT -p tcp --dport 8000 -m statistic --mode random --probability 0.5 -j DROP
    
    sleep $DURATION
    
    log "Removing API failure injection"
    iptables -D INPUT -p tcp --dport 8000 -m statistic --mode random --probability 0.5 -j DROP
}

# Main chaos selection
case $CHAOS_MODE in
    "random")
        # Pick a random chaos function
        CHAOS_FUNCS=(
            "chaos_kill_service"
            "chaos_network_partition"
            "chaos_resource_exhaustion"
            "chaos_database_failure"
            "chaos_sse_bridge"
            "chaos_disk_pressure"
            "chaos_api_failures"
        )
        SELECTED=${CHAOS_FUNCS[$RANDOM % ${#CHAOS_FUNCS[@]}]}
        log "Random selection: $SELECTED"
        $SELECTED
        ;;
    "network")
        chaos_network_partition
        ;;
    "service")
        chaos_kill_service
        ;;
    "database")
        chaos_database_failure
        ;;
    "resource")
        chaos_resource_exhaustion
        ;;
    "sse")
        chaos_sse_bridge
        ;;
    "disk")
        chaos_disk_pressure
        ;;
    "api")
        chaos_api_failures
        ;;
    *)
        echo "Unknown chaos mode: $CHAOS_MODE"
        echo "Available modes: random, network, service, database, resource, sse, disk, api"
        exit 1
        ;;
esac

log "Chaos test completed"

# Verify system recovery
sleep 10
log "Checking system health post-chaos..."

if curl -f https://pulser-ai.com/health > /dev/null 2>&1; then
    log "✅ System recovered successfully"
else
    log "❌ System did not recover - manual intervention may be required"
    exit 1
fi