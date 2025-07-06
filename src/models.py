from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums
class ContentType(str, Enum):
    text = "text"
    code = "code"
    image = "image"
    summary = "summary"
    analysis = "analysis"

class AnalysisType(str, Enum):
    summary = "summary"
    sentiment = "sentiment"
    entities = "entities"
    keywords = "keywords"
    comprehensive = "comprehensive"

class ModelProvider(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    deepseek = "deepseek"

# Search models
class SearchFilters(BaseModel):
    agent: Optional[str] = None
    date_range: Optional[Dict[str, datetime]] = None
    tags: Optional[List[str]] = None

class SearchRequest(BaseModel):
    query: str = Field(..., description="The semantic query to search")
    filters: Optional[SearchFilters] = None
    limit: int = Field(10, ge=1, le=100)

class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    agent: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query_time_ms: float

# Generate models
class GenerateParameters(BaseModel):
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(2000, ge=1, le=8000)
    style: Optional[str] = None
    language: Optional[str] = None

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gpt-4-turbo"
    type: ContentType = ContentType.text
    parameters: Optional[GenerateParameters] = None

class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int

class GenerateResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    output: str
    model_used: str
    tokens_used: Optional[TokenUsage] = None
    metadata: Optional[Dict[str, Any]] = None

# Analyze models
class AnalyzeOptions(BaseModel):
    language: Optional[str] = None
    max_summary_length: Optional[int] = None
    extract_tables: Optional[bool] = False
    extract_images: Optional[bool] = False

class AnalyzeRequest(BaseModel):
    document_url: Optional[str] = None
    content: Optional[str] = None
    analysis_type: AnalysisType = AnalysisType.comprehensive
    options: Optional[AnalyzeOptions] = None

class SentimentAnalysis(BaseModel):
    score: float = Field(..., ge=-1, le=1)
    label: str

class Entity(BaseModel):
    text: str
    type: str
    confidence: float

class Keyword(BaseModel):
    keyword: str
    score: float

class AnalyzeMetadata(BaseModel):
    word_count: int
    language: str
    processing_time_ms: float

class AnalyzeResponse(BaseModel):
    summary: str
    sentiment: Optional[SentimentAnalysis] = None
    entities: Optional[List[Entity]] = None
    keywords: Optional[List[Keyword]] = None
    metadata: Optional[AnalyzeMetadata] = None

# Command models
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

# System models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class StatusResponse(BaseModel):
    status: str
    active_models: List[str]
    active_agents: List[str]
    queue_depth: int
    timestamp: str

class Tool(BaseModel):
    name: str
    description: str

class Model(BaseModel):
    name: str
    provider: str

class Agent(BaseModel):
    id: str
    role: str

class CapabilitiesResponse(BaseModel):
    tools: List[Tool]
    models: List[Model]
    agents: List[Agent]