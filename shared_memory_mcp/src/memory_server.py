#!/usr/bin/env python3
"""
Shared Memory MCP Server - Graphiti-powered episodic memory for cross-agent communication
Enables Scout Edge and CES to share insights and context
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import uvicorn
from neo4j import GraphDatabase
import redis
import hashlib
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "graphiti123")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6381")
MEMORY_TTL_DAYS = int(os.getenv("MEMORY_TTL_DAYS", 30))

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

app = FastAPI(title="Shared Memory MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Memory types
class MemoryType(str, Enum):
    FACT = "fact"
    INSIGHT = "insight"
    DECISION = "decision"
    CONTEXT = "context"
    RELATIONSHIP = "relationship"

# Pydantic models
class MemoryEntry(BaseModel):
    content: str
    memory_type: MemoryType
    source_agent: str
    conversation_id: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    ttl_days: Optional[int] = MEMORY_TTL_DAYS

class MemoryQuery(BaseModel):
    query: str
    agents: Optional[List[str]] = []
    memory_types: Optional[List[MemoryType]] = []
    tags: Optional[List[str]] = []
    limit: int = 10
    include_expired: bool = False

class MemoryRelation(BaseModel):
    from_memory_id: str
    to_memory_id: str
    relation_type: str
    properties: Dict[str, Any] = {}

class MemoryUpdate(BaseModel):
    memory_id: str
    updates: Dict[str, Any]
    extend_ttl: bool = True

# Neo4j connection
class GraphitiMemory:
    def __init__(self):
        self.driver = None
        self.redis_client = None
        
    def connect(self):
        """Initialize connections"""
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            self.driver.verify_connectivity()
            logger.info("Neo4j connection established")
            
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Create indexes
            self._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    def _create_indexes(self):
        """Create necessary indexes in Neo4j"""
        with self.driver.session() as session:
            # Memory node indexes
            session.run("""
                CREATE INDEX memory_id IF NOT EXISTS
                FOR (m:Memory) ON (m.id)
            """)
            session.run("""
                CREATE INDEX memory_agent IF NOT EXISTS
                FOR (m:Memory) ON (m.source_agent)
            """)
            session.run("""
                CREATE INDEX memory_type IF NOT EXISTS
                FOR (m:Memory) ON (m.memory_type)
            """)
            session.run("""
                CREATE INDEX memory_created IF NOT EXISTS
                FOR (m:Memory) ON (m.created_at)
            """)
            
            # Tag index
            session.run("""
                CREATE INDEX tag_name IF NOT EXISTS
                FOR (t:Tag) ON (t.name)
            """)
    
    def close(self):
        """Close connections"""
        if self.driver:
            self.driver.close()
        if self.redis_client:
            self.redis_client.close()

# MCP Tools
class MCPTools:
    @staticmethod
    async def store_memory(memory: MemoryEntry) -> Dict[str, Any]:
        """Store a memory entry in the graph"""
        try:
            memory_id = str(uuid.uuid4())
            created_at = datetime.now()
            expires_at = created_at + timedelta(days=memory.ttl_days or MEMORY_TTL_DAYS)
            
            # Generate embedding (mock - replace with actual embedding model)
            embedding = MCPTools._generate_embedding(memory.content)
            
            with app.state.memory.driver.session() as session:
                # Create memory node
                result = session.run("""
                    CREATE (m:Memory {
                        id: $id,
                        content: $content,
                        memory_type: $memory_type,
                        source_agent: $source_agent,
                        conversation_id: $conversation_id,
                        created_at: datetime($created_at),
                        expires_at: datetime($expires_at),
                        embedding: $embedding,
                        metadata: $metadata
                    })
                    RETURN m
                """, {
                    "id": memory_id,
                    "content": memory.content,
                    "memory_type": memory.memory_type,
                    "source_agent": memory.source_agent,
                    "conversation_id": memory.conversation_id,
                    "created_at": created_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "embedding": embedding,
                    "metadata": json.dumps(memory.metadata)
                })
                
                # Add tags
                for tag in memory.tags:
                    session.run("""
                        MERGE (t:Tag {name: $tag})
                        WITH t
                        MATCH (m:Memory {id: $memory_id})
                        CREATE (m)-[:TAGGED_WITH]->(t)
                    """, {"tag": tag, "memory_id": memory_id})
                
                # Cache in Redis for fast access
                cache_key = f"memory:{memory_id}"
                app.state.memory.redis_client.setex(
                    cache_key,
                    86400,  # 24 hour cache
                    json.dumps({
                        "id": memory_id,
                        "content": memory.content,
                        "source_agent": memory.source_agent,
                        "created_at": created_at.isoformat()
                    })
                )
            
            return {
                "success": True,
                "memory_id": memory_id,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def recall_memories(query: MemoryQuery) -> Dict[str, Any]:
        """Recall memories based on query"""
        try:
            # Check cache first
            cache_key = f"recall:{hashlib.md5(json.dumps(query.dict(), sort_keys=True).encode()).hexdigest()}"
            cached = app.state.memory.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Build Cypher query
            where_clauses = []
            params = {"limit": query.limit}
            
            if query.agents:
                where_clauses.append("m.source_agent IN $agents")
                params["agents"] = query.agents
            
            if query.memory_types:
                where_clauses.append("m.memory_type IN $types")
                params["types"] = [t.value for t in query.memory_types]
            
            if not query.include_expired:
                where_clauses.append("m.expires_at > datetime()")
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Vector similarity search (mock - replace with actual vector search)
            query_embedding = MCPTools._generate_embedding(query.query)
            
            with app.state.memory.driver.session() as session:
                # Fetch memories with similarity score
                result = session.run(f"""
                    MATCH (m:Memory)
                    WHERE {where_clause}
                    WITH m, gds.similarity.cosine(m.embedding, $query_embedding) AS similarity
                    WHERE similarity > 0.7
                    OPTIONAL MATCH (m)-[:TAGGED_WITH]->(t:Tag)
                    RETURN m, collect(t.name) as tags, similarity
                    ORDER BY similarity DESC
                    LIMIT $limit
                """, {**params, "query_embedding": query_embedding})
                
                memories = []
                for record in result:
                    memory_node = record["m"]
                    memories.append({
                        "id": memory_node["id"],
                        "content": memory_node["content"],
                        "memory_type": memory_node["memory_type"],
                        "source_agent": memory_node["source_agent"],
                        "created_at": memory_node["created_at"],
                        "tags": record["tags"],
                        "similarity": record["similarity"],
                        "metadata": json.loads(memory_node.get("metadata", "{}"))
                    })
            
            response = {
                "success": True,
                "query": query.query,
                "memories_found": len(memories),
                "memories": memories
            }
            
            # Cache results
            app.state.memory.redis_client.setex(cache_key, 300, json.dumps(response))
            
            return response
            
        except Exception as e:
            logger.error(f"Error recalling memories: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def create_relation(relation: MemoryRelation) -> Dict[str, Any]:
        """Create relationship between memories"""
        try:
            with app.state.memory.driver.session() as session:
                result = session.run("""
                    MATCH (from:Memory {id: $from_id})
                    MATCH (to:Memory {id: $to_id})
                    CREATE (from)-[r:RELATES_TO {
                        type: $relation_type,
                        created_at: datetime(),
                        properties: $properties
                    }]->(to)
                    RETURN r
                """, {
                    "from_id": relation.from_memory_id,
                    "to_id": relation.to_memory_id,
                    "relation_type": relation.relation_type,
                    "properties": json.dumps(relation.properties)
                })
                
                if result.peek():
                    return {
                        "success": True,
                        "relation_created": True,
                        "from": relation.from_memory_id,
                        "to": relation.to_memory_id,
                        "type": relation.relation_type
                    }
                else:
                    return {
                        "success": False,
                        "error": "One or both memories not found"
                    }
                    
        except Exception as e:
            logger.error(f"Error creating relation: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_memory_graph(memory_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get memory and its relationships"""
        try:
            with app.state.memory.driver.session() as session:
                result = session.run("""
                    MATCH path = (m:Memory {id: $memory_id})-[*0..$depth]-(connected)
                    WITH m, collect(distinct connected) as connected_nodes,
                         collect(distinct relationships(path)) as all_rels
                    RETURN m, connected_nodes, all_rels
                """, {"memory_id": memory_id, "depth": depth})
                
                record = result.single()
                if not record:
                    return {"success": False, "error": "Memory not found"}
                
                # Format response
                central_memory = record["m"]
                connected = record["connected_nodes"]
                
                nodes = [{
                    "id": central_memory["id"],
                    "content": central_memory["content"],
                    "type": central_memory["memory_type"],
                    "agent": central_memory["source_agent"]
                }]
                
                for node in connected:
                    if "Memory" in node.labels:
                        nodes.append({
                            "id": node["id"],
                            "content": node["content"],
                            "type": node["memory_type"],
                            "agent": node["source_agent"]
                        })
                
                # Extract relationships
                edges = []
                for rel_list in record["all_rels"]:
                    for rel in rel_list:
                        edges.append({
                            "from": rel.start_node["id"],
                            "to": rel.end_node["id"],
                            "type": rel.type,
                            "properties": dict(rel)
                        })
                
                return {
                    "success": True,
                    "central_memory": memory_id,
                    "nodes": nodes,
                    "edges": edges,
                    "depth": depth
                }
                
        except Exception as e:
            logger.error(f"Error getting memory graph: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _generate_embedding(text: str) -> List[float]:
        """Generate text embedding (mock implementation)"""
        # In production, use actual embedding model
        # This is a deterministic mock based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        import random
        random.seed(seed)
        return [random.random() for _ in range(768)]

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    app.state.memory = GraphitiMemory()
    app.state.memory.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    if hasattr(app.state, "memory"):
        app.state.memory.close()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "active",
        "service": "Shared Memory MCP Server",
        "neo4j_browser": "http://localhost:7474"
    }

@api_v1.post("/mcp/tools/store_memory")
async def store_memory(memory: MemoryEntry, current_user: str = Depends(verify_token)):
    """Store a memory entry"""
    result = await MCPTools.store_memory(memory)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/recall_memories")
async def recall_memories(query: MemoryQuery, current_user: str = Depends(verify_token)):
    """Recall memories based on query"""
    result = await MCPTools.recall_memories(query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/create_relation")
async def create_relation(relation: MemoryRelation, current_user: str = Depends(verify_token)):
    """Create relationship between memories"""
    result = await MCPTools.create_relation(relation)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.get("/mcp/tools/get_memory_graph/{memory_id}")
async def get_memory_graph(memory_id: str, depth: int = 2, current_user: str = Depends(verify_token)):
    """Get memory and its relationships"""
    result = await MCPTools.get_memory_graph(memory_id, depth)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@api_v1.delete("/mcp/tools/forget_memory/{memory_id}")
async def forget_memory(memory_id: str, current_user: str = Depends(verify_token)):
    """Delete a memory (GDPR compliance)"""
    try:
        with app.state.memory.driver.session() as session:
            session.run("""
                MATCH (m:Memory {id: $memory_id})
                DETACH DELETE m
            """, {"memory_id": memory_id})
        
        # Clear from cache
        app.state.memory.redis_client.delete(f"memory:{memory_id}")
        
        return {"success": True, "forgotten": memory_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# MCP metadata endpoint
@api_v1.get("/mcp/metadata")
async def get_metadata(current_user: str = Depends(verify_token)):
    """Return MCP server metadata"""
    return {
        "name": "shared-memory-mcp",
        "version": "1.0.0",
        "description": "Graphiti-powered shared episodic memory for cross-agent communication",
        "tools": [
            {
                "name": "store_memory",
                "description": "Store a memory entry in the graph",
                "parameters": {
                    "content": "string",
                    "memory_type": "enum (fact, insight, decision, context, relationship)",
                    "source_agent": "string",
                    "conversation_id": "string (optional)",
                    "tags": "array[string]",
                    "metadata": "object",
                    "ttl_days": "integer (optional)"
                }
            },
            {
                "name": "recall_memories",
                "description": "Recall relevant memories",
                "parameters": {
                    "query": "string",
                    "agents": "array[string] (optional)",
                    "memory_types": "array[enum] (optional)",
                    "tags": "array[string] (optional)",
                    "limit": "integer (default: 10)",
                    "include_expired": "boolean (default: false)"
                }
            },
            {
                "name": "create_relation",
                "description": "Create relationship between memories",
                "parameters": {
                    "from_memory_id": "string",
                    "to_memory_id": "string",
                    "relation_type": "string",
                    "properties": "object (optional)"
                }
            },
            {
                "name": "get_memory_graph",
                "description": "Get memory and its relationships",
                "parameters": {
                    "memory_id": "string",
                    "depth": "integer (default: 2)"
                }
            }
        ]
    }


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5700)