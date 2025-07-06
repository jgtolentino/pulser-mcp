"""
OpenAI GPT Integration for Pulser MCP Server

This module shows how to integrate OpenAI's GPT models with the MCP server
for function calling and tool use.
"""

import openai
from openai import OpenAI
import json
from typing import List, Dict, Any, Optional
import httpx

class OpenAIMCPClient:
    """Client for integrating OpenAI with MCP server"""
    
    def __init__(self, openai_api_key: str, mcp_url: str = "http://localhost:8000"):
        self.client = OpenAI(api_key=openai_api_key)
        self.mcp_url = mcp_url
        self.http_client = httpx.Client()
    
    def create_functions_for_openai(self) -> List[Dict[str, Any]]:
        """Create function definitions in OpenAI's format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search the Pulser knowledge base for relevant information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "filters": {
                                "type": "object",
                                "properties": {
                                    "agent": {
                                        "type": "string",
                                        "description": "Filter by specific agent"
                                    }
                                },
                                "required": []
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_content",
                    "description": "Generate content using various AI models",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt for content generation"
                            },
                            "model": {
                                "type": "string",
                                "enum": ["claude-3-opus", "gpt-4-turbo", "deepseek-coder"],
                                "description": "The model to use",
                                "default": "gpt-4-turbo"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["text", "code", "summary", "analysis"],
                                "description": "Type of content to generate",
                                "default": "text"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_document",
                    "description": "Analyze a document for insights, sentiment, and key information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "The document content to analyze"
                            },
                            "document_url": {
                                "type": "string",
                                "description": "URL of the document (alternative to content)"
                            },
                            "analysis_type": {
                                "type": "string",
                                "enum": ["summary", "sentiment", "entities", "comprehensive"],
                                "description": "Type of analysis to perform",
                                "default": "comprehensive"
                            }
                        },
                        "oneOf": [
                            {"required": ["content"]},
                            {"required": ["document_url"]}
                        ]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "Execute a command through a Pulser agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The command to execute"
                            },
                            "agent": {
                                "type": "string",
                                "enum": ["claudia", "maya", "surf", "basher", "kalaw"],
                                "description": "The agent to use"
                            },
                            "environment": {
                                "type": "string",
                                "enum": ["terminal", "vscode", "database"],
                                "description": "The execution environment",
                                "default": "terminal"
                            }
                        },
                        "required": ["command", "agent"]
                    }
                }
            }
        ]
    
    async def call_mcp_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP function and return the result"""
        
        # Map function names to MCP endpoints
        endpoint_map = {
            "search_knowledge_base": "/tools/search",
            "generate_content": "/tools/generate",
            "analyze_document": "/tools/analyze",
            "execute_command": "/command"
        }
        
        endpoint = endpoint_map.get(function_name)
        if not endpoint:
            return {"error": f"Unknown function: {function_name}"}
        
        try:
            response = self.http_client.post(
                f"{self.mcp_url}{endpoint}",
                json=arguments,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"MCP server error: {response.status_code}",
                    "detail": response.text
                }
        except Exception as e:
            return {"error": f"Failed to call MCP: {str(e)}"}
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], 
                             model: str = "gpt-4-turbo-preview") -> str:
        """
        Have a conversation with GPT using MCP tools
        
        Args:
            messages: Conversation history
            model: OpenAI model to use
        
        Returns:
            Assistant's response
        """
        tools = self.create_functions_for_openai()
        
        # Make initial request
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # If no tool calls, return the response
        if not tool_calls:
            return response_message.content
        
        # Process tool calls
        messages.append(response_message)
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Call MCP function
            function_response = await self.call_mcp_function(function_name, function_args)
            
            # Add function response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(function_response)
            })
        
        # Get final response
        final_response = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        return final_response.choices[0].message.content

# Example prompts that leverage MCP tools
EXAMPLE_PROMPTS = {
    "research_task": """
    I need to understand the current state of our MCP integration patterns.
    Please search for relevant information and summarize the key findings.
    """,
    
    "code_generation": """
    Search for examples of vector store implementations in our codebase,
    then generate an improved version that includes caching and error handling.
    """,
    
    "document_analysis": """
    Analyze this technical specification and identify:
    1. Key requirements
    2. Potential risks
    3. Implementation complexity
    
    Then search for similar projects we've done before.
    """,
    
    "multi_agent_task": """
    I need to deploy a new service. Please:
    1. Use Surf to check the current codebase structure
    2. Use Maya to create a deployment plan
    3. Use Basher to execute the deployment commands
    """
}

# System prompt for GPT when using MCP
SYSTEM_PROMPT_WITH_MCP = """
You are an AI assistant with access to the Pulser MCP server, which provides:

1. **Knowledge Base Search**: Search across all Pulser agent knowledge and documentation
2. **Content Generation**: Generate text, code, or summaries using multiple AI models
3. **Document Analysis**: Analyze documents for insights, sentiment, and key information
4. **Command Execution**: Execute commands through specialized Pulser agents

Available Pulser agents:
- Claudia: Strategic planning and orchestration
- Maya: Process design and workflow creation
- Surf: Engineering and technical implementation
- Basher: System automation and shell commands
- Kalaw: Research and knowledge management

Use these tools whenever you need to:
- Search for information beyond your training data
- Generate specialized content
- Analyze documents or data
- Execute system commands or workflows

Always prefer using tools over relying solely on your training when the user's request
involves current information, specific system states, or executable actions.
"""

# Example usage
async def example_openai_mcp_conversation():
    """Example of using OpenAI with MCP tools"""
    
    # Initialize client
    client = OpenAIMCPClient(
        openai_api_key="your-openai-api-key",
        mcp_url="http://localhost:8000"
    )
    
    # Example conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_WITH_MCP},
        {"role": "user", "content": EXAMPLE_PROMPTS["research_task"]}
    ]
    
    # Get response with tool use
    response = await client.chat_with_tools(messages)
    print("Assistant:", response)
    
    return response

# Streaming example with tool use
async def stream_with_tools(client: OpenAIMCPClient, prompt: str):
    """Example of streaming responses with tool use"""
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_WITH_MCP},
        {"role": "user", "content": prompt}
    ]
    
    tools = client.create_functions_for_openai()
    
    # Create streaming response
    stream = client.client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        tools=tools,
        stream=True
    )
    
    collected_messages = []
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="")
        
        # Collect tool calls if any
        if chunk.choices[0].delta.tool_calls:
            collected_messages.append(chunk.choices[0].delta)
    
    # Process any tool calls after streaming completes
    # ... (similar to non-streaming example)

if __name__ == "__main__":
    # Print available functions
    client = OpenAIMCPClient("dummy-key")
    print("Available MCP functions for OpenAI:")
    for tool in client.create_functions_for_openai():
        func = tool["function"]
        print(f"- {func['name']}: {func['description']}")