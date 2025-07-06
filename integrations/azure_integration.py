"""
Azure Services Integration for Pulser MCP Server

This module provides integration with Azure services including:
- Azure OpenAI for embeddings and completions
- Azure Cognitive Search for vector storage
- Azure Static Web Apps for deployment
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswVectorSearchAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    VectorSearchField
)
import openai
from openai import AzureOpenAI

class AzureVectorStore:
    """Azure Cognitive Search vector store implementation"""
    
    def __init__(self, 
                 search_endpoint: str,
                 search_key: str,
                 index_name: str = "pulser-mcp-vectors"):
        self.endpoint = search_endpoint
        self.credential = AzureKeyCredential(search_key)
        self.index_name = index_name
        self.search_client = None
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=self.credential
        )
    
    async def initialize(self):
        """Initialize the search index with vector support"""
        
        # Define the index schema
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="agent", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, filterable=True),
            VectorSearchField(
                name="embedding",
                vector_search_dimensions=1536,
                vector_search_profile_name="my-vector-config"
            ),
            SimpleField(name="metadata", type=SearchFieldDataType.String)
        ]
        
        # Configure vector search
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="my-vector-config",
                    algorithm_configuration_name="my-algorithms-config"
                )
            ],
            algorithms=[
                HnswVectorSearchAlgorithmConfiguration(
                    name="my-algorithms-config",
                    parameters={
                        "m": 4,
                        "metric": "cosine",
                        "ef_construction": 400,
                        "ef_search": 500
                    }
                )
            ]
        )
        
        # Create the index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        self.index_client.create_or_update_index(index)
        
        # Initialize search client
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
    
    async def search(self, query_vector: List[float], 
                    filters: Optional[str] = None,
                    top: int = 10) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        
        search_results = self.search_client.search(
            search_text=None,
            vector_queries=[{
                "vector": query_vector,
                "k_nearest_neighbors": top,
                "fields": "embedding"
            }],
            filter=filters,
            select=["id", "title", "content", "agent", "timestamp", "metadata"]
        )
        
        results = []
        for result in search_results:
            results.append({
                "id": result["id"],
                "title": result["title"],
                "content": result["content"],
                "score": result["@search.score"],
                "agent": result.get("agent"),
                "timestamp": result.get("timestamp"),
                "metadata": result.get("metadata")
            })
        
        return results
    
    async def insert(self, documents: List[Dict[str, Any]]):
        """Insert documents into the vector store"""
        self.search_client.upload_documents(documents=documents)

class AzureOpenAIEmbeddings:
    """Azure OpenAI embeddings generator"""
    
    def __init__(self, 
                 endpoint: str,
                 api_key: str,
                 deployment_name: str = "text-embedding-ada-002"):
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-01"
        )
        self.deployment_name = deployment_name
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text"""
        response = self.client.embeddings.create(
            input=text,
            model=self.deployment_name
        )
        return response.data[0].embedding

class AzureMCPIntegration:
    """Main Azure integration class for MCP server"""
    
    def __init__(self, config: Dict[str, str]):
        self.vector_store = AzureVectorStore(
            search_endpoint=config["AZURE_SEARCH_ENDPOINT"],
            search_key=config["AZURE_SEARCH_KEY"]
        )
        self.embeddings = AzureOpenAIEmbeddings(
            endpoint=config["AZURE_OPENAI_ENDPOINT"],
            api_key=config["AZURE_OPENAI_KEY"]
        )
        self.openai_client = AzureOpenAI(
            azure_endpoint=config["AZURE_OPENAI_ENDPOINT"],
            api_key=config["AZURE_OPENAI_KEY"],
            api_version="2024-02-01"
        )
    
    async def initialize(self):
        """Initialize all Azure services"""
        await self.vector_store.initialize()
    
    async def search_with_embedding(self, query: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Search using query embedding"""
        # Create embedding for query
        query_embedding = await self.embeddings.create_embedding(query)
        
        # Build filter string if provided
        filter_str = None
        if filters:
            if filters.get("agent"):
                filter_str = f"agent eq '{filters['agent']}'"
        
        # Perform search
        return await self.vector_store.search(
            query_vector=query_embedding,
            filters=filter_str
        )
    
    async def generate_completion(self, prompt: str, model: str = "gpt-4") -> Dict[str, Any]:
        """Generate completion using Azure OpenAI"""
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return {
            "output": response.choices[0].message.content,
            "model_used": model,
            "tokens_used": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }

# Deployment script for Azure Static Web Apps
AZURE_DEPLOYMENT_SCRIPT = """
#!/bin/bash
# Azure Static Web Apps deployment script for MCP server

# Build the Docker image
docker build -t pulser-mcp-server .

# Tag for Azure Container Registry
docker tag pulser-mcp-server $ACR_NAME.azurecr.io/pulser-mcp-server:latest

# Push to ACR
az acr login --name $ACR_NAME
docker push $ACR_NAME.azurecr.io/pulser-mcp-server:latest

# Deploy to Azure Container Instances
az container create \\
    --resource-group $RESOURCE_GROUP \\
    --name pulser-mcp-server \\
    --image $ACR_NAME.azurecr.io/pulser-mcp-server:latest \\
    --dns-name-label pulser-mcp \\
    --ports 8000 \\
    --environment-variables \\
        AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT \\
        AZURE_OPENAI_KEY=$AZURE_OPENAI_KEY \\
        AZURE_SEARCH_ENDPOINT=$AZURE_SEARCH_ENDPOINT \\
        AZURE_SEARCH_KEY=$AZURE_SEARCH_KEY

echo "MCP Server deployed to: pulser-mcp.$LOCATION.azurecontainer.io"
"""

# Example usage
if __name__ == "__main__":
    # Configuration
    config = {
        "AZURE_SEARCH_ENDPOINT": "https://your-search.search.windows.net",
        "AZURE_SEARCH_KEY": "your-search-key",
        "AZURE_OPENAI_ENDPOINT": "https://your-openai.openai.azure.com/",
        "AZURE_OPENAI_KEY": "your-openai-key"
    }
    
    # Initialize Azure integration
    azure_mcp = AzureMCPIntegration(config)
    
    # Example search
    async def example_search():
        await azure_mcp.initialize()
        results = await azure_mcp.search_with_embedding(
            "MCP integration patterns",
            filters={"agent": "claudia"}
        )
        print(f"Found {len(results)} results")
        for result in results:
            print(f"- {result['title']} (score: {result['score']})")
    
    # Run example
    # asyncio.run(example_search())