const Redis = require('ioredis');

class CacheAdapter {
  constructor(config, logger) {
    this.config = config;
    this.logger = logger;
    this.client = null;
    this.type = config.type;
    this.memoryCache = new Map();
    this.memoryTtl = new Map();
  }

  async initialize() {
    try {
      switch (this.type) {
        case 'redis':
          await this.initializeRedis();
          break;
        case 'memory':
          await this.initializeMemory();
          break;
        default:
          throw new Error(`Unsupported cache type: ${this.type}`);
      }

      this.logger.info('Cache initialized successfully', { type: this.type });
    } catch (error) {
      this.logger.error('Cache initialization failed', { error: error.message });
      throw error;
    }
  }

  async initializeRedis() {
    if (!this.config.url) {
      throw new Error('Redis URL is required');
    }

    this.client = new Redis(this.config.url, {
      retryDelayOnFailover: 100,
      enableReadyCheck: false,
      maxRetriesPerRequest: 3,
      lazyConnect: true
    });

    this.client.on('error', (error) => {
      this.logger.error('Redis error', { error: error.message });
    });

    this.client.on('connect', () => {
      this.logger.info('Redis connected');
    });

    this.client.on('disconnect', () => {
      this.logger.warn('Redis disconnected');
    });

    // Test connection
    await this.client.ping();
  }

  async initializeMemory() {
    this.memoryCache = new Map();
    this.memoryTtl = new Map();

    // Cleanup expired entries every minute
    setInterval(() => {
      this.cleanupMemoryCache();
    }, 60000);
  }

  cleanupMemoryCache() {
    const now = Date.now();
    for (const [key, expiry] of this.memoryTtl.entries()) {
      if (expiry <= now) {
        this.memoryCache.delete(key);
        this.memoryTtl.delete(key);
      }
    }

    // Limit cache size
    if (this.memoryCache.size > this.config.maxSize) {
      const entries = Array.from(this.memoryCache.keys());
      const toDelete = entries.slice(0, entries.length - this.config.maxSize);
      toDelete.forEach(key => {
        this.memoryCache.delete(key);
        this.memoryTtl.delete(key);
      });
    }
  }

  async get(key) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.redisGet(key);
        case 'memory':
          return this.memoryGet(key);
      }
    } catch (error) {
      this.logger.error('Cache get error', { key, error: error.message });
      return null;
    }
  }

  async set(key, value, ttl = null) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.redisSet(key, value, ttl);
        case 'memory':
          return this.memorySet(key, value, ttl);
      }
    } catch (error) {
      this.logger.error('Cache set error', { key, error: error.message });
      return false;
    }
  }

  async delete(key) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.redisDelete(key);
        case 'memory':
          return this.memoryDelete(key);
      }
    } catch (error) {
      this.logger.error('Cache delete error', { key, error: error.message });
      return false;
    }
  }

  async exists(key) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.redisExists(key);
        case 'memory':
          return this.memoryExists(key);
      }
    } catch (error) {
      this.logger.error('Cache exists error', { key, error: error.message });
      return false;
    }
  }

  async keys(pattern = '*') {
    try {
      switch (this.type) {
        case 'redis':
          return await this.redisKeys(pattern);
        case 'memory':
          return this.memoryKeys(pattern);
      }
    } catch (error) {
      this.logger.error('Cache keys error', { pattern, error: error.message });
      return [];
    }
  }

  async flush() {
    try {
      switch (this.type) {
        case 'redis':
          return await this.redisFlush();
        case 'memory':
          return this.memoryFlush();
      }
    } catch (error) {
      this.logger.error('Cache flush error', { error: error.message });
      return false;
    }
  }

  // Redis implementations
  async redisGet(key) {
    const value = await this.client.get(key);
    if (value === null) return null;
    
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }

  async redisSet(key, value, ttl = null) {
    const serialized = typeof value === 'string' ? value : JSON.stringify(value);
    const actualTtl = ttl || this.config.ttl;
    
    if (actualTtl) {
      await this.client.setex(key, actualTtl, serialized);
    } else {
      await this.client.set(key, serialized);
    }
    
    return true;
  }

  async redisDelete(key) {
    const result = await this.client.del(key);
    return result > 0;
  }

  async redisExists(key) {
    const result = await this.client.exists(key);
    return result > 0;
  }

  async redisKeys(pattern) {
    return await this.client.keys(pattern);
  }

  async redisFlush() {
    await this.client.flushdb();
    return true;
  }

  // Memory implementations
  memoryGet(key) {
    if (!this.memoryCache.has(key)) return null;
    
    // Check TTL
    const expiry = this.memoryTtl.get(key);
    if (expiry && expiry <= Date.now()) {
      this.memoryCache.delete(key);
      this.memoryTtl.delete(key);
      return null;
    }
    
    return this.memoryCache.get(key);
  }

  memorySet(key, value, ttl = null) {
    this.memoryCache.set(key, value);
    
    const actualTtl = ttl || this.config.ttl;
    if (actualTtl) {
      this.memoryTtl.set(key, Date.now() + (actualTtl * 1000));
    }
    
    return true;
  }

  memoryDelete(key) {
    const deleted = this.memoryCache.delete(key);
    this.memoryTtl.delete(key);
    return deleted;
  }

  memoryExists(key) {
    if (!this.memoryCache.has(key)) return false;
    
    // Check TTL
    const expiry = this.memoryTtl.get(key);
    if (expiry && expiry <= Date.now()) {
      this.memoryCache.delete(key);
      this.memoryTtl.delete(key);
      return false;
    }
    
    return true;
  }

  memoryKeys(pattern) {
    const keys = Array.from(this.memoryCache.keys());
    
    if (pattern === '*') return keys;
    
    // Convert pattern to regex
    const regex = new RegExp(
      '^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$',
      'i'
    );
    
    return keys.filter(key => regex.test(key));
  }

  memoryFlush() {
    this.memoryCache.clear();
    this.memoryTtl.clear();
    return true;
  }

  // Utility methods
  async increment(key, amount = 1) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.client.incrby(key, amount);
        case 'memory':
          const current = this.memoryGet(key) || 0;
          const newValue = current + amount;
          this.memorySet(key, newValue);
          return newValue;
      }
    } catch (error) {
      this.logger.error('Cache increment error', { key, amount, error: error.message });
      return null;
    }
  }

  async expire(key, ttl) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.client.expire(key, ttl);
        case 'memory':
          if (this.memoryCache.has(key)) {
            this.memoryTtl.set(key, Date.now() + (ttl * 1000));
            return true;
          }
          return false;
      }
    } catch (error) {
      this.logger.error('Cache expire error', { key, ttl, error: error.message });
      return false;
    }
  }

  async ttl(key) {
    try {
      switch (this.type) {
        case 'redis':
          return await this.client.ttl(key);
        case 'memory':
          const expiry = this.memoryTtl.get(key);
          if (!expiry) return -1;
          const remaining = Math.max(0, Math.floor((expiry - Date.now()) / 1000));
          return remaining;
      }
    } catch (error) {
      this.logger.error('Cache TTL error', { key, error: error.message });
      return -1;
    }
  }

  async mget(keys) {
    try {
      switch (this.type) {
        case 'redis':
          const values = await this.client.mget(...keys);
          return values.map(value => {
            if (value === null) return null;
            try {
              return JSON.parse(value);
            } catch {
              return value;
            }
          });
        case 'memory':
          return keys.map(key => this.memoryGet(key));
      }
    } catch (error) {
      this.logger.error('Cache mget error', { keys, error: error.message });
      return keys.map(() => null);
    }
  }

  async mset(keyValuePairs, ttl = null) {
    try {
      switch (this.type) {
        case 'redis':
          const pipeline = this.client.pipeline();
          Object.entries(keyValuePairs).forEach(([key, value]) => {
            const serialized = typeof value === 'string' ? value : JSON.stringify(value);
            if (ttl) {
              pipeline.setex(key, ttl, serialized);
            } else {
              pipeline.set(key, serialized);
            }
          });
          await pipeline.exec();
          return true;
        case 'memory':
          Object.entries(keyValuePairs).forEach(([key, value]) => {
            this.memorySet(key, value, ttl);
          });
          return true;
      }
    } catch (error) {
      this.logger.error('Cache mset error', { error: error.message });
      return false;
    }
  }

  async healthCheck() {
    try {
      switch (this.type) {
        case 'redis':
          await this.client.ping();
          return { status: 'healthy', type: 'redis' };
        case 'memory':
          return { 
            status: 'healthy', 
            type: 'memory',
            size: this.memoryCache.size,
            maxSize: this.config.maxSize
          };
      }
    } catch (error) {
      return { status: 'unhealthy', type: this.type, error: error.message };
    }
  }

  async getStats() {
    try {
      switch (this.type) {
        case 'redis':
          const info = await this.client.info('memory');
          const lines = info.split('\r\n');
          const stats = {};
          lines.forEach(line => {
            const [key, value] = line.split(':');
            if (key && value) {
              stats[key] = value;
            }
          });
          return {
            type: 'redis',
            connected: this.client.status === 'ready',
            memory: stats,
            timestamp: new Date().toISOString()
          };
        case 'memory':
          return {
            type: 'memory',
            size: this.memoryCache.size,
            maxSize: this.config.maxSize,
            ttlEntries: this.memoryTtl.size,
            memoryUsage: process.memoryUsage(),
            timestamp: new Date().toISOString()
          };
      }
    } catch (error) {
      return { type: this.type, error: error.message };
    }
  }

  async cleanup() {
    try {
      switch (this.type) {
        case 'redis':
          // Redis handles cleanup automatically, but we can run a scan for expired keys
          const keys = await this.client.keys('*');
          let cleaned = 0;
          for (const key of keys) {
            const ttl = await this.client.ttl(key);
            if (ttl === -2) { // Key doesn't exist (expired)
              cleaned++;
            }
          }
          this.logger.info('Redis cleanup completed', { expiredKeys: cleaned });
          return cleaned;
        case 'memory':
          const sizeBefore = this.memoryCache.size;
          this.cleanupMemoryCache();
          const sizeAfter = this.memoryCache.size;
          const cleaned = sizeBefore - sizeAfter;
          this.logger.info('Memory cache cleanup completed', { removedEntries: cleaned });
          return cleaned;
      }
    } catch (error) {
      this.logger.error('Cache cleanup error', { error: error.message });
      return 0;
    }
  }

  async close() {
    if (this.type === 'redis' && this.client) {
      await this.client.quit();
    }
  }
}

module.exports = CacheAdapter;
