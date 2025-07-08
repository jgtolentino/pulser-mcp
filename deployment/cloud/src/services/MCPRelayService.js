class MCPRelayService {
  constructor(config, database, cache, logger) {
    this.config = config;
    this.db = database;
    this.cache = cache;
    this.logger = logger;
    this.tools = new Map();
    this.middleware = [];
  }

  async initialize() {
    try {
      // Register built-in MCP tools
      await this.registerBuiltInTools();
      
      // Setup middleware
      this.setupMiddleware();
      
      this.logger.info('MCP Relay Service initialized', { 
        toolCount: this.tools.size,
        middlewareCount: this.middleware.length
      });
    } catch (error) {
      this.logger.error('MCP Relay Service initialization failed', { error: error.message });
      throw error;
    }
  }

  async registerBuiltInTools() {
    // Database tools
    this.registerTool('sqlite_get', {
      description: 'Get value by key from database',
      parameters: {
        key: { type: 'string', required: true, description: 'Key to retrieve' }
      },
      handler: async (params) => {
        const result = await this.db.get(params.key);
        return {
          success: true,
          key: params.key,
          value: result ? result.value : null,
          type: result ? result.type : null,
          found: !!result
        };
      }
    });

    this.registerTool('sqlite_set', {
      description: 'Set key-value pair in database',
      parameters: {
        key: { type: 'string', required: true, description: 'Key to store' },
        value: { type: 'string', required: true, description: 'Value to store' },
        type: { type: 'string', required: false, description: 'Data type', default: 'string' }
      },
      handler: async (params) => {
        const result = await this.db.set(params.key, params.value, params.type || 'string');
        
        // Invalidate cache
        await this.cache.delete(`cache_${params.key}`);
        
        return {
          success: true,
          key: params.key,
          value: params.value,
          type: params.type || 'string',
          changes: result.changes
        };
      }
    });

    this.registerTool('sqlite_delete', {
      description: 'Delete key from database',
      parameters: {
        key: { type: 'string', required: true, description: 'Key to delete' }
      },
      handler: async (params) => {
        const result = await this.db.delete(params.key);
        
        // Invalidate cache
        await this.cache.delete(`cache_${params.key}`);
        
        return {
          success: true,
          key: params.key,
          deleted: result.deleted
        };
      }
    });

    this.registerTool('sqlite_list', {
      description: 'List keys with optional pattern matching',
      parameters: {
        pattern: { type: 'string', required: false, description: 'Pattern to match (% wildcards)', default: '%' },
        limit: { type: 'number', required: false, description: 'Maximum results', default: 100 },
        offset: { type: 'number', required: false, description: 'Results offset', default: 0 }
      },
      handler: async (params) => {
        const result = await this.db.list(
          params.pattern || '%',
          Math.min(params.limit || 100, 1000), // Cap at 1000
          params.offset || 0
        );
        
        return {
          success: true,
          keys: result.keys,
          count: result.count,
          pattern: params.pattern || '%',
          limit: params.limit || 100,
          offset: params.offset || 0
        };
      }
    });

    this.registerTool('sqlite_query', {
      description: 'Execute SQL query on database',
      parameters: {
        query: { type: 'string', required: true, description: 'SQL query to execute' },
        params: { type: 'array', required: false, description: 'Query parameters' }
      },
      handler: async (params) => {
        // Security check
        const query = params.query.toLowerCase().trim();
        const allowedQueries = ['select', 'insert', 'update', 'delete'];
        const queryType = query.split(' ')[0];
        
        if (!allowedQueries.includes(queryType)) {
          throw new Error(`Unauthorized query type: ${queryType}`);
        }
        
        // Additional security checks
        if (query.includes('drop') || query.includes('truncate') || query.includes('alter')) {
          throw new Error('Potentially dangerous query detected');
        }
        
        const result = await this.db.query(params.query, params.params || []);
        
        return {
          success: true,
          query: params.query,
          queryType,
          ...result
        };
      }
    });

    // Cache tools
    this.registerTool('cache_get', {
      description: 'Get value from cache',
      parameters: {
        key: { type: 'string', required: true, description: 'Cache key to retrieve' }
      },
      handler: async (params) => {
        const value = await this.cache.get(params.key);
        return {
          success: true,
          key: params.key,
          value,
          found: value !== null
        };
      }
    });

    this.registerTool('cache_set', {
      description: 'Set value in cache',
      parameters: {
        key: { type: 'string', required: true, description: 'Cache key to store' },
        value: { type: 'any', required: true, description: 'Value to cache' },
        ttl: { type: 'number', required: false, description: 'Time to live in seconds' }
      },
      handler: async (params) => {
        const success = await this.cache.set(params.key, params.value, params.ttl);
        return {
          success,
          key: params.key,
          value: params.value,
          ttl: params.ttl
        };
      }
    });

    this.registerTool('cache_delete', {
      description: 'Delete key from cache',
      parameters: {
        key: { type: 'string', required: true, description: 'Cache key to delete' }
      },
      handler: async (params) => {
        const deleted = await this.cache.delete(params.key);
        return {
          success: true,
          key: params.key,
          deleted
        };
      }
    });

    // System tools
    this.registerTool('system_info', {
      description: 'Get system information',
      parameters: {},
      handler: async () => {
        const memoryUsage = process.memoryUsage();
        const dbStats = await this.db.getStats();
        const cacheStats = await this.cache.getStats();
        
        return {
          success: true,
          system: {
            uptime: process.uptime(),
            memory: {
              rss: Math.round(memoryUsage.rss / 1024 / 1024),
              heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024),
              heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024),
              external: Math.round(memoryUsage.external / 1024 / 1024)
            },
            node: process.version,
            platform: process.platform,
            arch: process.arch
          },
          database: dbStats,
          cache: cacheStats,
          timestamp: new Date().toISOString()
        };
      }
    });

    // Utility tools
    this.registerTool('echo', {
      description: 'Echo input for testing',
      parameters: {
        message: { type: 'string', required: true, description: 'Message to echo' },
        delay: { type: 'number', required: false, description: 'Delay in milliseconds', default: 0 }
      },
      handler: async (params) => {
        if (params.delay > 0) {
          await new Promise(resolve => setTimeout(resolve, params.delay));
        }
        
        return {
          success: true,
          echo: params.message,
          timestamp: new Date().toISOString(),
          delay: params.delay || 0
        };
      }
    });

    this.registerTool('health_check', {
      description: 'Perform comprehensive health check',
      parameters: {},
      handler: async () => {
        const dbHealth = await this.db.healthCheck();
        const cacheHealth = await this.cache.healthCheck();
        
        const overallHealthy = dbHealth.status === 'healthy' && cacheHealth.status === 'healthy';
        
        return {
          success: true,
          status: overallHealthy ? 'healthy' : 'unhealthy',
          checks: {
            database: dbHealth,
            cache: cacheHealth
          },
          timestamp: new Date().toISOString()
        };
      }
    });
  }

  registerTool(name, definition) {
    if (this.tools.has(name)) {
      this.logger.warn('Tool already registered, overwriting', { tool: name });
    }
    
    this.tools.set(name, {
      name,
      description: definition.description,
      parameters: definition.parameters || {},
      handler: definition.handler,
      middleware: definition.middleware || [],
      rateLimit: definition.rateLimit,
      cache: definition.cache || false,
      cacheTtl: definition.cacheTtl || 300
    });
    
    this.logger.debug('Tool registered', { tool: name });
  }

  setupMiddleware() {
    // Caching middleware
    this.middleware.push({
      name: 'cache',
      handler: async (toolName, params, next) => {
        const tool = this.tools.get(toolName);
        if (!tool.cache) {
          return next();
        }
        
        const cacheKey = `tool_cache_${toolName}_${JSON.stringify(params)}`;
        const cached = await this.cache.get(cacheKey);
        
        if (cached) {
          this.logger.debug('Cache hit', { tool: toolName, cacheKey });
          return { ...cached, cached: true };
        }
        
        const result = await next();
        
        if (result.success) {
          await this.cache.set(cacheKey, result, tool.cacheTtl);
          this.logger.debug('Result cached', { tool: toolName, cacheKey, ttl: tool.cacheTtl });
        }
        
        return result;
      }
    });

    // Validation middleware
    this.middleware.push({
      name: 'validation',
      handler: async (toolName, params, next) => {
        const tool = this.tools.get(toolName);
        const validationErrors = this.validateParameters(params, tool.parameters);
        
        if (validationErrors.length > 0) {
          throw new Error(`Validation failed: ${validationErrors.join(', ')}`);
        }
        
        return next();
      }
    });

    // Rate limiting middleware
    this.middleware.push({
      name: 'rateLimit',
      handler: async (toolName, params, next) => {
        const tool = this.tools.get(toolName);
        if (!tool.rateLimit) {
          return next();
        }
        
        const rateLimitKey = `rate_limit_${toolName}`;
        const current = await this.cache.get(rateLimitKey) || 0;
        
        if (current >= tool.rateLimit.requests) {
          throw new Error(`Rate limit exceeded for tool ${toolName}`);
        }
        
        await this.cache.set(rateLimitKey, current + 1, tool.rateLimit.window || 60);
        
        return next();
      }
    });

    // Logging middleware
    this.middleware.push({
      name: 'logging',
      handler: async (toolName, params, next) => {
        const start = Date.now();
        
        this.logger.info('Tool execution started', { 
          tool: toolName, 
          params: this.sanitizeParams(params) 
        });
        
        try {
          const result = await next();
          const duration = Date.now() - start;
          
          this.logger.info('Tool execution completed', { 
            tool: toolName, 
            success: result.success,
            duration 
          });
          
          return result;
        } catch (error) {
          const duration = Date.now() - start;
          
          this.logger.error('Tool execution failed', { 
            tool: toolName, 
            error: error.message,
            duration 
          });
          
          throw error;
        }
      }
    });
  }

  async executeTool(toolName, parameters = {}, options = {}) {
    const start = Date.now();
    
    try {
      if (!this.tools.has(toolName)) {
        throw new Error(`Unknown tool: ${toolName}`);
      }

      const tool = this.tools.get(toolName);
      
      // Create middleware chain
      let index = 0;
      const executeNext = async () => {
        if (index < this.middleware.length) {
          const middleware = this.middleware[index++];
          return middleware.handler(toolName, parameters, executeNext);
        } else {
          // Execute the actual tool
          return tool.handler(parameters, options);
        }
      };

      const result = await Promise.race([
        executeNext(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Tool execution timeout')), this.config.timeoutMs)
        )
      ]);

      const duration = Date.now() - start;
      
      // Record metrics (if monitoring service is available)
      if (this.monitoring) {
        this.monitoring.recordToolExecution(toolName, true, duration);
      }

      return result;
      
    } catch (error) {
      const duration = Date.now() - start;
      
      // Record metrics
      if (this.monitoring) {
        this.monitoring.recordToolExecution(toolName, false, duration, error.message);
      }
      
      throw error;
    }
  }

  async executeBatch(calls, options = {}) {
    if (!this.config.enableBatching) {
      throw new Error('Batch execution is disabled');
    }

    if (calls.length > this.config.batchSize) {
      throw new Error(`Batch size exceeds limit of ${this.config.batchSize}`);
    }

    const results = [];
    const concurrency = options.concurrent ? Math.min(calls.length, 5) : 1;
    
    if (concurrency === 1) {
      // Sequential execution
      for (const call of calls) {
        try {
          const result = await this.executeTool(call.tool, call.parameters, call.options);
          results.push({ success: true, result });
        } catch (error) {
          results.push({ success: false, error: error.message, tool: call.tool });
        }
      }
    } else {
      // Concurrent execution
      const chunks = [];
      for (let i = 0; i < calls.length; i += concurrency) {
        chunks.push(calls.slice(i, i + concurrency));
      }
      
      for (const chunk of chunks) {
        const promises = chunk.map(async (call) => {
          try {
            const result = await this.executeTool(call.tool, call.parameters, call.options);
            return { success: true, result };
          } catch (error) {
            return { success: false, error: error.message, tool: call.tool };
          }
        });
        
        const chunkResults = await Promise.all(promises);
        results.push(...chunkResults);
      }
    }

    return results;
  }

  validateParameters(params, parameterSchema) {
    const errors = [];
    
    // Check required parameters
    for (const [name, schema] of Object.entries(parameterSchema)) {
      if (schema.required && (params[name] === undefined || params[name] === null)) {
        errors.push(`Missing required parameter: ${name}`);
      }
      
      if (params[name] !== undefined) {
        // Type validation
        if (schema.type && !this.validateType(params[name], schema.type)) {
          errors.push(`Parameter ${name} must be of type ${schema.type}`);
        }
        
        // Range validation
        if (schema.min !== undefined && params[name] < schema.min) {
          errors.push(`Parameter ${name} must be >= ${schema.min}`);
        }
        
        if (schema.max !== undefined && params[name] > schema.max) {
          errors.push(`Parameter ${name} must be <= ${schema.max}`);
        }
        
        // Pattern validation
        if (schema.pattern && typeof params[name] === 'string') {
          const regex = new RegExp(schema.pattern);
          if (!regex.test(params[name])) {
            errors.push(`Parameter ${name} does not match required pattern`);
          }
        }
      }
    }
    
    return errors;
  }

  validateType(value, expectedType) {
    switch (expectedType) {
      case 'string':
        return typeof value === 'string';
      case 'number':
        return typeof value === 'number' && !isNaN(value);
      case 'boolean':
        return typeof value === 'boolean';
      case 'array':
        return Array.isArray(value);
      case 'object':
        return typeof value === 'object' && value !== null && !Array.isArray(value);
      case 'any':
        return true;
      default:
        return false;
    }
  }

  sanitizeParams(params) {
    // Remove sensitive information from params for logging
    const sanitized = { ...params };
    const sensitiveKeys = ['password', 'token', 'secret', 'key', 'auth'];
    
    for (const key of Object.keys(sanitized)) {
      if (sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive))) {
        sanitized[key] = '[REDACTED]';
      }
    }
    
    return sanitized;
  }

  async getCapabilities() {
    const tools = Array.from(this.tools.entries()).map(([name, tool]) => ({
      name,
      description: tool.description,
      parameters: tool.parameters
    }));

    return {
      capabilities: [
        'database_operations',
        'cache_operations',
        'system_monitoring',
        'batch_execution',
        'real_time_relay'
      ],
      tools,
      version: '1.0.0',
      server: 'mcp-cloud-relay',
      features: {
        batchExecution: this.config.enableBatching,
        webSocket: this.config.enableWebSocket,
        caching: true,
        rateLimit: true,
        validation: true
      }
    };
  }

  async getToolUsageStats() {
    const stats = [];
    
    for (const [name] of this.tools) {
      const cacheKey = `tool_stats_${name}`;
      const toolStats = await this.cache.get(cacheKey) || {
        executions: 0,
        errors: 0,
        totalDuration: 0
      };
      
      stats.push({
        tool: name,
        executions: toolStats.executions,
        errors: toolStats.errors,
        successRate: toolStats.executions > 0 
          ? ((toolStats.executions - toolStats.errors) / toolStats.executions * 100).toFixed(2)
          : 0,
        avgDuration: toolStats.executions > 0 
          ? (toolStats.totalDuration / toolStats.executions).toFixed(2)
          : 0
      });
    }
    
    return stats;
  }

  setMonitoringService(monitoring) {
    this.monitoring = monitoring;
  }
}

module.exports = MCPRelayService;
