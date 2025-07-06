"""
PostgreSQL pgvector Integration for Pulser MCP Server

This module provides a production-ready vector store implementation
using PostgreSQL with the pgvector extension.
"""

import asyncio
import asyncpg
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from contextlib import asynccontextmanager

class PgVectorStore:
    """Production pgvector implementation with connection pooling"""
    
    def __init__(self, database_url: str, embedding_dim: int = 1536):
        self.database_url = database_url
        self.embedding_dim = embedding_dim
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool and ensure tables exist"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=10,
            max_size=20,
            command_timeout=60
        )
        
        # Ensure pgvector extension and tables exist
        async with self.pool.acquire() as conn:
            await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
            await self._create_tables(conn)
    
    async def _create_tables(self, conn):
        """Create necessary tables if they don't exist"""
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                agent VARCHAR(50),
                embedding vector($1),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''', self.embedding_dim)
        
        # Create indexes
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS documents_embedding_idx 
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        ''')
        
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS documents_agent_idx 
            ON documents(agent)
        ''')
        
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS documents_created_at_idx 
            ON documents(created_at DESC)
        ''')
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool"""
        async with self.pool.acquire() as conn:
            yield conn
    
    async def search(self, 
                    query_embedding: List[float],
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search with optional filters
        
        Args:
            query_embedding: Query vector
            filters: Optional filters (agent, date_range, metadata)
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
        """
        async with self.acquire() as conn:
            # Build the query
            query_parts = []
            params = []
            param_count = 1
            
            # Base query with similarity
            base_query = '''
                SELECT 
                    id,
                    title,
                    content,
                    agent,
                    1 - (embedding <=> $1::vector) as similarity,
                    metadata,
                    created_at,
                    updated_at
                FROM documents
                WHERE 1 - (embedding <=> $1::vector) > $2
            '''
            params.extend([query_embedding, similarity_threshold])
            param_count = 3
            
            # Apply filters
            if filters:
                if filters.get('agent'):
                    query_parts.append(f'agent = ${param_count}')
                    params.append(filters['agent'])
                    param_count += 1
                
                if filters.get('date_range'):
                    if filters['date_range'].get('from'):
                        query_parts.append(f'created_at >= ${param_count}')
                        params.append(filters['date_range']['from'])
                        param_count += 1
                    
                    if filters['date_range'].get('to'):
                        query_parts.append(f'created_at <= ${param_count}')
                        params.append(filters['date_range']['to'])
                        param_count += 1
                
                if filters.get('metadata'):
                    # JSONB containment query
                    query_parts.append(f'metadata @> ${param_count}::jsonb')
                    params.append(json.dumps(filters['metadata']))
                    param_count += 1
            
            # Combine query parts
            if query_parts:
                where_clause = ' AND '.join(query_parts)
                query = f"{base_query} AND {where_clause}"
            else:
                query = base_query
            
            # Add ordering and limit
            query += f' ORDER BY similarity DESC LIMIT ${param_count}'
            params.append(limit)
            
            # Execute query
            rows = await conn.fetch(query, *params)
            
            # Transform results
            results = []
            for row in rows:
                results.append({
                    'id': str(row['id']),
                    'title': row['title'],
                    'content': row['content'],
                    'agent': row['agent'],
                    'score': float(row['similarity']),
                    'metadata': row['metadata'],
                    'timestamp': row['created_at'].isoformat() if row['created_at'] else None
                })
            
            return results
    
    async def insert(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple documents with embeddings
        
        Args:
            documents: List of documents with embeddings
        
        Returns:
            List of inserted document IDs
        """
        async with self.acquire() as conn:
            # Prepare batch insert
            records = []
            for doc in documents:
                records.append((
                    doc['title'],
                    doc['content'],
                    doc.get('agent'),
                    doc['embedding'],
                    json.dumps(doc.get('metadata', {}))
                ))
            
            # Batch insert
            result = await conn.fetch('''
                INSERT INTO documents (title, content, agent, embedding, metadata)
                VALUES ($1, $2, $3, $4::vector, $5::jsonb)
                RETURNING id
            ''', *records)
            
            return [str(row['id']) for row in result]
    
    async def update_embedding(self, document_id: str, embedding: List[float]) -> bool:
        """Update the embedding for a document"""
        async with self.acquire() as conn:
            result = await conn.execute('''
                UPDATE documents 
                SET embedding = $1::vector, updated_at = CURRENT_TIMESTAMP
                WHERE id = $2::uuid
            ''', embedding, document_id)
            
            return result.split()[-1] != '0'
    
    async def delete(self, document_id: str) -> bool:
        """Delete a document"""
        async with self.acquire() as conn:
            result = await conn.execute('''
                DELETE FROM documents WHERE id = $1::uuid
            ''', document_id)
            
            return result.split()[-1] != '0'
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        async with self.acquire() as conn:
            stats = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(DISTINCT agent) as unique_agents,
                    AVG(length(content)) as avg_content_length,
                    MIN(created_at) as oldest_document,
                    MAX(created_at) as newest_document
                FROM documents
            ''')
            
            return dict(stats)
    
    async def optimize_index(self):
        """Optimize the vector index for better performance"""
        async with self.acquire() as conn:
            # Vacuum and analyze the table
            await conn.execute('VACUUM ANALYZE documents')
            
            # Rebuild the index with optimal parameters based on data size
            stats = await self.get_stats()
            total_docs = stats['total_documents']
            
            # Calculate optimal lists parameter
            lists = min(max(int(total_docs / 1000), 100), 1000)
            
            await conn.execute('DROP INDEX IF EXISTS documents_embedding_idx')
            await conn.execute(f'''
                CREATE INDEX documents_embedding_idx 
                ON documents USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = {lists})
            ''')
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()

class PgVectorMCPHandler:
    """Handler that integrates pgvector with the MCP server"""
    
    def __init__(self, database_url: str):
        self.vector_store = PgVectorStore(database_url)
        self.initialized = False
    
    async def initialize(self):
        """Initialize the vector store"""
        await self.vector_store.initialize()
        self.initialized = True
    
    async def handle_search(self, query_embedding: List[float], 
                          filters: Optional[Dict] = None,
                          limit: int = 10) -> Dict[str, Any]:
        """Handle search requests from MCP server"""
        if not self.initialized:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                filters=filters,
                limit=limit
            )
            
            query_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return {
                "success": True,
                "results": results,
                "total": len(results),
                "query_time_ms": query_time
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "total": 0,
                "query_time_ms": 0
            }
    
    async def handle_insert(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle insert requests from MCP server"""
        if not self.initialized:
            await self.initialize()
        
        try:
            ids = await self.vector_store.insert(documents)
            return {
                "success": True,
                "inserted_ids": ids,
                "count": len(ids)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "inserted_ids": [],
                "count": 0
            }

# Example configuration and usage
PGVECTOR_CONFIG = """
# PostgreSQL with pgvector configuration

# Local development
DATABASE_URL=postgres://user:password@localhost:5432/mcp_vectors

# Production (with connection pooling)
DATABASE_URL=postgres://user:password@pgbouncer:6432/mcp_vectors?sslmode=require

# Embedding configuration
EMBEDDING_DIM=1536  # OpenAI ada-002
# EMBEDDING_DIM=768  # Alternative models

# Performance tuning
PGVECTOR_LISTS=100  # Increase for larger datasets
PGVECTOR_PROBES=10  # Increase for better recall
"""

# Migration script from other vector stores
MIGRATION_SCRIPT = """
-- Migrate from basic PostgreSQL to pgvector

-- 1. Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add vector column to existing table
ALTER TABLE documents 
ADD COLUMN embedding vector(1536);

-- 3. Create index
CREATE INDEX documents_embedding_idx 
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Migrate embeddings (example)
UPDATE documents 
SET embedding = string_to_array(embedding_text, ',')::vector
WHERE embedding_text IS NOT NULL;
"""

if __name__ == "__main__":
    # Example usage
    async def example():
        # Initialize pgvector store
        db_url = "postgres://user:pass@localhost:5432/mcp_db"
        handler = PgVectorMCPHandler(db_url)
        await handler.initialize()
        
        # Example search
        mock_embedding = [0.1] * 1536  # Mock embedding
        results = await handler.handle_search(
            query_embedding=mock_embedding,
            filters={"agent": "claudia"},
            limit=5
        )
        
        print(f"Search results: {results['total']} documents found")
        print(f"Query time: {results['query_time_ms']}ms")
        
        # Get statistics
        stats = await handler.vector_store.get_stats()
        print(f"Vector store stats: {stats}")
        
        # Close connections
        await handler.vector_store.close()
    
    # Run example
    # asyncio.run(example())