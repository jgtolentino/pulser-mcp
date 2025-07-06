# Creative RAG MCP - Vector Search for Creative Assets

AI-powered semantic search across storyboards, campaign materials, and creative briefs using Qdrant vector database and ColPali embeddings.

## Features

- **Vector-Based Search**: Find conceptually similar creative assets
- **Multi-Modal Support**: Index text, images, and mixed content
- **Campaign Analytics**: Track performance metrics and awards
- **Web Integration**: Discover external creative references
- **Real-Time Ingestion**: Add new assets on the fly

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/creative_rag_mcp
   ./scripts/setup.sh
   ```

2. **Start Server**:
   ```bash
   source venv/bin/activate
   python src/rag_server.py
   ```

3. **Seed Sample Data**:
   ```bash
   python scripts/seed_qdrant.py
   ```

4. **Access Interfaces**:
   - MCP API: http://localhost:8001/mcp
   - Qdrant Dashboard: http://localhost:6333/dashboard
   - API Docs: http://localhost:8001/docs

## Available Tools

### ingest_asset
Add creative assets to the vector database:
```json
{
  "tool": "ingest_asset",
  "params": {
    "asset_id": "nike_just_do_it_storyboard_1",
    "asset_type": "storyboard",
    "brand": "Nike",
    "campaign": "Just Do It 2024",
    "metadata": {
      "awards": ["Cannes Lions Gold"],
      "tags": ["inspiring", "athletic", "motivational"],
      "performance_score": 92.5
    },
    "text_content": "Opening shot of sunrise over city skyline..."
  }
}
```

### search_vector
Find similar creative concepts:
```json
{
  "tool": "search_vector",
  "params": {
    "query": "minimalist design with emotional storytelling",
    "query_type": "text",
    "top_k": 5,
    "filters": {
      "brand": "Apple"
    }
  }
}
```

### search_web
Discover creative references online:
```json
{
  "tool": "search_web",
  "params": {
    "query": "award winning sustainability campaigns",
    "domains": ["adsoftheworld.com", "canneslions.com"],
    "max_results": 10
  }
}
```

## Integration Examples

### With Gagambi (Awards Intelligence)
```python
# Sync award-winning campaigns
gagambi_assets = fetch_gagambi_winners()
for asset in gagambi_assets:
    ingest_asset({
        "asset_id": asset.id,
        "metadata": {"awards": asset.awards}
    })
```

### With CES Dashboard
```python
# Find similar successful campaigns
similar = search_vector({
    "query": current_brief.concept,
    "filters": {"performance_score": {"$gte": 85}}
})
```

### With Scout Edge
```python
# Analyze retail creative trends
retail_creatives = search_vector({
    "query": "in-store promotional materials",
    "filters": {"asset_type": "thumbnail"}
})
```

## Architecture

```
┌──────────────┐     ┌─────────────┐     ┌──────────┐
│   Creative   │────▶│   Creative  │────▶│  Qdrant  │
│   Assets     │     │   RAG MCP   │     │ Vector DB│
└──────────────┘     └─────────────┘     └──────────┘
                            │
                     ┌──────┴──────┐
                     │   ColPali   │
                     │  Embeddings │
                     └─────────────┘
```

## Advanced Configuration

### Custom Embedding Models
```yaml
embeddings:
  model: your-custom-model
  dimension: 1024
  endpoint: http://your-model-server
```

### Performance Tuning
```yaml
performance:
  index_type: hnsw
  ef_construction: 200
  m: 16
```

## Troubleshooting

- **Qdrant Connection**: Ensure Docker is running
- **Slow Searches**: Increase `ef` parameter in Qdrant
- **Memory Issues**: Reduce `batch_size` for embeddings

## Future Enhancements

- [ ] Real ColPali integration
- [ ] GPU acceleration
- [ ] Multi-language support
- [ ] Video frame extraction
- [ ] A/B testing integration

## License

Part of InsightPulseAI SKR - Proprietary