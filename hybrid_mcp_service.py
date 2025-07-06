#!/usr/bin/env python3
"""
Hybrid MCP Service Base Class
Combines distributed performance with centralized coordination
Best of both architectures!
"""

import os
import json
import sqlite3
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from supabase import create_client, Client
from qdrant_client import QdrantClient
from redis import Redis
import neo4j

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.getenv("PULSER_JWT_SECRET")
DEVICE_ID = os.getenv("DEVICE_ID", os.uname().nodename)

logger = logging.getLogger(__name__)

class HybridMCPService(ABC):
    """
    Base class for MCP services with hybrid architecture:
    - Local SQLite for immediate operations
    - Specialized stores for performance (Qdrant, Redis, Neo4j)
    - Supabase for coordination and source of truth
    """
    
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = port
        
        # Initialize FastAPI
        self.app = FastAPI(
            title=f"{service_name} MCP",
            version="2.0.0",
            description="Hybrid local-first + cloud-backed service"
        )
        
        # Local SQLite for immediate operations
        self.local_db = self._init_sqlite()
        
        # Specialized stores (optional per service)
        self.vector_store = None  # Qdrant for similarity search
        self.graph_store = None   # Neo4j for relationships
        self.cache_store = None   # Redis for hot data
        
        # Supabase for coordination
        self.supa = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Setup routes
        self._setup_routes()
        
        # Start background sync
        asyncio.create_task(self._sync_daemon())
    
    def _init_sqlite(self) -> sqlite3.Connection:
        """Initialize local SQLite with sync capabilities"""
        db_path = f"{self.service_name}.db"
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Create sync tables
        with open("sync/sql/01_sync_schema.sql", "r") as f:
            conn.executescript(f.read())
        
        # Register device
        conn.execute("""
            INSERT OR REPLACE INTO _sync_devices(device_id, device_name, metadata)
            VALUES (?, ?, ?)
        """, (DEVICE_ID, self.service_name, json.dumps({
            "service": self.service_name,
            "version": "2.0.0",
            "capabilities": self.get_capabilities()
        })))
        
        conn.commit()
        return conn
    
    def _setup_routes(self):
        """Setup FastAPI routes with JWT auth"""
        security = HTTPBearer()
        
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": self.service_name,
                "device_id": DEVICE_ID,
                "sync_status": self._get_sync_status()
            }
        
        @self.app.post("/auth/token")
        async def login(username: str, password: str):
            # Validate against Supabase auth
            try:
                response = self.supa.auth.sign_in_with_password({
                    "email": username,
                    "password": password
                })
                
                # Create JWT token
                access_token = jwt.encode(
                    {"sub": username, "exp": datetime.utcnow() + timedelta(hours=1)},
                    JWT_SECRET,
                    algorithm="HS256"
                )
                
                return {"access_token": access_token, "token_type": "bearer"}
            except Exception as e:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Add service-specific routes
        self._add_service_routes(security)
    
    @abstractmethod
    def _add_service_routes(self, security):
        """Override to add service-specific routes"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return service capabilities"""
        pass
    
    def _get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        cursor = self.local_db.execute("SELECT * FROM _sync_status WHERE id = 1")
        row = cursor.fetchone()
        
        if row:
            return {
                "pending_changes": row["pending_changes"],
                "last_sync": row["last_sync_ts"],
                "sync_errors": row["sync_errors"]
            }
        return {"status": "no_sync_data"}
    
    async def _sync_daemon(self):
        """Background sync to Supabase"""
        while True:
            try:
                await self._sync_batch()
                await asyncio.sleep(15)  # Sync interval
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(60)  # Retry after error
    
    async def _sync_batch(self):
        """Sync a batch of changes to Supabase"""
        # Implementation from sync_to_supabase.py
        pass
    
    # Specialized store methods
    
    def init_vector_store(self, collection_name: str):
        """Initialize Qdrant for vector operations"""
        self.vector_store = QdrantClient(
            url=os.getenv("QDRANT_URL", "localhost"),
            port=6333
        )
        # Create collection if needed
        
    def init_graph_store(self):
        """Initialize Neo4j for graph operations"""
        self.graph_store = neo4j.GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
    
    def init_cache_store(self):
        """Initialize Redis for caching"""
        self.cache_store = Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )
    
    # Hybrid operation methods
    
    def local_write(self, table: str, data: Dict[str, Any]) -> str:
        """Write to local SQLite (immediate) + queue for Supabase sync"""
        # Generate ID
        import ulid
        record_id = str(ulid.new())
        data["id"] = record_id
        
        # Write locally
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        
        self.local_db.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            list(data.values())
        )
        self.local_db.commit()
        
        # Change log entry created by trigger
        return record_id
    
    def local_read(self, table: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """Read from local SQLite (immediate)"""
        query = f"SELECT * FROM {table}"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(f"{key} = ?")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        cursor = self.local_db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    async def cloud_read(self, table: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """Read from Supabase (source of truth)"""
        query = self.supa.table(table).select("*")
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        response = query.execute()
        return response.data
    
    def vector_search(self, query_vector: List[float], limit: int = 10) -> List[Dict]:
        """Search similar vectors (if vector store initialized)"""
        if not self.vector_store:
            raise ValueError("Vector store not initialized")
        
        results = self.vector_store.search(
            collection_name=f"{self.service_name}_vectors",
            query_vector=query_vector,
            limit=limit
        )
        
        # Enrich with metadata from SQLite
        enriched = []
        for result in results:
            local_data = self.local_read("vector_metadata", {"vector_id": result.id})
            enriched.append({
                "score": result.score,
                "data": local_data[0] if local_data else None
            })
        
        return enriched
    
    def graph_query(self, cypher: str, params: Dict = None) -> List[Dict]:
        """Execute graph query (if graph store initialized)"""
        if not self.graph_store:
            raise ValueError("Graph store not initialized")
        
        with self.graph_store.session() as session:
            result = session.run(cypher, params or {})
            return [dict(record) for record in result]
    
    def cache_get(self, key: str) -> Any:
        """Get from cache (if cache store initialized)"""
        if not self.cache_store:
            return None
        
        value = self.cache_store.get(f"{self.service_name}:{key}")
        return json.loads(value) if value else None
    
    def cache_set(self, key: str, value: Any, ttl: int = 3600):
        """Set in cache (if cache store initialized)"""
        if not self.cache_store:
            return
        
        self.cache_store.setex(
            f"{self.service_name}:{key}",
            ttl,
            json.dumps(value)
        )
    
    def run(self):
        """Start the service"""
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)


# Example implementation for Scout Local MCP
class ScoutLocalMCP(HybridMCPService):
    """Scout Local MCP with hybrid architecture"""
    
    def __init__(self):
        super().__init__("scout_local", 8000)
        
        # Initialize local schema
        self._init_schema()
        
        # Optional: Initialize cache for hot data
        self.init_cache_store()
    
    def _init_schema(self):
        """Create Scout-specific tables"""
        self.local_db.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                store_id TEXT,
                product_id TEXT,
                amount REAL,
                quantity INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                price REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id TEXT PRIMARY KEY,
                query_hash TEXT,
                result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Generate sync triggers
        # (Implementation from 02_generate_triggers.sql)
    
    def get_capabilities(self) -> List[str]:
        return [
            "offline_analytics",
            "realtime_dashboard",
            "csv_export",
            "trend_analysis"
        ]
    
    def _add_service_routes(self, security):
        """Scout-specific routes"""
        
        @self.app.get("/api/v1/scout/dashboard")
        async def get_dashboard(
            timeframe: str = "today",
            auth: HTTPAuthorizationCredentials = Depends(security)
        ):
            # Check cache first
            cache_key = f"dashboard:{timeframe}"
            cached = self.cache_get(cache_key)
            if cached:
                return cached
            
            # Calculate from local data
            data = self._calculate_dashboard(timeframe)
            
            # Cache result
            self.cache_set(cache_key, data, ttl=300)  # 5 min cache
            
            return data
        
        @self.app.post("/api/v1/scout/transaction")
        async def add_transaction(
            transaction: Dict[str, Any],
            auth: HTTPAuthorizationCredentials = Depends(security)
        ):
            # Write locally (immediate)
            tx_id = self.local_write("transactions", transaction)
            
            # Return immediately (sync happens in background)
            return {"id": tx_id, "status": "recorded"}
        
        @self.app.get("/api/v1/scout/sync-status")
        async def sync_status(auth: HTTPAuthorizationCredentials = Depends(security)):
            return {
                "local_status": self._get_sync_status(),
                "device_id": DEVICE_ID,
                "capabilities": self.get_capabilities()
            }
    
    def _calculate_dashboard(self, timeframe: str) -> Dict[str, Any]:
        """Calculate dashboard metrics from local data"""
        # Implementation specific to Scout analytics
        return {
            "timeframe": timeframe,
            "total_revenue": 12345.67,
            "transactions": 234,
            "top_products": []
        }


# Example for Creative RAG MCP
class CreativeRAGMCP(HybridMCPService):
    """Creative RAG MCP with vector search"""
    
    def __init__(self):
        super().__init__("creative_rag", 8001)
        
        # Initialize vector store for similarity search
        self.init_vector_store("creative_assets")
        
        # Initialize cache for search results
        self.init_cache_store()
    
    def get_capabilities(self) -> List[str]:
        return [
            "semantic_search",
            "asset_management",
            "similarity_matching",
            "tag_extraction"
        ]
    
    def _add_service_routes(self, security):
        """Creative RAG specific routes"""
        
        @self.app.post("/api/v1/creative/search")
        async def search_assets(
            query: str,
            limit: int = 10,
            auth: HTTPAuthorizationCredentials = Depends(security)
        ):
            # Generate embedding
            embedding = self._generate_embedding(query)
            
            # Search vectors
            results = self.vector_search(embedding, limit)
            
            return {"query": query, "results": results}
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        # Implementation using sentence-transformers
        pass


if __name__ == "__main__":
    # Example: Run Scout Local MCP
    service = ScoutLocalMCP()
    service.run()