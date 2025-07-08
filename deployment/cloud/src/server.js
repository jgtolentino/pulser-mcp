const express = require('express');
const cors = require('cors');
const winston = require('winston');
const compression = require('compression');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const slowDown = require('express-slow-down');
const cron = require('node-cron');
require('dotenv').config();

// Database adapters
const DatabaseAdapter = require('./adapters/DatabaseAdapter');
const CacheAdapter = require('./adapters/CacheAdapter');
const MonitoringService = require('./services/MonitoringService');
const MCPRelayService = require('./services/MCPRelayService');

class MCPCloudServer {
  constructor() {
    this.app = express();
    this.config = this.loadConfiguration();
    this.logger = this.setupLogging();
    this.db = null;
    this.cache = null;
    this.monitoring = null;
    this.mcpRelay = null;
  }

  loadConfiguration() {
    return {
      port: process.env.PORT || 3000,
      host: process.env.HOST || '0.0.0.0',
      environment: process.env.NODE_ENV || 'production',
      
      // Database configuration
      database: {
        type: process.env.DB_TYPE || 'postgresql', // sqlite, postgresql, mysql, mongodb
        url: process.env.DATABASE_URL || process.env.DB_URL,
        ssl: process.env.DB_SSL === 'true',
        maxConnections: parseInt(process.env.DB_MAX_CONNECTIONS) || 20,
        timeout: parseInt(process.env.DB_TIMEOUT) || 30000
      },
      
      // Cache configuration
      cache: {
        type: process.env.CACHE_TYPE || 'memory', // memory, redis, memcached
        url: process.env.REDIS_URL || process.env.CACHE_URL,
        ttl: parseInt(process.env.CACHE_TTL) || 3600,
        maxSize: parseInt(process.env.CACHE_MAX_SIZE) || 1000
      },
      
      // Security configuration
      security: {
        apiKey: process.env.API_KEY,
        corsOrigins: (process.env.CORS_ORIGINS || '*').split(','),
        rateLimitRequests: parseInt(process.env.RATE_LIMIT_REQUESTS) || 100,
        rateLimitWindow: parseInt(process.env.RATE_LIMIT_WINDOW) || 900000, // 15 minutes
        enableSlowDown: process.env.ENABLE_SLOW_DOWN === 'true'
      },
      
      // Monitoring configuration
      monitoring: {
        enabled: process.env.MONITORING_ENABLED !== 'false',
        logLevel: process.env.LOG_LEVEL || 'info',
        metricsPort: parseInt(process.env.METRICS_PORT) || 9090,
        healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL) || 30000
      },
      
      // MCP configuration
      mcp: {
        enableWebSocket: process.env.ENABLE_WEBSOCKET !== 'false',
        maxPayloadSize: process.env.MAX_PAYLOAD_SIZE || '10mb',
        enableBatching: process.env.ENABLE_BATCHING === 'true',
        batchSize: parseInt(process.env.BATCH_SIZE) || 10,
        timeoutMs: parseInt(process.env.MCP_TIMEOUT) || 30000
      }
    };
  }

  setupLogging() {
    const transports = [
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          winston.format.timestamp(),
          winston.format.printf(({ timestamp, level, message, ...meta }) => {
            return `${timestamp} [${level}]: ${message} ${Object.keys(meta).length ? JSON.stringify(meta) : ''}`;
          })
        )
      })
    ];

    // Add file logging in production
    if (this.config.environment === 'production') {
      transports.push(
        new winston.transports.File({
          filename: 'logs/error.log',
          level: 'error',
          format: winston.format.json()
        }),
        new winston.transports.File({
          filename: 'logs/combined.log',
          format: winston.format.json()
        })
      );
    }

    return winston.createLogger({
      level: this.config.monitoring.logLevel,
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      transports
    });
  }

  async initialize() {
    try {
      this.logger.info('Initializing MCP Cloud Server', { config: this.config });

      // Setup database
      this.db = new DatabaseAdapter(this.config.database, this.logger);
      await this.db.initialize();

      // Setup cache
      this.cache = new CacheAdapter(this.config.cache, this.logger);
      await this.cache.initialize();

      // Setup monitoring
      this.monitoring = new MonitoringService(this.config.monitoring, this.logger);
      await this.monitoring.initialize();

      // Setup MCP relay
      this.mcpRelay = new MCPRelayService(this.config.mcp, this.db, this.cache, this.logger);
      await this.mcpRelay.initialize();

      // Setup Express middleware
      this.setupMiddleware();

      // Setup routes
      this.setupRoutes();

      // Setup scheduled tasks
      this.setupScheduledTasks();

      // Start server
      await this.start();

    } catch (error) {
      this.logger.error('Failed to initialize server', { error: error.message, stack: error.stack });
      process.exit(1);
    }
  }

  setupMiddleware() {
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: false,
      crossOriginEmbedderPolicy: false
    }));

    // Performance middleware
    this.app.use(compression());

    // CORS middleware
    this.app.use(cors({
      origin: this.config.security.corsOrigins.includes('*') 
        ? true 
        : this.config.security.corsOrigins,
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key', 'X-MCP-Version']
    }));

    // Rate limiting
    const limiter = rateLimit({
      windowMs: this.config.security.rateLimitWindow,
      max: this.config.security.rateLimitRequests,
      message: {
        error: 'Too many requests',
        retryAfter: Math.ceil(this.config.security.rateLimitWindow / 1000)
      },
      standardHeaders: true,
      legacyHeaders: false
    });
    this.app.use(limiter);

    // Slow down repeated requests
    if (this.config.security.enableSlowDown) {
      const speedLimiter = slowDown({
        windowMs: this.config.security.rateLimitWindow,
        delayAfter: Math.floor(this.config.security.rateLimitRequests / 2),
        delayMs: 500
      });
      this.app.use(speedLimiter);
    }

    // Body parsing
    this.app.use(express.json({ 
      limit: this.config.mcp.maxPayloadSize,
      strict: true
    }));
    this.app.use(express.urlencoded({ 
      extended: true, 
      limit: this.config.mcp.maxPayloadSize 
    }));

    // Request logging
    this.app.use((req, res, next) => {
      const start = Date.now();
      
      res.on('finish', () => {
        const duration = Date.now() - start;
        this.logger.info('HTTP Request', {
          method: req.method,
          url: req.url,
          status: res.statusCode,
          duration,
          ip: req.ip,
          userAgent: req.get('User-Agent')
        });
        
        // Update monitoring metrics
        if (this.monitoring) {
          this.monitoring.recordRequest(req.method, req.url, res.statusCode, duration);
        }
      });
      
      next();
    });

    // Authentication middleware
    this.app.use((req, res, next) => {
      // Skip auth for health checks and public endpoints
      if (req.path === '/health' || req.path === '/metrics' || req.path === '/') {
        return next();
      }

      const apiKey = req.header('X-API-Key') || req.header('Authorization')?.replace('Bearer ', '');
      
      if (this.config.security.apiKey && apiKey !== this.config.security.apiKey) {
        return res.status(401).json({ 
          error: 'Unauthorized',
          message: 'Valid API key required'
        });
      }
      
      next();
    });
  }

  setupRoutes() {
    // Root endpoint
    this.app.get('/', (req, res) => {
      res.json({
        name: 'MCP Cloud Relay Server',
        version: '1.0.0',
        status: 'running',
        timestamp: new Date().toISOString(),
        endpoints: {
          health: '/health',
          capabilities: '/capabilities',
          mcp: '/mcp/call',
          metrics: '/metrics'
        }
      });
    });

    // Health check endpoint
    this.app.get('/health', async (req, res) => {
      try {
        const health = await this.getHealthStatus();
        res.json(health);
      } catch (error) {
        this.logger.error('Health check failed', { error: error.message });
        res.status(503).json({
          status: 'unhealthy',
          error: error.message,
          timestamp: new Date().toISOString()
        });
      }
    });

    // Capabilities endpoint
    this.app.get('/capabilities', async (req, res) => {
      try {
        const capabilities = await this.mcpRelay.getCapabilities();
        res.json(capabilities);
      } catch (error) {
        this.logger.error('Failed to get capabilities', { error: error.message });
        res.status(500).json({ error: error.message });
      }
    });

    // MCP call endpoint
    this.app.post('/mcp/call', async (req, res) => {
      try {
        const { tool, parameters, options = {} } = req.body;
        
        if (!tool) {
          return res.status(400).json({ 
            error: 'Missing required field: tool' 
          });
        }

        const result = await this.mcpRelay.executeTool(tool, parameters, options);
        res.json(result);
      } catch (error) {
        this.logger.error('MCP call failed', { 
          error: error.message, 
          tool: req.body.tool,
          stack: error.stack
        });
        res.status(500).json({ 
          error: error.message,
          tool: req.body.tool
        });
      }
    });

    // Batch MCP calls endpoint
    this.app.post('/mcp/batch', async (req, res) => {
      try {
        const { calls, options = {} } = req.body;
        
        if (!Array.isArray(calls)) {
          return res.status(400).json({ 
            error: 'Calls must be an array' 
          });
        }

        if (calls.length > this.config.mcp.batchSize) {
          return res.status(400).json({ 
            error: `Batch size exceeds limit of ${this.config.mcp.batchSize}` 
          });
        }

        const results = await this.mcpRelay.executeBatch(calls, options);
        res.json({ results });
      } catch (error) {
        this.logger.error('Batch MCP call failed', { error: error.message });
        res.status(500).json({ error: error.message });
      }
    });

    // Metrics endpoint
    this.app.get('/metrics', async (req, res) => {
      try {
        const metrics = await this.monitoring.getMetrics();
        res.set('Content-Type', 'text/plain');
        res.send(metrics);
      } catch (error) {
        this.logger.error('Failed to get metrics', { error: error.message });
        res.status(500).json({ error: error.message });
      }
    });

    // Database stats endpoint
    this.app.get('/stats', async (req, res) => {
      try {
        const stats = await this.db.getStats();
        res.json(stats);
      } catch (error) {
        this.logger.error('Failed to get stats', { error: error.message });
        res.status(500).json({ error: error.message });
      }
    });

    // Error handling middleware
    this.app.use((error, req, res, next) => {
      this.logger.error('Unhandled error', { 
        error: error.message, 
        stack: error.stack,
        url: req.url,
        method: req.method
      });
      
      res.status(500).json({
        error: 'Internal server error',
        message: this.config.environment === 'development' ? error.message : 'Something went wrong'
      });
    });

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not found',
        message: `Route ${req.method} ${req.originalUrl} not found`
      });
    });
  }

  setupScheduledTasks() {
    // Database cleanup task - runs daily at 2 AM
    cron.schedule('0 2 * * *', async () => {
      try {
        this.logger.info('Running daily database cleanup');
        await this.db.cleanup();
      } catch (error) {
        this.logger.error('Database cleanup failed', { error: error.message });
      }
    });

    // Cache cleanup task - runs hourly
    cron.schedule('0 * * * *', async () => {
      try {
        this.logger.info('Running cache cleanup');
        await this.cache.cleanup();
      } catch (error) {
        this.logger.error('Cache cleanup failed', { error: error.message });
      }
    });

    // Health monitoring task - runs every 5 minutes
    cron.schedule('*/5 * * * *', async () => {
      try {
        const health = await this.getHealthStatus();
        if (health.status !== 'healthy') {
          this.logger.warn('Health check warning', { health });
        }
      } catch (error) {
        this.logger.error('Health monitoring failed', { error: error.message });
      }
    });
  }

  async getHealthStatus() {
    const checks = {
      database: await this.db.healthCheck(),
      cache: await this.cache.healthCheck(),
      memory: this.getMemoryUsage(),
      uptime: process.uptime()
    };

    const isHealthy = Object.values(checks).every(check => 
      typeof check === 'object' ? check.status === 'healthy' : true
    );

    return {
      status: isHealthy ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      checks,
      version: '1.0.0',
      environment: this.config.environment
    };
  }

  getMemoryUsage() {
    const usage = process.memoryUsage();
    return {
      rss: Math.round(usage.rss / 1024 / 1024),
      heapTotal: Math.round(usage.heapTotal / 1024 / 1024),
      heapUsed: Math.round(usage.heapUsed / 1024 / 1024),
      external: Math.round(usage.external / 1024 / 1024)
    };
  }

  async start() {
    return new Promise((resolve, reject) => {
      const server = this.app.listen(this.config.port, this.config.host, () => {
        this.logger.info('MCP Cloud Server started', {
          port: this.config.port,
          host: this.config.host,
          environment: this.config.environment,
          database: this.config.database.type,
          cache: this.config.cache.type
        });

        console.log(`
🚀 MCP Cloud Relay Server is running!
📍 Address: http://${this.config.host}:${this.config.port}
🏥 Health: http://${this.config.host}:${this.config.port}/health
🔧 Capabilities: http://${this.config.host}:${this.config.port}/capabilities
📊 Metrics: http://${this.config.host}:${this.config.port}/metrics

Environment: ${this.config.environment}
Database: ${this.config.database.type}
Cache: ${this.config.cache.type}
        `);

        resolve(server);
      });

      server.on('error', (error) => {
        this.logger.error('Server failed to start', { error: error.message });
        reject(error);
      });

      // Graceful shutdown
      const gracefulShutdown = async () => {
        this.logger.info('Initiating graceful shutdown...');
        
        server.close(async () => {
          try {
            if (this.db) await this.db.close();
            if (this.cache) await this.cache.close();
            if (this.monitoring) await this.monitoring.close();
            
            this.logger.info('Graceful shutdown completed');
            process.exit(0);
          } catch (error) {
            this.logger.error('Error during shutdown', { error: error.message });
            process.exit(1);
          }
        });
      };

      process.on('SIGTERM', gracefulShutdown);
      process.on('SIGINT', gracefulShutdown);
    });
  }
}

// Start the server
const server = new MCPCloudServer();
server.initialize().catch(console.error);

module.exports = MCPCloudServer;
