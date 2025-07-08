class MonitoringService {
  constructor(config, logger) {
    this.config = config;
    this.logger = logger;
    this.metrics = {
      requests: new Map(),
      errors: new Map(),
      responseTime: [],
      toolExecutions: new Map(),
      startTime: Date.now()
    };
    this.isEnabled = config.enabled;
  }

  async initialize() {
    if (!this.isEnabled) {
      this.logger.info('Monitoring disabled');
      return;
    }

    // Initialize metrics collection
    this.initializeMetrics();
    
    // Start metrics cleanup interval
    setInterval(() => {
      this.cleanupMetrics();
    }, 60000); // Every minute

    this.logger.info('Monitoring service initialized');
  }

  initializeMetrics() {
    // Initialize basic metrics
    this.metrics.requests.set('total', 0);
    this.metrics.requests.set('success', 0);
    this.metrics.requests.set('error', 0);
    this.metrics.errors.set('4xx', 0);
    this.metrics.errors.set('5xx', 0);
  }

  recordRequest(method, path, statusCode, duration) {
    if (!this.isEnabled) return;

    try {
      // Record total requests
      this.incrementMetric(this.metrics.requests, 'total');
      
      // Record by method
      this.incrementMetric(this.metrics.requests, method.toLowerCase());
      
      // Record by status
      if (statusCode >= 200 && statusCode < 400) {
        this.incrementMetric(this.metrics.requests, 'success');
      } else {
        this.incrementMetric(this.metrics.requests, 'error');
        
        if (statusCode >= 400 && statusCode < 500) {
          this.incrementMetric(this.metrics.errors, '4xx');
        } else if (statusCode >= 500) {
          this.incrementMetric(this.metrics.errors, '5xx');
        }
      }

      // Record response time
      this.metrics.responseTime.push({
        duration,
        timestamp: Date.now(),
        path,
        method,
        status: statusCode
      });

      // Keep only last 1000 response times
      if (this.metrics.responseTime.length > 1000) {
        this.metrics.responseTime = this.metrics.responseTime.slice(-1000);
      }

    } catch (error) {
      this.logger.error('Error recording request metrics', { error: error.message });
    }
  }

  recordToolExecution(tool, success, duration, error = null) {
    if (!this.isEnabled) return;

    try {
      const key = `tool_${tool}`;
      
      if (!this.metrics.toolExecutions.has(key)) {
        this.metrics.toolExecutions.set(key, {
          total: 0,
          success: 0,
          error: 0,
          totalDuration: 0,
          lastError: null,
          lastExecution: null
        });
      }

      const stats = this.metrics.toolExecutions.get(key);
      stats.total++;
      stats.totalDuration += duration;
      stats.lastExecution = new Date().toISOString();

      if (success) {
        stats.success++;
      } else {
        stats.error++;
        stats.lastError = error;
      }

    } catch (error) {
      this.logger.error('Error recording tool execution metrics', { error: error.message });
    }
  }

  recordError(error, context = {}) {
    if (!this.isEnabled) return;

    try {
      this.incrementMetric(this.metrics.errors, 'application');
      
      this.logger.error('Application error recorded', {
        error: error.message,
        stack: error.stack,
        context
      });
    } catch (err) {
      this.logger.error('Error recording error metrics', { error: err.message });
    }
  }

  incrementMetric(map, key, amount = 1) {
    const current = map.get(key) || 0;
    map.set(key, current + amount);
  }

  async getMetrics() {
    if (!this.isEnabled) {
      return 'Monitoring disabled';
    }

    try {
      const uptime = Math.floor((Date.now() - this.metrics.startTime) / 1000);
      const memoryUsage = process.memoryUsage();
      
      // Calculate response time statistics
      const responseTimes = this.metrics.responseTime.map(r => r.duration);
      const avgResponseTime = responseTimes.length > 0 
        ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length 
        : 0;
      
      const p95ResponseTime = this.calculatePercentile(responseTimes, 95);
      const p99ResponseTime = this.calculatePercentile(responseTimes, 99);

      // Generate Prometheus-style metrics
      const metrics = [];
      
      // Basic metrics
      metrics.push(`# HELP mcp_uptime_seconds Total uptime in seconds`);
      metrics.push(`# TYPE mcp_uptime_seconds counter`);
      metrics.push(`mcp_uptime_seconds ${uptime}`);
      
      // Request metrics
      metrics.push(`# HELP mcp_requests_total Total number of requests`);
      metrics.push(`# TYPE mcp_requests_total counter`);
      for (const [key, value] of this.metrics.requests) {
        metrics.push(`mcp_requests_total{type="${key}"} ${value}`);
      }
      
      // Error metrics
      metrics.push(`# HELP mcp_errors_total Total number of errors`);
      metrics.push(`# TYPE mcp_errors_total counter`);
      for (const [key, value] of this.metrics.errors) {
        metrics.push(`mcp_errors_total{type="${key}"} ${value}`);
      }
      
      // Response time metrics
      metrics.push(`# HELP mcp_response_time_ms Response time statistics`);
      metrics.push(`# TYPE mcp_response_time_ms histogram`);
      metrics.push(`mcp_response_time_ms{quantile="0.5"} ${this.calculatePercentile(responseTimes, 50)}`);
      metrics.push(`mcp_response_time_ms{quantile="0.95"} ${p95ResponseTime}`);
      metrics.push(`mcp_response_time_ms{quantile="0.99"} ${p99ResponseTime}`);
      metrics.push(`mcp_response_time_ms_avg ${avgResponseTime.toFixed(2)}`);
      
      // Tool execution metrics
      metrics.push(`# HELP mcp_tool_executions_total Total tool executions`);
      metrics.push(`# TYPE mcp_tool_executions_total counter`);
      for (const [tool, stats] of this.metrics.toolExecutions) {
        const toolName = tool.replace('tool_', '');
        metrics.push(`mcp_tool_executions_total{tool="${toolName}",status="success"} ${stats.success}`);
        metrics.push(`mcp_tool_executions_total{tool="${toolName}",status="error"} ${stats.error}`);
        
        const avgDuration = stats.total > 0 ? (stats.totalDuration / stats.total).toFixed(2) : 0;
        metrics.push(`mcp_tool_duration_ms_avg{tool="${toolName}"} ${avgDuration}`);
      }
      
      // Memory metrics
      metrics.push(`# HELP mcp_memory_usage_bytes Memory usage in bytes`);
      metrics.push(`# TYPE mcp_memory_usage_bytes gauge`);
      metrics.push(`mcp_memory_usage_bytes{type="rss"} ${memoryUsage.rss}`);
      metrics.push(`mcp_memory_usage_bytes{type="heap_total"} ${memoryUsage.heapTotal}`);
      metrics.push(`mcp_memory_usage_bytes{type="heap_used"} ${memoryUsage.heapUsed}`);
      metrics.push(`mcp_memory_usage_bytes{type="external"} ${memoryUsage.external}`);
      
      return metrics.join('\n');
    } catch (error) {
      this.logger.error('Error generating metrics', { error: error.message });
      return 'Error generating metrics';
    }
  }

  calculatePercentile(values, percentile) {
    if (values.length === 0) return 0;
    
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil(sorted.length * (percentile / 100)) - 1;
    return sorted[Math.max(0, index)] || 0;
  }

  async getDashboardData() {
    if (!this.isEnabled) {
      return { error: 'Monitoring disabled' };
    }

    try {
      const uptime = Math.floor((Date.now() - this.metrics.startTime) / 1000);
      const memoryUsage = process.memoryUsage();
      
      // Recent response times (last 100)
      const recentResponseTimes = this.metrics.responseTime
        .slice(-100)
        .map(r => ({
          timestamp: r.timestamp,
          duration: r.duration,
          path: r.path,
          method: r.method,
          status: r.status
        }));

      // Tool execution summary
      const toolStats = Array.from(this.metrics.toolExecutions.entries()).map(([tool, stats]) => ({
        tool: tool.replace('tool_', ''),
        total: stats.total,
        success: stats.success,
        error: stats.error,
        successRate: stats.total > 0 ? ((stats.success / stats.total) * 100).toFixed(2) : 0,
        avgDuration: stats.total > 0 ? (stats.totalDuration / stats.total).toFixed(2) : 0,
        lastExecution: stats.lastExecution,
        lastError: stats.lastError
      }));

      // Error rate calculation
      const totalRequests = this.metrics.requests.get('total') || 0;
      const totalErrors = this.metrics.requests.get('error') || 0;
      const errorRate = totalRequests > 0 ? ((totalErrors / totalRequests) * 100).toFixed(2) : 0;

      return {
        uptime,
        memory: {
          rss: Math.round(memoryUsage.rss / 1024 / 1024),
          heapTotal: Math.round(memoryUsage.heapTotal / 1024 / 1024),
          heapUsed: Math.round(memoryUsage.heapUsed / 1024 / 1024),
          external: Math.round(memoryUsage.external / 1024 / 1024)
        },
        requests: Object.fromEntries(this.metrics.requests),
        errors: Object.fromEntries(this.metrics.errors),
        errorRate: parseFloat(errorRate),
        recentResponseTimes,
        toolStats,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      this.logger.error('Error generating dashboard data', { error: error.message });
      return { error: error.message };
    }
  }

  async getHealthMetrics() {
    if (!this.isEnabled) {
      return { status: 'disabled' };
    }

    try {
      const uptime = Math.floor((Date.now() - this.metrics.startTime) / 1000);
      const memoryUsage = process.memoryUsage();
      const totalRequests = this.metrics.requests.get('total') || 0;
      const totalErrors = this.metrics.requests.get('error') || 0;
      const errorRate = totalRequests > 0 ? (totalErrors / totalRequests) * 100 : 0;

      // Health thresholds
      const memoryThreshold = 500; // MB
      const errorRateThreshold = 5; // 5%
      const responseTimeThreshold = 5000; // 5 seconds

      const recentResponseTimes = this.metrics.responseTime.slice(-10);
      const avgRecentResponseTime = recentResponseTimes.length > 0
        ? recentResponseTimes.reduce((a, b) => a + b.duration, 0) / recentResponseTimes.length
        : 0;

      const issues = [];
      
      if (memoryUsage.heapUsed / 1024 / 1024 > memoryThreshold) {
        issues.push(`High memory usage: ${Math.round(memoryUsage.heapUsed / 1024 / 1024)}MB`);
      }
      
      if (errorRate > errorRateThreshold) {
        issues.push(`High error rate: ${errorRate.toFixed(2)}%`);
      }
      
      if (avgRecentResponseTime > responseTimeThreshold) {
        issues.push(`Slow response time: ${avgRecentResponseTime.toFixed(0)}ms`);
      }

      return {
        status: issues.length === 0 ? 'healthy' : 'warning',
        uptime,
        errorRate: errorRate.toFixed(2),
        avgResponseTime: avgRecentResponseTime.toFixed(0),
        memoryUsageMB: Math.round(memoryUsage.heapUsed / 1024 / 1024),
        issues,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  cleanupMetrics() {
    try {
      // Clean old response time entries (older than 1 hour)
      const oneHourAgo = Date.now() - (60 * 60 * 1000);
      this.metrics.responseTime = this.metrics.responseTime.filter(
        r => r.timestamp > oneHourAgo
      );

      // Reset daily metrics at midnight
      const now = new Date();
      if (now.getHours() === 0 && now.getMinutes() === 0) {
        this.resetDailyMetrics();
      }
    } catch (error) {
      this.logger.error('Error cleaning up metrics', { error: error.message });
    }
  }

  resetDailyMetrics() {
    // Reset some metrics daily but keep cumulative ones
    this.metrics.responseTime = [];
    
    this.logger.info('Daily metrics reset completed');
  }

  async exportMetrics(format = 'prometheus') {
    switch (format) {
      case 'prometheus':
        return await this.getMetrics();
      case 'json':
        return JSON.stringify(await this.getDashboardData(), null, 2);
      case 'health':
        return JSON.stringify(await this.getHealthMetrics(), null, 2);
      default:
        throw new Error(`Unsupported export format: ${format}`);
    }
  }

  // Alert system
  checkAlerts() {
    if (!this.isEnabled) return;

    try {
      const healthMetrics = this.getHealthMetrics();
      
      if (healthMetrics.status === 'warning' || healthMetrics.status === 'error') {
        this.logger.warn('Health alert triggered', { health: healthMetrics });
        
        // Here you could integrate with external alerting systems
        // like PagerDuty, Slack, email, etc.
      }
    } catch (error) {
      this.logger.error('Error checking alerts', { error: error.message });
    }
  }

  // Custom metrics
  recordCustomMetric(name, value, labels = {}) {
    if (!this.isEnabled) return;

    try {
      if (!this.metrics.custom) {
        this.metrics.custom = new Map();
      }

      const key = `${name}_${JSON.stringify(labels)}`;
      this.metrics.custom.set(key, {
        name,
        value,
        labels,
        timestamp: Date.now()
      });
    } catch (error) {
      this.logger.error('Error recording custom metric', { error: error.message });
    }
  }

  async close() {
    if (this.isEnabled) {
      this.logger.info('Monitoring service shutting down');
      
      // Export final metrics before shutdown
      try {
        const finalMetrics = await this.getDashboardData();
        this.logger.info('Final metrics', { metrics: finalMetrics });
      } catch (error) {
        this.logger.error('Error exporting final metrics', { error: error.message });
      }
    }
  }
}

module.exports = MonitoringService;
