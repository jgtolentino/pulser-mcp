#!/bin/bash
# Production Readiness Validation Script
# Validates all security and operational requirements are met

set -e

echo "🔍 MCP Production Readiness Validator"
echo "===================================="
echo "Validating all production requirements..."
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Validation function
validate() {
    local description=$1
    local command=$2
    local required=${3:-true}
    
    echo -n "Checking: $description... "
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗ FAILED${NC}"
            ((FAILED++))
        else
            echo -e "${YELLOW}⚠ WARNING${NC}"
            ((WARNINGS++))
        fi
    fi
}

echo "1️⃣ Security Requirements"
echo "------------------------"

# JWT Authentication
validate "JWT authentication implementation" "grep -q 'HTTPBearer' harden_all.py"
validate "Secret key generation" "grep -q 'secrets.token_urlsafe' harden_all.py"
validate "Token verification" "grep -q 'verify_token' harden_all.py"

# Network Security
validate "TLS configuration script" "[ -f network_security.sh ]"
validate "Firewall rules" "grep -q 'ufw allow' network_security.sh"
validate "Certificate automation" "grep -q 'certbot' network_security.sh"
validate "Nginx reverse proxy config" "grep -q 'ssl_protocols TLSv1.2 TLSv1.3' network_security.sh"

# Database Security
validate "Database security script" "[ -f secure_databases.sh ]"
validate "Redis password generation" "grep -q 'REDIS_PASSWORD=' secure_databases.sh"
validate "Neo4j password generation" "grep -q 'NEO4J_PASSWORD=' secure_databases.sh"
validate "ACL configuration" "grep -q 'redis_users.acl' secure_databases.sh"

echo ""
echo "2️⃣ Monitoring & Logging"
echo "----------------------"

# Centralized Logging
validate "Logging setup script" "[ -f logging_setup.sh ]"
validate "Loki configuration" "grep -q 'loki-config.yaml' logging_setup.sh"
validate "Prometheus configuration" "grep -q 'prometheus.yml' logging_setup.sh"
validate "Grafana dashboards" "grep -q 'mcp-overview.json' logging_setup.sh"
validate "Log rotation" "grep -q 'RotatingFileHandler' logging_setup.sh"

echo ""
echo "3️⃣ Testing & Quality"
echo "-------------------"

# Test Suite
validate "Comprehensive test suite" "[ -f test_suite.py ]"
validate "Security tests" "grep -q 'TestMCPSecurity' test_suite.py"
validate "Performance tests" "grep -q 'TestMCPPerformance' test_suite.py"
validate "Integration tests" "grep -q 'TestMCPFunctionality' test_suite.py"
validate "Load testing configuration" "[ -f load_tests.py ]"
validate "Locust scenarios" "grep -q 'class MCPUser' load_tests.py"

echo ""
echo "4️⃣ CI/CD & Automation"
echo "--------------------"

# CI/CD Pipeline
validate "GitHub Actions workflow" "[ -f .github/workflows/mcp-ci-cd.yml ]"
validate "Security scanning" "grep -q 'trivy' .github/workflows/mcp-ci-cd.yml"
validate "Automated testing" "grep -q 'pytest' .github/workflows/mcp-ci-cd.yml"
validate "Docker image building" "grep -q 'docker/build-push-action' .github/workflows/mcp-ci-cd.yml"
validate "Staging deployment" "grep -q 'deploy-staging' .github/workflows/mcp-ci-cd.yml"

echo ""
echo "5️⃣ Infrastructure"
echo "----------------"

# Docker Configuration
validate "Docker Compose with limits" "[ -f docker-compose.yml ]"
validate "CPU limits" "grep -q 'cpus:' docker-compose.yml"
validate "Memory limits" "grep -q 'memory:' docker-compose.yml"
validate "Health checks" "grep -q 'healthcheck:' docker-compose.yml"
validate "Dockerfile template" "[ -f Dockerfile.template ]"
validate "Non-root user" "grep -q 'USER mcp' Dockerfile.template"

echo ""
echo "6️⃣ Backup & Recovery"
echo "-------------------"

# Backup System
validate "Backup script" "[ -f backup_restore.sh ]"
validate "Encryption support" "grep -q 'openssl enc' backup_restore.sh"
validate "S3 upload capability" "grep -q 'aws s3 cp' backup_restore.sh"
validate "Restore functionality" "grep -q 'restore_backup()' backup_restore.sh"
validate "Backup verification" "grep -q 'verify_backup()' backup_restore.sh"

echo ""
echo "7️⃣ API Standards"
echo "----------------"

# API Versioning
validate "API versioning implementation" "grep -q 'add_api_versioning' harden_all.py"
validate "Version prefix /api/v1" "grep -q '/api/v1' harden_all.py"
validate "Router configuration" "grep -q 'APIRouter' harden_all.py"

echo ""
echo "8️⃣ Documentation"
echo "----------------"

# Documentation
validate "Third-party licenses" "[ -f THIRD_PARTY_LICENSES.md ]"
validate "License compliance" "grep -q 'License Compliance' THIRD_PARTY_LICENSES.md"
validate "Production checklist" "[ -f PRODUCTION_READY_CHECKLIST.md ]"
validate "Bootstrap documentation" "grep -q 'Usage' pulser_bootstrap.py"

echo ""
echo "9️⃣ Environment Configuration"
echo "---------------------------"

# Environment Setup
validate "Production environment template" "[ -f .env.production ]"
validate "JWT secret configured" "grep -q 'PULSER_JWT_SECRET=' .env.production || [ -f .env.production ]"
validate "Database passwords configured" "grep -q 'REDIS_PASSWORD=' .env.production || [ -f .env.production ]"
validate "Resource limits configured" "grep -q 'MAX_WORKERS=' .env.production || [ -f .env.production ]"

echo ""
echo "🔟 Operational Scripts"
echo "--------------------"

# Utility Scripts
validate "Security audit script" "grep -q 'security_audit.sh' network_security.sh"
validate "Certificate check script" "grep -q 'check_certs.sh' network_security.sh"
validate "Log viewer script" "grep -q 'view_logs.sh' logging_setup.sh"
validate "Database monitor script" "[ -f monitor_db_security.sh ] || grep -q 'monitor_db_security.sh' secure_databases.sh"

echo ""
echo "📊 Validation Summary"
echo "===================="
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL PRODUCTION REQUIREMENTS MET!${NC}"
    echo ""
    echo "The MCP Ecosystem is ready for production deployment."
    echo ""
    echo "Next steps:"
    echo "1. Review and update passwords in .env.production"
    echo "2. Configure your domain and SSL certificates"
    echo "3. Set up monitoring alerts in Grafana"
    echo "4. Schedule automated backups"
    echo "5. Run final security audit"
    echo ""
    exit 0
else
    echo -e "${RED}❌ PRODUCTION REQUIREMENTS NOT MET${NC}"
    echo ""
    echo "Please address the failed checks before deploying to production."
    echo ""
    exit 1
fi