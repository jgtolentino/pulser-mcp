#!/usr/bin/env python3
"""
Scout Local MCP Server - 100% Local SQLite-based MCP Client
Provides offline analytics capabilities for Scout field agents
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = Path(__file__).parent.parent / "data" / "scout_local.db"
DB_PATH.parent.mkdir(exist_ok=True)

# FastAPI app
app = FastAPI(title="Scout Local MCP Server")

# Pydantic models
class TranscriptionData(BaseModel):
    store_id: str
    region: str
    brand: str
    transcript: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None

class QueryRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = {}

class ToolCall(BaseModel):
    tool: str
    params: Dict[str, Any]

# Database initialization
def init_database():
    """Initialize the local SQLite database with Scout schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create bronze_transcriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bronze_transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT NOT NULL,
            region TEXT NOT NULL,
            brand TEXT NOT NULL,
            transcript TEXT NOT NULL,
            metadata TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create analytics_cache table for offline insights
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_hash TEXT UNIQUE,
            query TEXT,
            result TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)
    
    # Create indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_region ON bronze_transcriptions(store_id, region)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand ON bronze_transcriptions(brand)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON bronze_transcriptions(timestamp)")
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# MCP Tools
class MCPTools:
    @staticmethod
    def add_transcription(data: TranscriptionData) -> Dict[str, Any]:
        """Add sales transcription data to local database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO bronze_transcriptions 
                (store_id, region, brand, transcript, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.store_id,
                data.region,
                data.brand,
                data.transcript,
                json.dumps(data.metadata),
                data.timestamp or datetime.now()
            ))
            
            conn.commit()
            return {
                "success": True,
                "id": cursor.lastrowid,
                "message": "Transcription added successfully"
            }
        except Exception as e:
            logger.error(f"Error adding transcription: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def fetch_transcriptions(query: QueryRequest) -> Dict[str, Any]:
        """Fetch transcriptions with flexible querying"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Parse query parameters
            filters = []
            params = []
            
            if "store_id" in query.params:
                filters.append("store_id = ?")
                params.append(query.params["store_id"])
            
            if "region" in query.params:
                filters.append("region = ?")
                params.append(query.params["region"])
            
            if "brand" in query.params:
                filters.append("brand = ?")
                params.append(query.params["brand"])
            
            if "date_from" in query.params:
                filters.append("timestamp >= ?")
                params.append(query.params["date_from"])
            
            if "date_to" in query.params:
                filters.append("timestamp <= ?")
                params.append(query.params["date_to"])
            
            # Build query
            base_query = "SELECT * FROM bronze_transcriptions"
            if filters:
                base_query += " WHERE " + " AND ".join(filters)
            
            base_query += " ORDER BY timestamp DESC LIMIT 100"
            
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                result = dict(row)
                result['metadata'] = json.loads(result['metadata']) if result['metadata'] else {}
                results.append(result)
            
            return {
                "success": True,
                "count": len(results),
                "data": results
            }
        except Exception as e:
            logger.error(f"Error fetching transcriptions: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def analyze_local_trends() -> Dict[str, Any]:
        """Perform local analytics on cached data"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Brand performance
            cursor.execute("""
                SELECT brand, COUNT(*) as count, region
                FROM bronze_transcriptions
                GROUP BY brand, region
                ORDER BY count DESC
            """)
            brand_stats = [dict(row) for row in cursor.fetchall()]
            
            # Regional activity
            cursor.execute("""
                SELECT region, COUNT(*) as activity_count,
                       COUNT(DISTINCT store_id) as store_count,
                       COUNT(DISTINCT brand) as brand_count
                FROM bronze_transcriptions
                GROUP BY region
            """)
            regional_stats = [dict(row) for row in cursor.fetchall()]
            
            # Recent activity
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM bronze_transcriptions
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)
            recent_activity = [dict(row) for row in cursor.fetchall()]
            
            return {
                "success": True,
                "analytics": {
                    "brand_performance": brand_stats,
                    "regional_activity": regional_stats,
                    "recent_activity": recent_activity,
                    "total_transcriptions": sum(r['count'] for r in brand_stats),
                    "generated_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "active", "service": "Scout Local MCP Server"}

@app.post("/mcp/tools/add_transcription")
async def add_transcription(data: TranscriptionData):
    """MCP endpoint for adding transcription data"""
    result = MCPTools.add_transcription(data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/mcp/tools/fetch_transcriptions")
async def fetch_transcriptions(query: QueryRequest):
    """MCP endpoint for fetching transcriptions"""
    result = MCPTools.fetch_transcriptions(query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/mcp/tools/analyze_trends")
async def analyze_trends():
    """MCP endpoint for local trend analysis"""
    result = MCPTools.analyze_local_trends()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/mcp/execute")
async def execute_tool(tool_call: ToolCall):
    """Generic MCP tool execution endpoint"""
    tool_map = {
        "add_transcription": lambda p: MCPTools.add_transcription(TranscriptionData(**p)),
        "fetch_transcriptions": lambda p: MCPTools.fetch_transcriptions(QueryRequest(**p)),
        "analyze_trends": lambda p: MCPTools.analyze_local_trends()
    }
    
    if tool_call.tool not in tool_map:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_call.tool}")
    
    try:
        result = tool_map[tool_call.tool](tool_call.params)
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_call.tool}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MCP metadata endpoint
@app.get("/mcp/metadata")
async def get_metadata():
    """Return MCP server metadata"""
    return {
        "name": "scout-local-mcp",
        "version": "1.0.0",
        "description": "100% Local SQLite-based analytics for Scout field agents",
        "tools": [
            {
                "name": "add_transcription",
                "description": "Add sales transcription to local database",
                "parameters": {
                    "store_id": "string",
                    "region": "string",
                    "brand": "string",
                    "transcript": "string",
                    "metadata": "object (optional)",
                    "timestamp": "datetime (optional)"
                }
            },
            {
                "name": "fetch_transcriptions",
                "description": "Query transcriptions with filters",
                "parameters": {
                    "query": "string",
                    "params": {
                        "store_id": "string (optional)",
                        "region": "string (optional)",
                        "brand": "string (optional)",
                        "date_from": "datetime (optional)",
                        "date_to": "datetime (optional)"
                    }
                }
            },
            {
                "name": "analyze_trends",
                "description": "Perform local trend analysis on cached data",
                "parameters": {}
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)