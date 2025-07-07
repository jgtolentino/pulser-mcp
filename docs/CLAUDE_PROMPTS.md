# Claude Desktop MCP Prompts Guide

Example prompts to use with Pulser MCP in Claude Desktop after integration.

## 🚀 Getting Started

First, verify the connection:
```
Check MCP health status
```

## 📊 Scout Analytics Prompts

### Sales Analysis
```
Using scout_analytics, show me the top 5 products by revenue for the last 7 days
```

```
Query Scout for sales trends in Metro Manila comparing this week to last week
```

```
What are the best performing barangays by transaction volume this month?
```

### Inventory Insights
```
Check Scout inventory levels for products with less than 10 units in stock
```

```
Show me products that haven't sold in the last 30 days using scout_analytics
```

## 🎨 Creative Search Prompts

### Asset Discovery
```
Search creative assets for "summer campaign 2024" materials
```

```
Find all video assets tagged with "product launch" using creative_search
```

```
Look for marketing materials related to "holiday promotion" in the creative database
```

### Brand Assets
```
Search for our latest brand guidelines and logo files
```

```
Find presentation templates for client pitches using creative RAG
```

## 📈 Financial Forecast Prompts

### Revenue Predictions
```
Generate a 30-day revenue forecast based on current trends
```

```
Using financial_forecast, predict next quarter's sales for our top 3 product categories
```

```
What's the expected profit margin for next month?
```

### KPI Forecasting
```
Forecast customer acquisition rate for the next 60 days
```

```
Predict inventory turnover ratio for Q2 2024
```

## 🔄 Sync Status Prompts

### System Health
```
Check the synchronization status between local and cloud databases
```

```
Show me the last sync timestamp for all MCP services
```

```
Are there any pending sync operations?
```

### Data Freshness
```
When was Scout data last synchronized with Supabase?
```

```
Check if creative assets are fully synced across all nodes
```

## 🏥 Combined Operations

### Multi-Service Queries
```
First check MCP health, then show me today's sales if all services are running
```

```
Search for marketing materials about our best-selling product from scout_analytics
```

```
Generate a financial forecast for products that are low in inventory
```

### Business Intelligence
```
Create a summary report combining:
1. Today's sales from Scout
2. Revenue forecast for next week
3. Any creative assets we should use for promotion
```

```
Analyze which products need marketing campaigns based on:
- Low sales velocity (Scout)
- High profit margins (Financial)
- Available creative assets (Creative RAG)
```

## 💡 Advanced Prompts

### Conditional Queries
```
If sync_status shows all systems are current, then query scout_analytics for real-time sales data
```

### Batch Operations
```
For each of our top 5 selling products:
1. Show current inventory levels
2. Generate 14-day sales forecast
3. Find related marketing materials
```

### Trend Analysis
```
Compare this week's performance metrics to:
- Same week last month
- Same week last year
- Industry benchmarks if available
```

## 🛠️ Troubleshooting Prompts

### Debug Connections
```
List all available MCP tools and their current status
```

```
Test each MCP service endpoint and report which ones respond
```

### Performance Checks
```
Measure response time for a simple scout_analytics query
```

```
Check memory usage and performance metrics for all MCP services
```

## 📝 Best Practices

1. **Be Specific**: Include date ranges, product names, or specific metrics
2. **Chain Commands**: Use results from one query to inform the next
3. **Verify First**: Always check health/sync status for critical queries
4. **Use Tool Names**: Explicitly mention the tool (scout_analytics, creative_search, etc.)

## 🔗 Tool Reference

| Tool | Best For | Example Use Case |
|------|----------|------------------|
| `scout_analytics` | Sales & inventory data | Daily sales reports |
| `creative_search` | Marketing assets | Finding campaign materials |
| `financial_forecast` | Predictions & trends | Revenue forecasting |
| `sync_status` | System monitoring | Data freshness checks |
| `mcp_health` | Service availability | Pre-flight checks |