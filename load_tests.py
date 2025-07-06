#!/usr/bin/env python3
"""
Load Testing Configuration for MCP Ecosystem using Locust
Tests performance, scalability, and resilience of all MCP services
"""

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import json
import random
import jwt
from datetime import datetime, timedelta
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
JWT_SECRET = os.getenv("PULSER_JWT_SECRET", "test-secret")
ADMIN_USER = os.getenv("MCP_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("MCP_ADMIN_PASS", "test-password")

# Test data
SAMPLE_QUERIES = [
    "Show me top performing campaigns",
    "Analyze brand sentiment for Q4",
    "Compare revenue trends across regions",
    "Find creative assets for luxury brands",
    "Generate market analysis report"
]

SAMPLE_ASSETS = [
    {
        "name": "Q4 Campaign Creative",
        "content": "Premium luxury brand campaign focusing on sustainability",
        "metadata": {"client": "LuxuryBrand", "year": 2024, "category": "premium"}
    },
    {
        "name": "Social Media Strategy",
        "content": "Integrated social media approach for Gen Z engagement",
        "metadata": {"client": "YouthBrand", "year": 2024, "category": "social"}
    }
]

class MCPUser(FastHttpUser):
    """Base user class with authentication"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Authenticate and get JWT token"""
        response = self.client.post(
            "/auth/token",
            data={"username": ADMIN_USER, "password": ADMIN_PASS}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            logger.error(f"Authentication failed: {response.status_code}")
            self.headers = {}

class ScoutLocalUser(MCPUser):
    """Test Scout Local MCP analytics endpoints"""
    
    host = "http://localhost:8000"
    
    @task(3)
    def get_dashboard(self):
        """Test dashboard data retrieval"""
        self.client.get(
            "/api/v1/scout/dashboard",
            headers=self.headers,
            name="Scout: Dashboard"
        )
    
    @task(2)
    def analyze_trends(self):
        """Test trend analysis"""
        self.client.post(
            "/api/v1/scout/analyze/trends",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "metrics": ["revenue", "conversion", "traffic"]
            },
            headers=self.headers,
            name="Scout: Analyze Trends"
        )
    
    @task(1)
    def export_report(self):
        """Test report generation"""
        self.client.post(
            "/api/v1/scout/export",
            json={
                "format": "pdf",
                "include_charts": True,
                "sections": ["overview", "metrics", "recommendations"]
            },
            headers=self.headers,
            name="Scout: Export Report"
        )

class CreativeRAGUser(MCPUser):
    """Test Creative RAG MCP search capabilities"""
    
    host = "http://localhost:8001"
    
    @task(4)
    def search_assets(self):
        """Test semantic search"""
        query = random.choice(SAMPLE_QUERIES)
        self.client.post(
            "/api/v1/creative/search",
            json={
                "query": query,
                "limit": 10,
                "filters": {"year": 2024}
            },
            headers=self.headers,
            name="Creative: Search Assets"
        )
    
    @task(2)
    def upload_asset(self):
        """Test asset upload"""
        asset = random.choice(SAMPLE_ASSETS)
        self.client.post(
            "/api/v1/creative/assets",
            json=asset,
            headers=self.headers,
            name="Creative: Upload Asset"
        )
    
    @task(1)
    def get_similar(self):
        """Test similarity search"""
        self.client.post(
            "/api/v1/creative/similar",
            json={
                "asset_id": f"asset_{random.randint(1, 100)}",
                "limit": 5
            },
            headers=self.headers,
            name="Creative: Find Similar"
        )

class FinancialAnalystUser(MCPUser):
    """Test Financial Analyst MCP forecasting"""
    
    host = "http://localhost:8002"
    
    @task(3)
    def forecast_kpi(self):
        """Test KPI forecasting"""
        self.client.post(
            "/api/v1/financial/forecast",
            json={
                "metric": random.choice(["revenue", "costs", "profit", "roi"]),
                "periods": random.randint(3, 12),
                "confidence_level": 0.95,
                "include_seasonality": True
            },
            headers=self.headers,
            name="Financial: Forecast KPI"
        )
    
    @task(2)
    def analyze_performance(self):
        """Test performance analysis"""
        self.client.post(
            "/api/v1/financial/analyze",
            json={
                "metrics": ["revenue", "margin", "growth"],
                "comparison": "year-over-year",
                "segments": ["region", "product", "channel"]
            },
            headers=self.headers,
            name="Financial: Analyze Performance"
        )
    
    @task(1)
    def generate_insights(self):
        """Test insight generation"""
        self.client.get(
            "/api/v1/financial/insights",
            headers=self.headers,
            name="Financial: Get Insights"
        )

class VoiceAgentUser(MCPUser):
    """Test Voice Agent MCP real-time capabilities"""
    
    host = "http://localhost:8003"
    
    def on_start(self):
        """Start voice session on user creation"""
        super().on_start()
        response = self.client.post(
            "/api/v1/voice/sessions",
            json={"context": "load_test"},
            headers=self.headers
        )
        if response.status_code == 200:
            self.session_id = response.json()["session_id"]
        else:
            self.session_id = None
    
    @task(5)
    def send_audio_chunk(self):
        """Test audio streaming"""
        if self.session_id:
            # Simulate audio data (base64 encoded)
            audio_data = "UklGRi..." * 100  # Simulated audio chunk
            self.client.post(
                f"/api/v1/voice/sessions/{self.session_id}/audio",
                json={"audio": audio_data},
                headers=self.headers,
                name="Voice: Send Audio"
            )
    
    @task(2)
    def get_transcript(self):
        """Test transcript retrieval"""
        if self.session_id:
            self.client.get(
                f"/api/v1/voice/sessions/{self.session_id}/transcript",
                headers=self.headers,
                name="Voice: Get Transcript"
            )
    
    def on_stop(self):
        """End voice session on user stop"""
        if hasattr(self, 'session_id') and self.session_id:
            self.client.post(
                f"/api/v1/voice/sessions/{self.session_id}/end",
                headers=self.headers
            )

class SharedMemoryUser(MCPUser):
    """Test Shared Memory MCP operations"""
    
    host = "http://localhost:5700"
    
    @task(4)
    def store_memory(self):
        """Test memory storage"""
        key = f"test_key_{random.randint(1, 1000)}"
        self.client.post(
            "/api/v1/memory/store",
            json={
                "key": key,
                "value": {
                    "data": f"test_value_{datetime.utcnow().isoformat()}",
                    "metadata": {"source": "load_test"}
                },
                "ttl": 3600
            },
            headers=self.headers,
            name="Memory: Store"
        )
    
    @task(3)
    def retrieve_memory(self):
        """Test memory retrieval"""
        key = f"test_key_{random.randint(1, 100)}"
        self.client.get(
            f"/api/v1/memory/retrieve/{key}",
            headers=self.headers,
            name="Memory: Retrieve"
        )
    
    @task(2)
    def query_graph(self):
        """Test graph queries"""
        self.client.post(
            "/api/v1/memory/query",
            json={
                "cypher": "MATCH (n:Agent)-[:KNOWS]->(m:Memory) RETURN n, m LIMIT 10"
            },
            headers=self.headers,
            name="Memory: Query Graph"
        )
    
    @task(1)
    def get_connections(self):
        """Test connection retrieval"""
        self.client.get(
            f"/api/v1/memory/connections/agent_{random.randint(1, 10)}",
            headers=self.headers,
            name="Memory: Get Connections"
        )

class SyntheticDataUser(MCPUser):
    """Test Synthetic Data MCP generation"""
    
    host = "http://localhost:8005"
    
    @task(3)
    def generate_retail_data(self):
        """Test retail data generation"""
        self.client.post(
            "/api/v1/synthetic/generate",
            json={
                "dataset": "retail_transactions",
                "count": random.randint(100, 1000),
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "include_anomalies": True
            },
            headers=self.headers,
            name="Synthetic: Generate Retail Data"
        )
    
    @task(2)
    def generate_customer_profiles(self):
        """Test customer profile generation"""
        self.client.post(
            "/api/v1/synthetic/profiles",
            json={
                "count": random.randint(50, 200),
                "segments": ["premium", "regular", "budget"],
                "include_behavior": True
            },
            headers=self.headers,
            name="Synthetic: Generate Profiles"
        )
    
    @task(1)
    def export_dataset(self):
        """Test dataset export"""
        self.client.post(
            "/api/v1/synthetic/export",
            json={
                "format": random.choice(["csv", "json", "parquet"]),
                "dataset_id": f"dataset_{random.randint(1, 10)}"
            },
            headers=self.headers,
            name="Synthetic: Export Dataset"
        )

class MixedWorkloadUser(MCPUser):
    """Simulate mixed workload across all services"""
    
    tasks = {
        ScoutLocalUser.get_dashboard: 3,
        CreativeRAGUser.search_assets: 4,
        FinancialAnalystUser.forecast_kpi: 2,
        VoiceAgentUser.send_audio_chunk: 1,
        SharedMemoryUser.retrieve_memory: 3,
        SyntheticDataUser.generate_retail_data: 1
    }
    
    def on_start(self):
        """Initialize all service clients"""
        super().on_start()
        self.services = {
            "scout": "http://localhost:8000",
            "creative": "http://localhost:8001",
            "financial": "http://localhost:8002",
            "voice": "http://localhost:8003",
            "memory": "http://localhost:5700",
            "synthetic": "http://localhost:8005"
        }

# Event handlers for detailed metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics"""
    logger.info("Load test started")
    logger.info(f"Target host: {environment.host}")
    logger.info(f"Total users: {environment.parsed_options.num_users}")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Log detailed request metrics"""
    if response_time > 2000:  # Log slow requests (>2s)
        logger.warning(f"Slow request: {name} took {response_time}ms")
    
    if response and response.status_code >= 400:
        logger.error(f"Request failed: {name} - Status: {response.status_code}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate test summary"""
    logger.info("Load test completed")
    
    # Calculate and log statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Failed requests: {stats.total.num_failures}")
    logger.info(f"Median response time: {stats.total.median_response_time}ms")
    logger.info(f"95th percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    
    # Generate performance report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_requests": stats.total.num_requests,
        "failed_requests": stats.total.num_failures,
        "failure_rate": stats.total.fail_ratio,
        "median_response_time": stats.total.median_response_time,
        "p95_response_time": stats.total.get_response_time_percentile(0.95),
        "p99_response_time": stats.total.get_response_time_percentile(0.99),
        "rps": stats.total.current_rps
    }
    
    with open("load_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info("Performance report saved to load_test_report.json")

# Custom load test scenarios
class StressTestUser(MixedWorkloadUser):
    """Stress test with aggressive parameters"""
    wait_time = between(0.1, 0.5)  # Minimal wait time

class SpikeTestUser(MixedWorkloadUser):
    """Spike test to simulate sudden traffic"""
    wait_time = between(0.5, 1)

class EnduranceTestUser(MixedWorkloadUser):
    """Endurance test for long-running scenarios"""
    wait_time = between(2, 5)

if __name__ == "__main__":
    # Run with: locust -f load_tests.py --host=http://localhost:8000
    import os
    os.system("locust -f " + __file__)