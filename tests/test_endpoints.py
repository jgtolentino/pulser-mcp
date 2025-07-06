"""
Test suite for MCP Server endpoints
"""

import pytest
import httpx
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"
    
    def test_status_endpoint(self):
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "active_models" in data
        assert "active_agents" in data
    
    def test_capabilities_endpoint(self):
        response = client.get("/capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "models" in data
        assert "agents" in data

class TestSearchEndpoint:
    """Test search functionality"""
    
    def test_search_basic(self):
        response = client.post("/tools/search", json={
            "query": "MCP integration"
        })
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query_time_ms" in data
    
    def test_search_with_filters(self):
        response = client.post("/tools/search", json={
            "query": "vector search",
            "filters": {"agent": "claudia"},
            "limit": 5
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5
    
    def test_search_invalid_request(self):
        response = client.post("/tools/search", json={})
        assert response.status_code == 422  # Validation error

class TestGenerateEndpoint:
    """Test content generation"""
    
    def test_generate_text(self):
        response = client.post("/tools/generate", json={
            "prompt": "Write a hello world function",
            "type": "code"
        })
        assert response.status_code == 200
        data = response.json()
        assert "output" in data
        assert "model_used" in data
    
    def test_generate_with_model(self):
        response = client.post("/tools/generate", json={
            "prompt": "Explain MCP",
            "model": "claude-3-opus",
            "type": "text"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "claude-3-opus"

class TestAnalyzeEndpoint:
    """Test document analysis"""
    
    def test_analyze_content(self):
        response = client.post("/tools/analyze", json={
            "content": "This is a test document about MCP integration.",
            "analysis_type": "summary"
        })
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
    
    def test_analyze_comprehensive(self):
        response = client.post("/tools/analyze", json={
            "content": "The Pulser MCP server is amazing! It integrates well.",
            "analysis_type": "comprehensive"
        })
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "sentiment" in data
        assert "entities" in data
        assert "keywords" in data

class TestCommandEndpoint:
    """Test command execution"""
    
    def test_execute_command(self):
        response = client.post("/command", json={
            "command": "echo 'Hello MCP'",
            "agent": "basher",
            "environment": "terminal"
        })
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "success" in data
        assert data["agent_used"] == "basher"
    
    def test_execute_invalid_agent(self):
        response = client.post("/command", json={
            "command": "test",
            "agent": "invalid_agent",
            "environment": "terminal"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async operations"""
    
    async def test_concurrent_searches(self):
        """Test multiple concurrent search requests"""
        async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
            tasks = []
            for i in range(5):
                task = ac.post("/tools/search", json={
                    "query": f"test query {i}"
                })
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            for response in responses:
                assert response.status_code == 200