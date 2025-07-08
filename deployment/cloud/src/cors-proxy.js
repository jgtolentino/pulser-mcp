const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');
const winston = require('winston');

const config = {
  port: process.env.CORS_PORT || 8001,
  host: process.env.CORS_HOST || '0.0.0.0',
  targetPort: process.env.MCP_PORT || 8000,
  targetHost: process.env.MCP_HOST || 'localhost'
};

// Setup logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: './logs/cors-proxy.log' }),
    new winston.transports.Console()
  ]
});

const app = express();

// Claude-optimized CORS configuration
app.use(cors({
  origin: function(origin, callback) {
    // Allow requests from Claude domains
    const allowedOrigins = [
      'https://claude.ai',
      'https://claude.anthropic.com',
      'http://localhost:3000',
      'http://localhost:3001'
    ];
    
    // Allow requests with no origin (like mobile apps or Postman)
    if (!origin) return callback(null, true);
    
    // Check if origin is allowed
    if (allowedOrigins.indexOf(origin) !== -1 || process.env.NODE_ENV === 'development') {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'X-API-Key'],
  exposedHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset']
}));

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    proxy: 'cors-proxy',
    target: `http://${config.targetHost}:${config.targetPort}`,
    timestamp: new Date().toISOString(),
    corsEnabled: true,
    claudeOptimized: true
  });
});

// Claude-specific proxy endpoint
app.use('/proxy', createProxyMiddleware({
  target: `http://${config.targetHost}:${config.targetPort}`,
  changeOrigin: true,
  pathRewrite: {
    '^/proxy': '', // Remove /proxy prefix when forwarding
  },
  logLevel: 'info',
  onProxyReq: (proxyReq, req, res) => {
    logger.info(`Proxying ${req.method} ${req.path} from ${req.headers.origin || 'unknown'}`);
    
    // Forward auth headers
    if (req.headers['x-api-key']) {
      proxyReq.setHeader('X-API-Key', req.headers['x-api-key']);
    }
  },
  onProxyRes: (proxyRes, req, res) => {
    // Add Claude-specific headers
    proxyRes.headers['X-Powered-By'] = 'MCP-CORS-Proxy';
    proxyRes.headers['X-Claude-Compatible'] = 'true';
  },
  onError: (err, req, res) => {
    logger.error('Proxy error', { error: err.message, url: req.url });
    res.status(502).json({ 
      error: 'Bad Gateway', 
      message: 'Unable to reach MCP server',
      details: process.env.NODE_ENV === 'development' ? err.message : undefined
    });
  }
}));

// Root proxy for backward compatibility
const mainProxy = createProxyMiddleware({
  target: `http://${config.targetHost}:${config.targetPort}`,
  changeOrigin: true,
  logLevel: 'info'
});

app.use((req, res, next) => {
  if (req.path === '/health' || req.path.startsWith('/proxy')) {
    next();
  } else {
    mainProxy(req, res, next);
  }
});

app.listen(config.port, config.host, () => {
  logger.info(`CORS Proxy running on ${config.host}:${config.port}`);
  console.log(`
🌐 Claude-Optimized CORS Proxy Server
=====================================
📍 Address: http://${config.host}:${config.port}
🎯 Target: http://${config.targetHost}:${config.targetPort}
🔗 Proxy Endpoint: http://${config.host}:${config.port}/proxy

Claude Web App URLs:
- Direct: http://${config.host}:${config.port}
- Via Proxy: http://${config.host}:${config.port}/proxy/[endpoint]

Features:
✅ Claude.ai whitelisted
✅ Rate limit headers exposed
✅ API key forwarding
✅ Development mode auto-allow
  `);
});