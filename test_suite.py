#!/usr/bin/env python3
"""
Comprehensive Test Suite for MCP Ecosystem
Includes unit tests, integration tests, and security tests
"""

import pytest
import asyncio
import httpx
import json
import jwt
import os
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import time
import yaml

# Test configuration
BASE_URL = os.getenv("MCP_TEST_URL", "http://localhost")
JWT_SECRET = os.getenv("PULSER_JWT_SECRET", "test-secret")
ADMIN_USER = os.getenv("MCP_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("MCP_ADMIN_PASS", "test-password")

# MCP service endpoints
SERVICES = {
    "scout": {"port": 8000, "path": "/api/v1/scout"},
    "creative": {"port": 8001, "path": "/api/v1/creative"},
    "financial": {"port": 8002, "path": "/api/v1/financial"},
    "voice": {"port": 8003, "path": "/api/v1/voice"},
    "unified": {"port": 8004, "path": "/api/v1/unified"},
    "synthetic": {"port": 8005, "path": "/api/v1/synthetic"},
    "briefvault": {"port": 8006, "path": "/api/v1/briefvault"},
    "researcher": {"port": 8007, "path": "/api/v1/researcher"},
    "video": {"port": 8008, "path": "/api/v1/video"},
    "audio": {"port": 8009, "path": "/api/v1/audio"},
    "memory": {"port": 5700, "path": "/api/v1/memory"}
}

class TestMCPSecurity:
    """Security test cases"""
    
    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers"""
        token = jwt.encode(
            {"sub": ADMIN_USER, "exp": datetime.utcnow() + timedelta(hours=1)},
            JWT_SECRET,
            algorithm="HS256"
        )
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def invalid_auth_headers(self):
        """Get invalid authentication headers"""
        token = jwt.encode(
            {"sub": "invalid", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256"
        )
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_unauthenticated_access(self):
        """Test that protected endpoints require authentication"""
        async with httpx.AsyncClient() as client:
            for service, config in SERVICES.items():
                url = f"{BASE_URL}:{config['port']}{config['path']}/protected"
                response = await client.get(url)
                assert response.status_code == 401, f"{service} allows unauthenticated access"
    
    @pytest.mark.asyncio
    async def test_invalid_token(self, invalid_auth_headers):
        """Test that invalid tokens are rejected"""
        async with httpx.AsyncClient() as client:
            for service, config in SERVICES.items():
                url = f"{BASE_URL}:{config['port']}{config['path']}/protected"
                response = await client.get(url, headers=invalid_auth_headers)
                assert response.status_code == 401, f"{service} accepts invalid tokens"
    
    @pytest.mark.asyncio
    async def test_valid_authentication(self, auth_headers):
        """Test that valid authentication works"""
        async with httpx.AsyncClient() as client:
            for service, config in SERVICES.items():
                # Get auth token
                auth_url = f"{BASE_URL}:{config['port']}/auth/token"
                response = await client.post(
                    auth_url,
                    data={"username": ADMIN_USER, "password": ADMIN_PASS}
                )
                
                if response.status_code == 200:
                    token = response.json()["access_token"]
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    # Test protected endpoint
                    health_url = f"{BASE_URL}:{config['port']}/health"
                    response = await client.get(health_url, headers=headers)
                    assert response.status_code == 200, f"{service} auth failed"

class TestMCPFunctionality:
    """Functional test cases"""
    
    @pytest.fixture
    async def auth_client(self):
        """Create authenticated HTTP client"""
        client = httpx.AsyncClient()
        # Get auth token
        response = await client.post(
            f"{BASE_URL}:8000/auth/token",
            data={"username": ADMIN_USER, "password": ADMIN_PASS}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
        return client
    
    @pytest.mark.asyncio
    async def test_health_endpoints(self):
        """Test all health endpoints"""
        async with httpx.AsyncClient() as client:
            for service, config in SERVICES.items():
                url = f"{BASE_URL}:{config['port']}/health"
                response = await client.get(url, timeout=10)
                assert response.status_code == 200, f"{service} health check failed"
                assert response.json()["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_scout_local_analytics(self, auth_client):
        """Test Scout Local MCP analytics"""
        # Test dashboard data
        response = await auth_client.get(f"{BASE_URL}:8000/api/v1/scout/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "totalRevenue" in data
        assert "topProducts" in data
    
    @pytest.mark.asyncio
    async def test_creative_rag_search(self, auth_client):
        """Test Creative RAG MCP search"""
        # Upload test asset
        test_asset = {
            "name": "Test Campaign",
            "content": "This is a test creative campaign for unit testing",
            "metadata": {"client": "TestClient", "year": 2024}
        }
        
        response = await auth_client.post(
            f"{BASE_URL}:8001/api/v1/creative/assets",
            json=test_asset
        )
        assert response.status_code in [200, 201]
        
        # Search for asset
        response = await auth_client.post(
            f"{BASE_URL}:8001/api/v1/creative/search",
            json={"query": "test campaign", "limit": 5}
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_financial_kpi_forecast(self, auth_client):
        """Test Financial Analyst MCP forecasting"""
        forecast_request = {
            "metric": "revenue",
            "periods": 3,
            "confidence_level": 0.95
        }
        
        response = await auth_client.post(
            f"{BASE_URL}:8002/api/v1/financial/forecast",
            json=forecast_request
        )
        assert response.status_code == 200
        forecast = response.json()
        assert "predictions" in forecast
        assert len(forecast["predictions"]) == 3
    
    @pytest.mark.asyncio
    async def test_voice_agent_session(self, auth_client):
        """Test Voice Agent MCP session"""
        # Start session
        response = await auth_client.post(
            f"{BASE_URL}:8003/api/v1/voice/sessions",
            json={"context": "test"}
        )
        assert response.status_code == 200
        session = response.json()
        assert "session_id" in session
        
        # End session
        response = await auth_client.post(
            f"{BASE_URL}:8003/api/v1/voice/sessions/{session['session_id']}/end"
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_shared_memory_operations(self, auth_client):
        """Test Shared Memory MCP operations"""
        # Store memory
        memory_data = {
            "key": "test_key",
            "value": {"data": "test_value"},
            "ttl": 3600
        }
        
        response = await auth_client.post(
            f"{BASE_URL}:5700/api/v1/memory/store",
            json=memory_data
        )
        assert response.status_code == 200
        
        # Retrieve memory
        response = await auth_client.get(
            f"{BASE_URL}:5700/api/v1/memory/retrieve/test_key"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"]["data"] == "test_value"

class TestMCPPerformance:
    """Performance test cases"""
    
    @pytest.fixture
    async def auth_client(self):
        """Create authenticated HTTP client"""
        client = httpx.AsyncClient()
        response = await client.post(
            f"{BASE_URL}:8000/auth/token",
            data={"username": ADMIN_USER, "password": ADMIN_PASS}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
        return client
    
    @pytest.mark.asyncio
    async def test_response_times(self, auth_client):
        """Test that all endpoints respond within acceptable time"""
        max_response_time = 2.0  # seconds
        
        for service, config in SERVICES.items():
            start_time = time.time()
            response = await auth_client.get(
                f"{BASE_URL}:{config['port']}/health",
                timeout=max_response_time + 1
            )
            response_time = time.time() - start_time
            
            assert response.status_code == 200
            assert response_time < max_response_time, \
                f"{service} took {response_time:.2f}s (max: {max_response_time}s)"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, auth_client):
        """Test handling of concurrent requests"""
        async def make_request(service, config):
            response = await auth_client.get(
                f"{BASE_URL}:{config['port']}/health"
            )
            return service, response.status_code
        
        # Make 10 concurrent requests to each service
        tasks = []
        for _ in range(10):
            for service, config in SERVICES.items():
                tasks.append(make_request(service, config))
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for service, status in results:
            assert status == 200, f"{service} failed under concurrent load"

class TestMCPResilience:
    """Resilience and error handling tests"""
    
    @pytest.fixture
    async def auth_client(self):
        """Create authenticated HTTP client"""
        client = httpx.AsyncClient()
        response = await client.post(
            f"{BASE_URL}:8000/auth/token",
            data={"username": ADMIN_USER, "password": ADMIN_PASS}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
        return client
    
    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, auth_client):
        """Test handling of invalid inputs"""
        # Test with invalid JSON
        response = await auth_client.post(
            f"{BASE_URL}:8001/api/v1/creative/search",
            content="invalid json{",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
        
        # Test with missing required fields
        response = await auth_client.post(
            f"{BASE_URL}:8002/api/v1/financial/forecast",
            json={}  # Missing required fields
        )
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_resource_limits(self, auth_client):
        """Test resource limit handling"""
        # Test large payload
        large_data = {"data": "x" * 1000000}  # 1MB of data
        
        response = await auth_client.post(
            f"{BASE_URL}:8005/api/v1/synthetic/generate",
            json=large_data
        )
        # Should either succeed or return 413 (Payload Too Large)
        assert response.status_code in [200, 413]

def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running MCP Integration Tests")
    print("=" * 50)
    
    # Run pytest with coverage
    result = subprocess.run([
        "pytest",
        __file__,
        "-v",
        "--cov=.",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-x"  # Stop on first failure
    ])
    
    return result.returncode == 0

def generate_test_report():
    """Generate test report"""
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "services_tested": list(SERVICES.keys()),
        "test_categories": [
            "Security",
            "Functionality",
            "Performance",
            "Resilience"
        ],
        "coverage_report": "htmlcov/index.html"
    }
    
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n📊 Test report generated: test_report.json")
    print("📈 Coverage report: htmlcov/index.html")

if __name__ == "__main__":
    success = run_integration_tests()
    generate_test_report()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        exit(1)