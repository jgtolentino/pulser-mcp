#!/usr/bin/env python3
"""
Unified MCP Server - MindsDB-powered cross-agent analytics hub
Connects all Pulser agents' data sources for unified insights
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import pandas as pd
import mindsdb_sdk
from sqlalchemy import create_engine
import redis
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MINDSDB_HOST = os.getenv("MINDSDB_HOST", "localhost")
MINDSDB_PORT = int(os.getenv("MINDSDB_PORT", 47334))
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://mindsdb:mindsdb123@localhost:5432/unified_analytics")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380")

# FastAPI app

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# JWT Configuration
SECRET_KEY = os.getenv("PULSER_JWT_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = ["/", "/health", "/auth/token"]

app = FastAPI(title="Unified MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Initialize connections
mindsdb_client = None
postgres_engine = None
redis_client = None

# Pydantic models
class DataSourceConfig(BaseModel):
    name: str
    type: str  # slack, gmail, github, supabase, api, database
    connection_params: Dict[str, Any]
    sync_interval: Optional[int] = 3600  # seconds

class UnifiedQueryRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = []  # Empty means all sources
    timeframe: Optional[str] = "1W"
    output_format: str = "data"  # data, chart, report

class CrossAgentAnalysis(BaseModel):
    analysis_type: str  # correlation, anomaly, trend, comparison
    agents: List[str]
    metrics: List[str]
    parameters: Optional[Dict[str, Any]] = {}

class PredictiveModelRequest(BaseModel):
    target_metric: str
    features: List[str]
    model_type: str = "timeseries"  # timeseries, regression, classification
    training_window: str = "30D"

# Initialize connections
def init_connections():
    """Initialize all data connections"""
    global mindsdb_client, postgres_engine, redis_client
    
    try:
        # MindsDB connection
        mindsdb_client = mindsdb_sdk.connect(
            f'http://{MINDSDB_HOST}:{MINDSDB_PORT}'
        )
        logger.info("MindsDB connection established")
        
        # PostgreSQL for metadata
        postgres_engine = create_engine(POSTGRES_URL)
        logger.info("PostgreSQL connection established")
        
        # Redis for caching
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("Redis connection established")
        
    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")
        raise

# Data Source Manager
class DataSourceManager:
    def __init__(self):
        self.sources = {}
        self.load_configured_sources()
    
    def load_configured_sources(self):
        """Load pre-configured data sources"""
        # Default Pulser agent data sources
        default_sources = {
            "scout_metrics": {
                "type": "database",
                "params": {
                    "engine": "postgresql",
                    "host": "localhost",
                    "database": "scout_db",
                    "table": "predicted_metrics"
                }
            },
            "creative_insights": {
                "type": "api",
                "params": {
                    "url": "http://localhost:8001/mcp/tools/search_vector",
                    "method": "POST"
                }
            },
            "voice_analytics": {
                "type": "supabase",
                "params": {
                    "table": "call_analytics",
                    "select": "*"
                }
            },
            "financial_kpis": {
                "type": "api", 
                "params": {
                    "url": "http://localhost:8002/mcp/tools/analyze_kpis",
                    "method": "POST"
                }
            }
        }
        
        for name, config in default_sources.items():
            self.add_source(DataSourceConfig(
                name=name,
                type=config["type"],
                connection_params=config["params"]
            ))
    
    def add_source(self, config: DataSourceConfig):
        """Add a new data source"""
        self.sources[config.name] = config
        
        # Create MindsDB datasource
        try:
            if config.type == "database":
                self._create_database_source(config)
            elif config.type == "api":
                self._create_api_source(config)
            elif config.type == "slack":
                self._create_slack_source(config)
            elif config.type == "gmail":
                self._create_gmail_source(config)
        except Exception as e:
            logger.error(f"Failed to create source {config.name}: {e}")
    
    def _create_database_source(self, config: DataSourceConfig):
        """Create database data source in MindsDB"""
        query = f"""
        CREATE DATABASE {config.name}
        WITH ENGINE = '{config.connection_params.get('engine', 'postgresql')}',
        PARAMETERS = {{
            "host": "{config.connection_params.get('host')}",
            "port": {config.connection_params.get('port', 5432)},
            "database": "{config.connection_params.get('database')}",
            "user": "{config.connection_params.get('user', 'postgres')}",
            "password": "{config.connection_params.get('password', '')}"
        }};
        """
        # Execute via MindsDB (mock for now)
        logger.info(f"Created database source: {config.name}")
    
    def _create_api_source(self, config: DataSourceConfig):
        """Create API data source"""
        # Register API endpoint for polling
        logger.info(f"Created API source: {config.name}")
    
    def _create_slack_source(self, config: DataSourceConfig):
        """Create Slack integration"""
        logger.info(f"Created Slack source: {config.name}")
    
    def _create_gmail_source(self, config: DataSourceConfig):
        """Create Gmail integration"""
        logger.info(f"Created Gmail source: {config.name}")

# MCP Tools
class MCPTools:
    @staticmethod
    async def query_unified_data(request: UnifiedQueryRequest) -> Dict[str, Any]:
        """Query across all connected data sources"""
        try:
            # Check cache first
            cache_key = f"unified_query:{hash(request.query)}:{','.join(request.sources)}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Parse natural language query (mock implementation)
            # In production, use MindsDB's NLP capabilities
            
            results = []
            
            # Query each requested source
            sources_to_query = request.sources if request.sources else list(app.state.source_manager.sources.keys())
            
            for source_name in sources_to_query:
                if source_name in app.state.source_manager.sources:
                    source_config = app.state.source_manager.sources[source_name]
                    
                    # Mock data retrieval based on source type
                    if source_config.type == "database":
                        # SQL query via MindsDB
                        data = {
                            "source": source_name,
                            "records": 150,
                            "sample": [
                                {"metric": "revenue", "value": 125000, "date": "2024-01-15"},
                                {"metric": "engagement", "value": 0.045, "date": "2024-01-15"}
                            ]
                        }
                    elif source_config.type == "api":
                        # API call
                        async with httpx.AsyncClient() as client:
                            # Mock API response
                            data = {
                                "source": source_name,
                                "status": "success",
                                "data": {"insights": "Sample insight from API"}
                            }
                    else:
                        data = {"source": source_name, "status": "pending"}
                    
                    results.append(data)
            
            # Aggregate results
            response = {
                "success": True,
                "query": request.query,
                "sources_queried": len(results),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache results
            redis_client.setex(cache_key, 300, json.dumps(response))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in unified query: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def analyze_cross_agent(request: CrossAgentAnalysis) -> Dict[str, Any]:
        """Perform cross-agent analysis"""
        try:
            analysis_results = {
                "analysis_type": request.analysis_type,
                "agents": request.agents,
                "metrics": request.metrics
            }
            
            if request.analysis_type == "correlation":
                # Mock correlation analysis
                correlations = {}
                for i, agent1 in enumerate(request.agents):
                    for agent2 in request.agents[i+1:]:
                        key = f"{agent1}_vs_{agent2}"
                        correlations[key] = {
                            "correlation_coefficient": 0.75,
                            "p_value": 0.001,
                            "relationship": "positive"
                        }
                analysis_results["correlations"] = correlations
                
            elif request.analysis_type == "anomaly":
                # Mock anomaly detection
                anomalies = []
                for agent in request.agents:
                    anomalies.append({
                        "agent": agent,
                        "timestamp": "2024-01-15T14:30:00",
                        "metric": "response_time",
                        "value": 2500,
                        "expected_range": [100, 500],
                        "severity": "high"
                    })
                analysis_results["anomalies"] = anomalies
                
            elif request.analysis_type == "trend":
                # Mock trend analysis
                trends = {}
                for agent in request.agents:
                    trends[agent] = {
                        "direction": "increasing",
                        "change_rate": "+15%",
                        "forecast_7d": [100, 115, 130, 145, 160, 175, 190]
                    }
                analysis_results["trends"] = trends
            
            return {
                "success": True,
                "analysis": analysis_results,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in cross-agent analysis: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def create_predictive_model(request: PredictiveModelRequest) -> Dict[str, Any]:
        """Create predictive model using MindsDB"""
        try:
            model_name = f"predict_{request.target_metric}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Mock MindsDB model creation
            # In production, use actual MindsDB CREATE PREDICTOR syntax
            create_query = f"""
            CREATE PREDICTOR {model_name}
            FROM unified_data
            (SELECT {', '.join(request.features)}, {request.target_metric}
             FROM agent_metrics
             WHERE timestamp > NOW() - INTERVAL '{request.training_window}')
            PREDICT {request.target_metric}
            USING engine = 'lightwood',
                  time_column = 'timestamp',
                  horizon = 7;
            """
            
            # Simulate model training
            await asyncio.sleep(2)  # Mock training time
            
            return {
                "success": True,
                "model_name": model_name,
                "target": request.target_metric,
                "features": request.features,
                "status": "training",
                "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating predictive model: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def enable_mcp_plugin() -> Dict[str, Any]:
        """Enable MCP plugin in MindsDB"""
        try:
            # Mock enabling MCP plugin
            # In production: mindsdb mcp enable
            
            return {
                "success": True,
                "status": "MCP plugin enabled",
                "endpoints": {
                    "query": "/mcp/query",
                    "analyze": "/mcp/analyze",
                    "predict": "/mcp/predict"
                },
                "version": "1.0.0"
            }
            
        except Exception as e:
            logger.error(f"Error enabling MCP plugin: {e}")
            return {"success": False, "error": str(e)}

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    init_connections()
    app.state.source_manager = DataSourceManager()
    
    # Enable MCP plugin
    await MCPTools.enable_mcp_plugin()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "Unified MCP Server",
        "mindsdb_studio": "http://localhost:8891"
    }

@api_v1.post("/mcp/tools/query_unified")
async def query_unified(request: UnifiedQueryRequest, current_user: str = Depends(verify_token)):
    """Query across all data sources"""
    result = await MCPTools.query_unified_data(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/analyze_cross_agent")
async def analyze_cross_agent(request: CrossAgentAnalysis, current_user: str = Depends(verify_token)):
    """Analyze patterns across agents"""
    result = await MCPTools.analyze_cross_agent(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/create_model")
async def create_model(request: PredictiveModelRequest, current_user: str = Depends(verify_token)):
    """Create predictive model"""
    result = await MCPTools.create_predictive_model(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/add_source")
async def add_source(config: DataSourceConfig, current_user: str = Depends(verify_token)):
    """Add new data source"""
    try:
        app.state.source_manager.add_source(config)
        return {"success": True, "source": config.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_v1.get("/mcp/tools/list_sources")
async def list_sources(current_user: str = Depends(verify_token)):
    """List all connected data sources"""
    sources = []
    for name, config in app.state.source_manager.sources.items():
        sources.append({
            "name": name,
            "type": config.type,
            "sync_interval": config.sync_interval
        })
    return {"sources": sources}

# MCP metadata endpoint
@api_v1.get("/mcp/metadata")
async def get_metadata(current_user: str = Depends(verify_token)):
    """Return MCP server metadata"""
    return {
        "name": "unified-mcp",
        "version": "1.0.0",
        "description": "MindsDB-powered unified analytics across all Pulser agents",
        "tools": [
            {
                "name": "query_unified",
                "description": "Query across all connected data sources",
                "parameters": {
                    "query": "string",
                    "sources": "array[string] (optional)",
                    "timeframe": "string (optional)",
                    "output_format": "string (data, chart, report)"
                }
            },
            {
                "name": "analyze_cross_agent",
                "description": "Analyze patterns across multiple agents",
                "parameters": {
                    "analysis_type": "string (correlation, anomaly, trend, comparison)",
                    "agents": "array[string]",
                    "metrics": "array[string]",
                    "parameters": "object (optional)"
                }
            },
            {
                "name": "create_model",
                "description": "Create predictive model with MindsDB",
                "parameters": {
                    "target_metric": "string",
                    "features": "array[string]",
                    "model_type": "string (timeseries, regression, classification)",
                    "training_window": "string (e.g., 30D)"
                }
            },
            {
                "name": "add_source",
                "description": "Add new data source connection",
                "parameters": {
                    "name": "string",
                    "type": "string (slack, gmail, github, supabase, api, database)",
                    "connection_params": "object",
                    "sync_interval": "integer (seconds)"
                }
            }
        ],
        "integrations": [
            "Slack", "Gmail", "GitHub", "HackerNews",
            "PostgreSQL", "MySQL", "MongoDB", "Supabase"
        ]
    }


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)