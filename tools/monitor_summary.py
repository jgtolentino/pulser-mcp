#!/usr/bin/env python3
"""
Monitor Summary Tool for Pulser MCP
Provides AI-powered monitoring summaries through Remote MCP
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any

class MonitorSummary:
    def __init__(self):
        self.grafana_url = os.getenv('GRAFANA_URL', 'http://localhost:3000')
        self.grafana_key = os.getenv('GRAFANA_API_KEY', '')
        self.pulser_url = os.getenv('PULSER_URL', 'https://gagambi-backend.onrender.com')
        self.jwt_token = self._get_jwt_token()
        
    def _get_jwt_token(self) -> str:
        """Generate or retrieve JWT token for internal auth"""
        import jwt
        secret = os.getenv('PULSER_JWT_SECRET', 'your-secret-jwt-key-change-this-in-production')
        payload = {
            'sub': 'monitor-summary',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, secret, algorithm='HS256')
    
    def fetch_health_status(self) -> Dict[str, Any]:
        """Fetch current health status from all MCP services"""
        try:
            headers = {'Authorization': f'Bearer {self.jwt_token}'}
            response = requests.get(f'{self.pulser_url}/health/all', headers=headers, timeout=10)
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching health status: {e}")
        
        return {'error': 'Unable to fetch health status'}
    
    def fetch_grafana_alerts(self) -> List[Dict]:
        """Fetch active alerts from Grafana"""
        if not self.grafana_key:
            return []
            
        try:
            headers = {'Authorization': f'Bearer {self.grafana_key}'}
            response = requests.get(
                f'{self.grafana_url}/api/alerts',
                headers=headers,
                timeout=10
            )
            if response.ok:
                alerts = response.json()
                # Filter and sort alerts
                active_alerts = [a for a in alerts if a.get('state') != 'ok']
                return sorted(active_alerts, key=lambda x: x.get('newStateDate', ''), reverse=True)[:5]
        except Exception as e:
            print(f"Error fetching Grafana alerts: {e}")
        
        return []
    
    def fetch_sync_status(self) -> Dict[str, Any]:
        """Fetch sync status between local and cloud"""
        try:
            headers = {'Authorization': f'Bearer {self.jwt_token}'}
            response = requests.get(f'{self.pulser_url}/api/v1/sync/status', headers=headers, timeout=10)
            if response.ok:
                return response.json()
        except Exception as e:
            print(f"Error fetching sync status: {e}")
        
        return {'error': 'Unable to fetch sync status'}
    
    def fetch_recent_incidents(self) -> List[Dict]:
        """Fetch recent incidents from logs"""
        # In a real implementation, this would query your incident management system
        # For now, we'll check for recent errors in health checks
        incidents = []
        
        try:
            # Check systemd journal for recent errors
            import subprocess
            result = subprocess.run(
                ['journalctl', '-u', 'pulser-mcp-*', '--since', '1 hour ago', '-p', 'err', '--output', 'json'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split('\n'):
                    try:
                        entry = json.loads(line)
                        incidents.append({
                            'time': entry.get('__REALTIME_TIMESTAMP'),
                            'service': entry.get('UNIT'),
                            'message': entry.get('MESSAGE')
                        })
                    except:
                        pass
        except:
            pass
        
        return incidents[:5]  # Last 5 incidents
    
    def generate_summary(self) -> str:
        """Generate AI-powered summary of monitoring status"""
        # Collect all monitoring data
        health = self.fetch_health_status()
        alerts = self.fetch_grafana_alerts()
        sync = self.fetch_sync_status()
        incidents = self.fetch_recent_incidents()
        
        # Count healthy services
        if isinstance(health, dict) and 'services' in health:
            total_services = len(health['services'])
            healthy_services = sum(1 for s in health['services'].values() if s.get('status') == 'healthy')
        else:
            total_services = 12
            healthy_services = 0
        
        # Check sync lag
        sync_lag = sync.get('lag_seconds', -1) if isinstance(sync, dict) else -1
        
        # Format summary
        summary_parts = []
        
        # Service health summary
        if healthy_services == total_services:
            summary_parts.append(f"✅ All {total_services} MCP services are healthy")
        else:
            summary_parts.append(f"⚠️ {healthy_services}/{total_services} services healthy")
        
        # Sync status summary
        if sync_lag >= 0:
            if sync_lag < 60:
                summary_parts.append(f"✅ Sync lag: {sync_lag}s (excellent)")
            elif sync_lag < 300:
                summary_parts.append(f"⚠️ Sync lag: {sync_lag}s (elevated)")
            else:
                summary_parts.append(f"🚨 Sync lag: {sync_lag}s (critical)")
        else:
            summary_parts.append("❓ Sync status unknown")
        
        # Alert summary
        if alerts:
            critical_count = sum(1 for a in alerts if a.get('state') == 'alerting')
            if critical_count > 0:
                summary_parts.append(f"🚨 {critical_count} active alerts firing")
            else:
                summary_parts.append(f"⚠️ {len(alerts)} warnings active")
        else:
            summary_parts.append("✅ No active alerts")
        
        # Add details if there are issues
        details = []
        
        if healthy_services < total_services:
            unhealthy = [name for name, info in health.get('services', {}).items() 
                        if info.get('status') != 'healthy']
            details.append(f"Unhealthy services: {', '.join(unhealthy[:3])}")
        
        if alerts:
            alert_names = [a.get('name', 'Unknown') for a in alerts[:3]]
            details.append(f"Active alerts: {', '.join(alert_names)}")
        
        if incidents:
            details.append(f"Recent incidents: {len(incidents)} in last hour")
        
        # Combine summary
        summary = '\n'.join(f"• {part}" for part in summary_parts)
        
        if details:
            summary += "\n\nDetails:\n" + '\n'.join(f"- {detail}" for detail in details)
        
        # Add timestamp
        summary += f"\n\nGenerated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        return summary

def main():
    """Main entry point for MCP tool"""
    monitor = MonitorSummary()
    summary = monitor.generate_summary()
    
    # Return in MCP format
    result = {
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }
    
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    main()