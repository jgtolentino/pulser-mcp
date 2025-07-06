#!/usr/bin/env python3
"""
Creative RAG MCP Server - Vector-based search for creative assets
Powered by Qdrant for ColPali embeddings of storyboards and thumbnails
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
import uvicorn
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import numpy as np
from PIL import Image
import io
import logging
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
COLLECTION_NAME = "creative_assets"
VECTOR_SIZE = 768  # ColPali embedding size

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

app = FastAPI(title="Creative RAG MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Pydantic models
class AssetIngestion(BaseModel):
    asset_id: str
    asset_type: str  # storyboard, thumbnail, video_frame, creative_brief
    brand: str
    campaign: Optional[str] = None
    metadata: Dict[str, Any] = {}
    text_content: Optional[str] = None
    image_url: Optional[str] = None

class VectorSearchQuery(BaseModel):
    query: str
    query_type: str = "text"  # text, image, hybrid
    top_k: int = 10
    filters: Optional[Dict[str, Any]] = {}

class WebSearchQuery(BaseModel):
    query: str
    domains: Optional[List[str]] = []
    max_results: int = 10

# Initialize Qdrant client
qdrant_client = None

def init_qdrant():
    """Initialize Qdrant client and create collection if needed"""
    global qdrant_client
    try:
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if COLLECTION_NAME not in collection_names:
            # Create collection with ColPali-compatible settings
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
        else:
            logger.info(f"Using existing Qdrant collection: {COLLECTION_NAME}")
            
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        raise

# Mock embedding function (replace with actual ColPali)
def generate_embedding(content: str, content_type: str = "text") -> List[float]:
    """Generate embeddings for content (mock implementation)"""
    # In production, use actual ColPali or similar model
    # This is a deterministic mock based on content hash
    content_hash = hashlib.md5(f"{content}{content_type}".encode()).hexdigest()
    np.random.seed(int(content_hash[:8], 16))
    return np.random.randn(VECTOR_SIZE).tolist()

# MCP Tools
class MCPTools:
    @staticmethod
    async def ingest_asset(asset: AssetIngestion) -> Dict[str, Any]:
        """Ingest creative asset into vector database"""
        try:
            # Generate unique point ID
            point_id = hashlib.md5(asset.asset_id.encode()).hexdigest()[:16]
            
            # Prepare content for embedding
            embedding_content = ""
            if asset.text_content:
                embedding_content = asset.text_content
            elif asset.image_url:
                # In production, download and process image with ColPali
                embedding_content = f"Image from {asset.image_url}"
            
            # Generate embedding
            embedding = generate_embedding(embedding_content, asset.asset_type)
            
            # Prepare payload
            payload = {
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "brand": asset.brand,
                "campaign": asset.campaign,
                "metadata": asset.metadata,
                "ingested_at": datetime.now().isoformat(),
                "content_preview": embedding_content[:200] if embedding_content else ""
            }
            
            # Store in Qdrant
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )
            
            return {
                "success": True,
                "asset_id": asset.asset_id,
                "point_id": point_id,
                "message": "Asset ingested successfully"
            }
            
        except Exception as e:
            logger.error(f"Error ingesting asset: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def search_vector(query: VectorSearchQuery) -> Dict[str, Any]:
        """Search creative assets using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = generate_embedding(query.query, query.query_type)
            
            # Build filter conditions
            filter_conditions = []
            if query.filters:
                for key, value in query.filters.items():
                    filter_conditions.append({
                        "key": key,
                        "match": {"value": value}
                    })
            
            # Search in Qdrant
            search_result = qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                limit=query.top_k,
                query_filter={"must": filter_conditions} if filter_conditions else None
            )
            
            # Format results
            results = []
            for hit in search_result:
                result = {
                    "score": hit.score,
                    "asset_id": hit.payload.get("asset_id"),
                    "asset_type": hit.payload.get("asset_type"),
                    "brand": hit.payload.get("brand"),
                    "campaign": hit.payload.get("campaign"),
                    "content_preview": hit.payload.get("content_preview"),
                    "metadata": hit.payload.get("metadata", {})
                }
                results.append(result)
            
            return {
                "success": True,
                "query": query.query,
                "results_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def search_web(query: WebSearchQuery) -> Dict[str, Any]:
        """Search web for creative references (using Pulser WebSearch agent)"""
        try:
            # In production, integrate with actual web search API
            # For now, return mock results
            mock_results = [
                {
                    "title": f"Creative Campaign: {query.query}",
                    "url": f"https://example.com/campaign/{i}",
                    "snippet": f"Award-winning campaign featuring {query.query}...",
                    "domain": "example.com",
                    "relevance_score": 0.9 - (i * 0.1)
                }
                for i in range(min(5, query.max_results))
            ]
            
            # Filter by domains if specified
            if query.domains:
                mock_results = [r for r in mock_results if r["domain"] in query.domains]
            
            return {
                "success": True,
                "query": query.query,
                "results_count": len(mock_results),
                "results": mock_results[:query.max_results]
            }
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return {"success": False, "error": str(e)}

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    init_qdrant()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "active", "service": "Creative RAG MCP Server"}

@api_v1.post("/mcp/tools/ingest_asset")
async def ingest_asset(asset: AssetIngestion, current_user: str = Depends(verify_token)):
    """MCP endpoint for asset ingestion"""
    result = await MCPTools.ingest_asset(asset)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/search_vector")
async def search_vector(query: VectorSearchQuery, current_user: str = Depends(verify_token)):
    """MCP endpoint for vector search"""
    result = await MCPTools.search_vector(query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/search_web")
async def search_web(query: WebSearchQuery, current_user: str = Depends(verify_token)):
    """MCP endpoint for web search"""
    result = await MCPTools.search_web(query)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/ingest_image")
async def ingest_image(
    asset_id: str,
    brand: str,
    asset_type: str = "image",
    campaign: Optional[str] = None,
    file: UploadFile = File(...)
, current_user: str = Depends(verify_token)):
    """Direct image upload endpoint"""
    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Extract basic metadata
        metadata = {
            "filename": file.filename,
            "size": len(contents),
            "format": image.format,
            "dimensions": f"{image.width}x{image.height}"
        }
        
        # Create asset ingestion request
        asset = AssetIngestion(
            asset_id=asset_id,
            asset_type=asset_type,
            brand=brand,
            campaign=campaign,
            metadata=metadata,
            text_content=f"Image: {file.filename}"
        )
        
        result = await MCPTools.ingest_asset(asset)
        return result
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# MCP metadata endpoint
@api_v1.get("/mcp/metadata")
async def get_metadata(current_user: str = Depends(verify_token)):
    """Return MCP server metadata"""
    return {
        "name": "creative-rag-mcp",
        "version": "1.0.0",
        "description": "Vector-based RAG for creative assets using Qdrant",
        "tools": [
            {
                "name": "ingest_asset",
                "description": "Ingest creative asset into vector database",
                "parameters": {
                    "asset_id": "string",
                    "asset_type": "string (storyboard, thumbnail, video_frame, creative_brief)",
                    "brand": "string",
                    "campaign": "string (optional)",
                    "metadata": "object (optional)",
                    "text_content": "string (optional)",
                    "image_url": "string (optional)"
                }
            },
            {
                "name": "search_vector",
                "description": "Search assets using vector similarity",
                "parameters": {
                    "query": "string",
                    "query_type": "string (text, image, hybrid)",
                    "top_k": "integer (default: 10)",
                    "filters": "object (optional)"
                }
            },
            {
                "name": "search_web",
                "description": "Search web for creative references",
                "parameters": {
                    "query": "string",
                    "domains": "array[string] (optional)",
                    "max_results": "integer (default: 10)"
                }
            }
        ]
    }


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)