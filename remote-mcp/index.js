import express from 'express'
import cors from 'cors'
import sse from 'sse-express'
import fetch from 'node-fetch'
import jwt from 'jsonwebtoken'

const app = express()
app.use(cors())
app.use(express.json())

// Configuration
const PULSER_URL = process.env.PULSER_URL || 'https://gagambi-backend.onrender.com'
const JWT_SECRET = process.env.PULSER_JWT_SECRET || 'your-secret-jwt-key-change-this-in-production'
const PORT = process.env.PORT || 3001

// Generate JWT for internal auth
function generateToken() {
  return jwt.sign(
    { 
      sub: 'remote-mcp-bridge',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600
    },
    JWT_SECRET
  );
}

// SSE endpoint for Claude Remote MCP
app.get('/sse', sse, async (req, res) => {
  console.log('[SSE] New connection from:', req.headers['x-forwarded-for'] || req.ip);
  
  // Set up SSE headers
  res.sse('init', { connected: true, timestamp: new Date().toISOString() });
  
  // Keep connection alive
  const keepAlive = setInterval(() => {
    res.sse('ping', { timestamp: new Date().toISOString() });
  }, 30000);
  
  // Set up event listeners for each MCP service
  const services = [
    'scout_local', 'creative_rag', 'financial_analyst',
    'voice_agent', 'unified', 'shared_memory',
    'briefvault_rag', 'synthetic_data', 'deep_researcher',
    'video_rag', 'audio_analysis', 'bootstrap'
  ];
  
  // Monitor service health
  const healthCheck = setInterval(async () => {
    try {
      const response = await fetch(`${PULSER_URL}/health/all`, {
        headers: {
          'Authorization': `Bearer ${generateToken()}`
        }
      });
      
      if (response.ok) {
        const health = await response.json();
        res.sse('health', health);
      }
    } catch (error) {
      res.sse('error', { message: 'Health check failed', error: error.message });
    }
  }, 10000);
  
  // Clean up on disconnect
  req.on('close', () => {
    clearInterval(keepAlive);
    clearInterval(healthCheck);
    console.log('[SSE] Connection closed');
  });
});

// MCP command endpoint (for Remote MCP actions)
app.post('/mcp/command', async (req, res) => {
  const { service, method, params } = req.body;
  
  try {
    // Special handling for monitor_summary
    if (service === 'monitor_summary') {
      const { exec } = require('child_process');
      const { promisify } = require('util');
      const execAsync = promisify(exec);
      
      try {
        const { stdout } = await execAsync('python3 /opt/pulser-mcp-bridge/monitor_summary.py');
        const result = JSON.parse(stdout);
        return res.json(result);
      } catch (error) {
        return res.status(500).json({ 
          error: `Monitor summary failed: ${error.message}`,
          status: 'error'
        });
      }
    }
    
    // Default handling for other services
    const response = await fetch(`${PULSER_URL}/api/v1/${service}/${method}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${generateToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(params)
    });
    
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Service discovery endpoint
app.get('/mcp/services', async (req, res) => {
  try {
    const response = await fetch(`${PULSER_URL}/api/v1/bootstrap/services`, {
      headers: {
        'Authorization': `Bearer ${generateToken()}`
      }
    });
    
    const services = await response.json();
    res.json(services);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Sync status endpoint
app.get('/mcp/sync-status', async (req, res) => {
  try {
    const response = await fetch(`${PULSER_URL}/api/v1/sync/status`, {
      headers: {
        'Authorization': `Bearer ${generateToken()}`
      }
    });
    
    const status = await response.json();
    res.json(status);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[Pulser MCP SSE Bridge] listening on http://0.0.0.0:${PORT}`);
  console.log(`[SSE Endpoint] http://0.0.0.0:${PORT}/sse`);
  console.log(`[Command Endpoint] http://0.0.0.0:${PORT}/mcp/command`);
});