#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import axios from 'axios';
import jwt from 'jsonwebtoken';

const PULSER_URL = process.env.PULSER_URL || 'http://localhost:8000';
const JWT_SECRET = process.env.PULSER_JWT_SECRET || 'your-secret-jwt-key-change-this-in-production';

// Generate JWT token for authentication
function generateToken() {
  return jwt.sign(
    { 
      sub: 'claude-desktop',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour
    },
    JWT_SECRET
  );
}

// Create axios instance with auth
const api = axios.create({
  baseURL: PULSER_URL,
  headers: {
    'Authorization': `Bearer ${generateToken()}`
  }
});

// Initialize MCP server
const server = new Server(
  {
    name: 'pulser-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define available tools
const tools = [
  {
    name: 'scout_analytics',
    description: 'Query Scout retail analytics data',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Analytics query' },
        date_range: { type: 'string', description: 'Date range (e.g., "last_7_days")' }
      },
      required: ['query']
    }
  },
  {
    name: 'creative_search',
    description: 'Search creative assets using RAG',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query' },
        limit: { type: 'number', description: 'Maximum results', default: 10 }
      },
      required: ['query']
    }
  },
  {
    name: 'financial_forecast',
    description: 'Generate financial forecasts and KPI predictions',
    inputSchema: {
      type: 'object',
      properties: {
        metric: { type: 'string', description: 'Metric to forecast' },
        horizon: { type: 'number', description: 'Forecast horizon in days', default: 30 }
      },
      required: ['metric']
    }
  },
  {
    name: 'sync_status',
    description: 'Check sync status between local and cloud',
    inputSchema: {
      type: 'object',
      properties: {
        service: { type: 'string', description: 'Service name (optional)' }
      }
    }
  },
  {
    name: 'mcp_health',
    description: 'Check health status of all MCP services',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  },
  {
    name: 'monitor_summary',
    description: 'Get AI-powered summary of entire monitoring stack',
    inputSchema: {
      type: 'object',
      properties: {}
    }
  }
];

// Register tools
tools.forEach(tool => {
  server.setRequestHandler(`tools/list`, async () => ({
    tools: tools
  }));
  
  server.setRequestHandler(`tools/call`, async (request) => {
    const { name, arguments: args } = request.params;
    
    try {
      let response;
      
      switch (name) {
        case 'scout_analytics':
          response = await api.post('/api/v1/scout/analytics', {
            query: args.query,
            date_range: args.date_range || 'last_7_days'
          });
          break;
          
        case 'creative_search':
          response = await api.post('/api/v1/creative/search', {
            query: args.query,
            limit: args.limit || 10
          });
          break;
          
        case 'financial_forecast':
          response = await api.post('/api/v1/financial/forecast', {
            metric: args.metric,
            horizon: args.horizon || 30
          });
          break;
          
        case 'sync_status':
          response = await api.get('/api/v1/sync/status', {
            params: { service: args.service }
          });
          break;
          
        case 'mcp_health':
          response = await api.get('/health/all');
          break;
          
        case 'monitor_summary':
          // Execute the monitor summary tool
          const { exec } = require('child_process');
          const { promisify } = require('util');
          const execAsync = promisify(exec);
          
          try {
            const { stdout } = await execAsync('python3 /Users/tbwa/Documents/GitHub/pulser-mcp-server/tools/monitor_summary.py');
            const result = JSON.parse(stdout);
            response = { data: result };
          } catch (error) {
            response = { 
              data: { 
                summary: `Error generating summary: ${error.message}`,
                status: 'error'
              }
            };
          }
          break;
          
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
      
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(response.data, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Error: ${error.message}`
          }
        ]
      };
    }
  });
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Pulser MCP Bridge started');
}

main().catch(console.error);