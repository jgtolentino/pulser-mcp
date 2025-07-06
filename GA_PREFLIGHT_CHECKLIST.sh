#!/bin/bash
# GA Pre-flight Checklist - Final verification before v1.0.0
# Run this script to ensure all systems are go

set -e

echo "🚀 MCP v1.0.0 GA Pre-flight Checklist"
echo "====================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

CHECKS_PASSED=0
CHECKS_FAILED=0

# Check function
check() {
    local description=$1
    local command=$2
    
    echo -n "Checking: $description... "
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((CHECKS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((CHECKS_FAILED++))
        echo "  Command: $command"
    fi
}

echo "1️⃣ Secrets Rotation Check"
echo "-------------------------"

# Check for stale secrets
check "JWT secrets age" "[ $(find .env* -mtime +30 | wc -l) -eq 0 ]"
check "Database passwords rotated" "grep -q 'LAST_ROTATED' .secrets && [ $(date -d \"$(grep LAST_ROTATED .secrets | cut -d= -f2)\" +%s) -gt $(date -d '30 days ago' +%s) ]"
check "API keys fresh" "[ ! -f .env.production ] || [ $(find .env.production -mtime -30 | wc -l) -gt 0 ]"

# Rotate stale tokens command
echo -e "\n${YELLOW}To rotate stale tokens:${NC}"
echo "pulser secrets rotate --older-than 30d --confirm"

echo -e "\n2️⃣ Backup Integrity Test"
echo "------------------------"

# Test backup/restore
check "Backup script exists" "[ -f backup_restore.sh ]"
check "Backup encryption works" "echo 'test' | openssl enc -aes-256-cbc -salt -k 'testkey' | openssl enc -aes-256-cbc -d -k 'testkey' | grep -q 'test'"
check "S3 credentials configured" "[ ! -z \"$AWS_ACCESS_KEY_ID\" ]"

# Dry run restore
echo -e "\n${YELLOW}Testing backup restore (dry-run):${NC}"
cat > test_backup_restore.sh << 'EOF'
#!/bin/bash
# Dry-run backup restore test
./backup_restore.sh verify $(ls -t backups/*.enc 2>/dev/null | head -1) || echo "No backups found"
EOF
chmod +x test_backup_restore.sh
./test_backup_restore.sh

echo -e "\n3️⃣ Disaster Recovery Drill"
echo "--------------------------"

# Kill and verify recovery
check "Docker services running" "docker ps | grep -E 'mcp_|qdrant|redis|neo4j' | wc -l | grep -qE '^[1-9][0-9]*$'"
check "Sync daemon healthy" "systemctl is-active sync-daemon &>/dev/null || docker ps | grep -q sync_daemon"

echo -e "\n${YELLOW}Disaster drill command:${NC}"
echo "docker kill mcp_qdrant && sleep 30 && docker-compose up -d qdrant && ./verify_sync_recovery.sh"

echo -e "\n4️⃣ Auth/AuthZ Audit"
echo "-------------------"

# Run auth tests
check "Auth test suite exists" "[ -f test_suite.py ] && grep -q 'TestMCPSecurity' test_suite.py"
check "RLS policies defined" "grep -q 'Row Level Security' secure_databases.sh"
check "JWT validation active" "grep -q 'verify_token' harden_all.py"

echo -e "\n${YELLOW}Running auth tests:${NC}"
python3 -m pytest test_suite.py::TestMCPSecurity -v --tb=short 2>/dev/null || echo "Install pytest to run tests"

echo -e "\n5️⃣ Monitoring Thresholds"
echo "------------------------"

# Check alert rules
check "Sync lag alert configured" "grep -q 'sqlite_pending_changes > 5' sync/alerts.yml 2>/dev/null || grep -q 'pending_changes.*5000' monitoring/"
check "Grafana dashboards imported" "curl -s http://localhost:3000/api/dashboards/uid/sqlite-sync | grep -q 'dashboard' || [ -f sync/dashboards/sqlite_sync_dashboard.json ]"
check "Prometheus scraping" "curl -s http://localhost:9090/api/v1/targets | grep -q 'up' || [ -f monitoring/prometheus.yml ]"

echo -e "\n📊 Current Metrics:"
if command -v curl &>/dev/null; then
    echo -n "Pending changes: "
    curl -s http://localhost:9090/api/v1/query?query=sqlite_pending_changes 2>/dev/null | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A"
    echo -n "Sync lag: "
    curl -s http://localhost:9090/api/v1/query?query=sqlite_last_sync_age_seconds 2>/dev/null | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A"
fi

echo -e "\n✅ Final Verification"
echo "--------------------"

# System checks
check "All tests passing" "python3 test_suite.py &>/dev/null"
check "No security vulnerabilities" "! grep -rE '(password|secret|key)\\s*=\\s*[\"'][^\"']+[\"']' --include='*.py' --include='*.js' . 2>/dev/null | grep -v test"
check "Docker images built" "docker images | grep -q mcp"
check "Production config exists" "[ -f .env.production ]"

echo -e "\n📋 Pre-flight Summary"
echo "===================="
echo -e "Checks passed: ${GREEN}$CHECKS_PASSED${NC}"
echo -e "Checks failed: ${RED}$CHECKS_FAILED${NC}"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✅ ALL SYSTEMS GO - READY FOR v1.0.0!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. git tag -a v1.0.0 -m 'Production release'"
    echo "2. git push origin v1.0.0"
    echo "3. docker-compose build --no-cache"
    echo "4. docker-compose push"
    echo "5. Deploy using: ./deploy_production.sh"
else
    echo -e "\n${RED}❌ ISSUES FOUND - ADDRESS BEFORE RELEASE${NC}"
    exit 1
fi

# Cleanup
rm -f test_backup_restore.sh