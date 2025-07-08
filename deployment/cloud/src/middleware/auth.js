const { RateLimiterMemory, RateLimiterRedis } = require("rate-limiter-flexible");
const Redis = require("ioredis");

// Create rate limiter based on environment
let limiter;

if (process.env.REDIS_URL) {
  // Use Redis for distributed rate limiting in production
  const redis = new Redis(process.env.REDIS_URL);
  limiter = new RateLimiterRedis({
    storeClient: redis,
    keyPrefix: 'mcp_rl',
    points: 100, // Number of requests
    duration: 60, // Per 60 seconds
    blockDuration: 60, // Block for 1 minute
  });
} else {
  // Use memory limiter for local development
  limiter = new RateLimiterMemory({
    points: 100,
    duration: 60,
    blockDuration: 60,
  });
}

// Auth middleware with rate limiting
module.exports = async (req, res, next) => {
  try {
    // Rate limiting
    const rateLimiterRes = await limiter.consume(req.ip);
    
    // Add rate limit headers
    res.setHeader('X-RateLimit-Limit', limiter.points);
    res.setHeader('X-RateLimit-Remaining', rateLimiterRes.remainingPoints);
    res.setHeader('X-RateLimit-Reset', new Date(Date.now() + rateLimiterRes.msBeforeNext).toISOString());
    
    // API Key authentication (optional)
    if (process.env.API_KEY) {
      const apiKey = req.headers['x-api-key'] || req.query.api_key;
      
      if (!apiKey) {
        return res.status(401).json({ 
          error: 'API key required',
          message: 'Please provide an API key via X-API-Key header or api_key query parameter'
        });
      }
      
      if (apiKey !== process.env.API_KEY) {
        return res.status(403).json({ 
          error: 'Invalid API key',
          message: 'The provided API key is invalid'
        });
      }
    }
    
    // Log successful auth
    console.log(`Auth passed for ${req.ip} - ${req.method} ${req.path}`);
    next();
    
  } catch (rejRes) {
    // Too many requests
    res.setHeader('X-RateLimit-Limit', limiter.points);
    res.setHeader('X-RateLimit-Remaining', rejRes.remainingPoints || 0);
    res.setHeader('X-RateLimit-Reset', new Date(Date.now() + rejRes.msBeforeNext).toISOString());
    res.setHeader('Retry-After', Math.round(rejRes.msBeforeNext / 1000) || 60);
    
    res.status(429).json({ 
      error: 'Too Many Requests',
      message: `Rate limit exceeded. Try again in ${Math.round(rejRes.msBeforeNext / 1000)} seconds`,
      retryAfter: Math.round(rejRes.msBeforeNext / 1000)
    });
  }
};