# MCP v1.0.0 Production Deployment Runbook

## 📋 Pre-Deployment Checklist

- [ ] Run GA preflight checks: `./GA_PREFLIGHT_CHECKLIST.sh`
- [ ] Verify all containers built: `docker images | grep mcp`
- [ ] Confirm monitoring stack ready: `docker ps | grep -E 'grafana|loki|prometheus'`
- [ ] Backup current state: `./backup_restore.sh backup`
- [ ] Review security audit: `./network_security.sh audit`

## 🚀 Deployment Steps

### 1. Tag Release
```bash
# Create release tag
git tag -a v1.0.0 -m "Production release: Hybrid MCP with Supabase sync"
git push origin v1.0.0

# Create GitHub release
gh release create v1.0.0 \
  --title "MCP v1.0.0 - Production Release" \
  --notes "First production release with hybrid architecture" \
  --generate-notes
```

### 2. Build & Push Containers
```bash
# Build all images with version tag
docker-compose build --no-cache

# Tag images
for service in scout_local creative_rag financial_analyst voice_agent unified synthetic_data briefvault_rag deep_researcher video_rag audio_analysis shared_memory; do
  docker tag mcp_${service}:latest ghcr.io/insightpulseai/mcp/${service}:v1.0.0
  docker tag mcp_${service}:latest ghcr.io/insightpulseai/mcp/${service}:latest
done

# Push to registry
docker-compose push
```

### 3. Deploy Infrastructure
```bash
# Create network
docker network create mcp_network

# Start databases first
docker-compose up -d redis neo4j

# Wait for databases
sleep 30

# Initialize database security
./secure_databases.sh

# Start monitoring stack
docker-compose up -d loki prometheus grafana

# Import dashboards
curl -X POST http://localhost:3000/api/dashboards/import \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d @sync/dashboards/sqlite_sync_dashboard.json
```

### 4. Deploy MCP Services
```bash
# Deploy services in dependency order
docker-compose up -d shared_memory_mcp
sleep 10

# Deploy remaining services
docker-compose up -d scout_local_mcp creative_rag_mcp financial_analyst_mcp \
  voice_agent_mcp unified_mcp synthetic_data_mcp briefvault_rag_mcp \
  deep_researcher_mcp video_rag_mcp audio_analysis_mcp

# Start nginx last
docker-compose up -d nginx
```

### 5. Initialize Sync
```bash
# Deploy sync daemon on each edge device
for device in $(cat devices.txt); do
  ssh $device "cd /opt/mcp && ./sync/deploy.sh"
done

# Verify sync status
./validate_sync_status.sh
```

### 6. Configure TLS
```bash
# Obtain certificates
sudo certbot certonly --standalone -d mcp.insightpulseai.com

# Configure nginx
sudo cp /etc/letsencrypt/live/mcp.insightpulseai.com/*.pem /etc/mcp/certs/
docker-compose restart nginx
```

### 7. Smoke Tests
```bash
# Health checks
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 5700; do
  curl -f http://localhost:$port/health || echo "Service on port $port unhealthy"
done

# Auth test
TOKEN=$(curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=$MCP_ADMIN_PASS" | jq -r .access_token)

# API test
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/scout/dashboard

# Sync test
sqlite3 test.db "INSERT INTO products VALUES ('TEST-001', 'Test Product', 99.99)"
sleep 20
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/scout/sync-status
```

### 8. Enable Monitoring Alerts
```bash
# Configure alert manager
docker-compose up -d alertmanager

# Test alerts
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {"alertname": "TestAlert", "severity": "info"},
    "annotations": {"summary": "Deployment test alert"}
  }]'
```

## 🔄 Rollback Procedure

If issues arise:

```bash
# 1. Stop new services
docker-compose stop

# 2. Restore previous version
git checkout v0.9.0
docker-compose pull
docker-compose up -d

# 3. Restore data
./backup_restore.sh restore backups/pre_v1.0.0_backup.enc

# 4. Verify rollback
./health_check.sh
```

## 📊 Post-Deployment Verification

### Metrics to Monitor (First 24 Hours)
- [ ] Error rate < 0.1%
- [ ] P95 latency < 200ms  
- [ ] Sync lag < 60s
- [ ] No memory leaks
- [ ] CPU usage stable

### Dashboards to Watch
- http://localhost:3000/d/sqlite-sync - Sync Status
- http://localhost:3000/d/mcp-overview - Service Health
- http://localhost:3000/d/mcp-security - Security Events

### Log Queries
```bash
# Check for errors
docker-compose logs --tail=1000 | grep -i error

# Sync status
journalctl -u sync-daemon -n 100

# Security events
docker logs mcp_nginx 2>&1 | grep -E '(401|403|429)'
```

## 📞 Escalation

### Severity Levels
- **P1** (Critical): All services down, data loss risk
- **P2** (High): Sync failure > 30 min, auth broken
- **P3** (Medium): Single service degraded, high latency
- **P4** (Low): Minor issues, cosmetic bugs

### Contacts
- On-call Engineer: via PagerDuty
- Tech Lead: @tech-lead
- Product Owner: @product-owner

## ✅ Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Release Manager | | | |
| Tech Lead | | | |
| Security | | | |
| Operations | | | |

---

**Version**: 1.0.0  
**Last Updated**: {{current_date}}  
**Status**: READY FOR PRODUCTION 🚀