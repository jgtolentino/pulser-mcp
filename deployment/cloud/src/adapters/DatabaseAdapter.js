const sqlite3 = require('sqlite3').verbose();
const { Pool } = require('pg');
const mysql = require('mysql2/promise');
const { MongoClient } = require('mongodb');

class DatabaseAdapter {
  constructor(config, logger) {
    this.config = config;
    this.logger = logger;
    this.client = null;
    this.type = config.type;
  }

  async initialize() {
    try {
      switch (this.type) {
        case 'sqlite':
          await this.initializeSQLite();
          break;
        case 'postgresql':
          await this.initializePostgreSQL();
          break;
        case 'mysql':
          await this.initializeMySQL();
          break;
        case 'mongodb':
          await this.initializeMongoDB();
          break;
        default:
          throw new Error(`Unsupported database type: ${this.type}`);
      }

      await this.createTables();
      this.logger.info('Database initialized successfully', { type: this.type });
    } catch (error) {
      this.logger.error('Database initialization failed', { error: error.message });
      throw error;
    }
  }

  async initializeSQLite() {
    const dbPath = this.config.url || '/tmp/mcp-cloud.db';
    this.client = new sqlite3.Database(dbPath, (err) => {
      if (err) throw err;
    });
  }

  async initializePostgreSQL() {
    this.client = new Pool({
      connectionString: this.config.url,
      ssl: this.config.ssl ? { rejectUnauthorized: false } : false,
      max: this.config.maxConnections,
      idleTimeoutMillis: this.config.timeout,
      connectionTimeoutMillis: this.config.timeout
    });

    // Test connection
    const client = await this.client.connect();
    client.release();
  }

  async initializeMySQL() {
    this.client = mysql.createPool({
      uri: this.config.url,
      ssl: this.config.ssl ? {} : false,
      connectionLimit: this.config.maxConnections,
      acquireTimeout: this.config.timeout,
      timeout: this.config.timeout
    });

    // Test connection
    const connection = await this.client.getConnection();
    connection.release();
  }

  async initializeMongoDB() {
    this.client = new MongoClient(this.config.url, {
      maxPoolSize: this.config.maxConnections,
      serverSelectionTimeoutMS: this.config.timeout,
      socketTimeoutMS: this.config.timeout
    });

    await this.client.connect();
  }

  async createTables() {
    switch (this.type) {
      case 'sqlite':
        await this.createSQLiteTables();
        break;
      case 'postgresql':
        await this.createPostgreSQLTables();
        break;
      case 'mysql':
        await this.createMySQLTables();
        break;
      case 'mongodb':
        await this.createMongoCollections();
        break;
    }
  }

  async createSQLiteTables() {
    return new Promise((resolve, reject) => {
      this.client.serialize(() => {
        this.client.run(`CREATE TABLE IF NOT EXISTS mcp_data (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key TEXT UNIQUE NOT NULL,
          value TEXT,
          type TEXT DEFAULT 'string',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )`, (err) => {
          if (err) return reject(err);
        });

        this.client.run(`CREATE TABLE IF NOT EXISTS mcp_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          level TEXT NOT NULL,
          message TEXT NOT NULL,
          data TEXT,
          source TEXT,
          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )`, (err) => {
          if (err) return reject(err);
        });

        this.client.run(`CREATE INDEX IF NOT EXISTS idx_mcp_data_key ON mcp_data(key)`, (err) => {
          if (err) return reject(err);
          resolve();
        });
      });
    });
  }

  async createPostgreSQLTables() {
    const client = await this.client.connect();
    try {
      await client.query(`CREATE TABLE IF NOT EXISTS mcp_data (
        id SERIAL PRIMARY KEY,
        key VARCHAR(255) UNIQUE NOT NULL,
        value TEXT,
        type VARCHAR(50) DEFAULT 'string',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`);

      await client.query(`CREATE TABLE IF NOT EXISTS mcp_logs (
        id SERIAL PRIMARY KEY,
        level VARCHAR(20) NOT NULL,
        message TEXT NOT NULL,
        data JSONB,
        source VARCHAR(100),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`);

      await client.query(`CREATE INDEX IF NOT EXISTS idx_mcp_data_key ON mcp_data(key)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_mcp_logs_timestamp ON mcp_logs(timestamp)`);
    } finally {
      client.release();
    }
  }

  async createMySQLTables() {
    const connection = await this.client.getConnection();
    try {
      await connection.execute(`CREATE TABLE IF NOT EXISTS mcp_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        \`key\` VARCHAR(255) UNIQUE NOT NULL,
        value TEXT,
        type VARCHAR(50) DEFAULT 'string',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
      )`);

      await connection.execute(`CREATE TABLE IF NOT EXISTS mcp_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        level VARCHAR(20) NOT NULL,
        message TEXT NOT NULL,
        data JSON,
        source VARCHAR(100),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )`);

      await connection.execute(`CREATE INDEX IF NOT EXISTS idx_mcp_data_key ON mcp_data(\`key\`)`);
    } finally {
      connection.release();
    }
  }

  async createMongoCollections() {
    const db = this.client.db();
    
    // Create collections with indexes
    const mcpData = db.collection('mcp_data');
    await mcpData.createIndex({ key: 1 }, { unique: true });
    await mcpData.createIndex({ created_at: 1 });

    const mcpLogs = db.collection('mcp_logs');
    await mcpLogs.createIndex({ timestamp: 1 });
    await mcpLogs.createIndex({ level: 1 });
  }

  // Universal methods that work across all database types
  async get(key) {
    switch (this.type) {
      case 'sqlite':
        return this.sqliteGet(key);
      case 'postgresql':
        return this.postgresGet(key);
      case 'mysql':
        return this.mysqlGet(key);
      case 'mongodb':
        return this.mongoGet(key);
    }
  }

  async set(key, value, type = 'string') {
    switch (this.type) {
      case 'sqlite':
        return this.sqliteSet(key, value, type);
      case 'postgresql':
        return this.postgresSet(key, value, type);
      case 'mysql':
        return this.mysqlSet(key, value, type);
      case 'mongodb':
        return this.mongoSet(key, value, type);
    }
  }

  async delete(key) {
    switch (this.type) {
      case 'sqlite':
        return this.sqliteDelete(key);
      case 'postgresql':
        return this.postgresDelete(key);
      case 'mysql':
        return this.mysqlDelete(key);
      case 'mongodb':
        return this.mongoDelete(key);
    }
  }

  async list(pattern = '%', limit = 100, offset = 0) {
    switch (this.type) {
      case 'sqlite':
        return this.sqliteList(pattern, limit, offset);
      case 'postgresql':
        return this.postgresList(pattern, limit, offset);
      case 'mysql':
        return this.mysqlList(pattern, limit, offset);
      case 'mongodb':
        return this.mongoList(pattern, limit, offset);
    }
  }

  async query(sql, params = []) {
    switch (this.type) {
      case 'sqlite':
        return this.sqliteQuery(sql, params);
      case 'postgresql':
        return this.postgresQuery(sql, params);
      case 'mysql':
        return this.mysqlQuery(sql, params);
      case 'mongodb':
        throw new Error('Raw SQL queries not supported for MongoDB');
    }
  }

  // SQLite implementations
  async sqliteGet(key) {
    return new Promise((resolve, reject) => {
      this.client.get('SELECT * FROM mcp_data WHERE key = ?', [key], (err, row) => {
        if (err) reject(err);
        else resolve(row ? { key, value: row.value, type: row.type } : null);
      });
    });
  }

  async sqliteSet(key, value, type) {
    return new Promise((resolve, reject) => {
      this.client.run(
        'INSERT OR REPLACE INTO mcp_data (key, value, type, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
        [key, value, type],
        function(err) {
          if (err) reject(err);
          else resolve({ key, value, type, changes: this.changes });
        }
      );
    });
  }

  async sqliteDelete(key) {
    return new Promise((resolve, reject) => {
      this.client.run('DELETE FROM mcp_data WHERE key = ?', [key], function(err) {
        if (err) reject(err);
        else resolve({ key, deleted: this.changes > 0 });
      });
    });
  }

  async sqliteList(pattern, limit, offset) {
    return new Promise((resolve, reject) => {
      this.client.all(
        'SELECT key, type, created_at, updated_at FROM mcp_data WHERE key LIKE ? ORDER BY updated_at DESC LIMIT ? OFFSET ?',
        [pattern, limit, offset],
        (err, rows) => {
          if (err) reject(err);
          else resolve({ keys: rows, count: rows.length });
        }
      );
    });
  }

  async sqliteQuery(sql, params) {
    return new Promise((resolve, reject) => {
      const queryType = sql.toLowerCase().trim().split(' ')[0];
      
      if (queryType === 'select') {
        this.client.all(sql, params, (err, rows) => {
          if (err) reject(err);
          else resolve({ data: rows, rowCount: rows.length });
        });
      } else {
        this.client.run(sql, params, function(err) {
          if (err) reject(err);
          else resolve({ changes: this.changes, lastID: this.lastID });
        });
      }
    });
  }

  // PostgreSQL implementations
  async postgresGet(key) {
    const client = await this.client.connect();
    try {
      const result = await client.query('SELECT * FROM mcp_data WHERE key = $1', [key]);
      const row = result.rows[0];
      return row ? { key, value: row.value, type: row.type } : null;
    } finally {
      client.release();
    }
  }

  async postgresSet(key, value, type) {
    const client = await this.client.connect();
    try {
      const result = await client.query(
        'INSERT INTO mcp_data (key, value, type, updated_at) VALUES ($1, $2, $3, CURRENT_TIMESTAMP) ON CONFLICT (key) DO UPDATE SET value = $2, type = $3, updated_at = CURRENT_TIMESTAMP RETURNING *',
        [key, value, type]
      );
      return { key, value, type, changes: result.rowCount };
    } finally {
      client.release();
    }
  }

  async postgresDelete(key) {
    const client = await this.client.connect();
    try {
      const result = await client.query('DELETE FROM mcp_data WHERE key = $1', [key]);
      return { key, deleted: result.rowCount > 0 };
    } finally {
      client.release();
    }
  }

  async postgresList(pattern, limit, offset) {
    const client = await this.client.connect();
    try {
      const result = await client.query(
        'SELECT key, type, created_at, updated_at FROM mcp_data WHERE key LIKE $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3',
        [pattern, limit, offset]
      );
      return { keys: result.rows, count: result.rows.length };
    } finally {
      client.release();
    }
  }

  async postgresQuery(sql, params) {
    const client = await this.client.connect();
    try {
      const result = await client.query(sql, params);
      return result.rows ? { data: result.rows, rowCount: result.rowCount } : { changes: result.rowCount };
    } finally {
      client.release();
    }
  }

  // MySQL implementations
  async mysqlGet(key) {
    const connection = await this.client.getConnection();
    try {
      const [rows] = await connection.execute('SELECT * FROM mcp_data WHERE `key` = ?', [key]);
      const row = rows[0];
      return row ? { key, value: row.value, type: row.type } : null;
    } finally {
      connection.release();
    }
  }

  async mysqlSet(key, value, type) {
    const connection = await this.client.getConnection();
    try {
      const [result] = await connection.execute(
        'INSERT INTO mcp_data (`key`, value, type) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE value = ?, type = ?, updated_at = CURRENT_TIMESTAMP',
        [key, value, type, value, type]
      );
      return { key, value, type, changes: result.affectedRows };
    } finally {
      connection.release();
    }
  }

  async mysqlDelete(key) {
    const connection = await this.client.getConnection();
    try {
      const [result] = await connection.execute('DELETE FROM mcp_data WHERE `key` = ?', [key]);
      return { key, deleted: result.affectedRows > 0 };
    } finally {
      connection.release();
    }
  }

  async mysqlList(pattern, limit, offset) {
    const connection = await this.client.getConnection();
    try {
      const [rows] = await connection.execute(
        'SELECT `key`, type, created_at, updated_at FROM mcp_data WHERE `key` LIKE ? ORDER BY updated_at DESC LIMIT ? OFFSET ?',
        [pattern, limit, offset]
      );
      return { keys: rows, count: rows.length };
    } finally {
      connection.release();
    }
  }

  async mysqlQuery(sql, params) {
    const connection = await this.client.getConnection();
    try {
      const [result] = await connection.execute(sql, params);
      return Array.isArray(result) ? { data: result, rowCount: result.length } : { changes: result.affectedRows };
    } finally {
      connection.release();
    }
  }

  // MongoDB implementations
  async mongoGet(key) {
    const db = this.client.db();
    const collection = db.collection('mcp_data');
    const doc = await collection.findOne({ key });
    return doc ? { key, value: doc.value, type: doc.type } : null;
  }

  async mongoSet(key, value, type) {
    const db = this.client.db();
    const collection = db.collection('mcp_data');
    const result = await collection.replaceOne(
      { key },
      { key, value, type, created_at: new Date(), updated_at: new Date() },
      { upsert: true }
    );
    return { key, value, type, changes: result.modifiedCount + result.upsertedCount };
  }

  async mongoDelete(key) {
    const db = this.client.db();
    const collection = db.collection('mcp_data');
    const result = await collection.deleteOne({ key });
    return { key, deleted: result.deletedCount > 0 };
  }

  async mongoList(pattern, limit, offset) {
    const db = this.client.db();
    const collection = db.collection('mcp_data');
    
    // Convert SQL LIKE pattern to MongoDB regex
    const regex = new RegExp(pattern.replace(/%/g, '.*'), 'i');
    
    const docs = await collection
      .find({ key: regex })
      .sort({ updated_at: -1 })
      .skip(offset)
      .limit(limit)
      .toArray();
    
    return { keys: docs, count: docs.length };
  }

  async healthCheck() {
    try {
      switch (this.type) {
        case 'sqlite':
          return new Promise((resolve, reject) => {
            this.client.get('SELECT 1', (err) => {
              if (err) reject(err);
              else resolve({ status: 'healthy', type: 'sqlite' });
            });
          });
        case 'postgresql':
          const pgClient = await this.client.connect();
          await pgClient.query('SELECT 1');
          pgClient.release();
          return { status: 'healthy', type: 'postgresql' };
        case 'mysql':
          const mysqlConn = await this.client.getConnection();
          await mysqlConn.execute('SELECT 1');
          mysqlConn.release();
          return { status: 'healthy', type: 'mysql' };
        case 'mongodb':
          await this.client.db().admin().ping();
          return { status: 'healthy', type: 'mongodb' };
      }
    } catch (error) {
      return { status: 'unhealthy', type: this.type, error: error.message };
    }
  }

  async getStats() {
    try {
      const total = await this.getCount();
      return {
        type: this.type,
        totalRecords: total,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return { type: this.type, error: error.message };
    }
  }

  async getCount() {
    switch (this.type) {
      case 'sqlite':
        return new Promise((resolve, reject) => {
          this.client.get('SELECT COUNT(*) as count FROM mcp_data', (err, row) => {
            if (err) reject(err);
            else resolve(row.count);
          });
        });
      case 'postgresql':
        const pgClient = await this.client.connect();
        try {
          const result = await pgClient.query('SELECT COUNT(*) as count FROM mcp_data');
          return parseInt(result.rows[0].count);
        } finally {
          pgClient.release();
        }
      case 'mysql':
        const mysqlConn = await this.client.getConnection();
        try {
          const [rows] = await mysqlConn.execute('SELECT COUNT(*) as count FROM mcp_data');
          return rows[0].count;
        } finally {
          mysqlConn.release();
        }
      case 'mongodb':
        const db = this.client.db();
        return await db.collection('mcp_data').countDocuments();
    }
  }

  async cleanup() {
    // Remove old log entries (older than 30 days)
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    
    switch (this.type) {
      case 'sqlite':
        return new Promise((resolve, reject) => {
          this.client.run('DELETE FROM mcp_logs WHERE timestamp < ?', [thirtyDaysAgo.toISOString()], function(err) {
            if (err) reject(err);
            else resolve(this.changes);
          });
        });
      case 'postgresql':
        const pgClient = await this.client.connect();
        try {
          const result = await pgClient.query('DELETE FROM mcp_logs WHERE timestamp < $1', [thirtyDaysAgo]);
          return result.rowCount;
        } finally {
          pgClient.release();
        }
      case 'mysql':
        const mysqlConn = await this.client.getConnection();
        try {
          const [result] = await mysqlConn.execute('DELETE FROM mcp_logs WHERE timestamp < ?', [thirtyDaysAgo]);
          return result.affectedRows;
        } finally {
          mysqlConn.release();
        }
      case 'mongodb':
        const db = this.client.db();
        const result = await db.collection('mcp_logs').deleteMany({ timestamp: { $lt: thirtyDaysAgo } });
        return result.deletedCount;
    }
  }

  async close() {
    if (this.client) {
      switch (this.type) {
        case 'sqlite':
          return new Promise((resolve) => {
            this.client.close(resolve);
          });
        case 'postgresql':
        case 'mysql':
          await this.client.end();
          break;
        case 'mongodb':
          await this.client.close();
          break;
      }
    }
  }
}

module.exports = DatabaseAdapter;
