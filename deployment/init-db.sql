-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    agent VARCHAR(50),
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops);

-- Create search logs table
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    results_count INTEGER,
    query_time_ms FLOAT,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create generation logs table
CREATE TABLE IF NOT EXISTS generation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT NOT NULL,
    output TEXT,
    model VARCHAR(50),
    tokens_used JSONB,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create analysis logs table
CREATE TABLE IF NOT EXISTS analysis_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_url TEXT,
    content_hash VARCHAR(64),
    analysis_type VARCHAR(50),
    results JSONB,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create command logs table
CREATE TABLE IF NOT EXISTS command_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command TEXT NOT NULL,
    agent VARCHAR(50),
    environment VARCHAR(50),
    result TEXT,
    success BOOLEAN,
    execution_time_ms FLOAT,
    user_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX search_logs_created_at_idx ON search_logs(created_at DESC);
CREATE INDEX generation_logs_created_at_idx ON generation_logs(created_at DESC);
CREATE INDEX analysis_logs_created_at_idx ON analysis_logs(created_at DESC);
CREATE INDEX command_logs_created_at_idx ON command_logs(created_at DESC);

-- Insert sample data
INSERT INTO documents (title, content, agent, metadata) VALUES
    ('MCP Integration Guide', 'How to integrate MCP with Pulser agents for seamless AI orchestration', 'claudia', '{"tags": ["mcp", "integration", "guide"]}'),
    ('Agent Orchestration Patterns', 'Best practices for multi-agent coordination in complex workflows', 'maya', '{"tags": ["orchestration", "patterns", "best-practices"]}'),
    ('Vector Search Optimization', 'Techniques for optimizing vector similarity search in production', 'kalaw', '{"tags": ["vector", "search", "optimization"]}');