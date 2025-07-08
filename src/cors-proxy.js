const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');
const winston = require('winston');

const config = {
  port: process.env.CORS_PORT || 8001,
  host: process.env.CORS_HOST || '0.0.0.0',
  targetPort: process.env.MCP_PORT || 8000
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

// Ultra-permissive CORS for development
app.use(cors({
  origin: true,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['*']
}));

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    proxy: 'cors-proxy',
    target: `http://localhost:${config.targetPort}`,
    timestamp: new Date().toISOString()
  });
});

// Proxy middleware
const proxyMiddleware = createProxyMiddleware({
  target: `http://localhost:${config.targetPort}`,
  changeOrigin: true,
  logLevel: 'info',
  onProxyReq: (proxyReq, req, res) => {
    logger.info(`Proxying ${req.method} ${req.path}`);
  },
  onError: (err, req, res) => {
    logger.error('Proxy error', { error: err.message, url: req.url });
    res.status(500).json({ error: 'Proxy error', message: err.message });
  }
});

// Apply proxy to all routes except health
app.use((req, res, next) => {
  if (req.path === '/health') {
    next();
  } else {
    proxyMiddleware(req, res, next);
  }
});

app.listen(config.port, config.host, () => {
  logger.info(`CORS Proxy running on ${config.host}:${config.port}`);
  console.log(`
🌐 CORS Proxy Server is running!
📍 Address: http://${config.host}:${config.port}
🎯 Target: http://localhost:${config.targetPort}

Use this URL in Claude Web App for CORS-free access:
http://localhost:${config.port}
  `);
});
