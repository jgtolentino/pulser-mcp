-- Initialize unified analytics database

-- Agent metrics table
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_type VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Cross-agent correlations
CREATE TABLE IF NOT EXISTS agent_correlations (
    id SERIAL PRIMARY KEY,
    agent1 VARCHAR(100) NOT NULL,
    agent2 VARCHAR(100) NOT NULL,
    correlation_coefficient DECIMAL(5,4),
    p_value DECIMAL(5,4),
    analysis_date DATE DEFAULT CURRENT_DATE,
    metrics JSONB
);

-- Data source registry
CREATE TABLE IF NOT EXISTS data_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    connection_params JSONB,
    last_sync TIMESTAMP,
    sync_interval INTEGER DEFAULT 3600,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Model registry
CREATE TABLE IF NOT EXISTS predictive_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(200) UNIQUE NOT NULL,
    target_metric VARCHAR(100),
    features TEXT[],
    model_type VARCHAR(50),
    training_params JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Query history
CREATE TABLE IF NOT EXISTS query_history (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    sources_queried TEXT[],
    execution_time_ms INTEGER,
    result_count INTEGER,
    user_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_agent_metrics_timestamp ON agent_metrics(timestamp);
CREATE INDEX idx_agent_metrics_agent_name ON agent_metrics(agent_name);
CREATE INDEX idx_correlations_agents ON agent_correlations(agent1, agent2);
CREATE INDEX idx_query_history_timestamp ON query_history(timestamp);

-- Insert default data sources
INSERT INTO data_sources (source_name, source_type, connection_params) VALUES
('scout_metrics', 'database', '{"engine": "postgresql", "table": "predicted_metrics"}'),
('creative_insights', 'api', '{"url": "http://localhost:8001/mcp/tools/search_vector"}'),
('voice_analytics', 'supabase', '{"table": "call_analytics"}'),
('financial_kpis', 'api', '{"url": "http://localhost:8002/mcp/tools/analyze_kpis"}'),
('slack_workspace', 'slack', '{"workspace": "insightpulse", "channels": ["#general", "#sales"]}'),
('gmail_account', 'gmail', '{"account": "insights@company.com"}'),
('github_repos', 'github', '{"org": "InsightPulseAI", "repos": ["SKR", "Scout"]}')
ON CONFLICT (source_name) DO NOTHING;

-- Sample agent metrics
INSERT INTO agent_metrics (agent_name, metric_name, metric_value, metric_type) VALUES
('scout_edge', 'response_time', 145.5, 'performance'),
('scout_edge', 'accuracy', 0.945, 'quality'),
('creative_rag', 'queries_per_hour', 1250, 'volume'),
('creative_rag', 'cache_hit_rate', 0.78, 'performance'),
('financial_analyst', 'predictions_made', 3200, 'volume'),
('financial_analyst', 'mape', 0.082, 'accuracy'),
('voice_agent', 'calls_handled', 450, 'volume'),
('voice_agent', 'avg_call_duration', 185.3, 'performance');

-- Sample correlations
INSERT INTO agent_correlations (agent1, agent2, correlation_coefficient, p_value, metrics) VALUES
('scout_edge', 'financial_analyst', 0.8234, 0.0012, '{"metrics": ["revenue", "engagement"]}'),
('creative_rag', 'voice_agent', 0.6521, 0.0234, '{"metrics": ["sentiment", "conversion"]}');

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mindsdb;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mindsdb;