const http = require('http');
const WebSocket = require('ws');

const config = {
  serverUrl: 'http://localhost:8000',
  proxyUrl: 'http://localhost:8001',
  wsUrl: 'ws://localhost:8000'
};

// HTTP request helper
const httpRequest = (url, options = {}) => {
  return new Promise((resolve, reject) => {
    const req = http.request(url, {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    }, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          resolve({ 
            status: res.statusCode, 
            data: JSON.parse(data),
            headers: res.headers
          });
        } catch (e) {
          resolve({ status: res.statusCode, data: data, headers: res.headers });
        }
      });
    });
    
    req.on('error', reject);
    if (options.data) req.write(JSON.stringify(options.data));
    req.end();
  });
};

// Test functions
const tests = {
  async testHealthEndpoint() {
    console.log('🏥 Testing health endpoint...');
    try {
      const response = await httpRequest(`${config.serverUrl}/health`);
      if (response.status === 200 && response.data.status === 'healthy') {
        console.log('✅ Health endpoint: PASS');
        return true;
      } else {
        console.log('❌ Health endpoint: FAIL', response);
        return false;
      }
    } catch (error) {
      console.log('❌ Health endpoint: ERROR', error.message);
      return false;
    }
  },

  async testCapabilities() {
    console.log('🔧 Testing capabilities endpoint...');
    try {
      const response = await httpRequest(`${config.serverUrl}/capabilities`);
      if (response.status === 200 && response.data.tools) {
        console.log('✅ Capabilities endpoint: PASS');
        console.log(`   Found ${response.data.tools.length} tools`);
        return true;
      } else {
        console.log('❌ Capabilities endpoint: FAIL');
        return false;
      }
    } catch (error) {
      console.log('❌ Capabilities endpoint: ERROR', error.message);
      return false;
    }
  },

  async testSQLiteOperations() {
    console.log('💾 Testing SQLite operations...');
    const testKey = 'test_key_' + Date.now();
    const testValue = 'test_value_' + Date.now();
    
    try {
      // Test SET
      const setResponse = await httpRequest(`${config.serverUrl}/mcp/call`, {
        method: 'POST',
        data: { tool: 'sqlite_set', parameters: { key: testKey, value: testValue } }
      });
      
      if (setResponse.status !== 200 || !setResponse.data.success) {
        console.log('❌ SQLite SET: FAIL');
        return false;
      }
      
      // Test GET
      const getResponse = await httpRequest(`${config.serverUrl}/mcp/call`, {
        method: 'POST',
        data: { tool: 'sqlite_get', parameters: { key: testKey } }
      });
      
      if (getResponse.status !== 200 || getResponse.data.value !== testValue) {
        console.log('❌ SQLite GET: FAIL');
        return false;
      }
      
      // Test DELETE
      const deleteResponse = await httpRequest(`${config.serverUrl}/mcp/call`, {
        method: 'POST',
        data: { tool: 'sqlite_delete', parameters: { key: testKey } }
      });
      
      if (deleteResponse.status !== 200 || !deleteResponse.data.success) {
        console.log('❌ SQLite DELETE: FAIL');
        return false;
      }
      
      console.log('✅ SQLite operations: PASS');
      return true;
    } catch (error) {
      console.log('❌ SQLite operations: ERROR', error.message);
      return false;
    }
  },

  async testWebSocket() {
    console.log('📡 Testing WebSocket connection...');
    return new Promise((resolve) => {
      try {
        const ws = new WebSocket(config.wsUrl);
        let testPassed = false;
        
        ws.on('open', () => {
          ws.send(JSON.stringify({ type: 'ping' }));
        });
        
        ws.on('message', (data) => {
          try {
            const message = JSON.parse(data);
            if (message.type === 'welcome') {
              console.log('✅ WebSocket: PASS');
              testPassed = true;
              ws.close();
              resolve(true);
            }
          } catch (e) {
            console.log('❌ WebSocket: FAIL');
            ws.close();
            resolve(false);
          }
        });
        
        ws.on('error', () => {
          console.log('❌ WebSocket: ERROR');
          resolve(false);
        });
        
        setTimeout(() => {
          if (!testPassed) {
            console.log('❌ WebSocket: TIMEOUT');
            ws.close();
            resolve(false);
          }
        }, 5000);
      } catch (error) {
        console.log('❌ WebSocket: ERROR', error.message);
        resolve(false);
      }
    });
  },

  async testProxyServer() {
    console.log('🔄 Testing CORS proxy...');
    try {
      const response = await httpRequest(`${config.proxyUrl}/health`);
      if (response.status === 200) {
        console.log('✅ CORS proxy: PASS');
        return true;
      } else {
        console.log('❌ CORS proxy: FAIL');
        return false;
      }
    } catch (error) {
      console.log('❌ CORS proxy: ERROR', error.message);
      return false;
    }
  }
};

// Run all tests
async function runAllTests() {
  console.log('🧪 Running MCP Server Test Suite');
  console.log('=====================================\n');
  
  const results = [];
  
  for (const [testName, testFn] of Object.entries(tests)) {
    try {
      const result = await testFn();
      results.push({ test: testName, passed: result });
    } catch (error) {
      console.log(`❌ ${testName}: ERROR`, error.message);
      results.push({ test: testName, passed: false });
    }
    console.log('');
  }
  
  // Summary
  console.log('📊 Test Results Summary');
  console.log('=======================');
  
  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  
  results.forEach(result => {
    console.log(`${result.passed ? '✅' : '❌'} ${result.test}`);
  });
  
  console.log(`\n🎯 Overall: ${passed}/${total} tests passed`);
  
  if (passed === total) {
    console.log('🎉 All tests passed! MCP server is ready for Claude Web App.');
  } else {
    console.log('⚠️  Some tests failed. Please check the server configuration.');
  }
  
  return passed === total;
}

// Run tests if called directly
if (require.main === module) {
  runAllTests().then(success => {
    process.exit(success ? 0 : 1);
  });
}

module.exports = { runAllTests, tests };
