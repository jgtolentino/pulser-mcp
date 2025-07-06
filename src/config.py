from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Server settings
    app_name: str = "Pulser MCP Server"
    version: str = "0.1.0"
    debug: bool = False
    
    # Auth settings
    auth_enabled: bool = True
    jwt_secret: str = os.getenv("JWT_SECRET", "your-secret-key-here")
    jwt_algorithm: str = "HS256"
    
    # Database settings
    database_url: str = os.getenv("DATABASE_URL", "postgres://user:pass@localhost:5432/mcp_db")
    
    # Vector store settings
    vector_store_provider: str = "pgvector"
    embedding_model: str = "text-embedding-ada-002"
    
    # Azure OpenAI settings
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_key: str = os.getenv("AZURE_OPENAI_KEY", "")
    
    # OpenAI settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Anthropic settings
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # DeepSeek settings
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1000
    rate_limit_interval: str = "minute"
    
    # CORS settings
    cors_allowed_origins: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"