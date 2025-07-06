# Unified MCP Server - Cross-Agent Analytics Hub

MindsDB-powered unified analytics platform that connects all Pulser agents' data sources for comprehensive insights.

## Features

- **Unified Querying**: Query across all agent data sources with natural language
- **Cross-Agent Analysis**: Discover correlations and patterns between agents
- **Predictive Modeling**: Create ML models using MindsDB's AutoML
- **Multi-Source Integration**: Connect Slack, Gmail, GitHub, databases, APIs
- **Real-Time Analytics**: Live dashboards and monitoring

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/unified_mcp
   ./scripts/setup.sh
   ```

2. **Start Server**:
   ```bash
   source venv/bin/activate
   python src/unified_server.py
   ```

3. **Access Interfaces**:
   - MindsDB Studio: http://localhost:8891
   - Unified MCP API: http://localhost:8004
   - MindsDB SQL: `mysql -h 127.0.0.1 -P 47335 -u mindsdb -pmindsdb123`

## Available Tools

### query_unified
Query across all connected data sources:
```json
{
  "tool": "query_unified",
  "params": {
    "query": "Show revenue trends across all channels last month",
    "sources": ["scout_metrics", "financial_kpis"],
    "timeframe": "1M",
    "output_format": "chart"
  }
}
```

### analyze_cross_agent
Find patterns between agents:
```json
{
  "tool": "analyze_cross_agent",
  "params": {
    "analysis_type": "correlation",
    "agents": ["scout_edge", "creative_rag", "financial_analyst"],
    "metrics": ["revenue", "engagement", "conversion"]
  }
}
```

### create_model
Build predictive models:
```json
{
  "tool": "create_model",
  "params": {
    "target_metric": "revenue",
    "features": ["engagement", "conversion", "spend"],
    "model_type": "timeseries",
    "training_window": "90D"
  }
}
```

### add_source
Connect new data sources:
```json
{
  "tool": "add_source",
  "params": {
    "name": "salesforce_crm",
    "type": "database",
    "connection_params": {
      "engine": "postgresql",
      "host": "salesforce.db.example.com",
      "database": "crm"
    },
    "sync_interval": 1800
  }
}
```

## Data Sources

### Pre-configured Sources
- **scout_metrics**: Scout Edge performance data
- **creative_insights**: Creative RAG search analytics
- **voice_analytics**: Voice Agent call metrics
- **financial_kpis**: Financial Analyst predictions
- **slack_workspace**: Team communications
- **gmail_account**: Email insights
- **github_repos**: Development activity

### Adding Custom Sources

#### Slack Integration
```python
{
  "name": "company_slack",
  "type": "slack",
  "connection_params": {
    "bot_token": "xoxb-...",
    "channels": ["#sales", "#support"]
  }
}
```

#### Database Connection
```python
{
  "name": "analytics_db",
  "type": "database", 
  "connection_params": {
    "engine": "mysql",
    "host": "analytics.db.internal",
    "port": 3306,
    "database": "metrics"
  }
}
```

## MindsDB SQL Examples

### Create Predictor
```sql
CREATE PREDICTOR mindsdb.revenue_forecast
FROM unified_analytics
  (SELECT date, revenue, engagement, conversion
   FROM agent_metrics
   WHERE agent_name = 'scout_edge')
PREDICT revenue
ORDER BY date
WINDOW 30
HORIZON 7;
```

### Query Predictions
```sql
SELECT date, revenue, revenue_confidence
FROM mindsdb.revenue_forecast
WHERE date > NOW()
LIMIT 7;
```

### Join Multiple Sources
```sql
SELECT s.*, c.sentiment, v.call_duration
FROM scout_metrics s
JOIN creative_insights c ON s.brand = c.brand
JOIN voice_analytics v ON s.date = v.date
WHERE s.date >= '2024-01-01';
```

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Pulser Agents  │────▶│ Unified MCP  │────▶│   MindsDB   │
└─────────────────┘     └──────────────┘     └─────────────┘
        │                       │                     │
        ▼                       ▼                     ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Data Sources   │     │    Redis     │     │ PostgreSQL  │
└─────────────────┘     └──────────────┘     └─────────────┘
```

## Cross-Agent Analytics

### Correlation Analysis
Discover relationships between different agents:
```python
# Find correlation between creative performance and sales
correlation = analyze_cross_agent({
    "analysis_type": "correlation",
    "agents": ["creative_rag", "scout_edge"],
    "metrics": ["engagement", "revenue"]
})
```

### Anomaly Detection
Identify unusual patterns across agents:
```python
# Detect anomalies in agent response times
anomalies = analyze_cross_agent({
    "analysis_type": "anomaly",
    "agents": ["all"],
    "metrics": ["response_time", "error_rate"]
})
```

### Trend Forecasting
Predict future trends using combined data:
```python
# Forecast using multiple agent inputs
forecast = create_model({
    "target_metric": "total_revenue",
    "features": ["scout_sales", "creative_views", "voice_leads"],
    "model_type": "ensemble"
})
```

## Monitoring & Alerts

Set up alerts for cross-agent metrics:
```sql
CREATE JOB alert_performance_drop
START NOW
EVERY 5 minutes
AS (
  SELECT agent_name, metric_value
  FROM agent_metrics
  WHERE metric_name = 'accuracy'
    AND metric_value < 0.9
    AND timestamp > NOW() - INTERVAL '5 minutes'
);
```

## Best Practices

1. **Query Optimization**: Use specific sources when possible
2. **Cache Strategy**: Leverage Redis for repeated queries
3. **Model Management**: Version and monitor predictive models
4. **Data Governance**: Set appropriate access controls

## Troubleshooting

- **MindsDB Connection**: Check Docker containers are running
- **Slow Queries**: Review source indexing and caching
- **Model Accuracy**: Ensure sufficient training data
- **Integration Errors**: Verify API credentials

## License

Part of InsightPulseAI SKR - Proprietary