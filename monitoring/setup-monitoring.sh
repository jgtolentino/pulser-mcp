#!/bin/bash
# Setup monitoring for Pulser MCP Remote Bridge

set -e

echo "🔍 Setting up Pulser MCP monitoring..."

# 1. Install health monitor
echo "📦 Installing health monitor..."
sudo mkdir -p /opt/pulser-mcp-monitoring
sudo cp health-monitor.py /opt/pulser-mcp-monitoring/
sudo pip3 install aiohttp

# 2. Create monitoring user
echo "👤 Creating monitoring user..."
sudo useradd -r -s /bin/false monitoring || true
sudo touch /var/log/pulser-mcp-health.log
sudo chown monitoring:monitoring /var/log/pulser-mcp-health.log

# 3. Install systemd service
echo "⚙️  Installing systemd service..."
sudo cp mcp-health-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-health-monitor.service

# 4. Configure log rotation
echo "📝 Configuring log rotation..."
sudo tee /etc/logrotate.d/pulser-mcp-health > /dev/null << 'EOF'
/var/log/pulser-mcp-health.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 monitoring monitoring
}
EOF

# 5. Import Grafana dashboard
echo "📊 Importing Grafana dashboard..."
if command -v curl &> /dev/null && [ -n "$GRAFANA_API_KEY" ]; then
    curl -X POST http://localhost:3000/api/dashboards/import \
        -H "Authorization: Bearer $GRAFANA_API_KEY" \
        -H "Content-Type: application/json" \
        -d @grafana-dashboard.json
else
    echo "⚠️  Grafana API key not set. Import dashboard manually."
fi

# 6. Start monitoring
echo "🚀 Starting health monitor..."
sudo systemctl start mcp-health-monitor

# 7. Verify setup
echo "✅ Verifying setup..."
sleep 5

if systemctl is-active --quiet mcp-health-monitor; then
    echo "✅ Health monitor is running"
    echo "📝 View logs: sudo journalctl -u mcp-health-monitor -f"
else
    echo "❌ Health monitor failed to start"
    sudo journalctl -u mcp-health-monitor -n 20
fi

echo "
🎉 Monitoring setup complete!

Commands:
- View monitor logs: sudo journalctl -u mcp-health-monitor -f
- Check monitor status: sudo systemctl status mcp-health-monitor
- View health log: sudo tail -f /var/log/pulser-mcp-health.log
- Import Grafana dashboard: grafana-dashboard.json

Configure alerts by setting ALERT_WEBHOOK in:
/etc/systemd/system/mcp-health-monitor.service
"