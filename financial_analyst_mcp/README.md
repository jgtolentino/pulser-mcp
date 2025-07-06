# Financial Analyst MCP - Marketing KPI Forecasting

AI-powered financial analysis for marketing KPIs with secure code execution and advanced forecasting capabilities.

## Features

- **KPI Analysis**: Revenue, engagement, conversion tracking
- **Forecasting**: Time-series predictions using ML models
- **Code Generation**: Auto-generate Python analysis code
- **Secure Execution**: Docker-sandboxed code execution
- **CrewAI Integration**: Multi-agent orchestration

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/financial_analyst_mcp
   ./scripts/setup.sh
   ```

2. **Start Server**:
   ```bash
   source venv/bin/activate
   python src/financial_server.py
   ```

3. **Test Analysis**:
   ```bash
   curl -X POST http://localhost:8002/mcp/tools/analyze_kpis \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Analyze Nike revenue trends",
       "timeframe": "1M",
       "metrics": ["revenue", "roi"]
     }'
   ```

## Available Tools

### analyze_kpis
Analyze marketing performance metrics:
```json
{
  "tool": "analyze_kpis",
  "params": {
    "query": "Compare brand performance last quarter",
    "data_source": "supabase",
    "timeframe": "3M",
    "metrics": ["revenue", "engagement", "conversion"],
    "brands": ["Nike", "Adidas", "Puma"]
  }
}
```

### generate_code
Generate custom analysis code:
```json
{
  "tool": "generate_code",
  "params": {
    "analysis_type": "forecast",
    "parameters": {
      "metric": "revenue",
      "periods": 30,
      "title": "30-Day Revenue Forecast"
    },
    "output_format": "plot"
  }
}
```

### execute_code
Execute analysis code safely:
```json
{
  "tool": "execute_code",
  "params": {
    "code": "import pandas as pd\n# Your analysis code",
    "timeout": 30,
    "sandbox": true
  }
}
```

## Use Cases

### Marketing ROI Analysis
```python
# Auto-generated code for ROI calculation
df['roi'] = (df['revenue'] - df['spend']) / df['spend'] * 100
optimal_spend = df.groupby('brand')['roi'].idxmax()
```

### Campaign Performance Forecasting
```python
# Time-series forecast for campaign metrics
from prophet import Prophet
model = Prophet()
model.fit(df[['ds', 'y']])
forecast = model.predict(future_dates)
```

### Budget Optimization
```python
# Find optimal budget allocation
from scipy.optimize import minimize
optimal_allocation = minimize(
    objective_function,
    initial_budget,
    constraints=budget_constraints
)
```

## Integration Examples

### With Scout Dashboard
```yaml
# Pull real-time sales data for KPI analysis
data_source: scout_metrics
metrics:
  - actual_sales
  - predicted_sales
  - conversion_rate
```

### With CES Insights
```yaml
# Export ROI insights to creative dashboard
export_to: ces_dashboard
insights:
  - campaign_roi
  - creative_performance
  - budget_recommendations
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   CrewAI    │────▶│  Financial   │────▶│   Docker    │
│   Agents    │     │ Analyst MCP  │     │  Sandbox    │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                     │
       ▼                    ▼                     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│Query Parser │     │Code Generator│     │Safe Executor│
└─────────────┘     └──────────────┘     └─────────────┘
```

## Configuration

### Data Sources
```yaml
data_sources:
  supabase:
    tables: [predicted_metrics, campaign_performance]
  yfinance:
    symbols: [market_indices]
  csv:
    path: ./data/datasets/
```

### Security Settings
```yaml
security:
  sandbox: docker
  resource_limits:
    memory: 512MB
    cpu: 50%
    timeout: 60s
  code_review: enabled
```

## Troubleshooting

- **Docker Not Found**: Server works without Docker but less secure
- **Timeout Errors**: Increase timeout in execute_code params
- **Memory Errors**: Reduce dataset size or increase Docker memory

## Advanced Features

- **Prophet Integration**: Advanced time-series forecasting
- **A/B Test Analysis**: Statistical significance testing
- **Multi-variate Analysis**: Correlation and causation studies
- **Real-time Dashboards**: Live KPI monitoring

## License

Part of InsightPulseAI SKR - Proprietary