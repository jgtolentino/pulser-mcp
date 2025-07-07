#!/bin/bash
# Chaos Test Runner with Safety Checks

set -e

# Load configuration
CHAOS_CONFIG="chaos-schedule.yaml"
LOG_DIR="/var/log/pulser-chaos"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL}"

# Create log directory
mkdir -p "$LOG_DIR"

# Logging with timestamps
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/chaos-runner.log"
}

# Send notification
notify() {
    local message="$1"
    local severity="${2:-info}"
    
    log "$message"
    
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"🐵 Chaos Monkey: $message\",
                \"color\": \"$severity\"
            }" 2>/dev/null || true
    fi
}

# Pre-flight checks
run_prechecks() {
    log "Running pre-flight checks..."
    
    # Check if backup exists
    if [ ! -f "/backups/latest-encrypted.tar.gz" ]; then
        log "ERROR: No recent backup found"
        return 1
    fi
    
    # Check for ongoing incidents
    if docker-compose ps | grep -q "Exit"; then
        log "ERROR: Some services are already down"
        return 1
    fi
    
    # Check system load
    load=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}')
    if (( $(echo "$load > 5.0" | bc -l) )); then
        log "ERROR: System load too high: $load"
        return 1
    fi
    
    log "Pre-flight checks passed"
    return 0
}

# Post-chaos validation
validate_recovery() {
    local start_time=$(date +%s)
    local timeout=300  # 5 minutes
    
    log "Validating system recovery..."
    
    while true; do
        if curl -f https://pulser-ai.com/health > /dev/null 2>&1; then
            log "✅ Main health check passed"
            
            # Check all services
            all_healthy=true
            for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 5700; do
                if ! curl -f "http://localhost:$port/health" > /dev/null 2>&1; then
                    log "Service on port $port still unhealthy"
                    all_healthy=false
                fi
            done
            
            if $all_healthy; then
                log "✅ All services recovered"
                return 0
            fi
        fi
        
        # Check timeout
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log "❌ Recovery timeout exceeded"
            return 1
        fi
        
        sleep 10
    done
}

# Main execution
main() {
    local mode="${1:-service}"
    local duration="${2:-60}"
    
    notify "Starting chaos test: mode=$mode, duration=${duration}s" "warning"
    
    # Run pre-checks
    if ! run_prechecks; then
        notify "Pre-flight checks failed - aborting chaos test" "danger"
        exit 1
    fi
    
    # Create test ID
    test_id="chaos-$(date +%Y%m%d-%H%M%S)"
    log "Test ID: $test_id"
    
    # Capture initial state
    docker-compose ps > "$LOG_DIR/$test_id-before.txt"
    curl -s https://pulser-ai.com/mcp/services > "$LOG_DIR/$test_id-services.json"
    
    # Run chaos
    log "Executing chaos monkey..."
    if ./chaos-monkey.sh "$mode" "$duration"; then
        log "Chaos execution completed"
    else
        notify "Chaos execution failed" "danger"
    fi
    
    # Validate recovery
    if validate_recovery; then
        notify "✅ System recovered successfully from chaos test" "good"
        
        # Capture final state
        docker-compose ps > "$LOG_DIR/$test_id-after.txt"
        
        # Generate report
        cat > "$LOG_DIR/$test_id-report.txt" << EOF
Chaos Test Report
================
Test ID: $test_id
Mode: $mode
Duration: $duration seconds
Start: $(date -r $LOG_DIR/$test_id-before.txt)
End: $(date)
Result: SUCCESS

Services Status:
$(docker-compose ps)

Alerts Triggered:
$(grep "ALERT" /var/log/pulser-mcp-health.log | tail -n 10)
EOF
        
    else
        notify "❌ System failed to recover from chaos test!" "danger"
        
        # Attempt manual recovery
        log "Attempting manual recovery..."
        docker-compose restart
        sleep 30
        
        if curl -f https://pulser-ai.com/health > /dev/null 2>&1; then
            notify "⚠️ Manual recovery successful" "warning"
        else
            notify "🚨 MANUAL INTERVENTION REQUIRED - System is DOWN!" "danger"
            exit 1
        fi
    fi
    
    log "Chaos test completed: $test_id"
}

# Handle arguments
case "${1:-help}" in
    "service"|"network"|"database"|"resource"|"sse"|"disk"|"api"|"random")
        main "$1" "${2:-60}"
        ;;
    "schedule")
        # Run scheduled test based on cron
        log "Running scheduled chaos test"
        # Parse schedule from YAML and execute
        ;;
    "scenario")
        # Run specific scenario
        scenario_name="$2"
        log "Running chaos scenario: $scenario_name"
        # Execute scenario steps
        ;;
    *)
        echo "Usage: $0 <mode> [duration]"
        echo "Modes: service, network, database, resource, sse, disk, api, random"
        echo "       schedule - run from schedule"
        echo "       scenario <name> - run named scenario"
        exit 1
        ;;
esac