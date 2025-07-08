const fs = require('fs');
const path = require('path');

const EXISTING_MCP_DIR = '/Users/tbwa/Documents/GitHub/InsightPulseAI_SKR/tools/js/mcp';
const CURRENT_DIR = process.cwd();

async function integrateWithExisting() {
  console.log('🔗 Integrating with existing MCP setup...');
  
  try {
    // Check if existing directory exists
    if (!fs.existsSync(EXISTING_MCP_DIR)) {
      console.log('⚠️  Existing MCP directory not found, skipping integration');
      return;
    }
    
    // Create symlink in existing MCP directory
    const linkPath = path.join(EXISTING_MCP_DIR, 'complete_mcp_server');
    
    if (fs.existsSync(linkPath)) {
      fs.unlinkSync(linkPath);
    }
    
    fs.symlinkSync(CURRENT_DIR, linkPath);
    console.log('✅ Created symlink in existing MCP directory');
    
    // Update existing registry
    const registryPath = path.join(EXISTING_MCP_DIR, 'mcp_registry.json');
    
    if (fs.existsSync(registryPath)) {
      const registryData = fs.readFileSync(registryPath, 'utf8');
      const registry = JSON.parse(registryData);
      
      registry.servers = registry.servers || {};
      registry.servers.complete_mcp_server = {
        name: 'complete_mcp_server',
        path: linkPath,
        port: 8000,
        cors_port: 8001,
        status: 'registered',
        health_endpoint: 'http://localhost:8000/health',
        api_endpoint: 'http://localhost:8000',
        category: 'infrastructure',
        priority: 'high',
        features: [
          'sqlite_database',
          'key_value_store',
          'cors_proxy',
          'websocket_support',
          'comprehensive_logging'
        ],
        registered_at: new Date().toISOString()
      };
      
      registry.total_servers = Object.keys(registry.servers).length;
      
      fs.writeFileSync(registryPath, JSON.stringify(registry, null, 2));
      console.log('✅ Updated existing MCP registry');
    }
    
    // Create startup integration
    const existingStartScript = path.join(EXISTING_MCP_DIR, 'start_complete_mcp.sh');
    const startScript = `#!/bin/bash
# Start Complete MCP Server
cd "${CURRENT_DIR}"
./scripts/start.sh
`;
    
    fs.writeFileSync(existingStartScript, startScript);
    fs.chmodSync(existingStartScript, '755');
    console.log('✅ Created startup script in existing MCP directory');
    
    console.log('🎉 Integration completed successfully!');
    console.log('You can now start this server from the existing MCP directory using:');
    console.log(`cd ${EXISTING_MCP_DIR} && ./start_complete_mcp.sh`);
    
  } catch (error) {
    console.error('❌ Integration failed:', error.message);
  }
}

if (require.main === module) {
  integrateWithExisting();
}

module.exports = { integrateWithExisting };
