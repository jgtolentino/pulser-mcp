# Shared Memory MCP - Cross-Agent Episodic Memory

Graphiti-powered shared memory system enabling Scout Edge, CES, and other agents to share context and insights.

## Features

- **Episodic Memory**: Store facts, insights, decisions, and relationships
- **Cross-Agent Communication**: Share context between Scout and CES
- **Graph-Based Storage**: Neo4j for rich relationship modeling
- **Semantic Search**: Vector embeddings for similarity-based recall
- **TTL Management**: Automatic memory expiration (default 30 days)
- **GDPR Compliance**: Memory deletion capabilities

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/shared_memory_mcp
   docker-compose up -d
   pip install -r requirements.txt
   ```

2. **Start Server**:
   ```bash
   python src/memory_server.py
   ```

3. **Access Interfaces**:
   - MCP API: http://localhost:5700
   - Neo4j Browser: http://localhost:7474 (neo4j/graphiti123)

## Available Tools

### store_memory
Store facts, insights, or decisions:
```json
{
  "tool": "store_memory",
  "params": {
    "content": "Nike campaign showing 15% higher engagement in NCR region",
    "memory_type": "insight",
    "source_agent": "scout_edge",
    "tags": ["nike", "ncr", "engagement"],
    "metadata": {
      "confidence": 0.92,
      "data_points": 1500
    }
  }
}
```

### recall_memories
Retrieve relevant memories:
```json
{
  "tool": "recall_memories",
  "params": {
    "query": "What do we know about Nike performance in NCR?",
    "agents": ["scout_edge", "financial_analyst"],
    "memory_types": ["insight", "fact"],
    "limit": 5
  }
}
```

### create_relation
Link related memories:
```json
{
  "tool": "create_relation",
  "params": {
    "from_memory_id": "mem_123",
    "to_memory_id": "mem_456",
    "relation_type": "SUPPORTS",
    "properties": {
      "strength": 0.85
    }
  }
}
```

### get_memory_graph
Explore memory relationships:
```json
{
  "tool": "get_memory_graph",
  "params": {
    "memory_id": "mem_123",
    "depth": 3
  }
}
```

## Memory Types

### Facts
Objective, verifiable information:
```python
{
  "content": "Store SM-NCR-001 sold 450 Nike shoes in January",
  "memory_type": "fact",
  "source_agent": "scout_edge"
}
```

### Insights
Analytical conclusions:
```python
{
  "content": "Weekend sales 40% higher than weekdays for athletic wear",
  "memory_type": "insight",
  "source_agent": "financial_analyst"
}
```

### Decisions
Strategic choices made:
```python
{
  "content": "Increase Nike inventory for Q2 based on Q1 performance",
  "memory_type": "decision",
  "source_agent": "scout_edge"
}
```

### Context
Background information:
```python
{
  "content": "Chinese New Year promotion running Feb 1-15",
  "memory_type": "context",
  "source_agent": "ces_dashboard"
}
```

### Relationships
Connections between entities:
```python
{
  "content": "Nike and Adidas show inverse correlation in youth segment",
  "memory_type": "relationship",
  "source_agent": "unified_mcp"
}
```

## Cross-Agent Use Cases

### Scout Edge + CES Integration
```python
# Scout stores retail insight
scout_memory = store_memory({
  "content": "Minimalist designs selling 3x better in urban stores",
  "memory_type": "insight",
  "source_agent": "scout_edge",
  "tags": ["design", "urban", "trend"]
})

# CES queries for creative direction
creative_context = recall_memories({
  "query": "What design trends are working in urban markets?",
  "agents": ["scout_edge"],
  "memory_types": ["insight"]
})

# CES creates related decision
ces_decision = store_memory({
  "content": "Pivot Q2 campaigns to minimalist aesthetic for urban markets",
  "memory_type": "decision",
  "source_agent": "ces_dashboard"
})

# Link the memories
create_relation({
  "from_memory_id": scout_memory["memory_id"],
  "to_memory_id": ces_decision["memory_id"],
  "relation_type": "INFLUENCED"
})
```

### Multi-Agent Decision Making
```python
# Financial analyst prediction
fin_memory = store_memory({
  "content": "Q2 revenue projected to increase 20% based on current trends",
  "memory_type": "insight",
  "source_agent": "financial_analyst"
})

# Voice agent feedback
voice_memory = store_memory({
  "content": "Customer calls mentioning 'summer collection' up 150%",
  "memory_type": "fact",
  "source_agent": "voice_agent"
})

# Query cross-agent insights
decision_context = recall_memories({
  "query": "What factors support increasing Q2 inventory?",
  "memory_types": ["insight", "fact"],
  "limit": 10
})
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│Scout Edge   │────▶│ Shared Memory│◀────│CES Dashboard│
└─────────────┘     └──────────────┘     └─────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
                ┌───▼───┐      ┌────▼────┐
                │ Neo4j │      │  Redis  │
                │ Graph │      │  Cache  │
                └───────┘      └─────────┘
```

## Graph Schema

```cypher
// Memory node
(m:Memory {
  id: "uuid",
  content: "text",
  memory_type: "fact|insight|decision|context|relationship",
  source_agent: "agent_name",
  created_at: datetime,
  expires_at: datetime,
  embedding: [float]
})

// Tag node
(t:Tag {
  name: "tag_name"
})

// Relationships
(m1:Memory)-[:RELATES_TO {type: "supports|contradicts|depends_on"}]->(m2:Memory)
(m:Memory)-[:TAGGED_WITH]->(t:Tag)
(m1:Memory)-[:INFLUENCED]->(m2:Memory)
(m1:Memory)-[:PRECEDED]->(m2:Memory)
```

## Best Practices

1. **Memory Hygiene**:
   - Tag appropriately for discoverability
   - Set reasonable TTLs
   - Link related memories

2. **Cross-Agent Patterns**:
   - Store insights, not raw data
   - Include confidence scores
   - Reference source data

3. **Query Optimization**:
   - Use specific agents/types when possible
   - Leverage tags for filtering
   - Cache frequent queries

## Configuration

### TTL Settings
```python
# Per-memory TTL
store_memory({
  "content": "Temporary campaign insight",
  "ttl_days": 7  # Expires in 7 days
})

# Global default (environment variable)
MEMORY_TTL_DAYS=30
```

### Embedding Models
```yaml
# config/embeddings.yaml
model: sentence-transformers/all-MiniLM-L6-v2
dimension: 768
batch_size: 32
```

## Monitoring

### Memory Statistics
```cypher
// Total memories by agent
MATCH (m:Memory)
RETURN m.source_agent as agent, 
       m.memory_type as type,
       count(*) as count

// Memory growth over time
MATCH (m:Memory)
WHERE m.created_at > datetime() - duration('P7D')
RETURN date(m.created_at) as date, count(*) as memories
ORDER BY date
```

### Relationship Analysis
```cypher
// Most connected memories
MATCH (m:Memory)-[r]-()
RETURN m.id, m.content, count(r) as connections
ORDER BY connections DESC
LIMIT 10
```

## Troubleshooting

- **Neo4j Connection**: Check Docker container status
- **Slow Queries**: Review indexes, reduce depth
- **Memory Leaks**: Monitor TTL expiration
- **Cache Misses**: Increase Redis memory

## License

Part of InsightPulseAI SKR - Proprietary