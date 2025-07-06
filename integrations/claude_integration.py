"""
Claude MCP Integration Example

This example shows how to integrate Claude with the Pulser MCP server
to enable tool use and function calling.
"""

import httpx
import json
from typing import List, Dict, Any

class ClaudeMCPClient:
    def __init__(self, mcp_url: str = "http://localhost:8000"):
        self.mcp_url = mcp_url
        self.client = httpx.Client()
    
    def create_tools_for_claude(self) -> List[Dict[str, Any]]:
        """Create tool definitions in Claude's format"""
        return [
            {
                "name": "search_knowledge_base",
                "description": "Search the Pulser knowledge base for information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "generate_content",
                "description": "Generate content using available AI models",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The generation prompt"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use",
                            "enum": ["claude-3-opus", "gpt-4-turbo", "deepseek-coder"]
                        },
                        "type": {
                            "type": "string",
                            "description": "Content type",
                            "enum": ["text", "code", "summary"]
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "analyze_document",
                "description": "Analyze a document or text content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The content to analyze"
                        },
                        "analysis_type": {
                            "type": "string",
                            "description": "Type of analysis",
                            "enum": ["summary", "sentiment", "comprehensive"]
                        }
                    },
                    "required": ["content"]
                }
            }
        ]
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool through the MCP server"""
        
        # Map tool names to MCP endpoints
        endpoint_map = {
            "search_knowledge_base": "/tools/search",
            "generate_content": "/tools/generate",
            "analyze_document": "/tools/analyze"
        }
        
        endpoint = endpoint_map.get(tool_name)
        if not endpoint:
            return {"error": f"Unknown tool: {tool_name}"}
        
        # Make request to MCP server
        response = self.client.post(
            f"{self.mcp_url}{endpoint}",
            json=tool_input,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"MCP error: {response.status_code}", "detail": response.text}

# Example usage with Claude
def claude_with_mcp_example():
    """
    Example of how to use MCP tools with Claude
    """
    from anthropic import Anthropic
    
    # Initialize clients
    anthropic = Anthropic()
    mcp_client = ClaudeMCPClient()
    
    # Get tool definitions
    tools = mcp_client.create_tools_for_claude()
    
    # Example conversation with tool use
    messages = [
        {
            "role": "user",
            "content": "Search for information about MCP integration patterns and then summarize what you find."
        }
    ]
    
    # Claude makes the request with tools
    response = anthropic.messages.create(
        model="claude-3-opus-20240229",
        messages=messages,
        tools=tools,
        max_tokens=1000
    )
    
    # Process tool use if Claude wants to use tools
    if response.stop_reason == "tool_use":
        tool_use = response.content[0]
        
        # Execute the tool through MCP
        tool_result = mcp_client.execute_tool(
            tool_use.name,
            tool_use.input
        )
        
        # Continue conversation with tool results
        messages.append(response.to_dict())
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(tool_result)
                }
            ]
        })
        
        # Get final response
        final_response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            messages=messages,
            max_tokens=1000
        )
        
        return final_response.content[0].text
    
    return response.content[0].text

# Example: Claude prompt that automatically uses MCP
CLAUDE_MCP_PROMPT = """
You have access to the Pulser MCP server which provides the following tools:

1. search_knowledge_base - Search for information in the Pulser knowledge base
2. generate_content - Generate content using various AI models
3. analyze_document - Analyze documents for insights

Use these tools when appropriate to help answer questions. The MCP server handles:
- Vector similarity search across all Pulser agent knowledge
- Multi-model content generation (Claude, GPT-4, DeepSeek)
- Document analysis with sentiment, entities, and summarization

When you need to search for information, generate content, or analyze documents,
use the appropriate tool rather than relying solely on your training data.
"""

if __name__ == "__main__":
    # Example of setting up Claude with MCP tools
    print("Claude MCP Integration configured with tools:")
    client = ClaudeMCPClient()
    for tool in client.create_tools_for_claude():
        print(f"- {tool['name']}: {tool['description']}")