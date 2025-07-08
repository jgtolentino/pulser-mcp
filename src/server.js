const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const WebSocket = require('ws');
const winston = require('winston');
const compression = require('compression');
const helmet = require('helmet');
const path = require('path');
const fs = require('fs');

// Configuration
const config = {
  port: process.env.MCP_PORT || 8000,
  host: process.env.MCP_HOST || '0.0.0.0',
  dbPath: process.env.DB_PATH || './data/mcp.db',
  logLevel: process.env.LOG_LEVEL || 'info',
  environment: process.env.NODE_ENV || 'development'
};

// Setup logging
const logger = winston.createLogger({
  level: config.logLevel,
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: './logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: './logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

const app = express();

// Middleware
app.use(helmet({ contentSecurityPolicy: false }));
app.use(compression());

// CORS for Claude
app.use(cors({
  origin: [
    'https://claude.ai',
    'https://claude.anthropic.com',
    'http://localhost:3000',
    'http://localhost:3001'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

app.use(express.json({ limit: '10mb' }));

// Database setup
const setupDatabase = () => {
  return new Promise((resolve, reject) => {
    // Ensure data directory exists
    const dbDir = path.dirname(config.dbPath);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }
    
    const db = new sqlite3.Database(config.dbPath, (err) => {
      if (err) {
        logger.error('Database connection failed', { error: err.message });
        reject(err);
      } else {
        logger.info('Connected to SQLite database');
        
        // Initialize schema
        db.serialize(() => {
          db.run(`CREATE TABLE IF NOT EXISTS mcp_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            type TEXT DEFAULT 'string',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
          )`);

          db.run(`CREATE TABLE IF NOT EXISTS mcp_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
          )`);
        });
        
        resolve(db);
      }
    });
  });
};

// MCP Tools
const createMCPTools = (db) => ({
  sqlite_get: (params) => {
    return new Promise((resolve, reject) => {
      const { key } = params;
      logger.info('Getting value by key', { key });
      
      db.get('SELECT * FROM mcp_data WHERE key = ?', [key], (err, row) => {
        if (err) {
          logger.error('Get operation failed', { error: err.message, key });
          reject(err);
        } else {
          resolve({ 
            success: true, 
            key, 
            value: row ? row.value : null,
            type: row ? row.type : null
          });
        }
      });
    });
  },

  sqlite_set: (params) => {
    return new Promise((resolve, reject) => {
      const { key, value, type = 'string' } = params;
      logger.info('Setting value by key', { key, type });
      
      db.run(
        `INSERT OR REPLACE INTO mcp_data (key, value, type, updated_at) 
         VALUES (?, ?, ?, CURRENT_TIMESTAMP)`,
        [key, value, type],
        function(err) {
          if (err) {
            logger.error('Set operation failed', { error: err.message, key });
            reject(err);
          } else {
            resolve({ success: true, key, value, type, changes: this.changes });
          }
        }
      );
    });
  },

  sqlite_delete: (params) => {
    return new Promise((resolve, reject) => {
      const { key } = params;
      
      db.run('DELETE FROM mcp_data WHERE key = ?', [key], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve({ success: true, key, deleted: this.changes > 0 });
        }
      });
    });
  },

  sqlite_query: (params) => {
    return new Promise((resolve, reject) => {
      const { query, params: queryParams = [] } = params;
      
      // Security check
      const queryType = query.toLowerCase().trim().split(' ')[0];
      if (!['select', 'insert', 'update', 'delete'].includes(queryType)) {
        reject(new Error('Unauthorized query type'));
        return;
      }
      
      if (queryType === 'select') {
        db.all(query, queryParams, (err, rows) => {
          if (err) reject(err);
          else resolve({ success: true, data: rows, rowCount: rows.length });
        });
      } else {
        db.run(query, queryParams, function(err) {
          if (err) reject(err);
          else resolve({ success: true, changes: this.changes, lastID: this.lastID });
        });
      }
    });
  },

  sqlite_list: (params) => {
    return new Promise((resolve, reject) => {
      const { pattern = '%', limit = 100, offset = 0 } = params;
      
      db.all(
        'SELECT key, type, created_at, updated_at FROM mcp_data WHERE key LIKE ? ORDER BY updated_at DESC LIMIT ? OFFSET ?',
        [pattern, limit, offset],
        (err, rows) => {
          if (err) reject(err);
          else resolve({ success: true, keys: rows, count: rows.length });
        }
      );
    });
  },

  get_logs: (params) => {
    return new Promise((resolve, reject) => {
      const { level, limit = 50, offset = 0 } = params;
      
      let query = 'SELECT * FROM mcp_logs';
      const queryParams = [];
      
      if (level) {
        query += ' WHERE level = ?';
        queryParams.push(level);
      }
      
      query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?';
      queryParams.push(limit, offset);
      
      db.all(query, queryParams, (err, rows) => {
        if (err) reject(err);
        else resolve({ success: true, logs: rows });
      });
    });
  }
});

// Initialize server
const initServer = async () => {
  try {
    const db = await setupDatabase();
    const mcpTools = createMCPTools(db);

    // Health check
    app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        database: 'connected',
        version: '1.0.0'
      });
    });

    // Capabilities
    app.get('/capabilities', (req, res) => {
      res.json({
        capabilities: ['database_operations', 'key_value_store', 'sql_queries'],
        tools: [
          { name: 'sqlite_get', description: 'Get value by key' },
          { name: 'sqlite_set', description: 'Set value by key' },
          { name: 'sqlite_delete', description: 'Delete key' },
          { name: 'sqlite_query', description: 'Execute SQL query' },
          { name: 'sqlite_list', description: 'List keys' },
          { name: 'get_logs', description: 'Get system logs' }
        ],
        version: '1.0.0'
      });
    });

    // MCP Discovery endpoint - required by Claude
    app.get('/.well-known/mcp', (req, res) => {
      res.json({
        mcp_version: "1.0",
        name: "Complete MCP Server",
        description: "SQLite-based MCP server for persistent storage",
        tools: [
          {
            name: "sqlite_get",
            description: "Get value by key from SQLite database",
            input_schema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Key to retrieve" }
              },
              required: ["key"]
            },
            output_schema: {
              type: "object",
              properties: {
                success: { type: "boolean" },
                key: { type: "string" },
                value: { type: ["string", "null"] },
                type: { type: ["string", "null"] }
              }
            }
          },
          {
            name: "sqlite_set",
            description: "Set key-value pair in SQLite database",
            input_schema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Key to set" },
                value: { type: "string", description: "Value to store" },
                type: { type: "string", description: "Data type", default: "string" }
              },
              required: ["key", "value"]
            },
            output_schema: {
              type: "object",
              properties: {
                success: { type: "boolean" },
                key: { type: "string" },
                value: { type: "string" },
                type: { type: "string" },
                changes: { type: "number" }
              }
            }
          },
          {
            name: "sqlite_delete",
            description: "Delete key from SQLite database",
            input_schema: {
              type: "object",
              properties: {
                key: { type: "string", description: "Key to delete" }
              },
              required: ["key"]
            },
            output_schema: {
              type: "object",
              properties: {
                success: { type: "boolean" },
                key: { type: "string" },
                deleted: { type: "boolean" }
              }
            }
          },
          {
            name: "sqlite_query",
            description: "Execute SQL query on database",
            input_schema: {
              type: "object",
              properties: {
                query: { type: "string", description: "SQL query to execute" },
                params: { type: "array", items: { type: "string" }, description: "Query parameters" }
              },
              required: ["query"]
            },
            output_schema: {
              type: "object",
              properties: {
                success: { type: "boolean" },
                data: { type: "array" },
                rowCount: { type: "number" },
                changes: { type: "number" },
                lastID: { type: "number" }
              }
            }
          },
          {
            name: "sqlite_list",
            description: "List keys matching pattern",
            input_schema: {
              type: "object",
              properties: {
                pattern: { type: "string", description: "SQL LIKE pattern", default: "%" },
                limit: { type: "number", description: "Max results", default: 100 },
                offset: { type: "number", description: "Skip results", default: 0 }
              }
            },
            output_schema: {
              type: "object",
              properties: {
                success: { type: "boolean" },
                keys: { type: "array" },
                count: { type: "number" }
              }
            }
          },
          {
            name: "get_logs",
            description: "Retrieve system logs",
            input_schema: {
              type: "object",
              properties: {
                level: { type: "string", description: "Log level filter" },
                limit: { type: "number", description: "Max results", default: 50 },
                offset: { type: "number", description: "Skip results", default: 0 }
              }
            },
            output_schema: {
              type: "object",
              properties: {
                success: { type: "boolean" },
                logs: { type: "array" }
              }
            }
          }
        ]
      });
    });

    // MCP endpoint
    app.post('/mcp/call', async (req, res) => {
      try {
        const { tool, parameters } = req.body;
        
        if (!mcpTools[tool]) {
          return res.status(400).json({ 
            error: 'Unknown tool',
            available_tools: Object.keys(mcpTools)
          });
        }
        
        const result = await mcpTools[tool](parameters);
        res.json(result);
      } catch (error) {
        logger.error('Tool execution failed', { error: error.message });
        res.status(500).json({ error: error.message });
      }
    });

    // Status endpoint
    app.get('/status', (req, res) => {
      res.json({
        status: 'running',
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        timestamp: new Date().toISOString()
      });
    });

    // Start server
    const server = app.listen(config.port, config.host, () => {
      logger.info(`MCP Server started on ${config.host}:${config.port}`);
      console.log(`
🚀 MCP Complete Server is running!
📍 Address: http://${config.host}:${config.port}
🏥 Health: http://${config.host}:${config.port}/health
🔧 Tools: http://${config.host}:${config.port}/capabilities

Claude Web App Configuration:
- URL: http://localhost:${config.port}
- Type: HTTP
      `);
    });

    // WebSocket support
    const wss = new WebSocket.Server({ server });

    wss.on('connection', (ws) => {
      const clientId = Math.random().toString(36).substr(2, 9);
      logger.info('WebSocket client connected', { clientId });
      
      ws.send(JSON.stringify({
        type: 'welcome',
        clientId,
        timestamp: new Date().toISOString()
      }));
      
      ws.on('message', async (message) => {
        try {
          const data = JSON.parse(message);
          
          if (data.type === 'mcp_call') {
            const result = await mcpTools[data.tool](data.parameters);
            ws.send(JSON.stringify({
              type: 'mcp_response',
              id: data.id,
              result
            }));
          }
        } catch (error) {
          ws.send(JSON.stringify({
            type: 'error',
            id: data.id,
            error: error.message
          }));
        }
      });
    });

    // Graceful shutdown
    process.on('SIGINT', () => {
      logger.info('Shutting down...');
      wss.close();
      server.close();
      db.close();
      process.exit(0);
    });

  } catch (error) {
    logger.error('Server initialization failed', { error: error.message });
    process.exit(1);
  }
};

// Start server
initServer();
