from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

# Import our models and handlers
from .models import (
    SearchRequest, SearchResponse, 
    GenerateRequest, GenerateResponse,
    AnalyzeRequest, AnalyzeResponse,
    HealthResponse, StatusResponse, CapabilitiesResponse
)
from .handlers import SearchHandler, GenerateHandler, AnalyzeHandler, CommandHandler

app = FastAPI(
    title="Pulser MCP Server",
    version="0.1.0",
    description="A unified MCP server for Pulser agents",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize handlers
search_handler = SearchHandler()
generate_handler = GenerateHandler()
analyze_handler = AnalyzeHandler()
command_handler = CommandHandler()

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0"
    )

# Status endpoint
@app.get("/status", response_model=StatusResponse)
async def status():
    return StatusResponse(
        status="operational",
        active_models=["claude-3-opus", "gpt-4-turbo", "deepseek-coder"],
        active_agents=["claudia", "maya", "kalaw", "surf", "basher"],
        queue_depth=0,
        timestamp=datetime.utcnow().isoformat()
    )

# Capabilities endpoint
@app.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    return CapabilitiesResponse(
        tools=[
            {"name": "search", "description": "Vector search from semantic queries"},
            {"name": "generate", "description": "Create content from prompts"},
            {"name": "analyze", "description": "Extract insights from documents"},
            {"name": "execute", "description": "Execute commands through bridges"}
        ],
        models=[
            {"name": "claude-3-opus", "provider": "anthropic"},
            {"name": "gpt-4-turbo", "provider": "openai"},
            {"name": "deepseek-coder", "provider": "deepseek"}
        ],
        agents=[
            {"id": "claudia", "role": "Strategic Orchestrator"},
            {"id": "maya", "role": "Process Architect"},
            {"id": "kalaw", "role": "Research Indexer"},
            {"id": "surf", "role": "Engineering Expert"},
            {"id": "basher", "role": "Systems Automator"}
        ]
    )

# Search endpoint
@app.post("/tools/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    try:
        results = await search_handler.search(
            query=request.query,
            filters=request.filters.dict() if request.filters else None,
            limit=request.limit
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generate endpoint
@app.post("/tools/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    try:
        response = await generate_handler.generate(
            prompt=request.prompt,
            model=request.model,
            content_type=request.type.value,
            parameters=request.parameters.dict() if request.parameters else None
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analyze endpoint
@app.post("/tools/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    try:
        response = await analyze_handler.analyze(
            document_url=request.document_url,
            content=request.content,
            analysis_type=request.analysis_type.value,
            options=request.options.dict() if request.options else None
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simple command execution endpoint (without auth for demo)
class CommandRequest(BaseModel):
    command: str
    agent: str
    environment: str = "terminal"
    parameters: Optional[Dict[str, Any]] = None

class CommandResponse(BaseModel):
    result: str
    success: bool
    agent_used: str
    execution_time_ms: float
    metadata: Optional[Dict[str, Any]] = None

@app.post("/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    try:
        response = await command_handler.execute(
            command=request.command,
            agent=request.agent,
            environment=request.environment,
            parameters=request.parameters
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Pulser MCP Server",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "status": "/status",
        "capabilities": "/capabilities"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)