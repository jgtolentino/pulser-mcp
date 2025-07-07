# 🚨 Pulser MCP Incident Response Runbook

**Last Updated**: 2024-01-07 | **Version**: 1.0.0 | **Status**: ACTIVE

## 📋 Quick Reference

| Alert | Severity | Response Time | Escalation |
|-------|----------|---------------|------------|
| All services down | P1 | < 5 min | Immediate |
| SSE endpoint failure | P1 | < 10 min | After 15 min |
| Sync lag > 5 min | P2 | < 30 min | After 1 hour |
| Single service down | P3 | < 1 hour | After 2 hours |
| High error rate (>5%) | P2 | < 30 min | After 1 hour |

## 🔥 P1: Complete Outage Response

### Symptoms
- `mcp_health` returns connection error
- All Claude prompts fail with "MCP unavailable"
- Multiple services show as DOWN

### Immediate Actions (< 5 minutes)

1. **Verify the outage**
   ```bash
   curl -f https://pulser-ai.com/health || echo "CONFIRMED: Endpoint down"
   ssh prod-server "docker ps | grep mcp"
   ```

2. **Check infrastructure**
   ```bash
   # Is the server reachable?
   ping pulser-ai.com
   
   # Is nginx running?
   ssh prod-server "systemctl status nginx"
   
   # Are containers running?
   ssh prod-server "docker-compose ps"
   ```

3. **Quick recovery attempt**
   ```bash
   ssh prod-server "cd /opt/pulser-mcp && docker-compose restart"
   ```

### If Quick Recovery Fails

4. **Full restart sequence**
   ```bash
   ssh prod-server
   cd /opt/pulser-mcp
   
   # Stop everything
   docker-compose down
   
   # Clear any locks
   rm -f data/*.lock
   
   # Start databases first
   docker-compose up -d redis neo4j
   sleep 30
   
   # Start MCP services
   docker-compose up -d
   
   # Verify
   docker-compose ps
   curl http://localhost:8000/health
   ```

5. **Escalate if still down**
   - Page on-call lead: @tech-lead
   - Open P1 incident channel
   - Begin 15-minute status updates

## 🔄 P2: Sync Lag > 5 Minutes

### Symptoms
- Grafana shows sync_lag > 300 seconds
- `sync_status` endpoint shows growing queue
- Data inconsistencies reported

### Response Steps

1. **Check sync daemon status**
   ```bash
   ssh edge-device "systemctl status sync-daemon"
   ssh edge-device "journalctl -u sync-daemon -n 100"
   ```

2. **Identify bottleneck**
   ```bash
   # Check Supabase status
   curl https://status.supabase.com/api/v2/status.json
   
   # Check local SQLite
   ssh edge-device "du -h /var/lib/mcp/*.db"
   ssh edge-device "sqlite3 /var/lib/mcp/scout.db 'PRAGMA integrity_check;'"
   
   # Check network
   ssh edge-device "mtr -n -c 10 supabase.co"
   ```

3. **Manual sync trigger**
   ```bash
   # Force sync for specific service
   ssh edge-device "cd /opt/mcp && ./sync_manager.py --force --service scout_local"
   
   # If queue is huge, clear and resync
   ssh edge-device "cd /opt/mcp && ./sync_manager.py --clear-queue --resync"
   ```

4. **Monitor recovery**
   - Watch Grafana sync_lag metric
   - Verify with: `curl https://pulser-ai.com/mcp/sync-status`
   - Check for data consistency

## 🔥 P2: High Error Rate (>5%)

### Symptoms
- Grafana shows error_rate > 0.05
- Clients reporting intermittent failures
- Logs show 4xx/5xx responses

### Investigation

1. **Identify error patterns**
   ```bash
   # Check nginx logs
   ssh prod-server "tail -n 1000 /var/log/nginx/pulser-ai.com.error.log | grep -E '(500|502|503|504)'"
   
   # Check service logs
   ssh prod-server "docker-compose logs --tail=500 | grep ERROR"
   
   # Find failing endpoint
   ssh prod-server "awk '{print $7}' /var/log/nginx/pulser-ai.com.access.log | sort | uniq -c | sort -rn | head"
   ```

2. **Common causes & fixes**

   **JWT Token Expiry**
   ```bash
   # Regenerate tokens
   ssh prod-server "cd /opt/pulser-mcp && ./rotate_secrets.sh"
   docker-compose restart
   ```

   **Memory/CPU exhaustion**
   ```bash
   # Check resources
   ssh prod-server "docker stats --no-stream"
   
   # Restart problematic container
   docker-compose restart <service_name>
   ```

   **Database connection pool**
   ```bash
   # Reset connections
   docker-compose restart shared_memory_mcp
   ```

## 🟡 P3: Single Service Down

### Symptoms
- One MCP service unhealthy
- Other services operating normally
- Specific functionality unavailable

### Service-Specific Recovery

#### Scout Local MCP (Port 8000)
```bash
docker-compose restart scout_local_mcp
# Check for SQLite corruption
docker exec scout_local_mcp sqlite3 /data/scout.db 'PRAGMA integrity_check;'
```

#### Creative RAG MCP (Port 8001)
```bash
# Restart Qdrant if needed
docker-compose restart qdrant creative_rag_mcp
# Verify vector DB
curl http://localhost:6333/collections
```

#### Financial Analyst MCP (Port 8002)
```bash
docker-compose restart financial_analyst_mcp
# Check Prophet model files
docker exec financial_analyst_mcp ls -la /models/
```

#### Shared Memory MCP (Port 5700)
```bash
# This is critical - affects all services
docker-compose restart redis neo4j shared_memory_mcp
# Verify connections
docker exec redis redis-cli ping
docker exec neo4j cypher-shell "MATCH (n) RETURN count(n) LIMIT 1;"
```

## 📊 Monitoring Commands

### Real-time Health Check
```bash
watch -n 5 'curl -s https://pulser-ai.com/health | jq .'
```

### Service Status Dashboard
```bash
#!/bin/bash
clear
echo "=== Pulser MCP Status Board ==="
echo "Time: $(date)"
echo ""
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009 5700; do
  if curl -s -f http://localhost:$port/health > /dev/null; then
    echo "✅ Port $port: UP"
  else
    echo "❌ Port $port: DOWN"
  fi
done
```

### Log Aggregation
```bash
# All errors in last hour
docker-compose logs --since 1h | grep -E "(ERROR|CRITICAL|FATAL)"

# Specific service debug
docker-compose logs -f scout_local_mcp
```

## 🔐 Emergency Procedures

### Complete Data Recovery
```bash
# 1. Stop all services
docker-compose down

# 2. Restore from backup
./backup_restore.sh restore /backups/latest-encrypted.tar.gz

# 3. Restart services
docker-compose up -d

# 4. Force full resync
for device in $(cat devices.txt); do
  ssh $device "cd /opt/mcp && ./sync_manager.py --full-resync"
done
```

### Emergency Rollback
```bash
# If new deployment causes issues
cd /opt/pulser-mcp
git checkout v1.0.0  # Last stable version
docker-compose pull
docker-compose up -d
```

### SSL Certificate Emergency
```bash
# If cert expires
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

## 📞 Escalation Matrix

| Time | Action | Contact |
|------|--------|---------|
| 0 min | Initial response | On-call engineer |
| 15 min | No resolution | Tech lead + Product owner |
| 30 min | P1 ongoing | Engineering manager |
| 60 min | Major outage | CTO + Customer success |

## 📝 Post-Incident

After resolution:
1. Update incident ticket with timeline
2. Collect logs: `./collect_incident_logs.sh <incident_id>`
3. Schedule post-mortem within 48 hours
4. Update this runbook with learnings

## 🛠️ Useful Tools

```bash
# MCP health check script
alias mcp-health='curl -s https://pulser-ai.com/health | jq .'

# Quick service restart
alias mcp-restart='cd /opt/pulser-mcp && docker-compose restart'

# Tail all logs
alias mcp-logs='docker-compose logs -f --tail=100'

# Sync status check
alias mcp-sync='curl -s https://pulser-ai.com/mcp/sync-status | jq .'
```

---

**Remember**: Stay calm, follow the runbook, and communicate frequently. You've got this! 💪