from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

# Simple Pydantic models
class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query_time_ms: float

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gpt-4-turbo"

class GenerateResponse(BaseModel):
    output: str
    model_used: str

class AnalyzeRequest(BaseModel):
    content: str

class AnalyzeResponse(BaseModel):
    summary: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Create FastAPI app
app = FastAPI(
    title="Pulser MCP Server",
    version="0.1.0",
    description="A unified MCP server for Pulser agents"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
mock_documents = [
    {
        "id": "1",
        "title": "MCP Integration Guide",
        "content": "How to integrate MCP with Pulser agents for seamless AI orchestration",
        "score": 0.95
    },
    {
        "id": "2", 
        "title": "Agent Orchestration Patterns",
        "content": "Best practices for multi-agent coordination in complex workflows",
        "score": 0.88
    }
]

@app.get("/")
async def root():
    return {
        "message": "Pulser MCP Server",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0"
    )

@app.post("/tools/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    start_time = datetime.utcnow()
    
    # Mock search with filtering
    results = []
    for doc in mock_documents[:request.limit]:
        if request.query.lower() in doc["content"].lower():
            results.append(SearchResult(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"],
                score=doc["score"]
            ))
    
    query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    return SearchResponse(
        results=results,
        total=len(results),
        query_time_ms=query_time
    )

@app.post("/tools/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    await asyncio.sleep(0.1)  # Simulate processing
    
    return GenerateResponse(
        output=f"Generated response using {request.model} for: {request.prompt[:50]}...",
        model_used=request.model
    )

@app.post("/tools/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    await asyncio.sleep(0.1)  # Simulate processing
    
    return AnalyzeResponse(
        summary=f"Analysis of {len(request.content.split())} words: This content discusses MCP integration patterns."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)