#!/usr/bin/env python3
"""
SSE Health Monitor for Pulser MCP Remote Bridge
Monitors the SSE endpoint and sends alerts on failures
"""

import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

# Configuration
SSE_URL = os.getenv('SSE_URL', 'https://pulser-ai.com/sse')
HEALTH_URL = os.getenv('HEALTH_URL', 'https://pulser-ai.com/health')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
ALERT_WEBHOOK = os.getenv('ALERT_WEBHOOK')  # Optional webhook URL
LOG_FILE = os.getenv('LOG_FILE', '/var/log/pulser-mcp-health.log')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('mcp-health-monitor')

class HealthMonitor:
    def __init__(self):
        self.consecutive_failures = 0
        self.last_status = None
        self.session = None
        
    async def start(self):
        """Start the health monitoring loop"""
        self.session = aiohttp.ClientSession()
        logger.info(f"Starting health monitor for {SSE_URL}")
        
        try:
            while True:
                await self.check_health()
                await asyncio.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Health monitor stopped by user")
        finally:
            await self.session.close()
    
    async def check_health(self) -> Dict:
        """Check both health endpoint and SSE connectivity"""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'health_endpoint': False,
            'sse_endpoint': False,
            'services': {}
        }
        
        # Check health endpoint
        try:
            async with self.session.get(HEALTH_URL, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results['health_endpoint'] = True
                    results['health_data'] = data
                    logger.debug(f"Health endpoint OK: {data}")
        except Exception as e:
            logger.error(f"Health endpoint failed: {e}")
        
        # Check SSE endpoint
        try:
            async with self.session.get(
                SSE_URL,
                timeout=10,
                headers={'Accept': 'text/event-stream'}
            ) as resp:
                if resp.status == 200:
                    # Read first few bytes to ensure connection
                    chunk = await resp.content.read(100)
                    if chunk:
                        results['sse_endpoint'] = True
                        logger.debug("SSE endpoint connected successfully")
        except Exception as e:
            logger.error(f"SSE endpoint failed: {e}")
        
        # Check individual MCP services if main health is OK
        if results['health_endpoint']:
            try:
                async with self.session.get(
                    'https://pulser-ai.com/mcp/services',
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        services = await resp.json()
                        results['services'] = services
            except Exception as e:
                logger.warning(f"Could not fetch service list: {e}")
        
        # Handle status changes
        await self.handle_status_change(results)
        
        return results
    
    async def handle_status_change(self, current_status: Dict):
        """Handle changes in health status"""
        is_healthy = (
            current_status['health_endpoint'] and 
            current_status['sse_endpoint']
        )
        
        if not is_healthy:
            self.consecutive_failures += 1
            
            # Send alert after 3 consecutive failures
            if self.consecutive_failures == 3:
                await self.send_alert(
                    "🚨 Pulser MCP Remote Bridge is DOWN",
                    current_status
                )
            
            logger.warning(
                f"Health check failed ({self.consecutive_failures} consecutive): "
                f"Health={current_status['health_endpoint']}, "
                f"SSE={current_status['sse_endpoint']}"
            )
        else:
            # Recovery detected
            if self.consecutive_failures >= 3:
                await self.send_alert(
                    "✅ Pulser MCP Remote Bridge has RECOVERED",
                    current_status
                )
            
            self.consecutive_failures = 0
            logger.info("Health check passed")
        
        self.last_status = current_status
    
    async def send_alert(self, message: str, status: Dict):
        """Send alert via webhook or log critically"""
        alert_data = {
            'message': message,
            'timestamp': status['timestamp'],
            'status': status,
            'consecutive_failures': self.consecutive_failures
        }
        
        logger.critical(f"ALERT: {message}")
        
        if ALERT_WEBHOOK:
            try:
                async with self.session.post(
                    ALERT_WEBHOOK,
                    json=alert_data,
                    timeout=5
                ) as resp:
                    if resp.status == 200:
                        logger.info("Alert sent successfully")
                    else:
                        logger.error(f"Alert webhook returned {resp.status}")
            except Exception as e:
                logger.error(f"Failed to send alert webhook: {e}")

async def main():
    monitor = HealthMonitor()
    await monitor.start()

if __name__ == '__main__':
    asyncio.run(main())