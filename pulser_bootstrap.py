#!/usr/bin/env python3
"""
Pulser Bootstrap Script - MCP Server Registration and Synchronization
Automatically discovers, registers, and syncs all MCP servers in the ecosystem
"""

import os
import json
import yaml
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import requests
from datetime import datetime
import hashlib

class PulserBootstrap:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.mcp_dir = self.base_dir
        self.registry_file = self.base_dir / "mcp_registry.json"
        self.config_file = self.base_dir / "pulser_config.yaml"
        self.status_file = self.base_dir / "bootstrap_status.json"
        
        self.discovered_servers = {}
        self.registered_servers = {}
        self.server_status = {}
        
        print("🚀 Pulser Bootstrap - MCP Server Registration System")
        print(f"📁 Base directory: {self.base_dir}")
        print(f"🔍 Scanning MCP directory: {self.mcp_dir}")
        
    def discover_mcp_servers(self) -> Dict[str, Dict[str, Any]]:
        """Discover all MCP servers in the directory structure"""
        print("\n🔍 Discovering MCP servers...")
        
        servers = {}
        
        # Look for MCP server directories
        for item in self.mcp_dir.iterdir():
            if item.is_dir() and item.name.endswith('_mcp'):
                server_info = self._analyze_server_directory(item)
                if server_info:
                    servers[item.name] = server_info
                    print(f"   ✅ Found: {item.name} - {server_info.get('description', 'No description')}")
                else:
                    print(f"   ⚠️ Incomplete: {item.name} - Missing required files")
        
        self.discovered_servers = servers
        print(f"\n📊 Discovered {len(servers)} MCP servers")
        return servers
    
    def _analyze_server_directory(self, server_dir: Path) -> Optional[Dict[str, Any]]:
        """Analyze a server directory to extract configuration"""
        try:
            server_info = {
                "name": server_dir.name,
                "path": str(server_dir),
                "discovered_at": datetime.now().isoformat()
            }
            
            # Look for Python server file
            src_dir = server_dir / "src"
            if src_dir.exists():
                python_files = list(src_dir.glob("*.py"))
                if python_files:
                    main_server = python_files[0]  # Take first Python file
                    server_info["server_file"] = str(main_server)
                    server_info["language"] = "python"
                    
                    # Try to extract port from server file
                    try:
                        with open(main_server, 'r') as f:
                            content = f.read()
                            # Look for uvicorn.run or app.run with port
                            import re
                            port_match = re.search(r'port=(\d+)', content)
                            if port_match:
                                server_info["port"] = int(port_match.group(1))
                            else:
                                # Default ports based on naming
                                port_mapping = {
                                    "scout_local_mcp": 8001,
                                    "creative_rag_mcp": 8002,
                                    "financial_analyst_mcp": 8003,
                                    "voice_agent_mcp": 8004,
                                    "unified_mcp": 8005,
                                    "shared_memory_mcp": 8006,
                                    "briefvault_rag_mcp": 8007,
                                    "synthetic_data_mcp": 8008,
                                    "deep_researcher_mcp": 8009,
                                    "video_rag_mcp": 8010,
                                    "audio_analysis_mcp": 8011
                                }
                                server_info["port"] = port_mapping.get(server_dir.name, 8000)
                    except Exception as e:
                        print(f"   ⚠️ Could not analyze {main_server}: {e}")
            
            # Look for agent YAML file
            agents_dir = server_dir / "agents"
            if agents_dir.exists():
                yaml_files = list(agents_dir.glob("*.yaml")) + list(agents_dir.glob("*.yml"))
                if yaml_files:
                    agent_file = yaml_files[0]
                    server_info["agent_file"] = str(agent_file)
                    
                    # Parse agent configuration
                    try:
                        with open(agent_file, 'r') as f:
                            agent_config = yaml.safe_load(f)
                            if 'agent' in agent_config:
                                agent_info = agent_config['agent']
                                server_info["agent_name"] = agent_info.get('name')
                                server_info["description"] = agent_info.get('description')
                                server_info["version"] = agent_info.get('version')
                                server_info["capabilities"] = agent_info.get('capabilities', [])
                                server_info["tools"] = agent_info.get('tools', [])
                    except Exception as e:
                        print(f"   ⚠️ Could not parse {agent_file}: {e}")
            
            # Look for requirements.txt
            requirements_file = server_dir / "requirements.txt"
            if requirements_file.exists():
                server_info["requirements_file"] = str(requirements_file)
                try:
                    with open(requirements_file, 'r') as f:
                        requirements = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
                        server_info["dependencies"] = requirements
                except Exception as e:
                    print(f"   ⚠️ Could not read requirements: {e}")
            
            # Look for setup script
            scripts_dir = server_dir / "scripts"
            if scripts_dir.exists():
                setup_script = scripts_dir / "setup.sh"
                if setup_script.exists():
                    server_info["setup_script"] = str(setup_script)
            
            # Look for README
            readme_file = server_dir / "README.md"
            if readme_file.exists():
                server_info["readme_file"] = str(readme_file)
            
            # Calculate configuration hash for change detection
            config_str = json.dumps(server_info, sort_keys=True)
            server_info["config_hash"] = hashlib.md5(config_str.encode()).hexdigest()
            
            return server_info
            
        except Exception as e:
            print(f"   ❌ Error analyzing {server_dir}: {e}")
            return None
    
    def create_registry(self) -> Dict[str, Any]:
        """Create comprehensive MCP server registry"""
        print("\n📋 Creating MCP server registry...")
        
        registry = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "total_servers": len(self.discovered_servers),
            "servers": {}
        }
        
        for server_name, server_info in self.discovered_servers.items():
            # Enhanced server registration
            registry_entry = {
                **server_info,
                "status": "registered",
                "health_endpoint": f"http://localhost:{server_info.get('port', 8000)}/health",
                "api_endpoint": f"http://localhost:{server_info.get('port', 8000)}",
                "registered_at": datetime.now().isoformat()
            }
            
            # Add server-specific metadata
            if "scout" in server_name:
                registry_entry["category"] = "analytics"
                registry_entry["priority"] = "high"
            elif "rag" in server_name:
                registry_entry["category"] = "knowledge"
                registry_entry["priority"] = "high"
            elif "analyst" in server_name:
                registry_entry["category"] = "analytics"
                registry_entry["priority"] = "medium"
            elif "voice" in server_name:
                registry_entry["category"] = "interaction"
                registry_entry["priority"] = "high"
            elif "memory" in server_name:
                registry_entry["category"] = "infrastructure"
                registry_entry["priority"] = "high"
            elif "researcher" in server_name:
                registry_entry["category"] = "intelligence"
                registry_entry["priority"] = "medium"
            elif "synthetic" in server_name:
                registry_entry["category"] = "data"
                registry_entry["priority"] = "medium"
            elif "video" in server_name:
                registry_entry["category"] = "content"
                registry_entry["priority"] = "medium"
            elif "audio" in server_name:
                registry_entry["category"] = "quality"
                registry_entry["priority"] = "low"
            else:
                registry_entry["category"] = "general"
                registry_entry["priority"] = "medium"
            
            registry["servers"][server_name] = registry_entry
        
        # Save registry
        with open(self.registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
        
        self.registered_servers = registry
        print(f"✅ Registry created with {len(registry['servers'])} servers")
        print(f"💾 Saved to: {self.registry_file}")
        
        return registry
    
    def create_pulser_config(self) -> Dict[str, Any]:
        """Create Pulser CLI configuration"""
        print("\n⚙️ Creating Pulser configuration...")
        
        config = {
            "pulser": {
                "version": "4.0.0",
                "ecosystem": "InsightPulseAI SKR",
                "mcp_architecture": True
            },
            "agents": {},
            "servers": {},
            "routing": {
                "default_timeout": 30,
                "retry_attempts": 3,
                "load_balancing": "round_robin"
            },
            "monitoring": {
                "health_check_interval": 30,
                "performance_tracking": True,
                "logging_level": "INFO"
            }
        }
        
        # Add agent configurations
        for server_name, server_info in self.discovered_servers.items():
            if server_info.get("agent_name"):
                config["agents"][server_info["agent_name"]] = {
                    "server": server_name,
                    "endpoint": f"http://localhost:{server_info.get('port', 8000)}",
                    "capabilities": server_info.get("capabilities", []),
                    "category": self._get_category(server_name),
                    "priority": self._get_priority(server_name)
                }
            
            # Add server configurations
            config["servers"][server_name] = {
                "host": "localhost",
                "port": server_info.get("port", 8000),
                "protocol": "http",
                "health_endpoint": "/health",
                "status": "configured"
            }
        
        # Save configuration
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        print(f"✅ Configuration created for {len(config['agents'])} agents")
        print(f"💾 Saved to: {self.config_file}")
        
        return config
    
    def _get_category(self, server_name: str) -> str:
        """Get category for server"""
        if "scout" in server_name: return "analytics"
        if "rag" in server_name: return "knowledge"
        if "analyst" in server_name: return "analytics"
        if "voice" in server_name: return "interaction"
        if "memory" in server_name: return "infrastructure"
        if "researcher" in server_name: return "intelligence"
        if "synthetic" in server_name: return "data"
        if "video" in server_name: return "content"
        if "audio" in server_name: return "quality"
        return "general"
    
    def _get_priority(self, server_name: str) -> str:
        """Get priority for server"""
        high_priority = ["scout", "rag", "voice", "memory"]
        if any(keyword in server_name for keyword in high_priority):
            return "high"
        if "audio" in server_name:
            return "low"
        return "medium"
    
    def check_server_health(self, max_retries: int = 3, delay: int = 2) -> Dict[str, Any]:
        """Check health status of all registered servers"""
        print("\n🏥 Checking server health...")
        
        health_status = {
            "checked_at": datetime.now().isoformat(),
            "total_servers": len(self.discovered_servers),
            "healthy_servers": 0,
            "unhealthy_servers": 0,
            "servers": {}
        }
        
        for server_name, server_info in self.discovered_servers.items():
            port = server_info.get('port', 8000)
            health_url = f"http://localhost:{port}/health"
            
            print(f"   🔍 Checking {server_name} at port {port}...")
            
            server_health = {
                "server_name": server_name,
                "port": port,
                "health_url": health_url,
                "status": "unknown",
                "checked_at": datetime.now().isoformat()
            }
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        health_data = response.json()
                        server_health.update({
                            "status": "healthy",
                            "response_time": response.elapsed.total_seconds(),
                            "health_data": health_data
                        })
                        health_status["healthy_servers"] += 1
                        print(f"      ✅ Healthy (attempt {attempt + 1})")
                        break
                    else:
                        server_health["status"] = f"unhealthy_http_{response.status_code}"
                        print(f"      ⚠️ HTTP {response.status_code} (attempt {attempt + 1})")
                        
                except requests.exceptions.ConnectionError:
                    server_health["status"] = "not_running"
                    print(f"      ❌ Not running (attempt {attempt + 1})")
                    
                except requests.exceptions.Timeout:
                    server_health["status"] = "timeout"
                    print(f"      ⏱️ Timeout (attempt {attempt + 1})")
                    
                except Exception as e:
                    server_health["status"] = f"error_{type(e).__name__}"
                    server_health["error"] = str(e)
                    print(f"      ❌ Error: {e} (attempt {attempt + 1})")
                
                if attempt < max_retries - 1:
                    time.sleep(delay)
            
            if server_health["status"] not in ["healthy"]:
                health_status["unhealthy_servers"] += 1
            
            health_status["servers"][server_name] = server_health
        
        self.server_status = health_status
        
        print(f"\n📊 Health check complete:")
        print(f"   ✅ Healthy: {health_status['healthy_servers']}")
        print(f"   ❌ Unhealthy: {health_status['unhealthy_servers']}")
        
        return health_status
    
    def generate_startup_scripts(self) -> Dict[str, str]:
        """Generate startup scripts for all servers"""
        print("\n📝 Generating startup scripts...")
        
        scripts = {}
        
        # Individual server startup scripts
        for server_name, server_info in self.discovered_servers.items():
            script_content = f"""#!/bin/bash
# Startup script for {server_name}
# Generated by Pulser Bootstrap

set -e

echo "🚀 Starting {server_name}..."

# Navigate to server directory
cd "{server_info['path']}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📚 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo "▶️ Starting server on port {server_info.get('port', 8000)}..."
python {server_info.get('server_file', 'src/server.py')}
"""
            
            script_path = f"start_{server_name}.sh"
            scripts[script_path] = script_content
            
            # Write script file
            script_file = self.base_dir / script_path
            with open(script_file, 'w') as f:
                f.write(script_content)
            os.chmod(script_file, 0o755)
        
        # Master startup script
        master_script = """#!/bin/bash
# Master startup script for all MCP servers
# Generated by Pulser Bootstrap

set -e

echo "🚀 Starting all MCP servers..."

# Function to start server in background
start_server() {
    local server_name=$1
    local script_path=$2
    
    echo "📦 Starting $server_name..."
    nohup ./$script_path > logs/${server_name}.log 2>&1 &
    local pid=$!
    echo "$pid" > "pids/${server_name}.pid"
    echo "   ✅ Started $server_name (PID: $pid)"
}

# Create directories
mkdir -p logs pids

# Start servers in order of priority
"""
        
        # Add servers by priority
        high_priority = [name for name, info in self.discovered_servers.items() 
                        if self._get_priority(name) == "high"]
        medium_priority = [name for name, info in self.discovered_servers.items() 
                          if self._get_priority(name) == "medium"]
        low_priority = [name for name, info in self.discovered_servers.items() 
                       if self._get_priority(name) == "low"]
        
        for priority_group, delay in [(high_priority, 2), (medium_priority, 1), (low_priority, 1)]:
            for server_name in priority_group:
                master_script += f'start_server "{server_name}" "start_{server_name}.sh"\n'
                master_script += f'sleep {delay}\n'
        
        master_script += """
echo "⏱️ Waiting for servers to start..."
sleep 10

echo "🏥 Checking server health..."
python pulser_bootstrap.py --health-check

echo "✅ All servers started!"
echo "📊 Check logs/ directory for individual server logs"
echo "🔍 Use 'python pulser_bootstrap.py --status' to check status"
"""
        
        scripts["start_all_servers.sh"] = master_script
        
        # Write master script
        master_script_file = self.base_dir / "start_all_servers.sh"
        with open(master_script_file, 'w') as f:
            f.write(master_script)
        os.chmod(master_script_file, 0o755)
        
        # Stop script
        stop_script = """#!/bin/bash
# Stop all MCP servers
# Generated by Pulser Bootstrap

echo "🛑 Stopping all MCP servers..."

# Kill servers using PID files
if [ -d "pids" ]; then
    for pid_file in pids/*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            server_name=$(basename "$pid_file" .pid)
            
            if kill -0 "$pid" 2>/dev/null; then
                echo "🔴 Stopping $server_name (PID: $pid)"
                kill "$pid"
                rm "$pid_file"
            else
                echo "⚠️ $server_name was not running"
                rm "$pid_file"
            fi
        fi
    done
fi

echo "✅ All servers stopped"
"""
        
        scripts["stop_all_servers.sh"] = stop_script
        
        stop_script_file = self.base_dir / "stop_all_servers.sh"
        with open(stop_script_file, 'w') as f:
            f.write(stop_script)
        os.chmod(stop_script_file, 0o755)
        
        print(f"✅ Generated {len(scripts)} startup scripts")
        
        return scripts
    
    def save_bootstrap_status(self):
        """Save bootstrap status and results"""
        status = {
            "bootstrap_completed_at": datetime.now().isoformat(),
            "discovered_servers": len(self.discovered_servers),
            "registered_servers": len(self.registered_servers.get('servers', {})),
            "healthy_servers": self.server_status.get('healthy_servers', 0),
            "unhealthy_servers": self.server_status.get('unhealthy_servers', 0),
            "files_created": [
                str(self.registry_file),
                str(self.config_file),
                "start_all_servers.sh",
                "stop_all_servers.sh"
            ] + [f"start_{name}.sh" for name in self.discovered_servers.keys()],
            "next_steps": [
                "1. Review generated configuration files",
                "2. Start servers with: ./start_all_servers.sh",
                "3. Check health with: python pulser_bootstrap.py --health-check",
                "4. View registry with: cat mcp_registry.json"
            ]
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        print(f"\n💾 Bootstrap status saved to: {self.status_file}")
    
    def run_bootstrap(self):
        """Run complete bootstrap process"""
        print("=" * 60)
        print("🚀 PULSER BOOTSTRAP - MCP SERVER REGISTRATION")
        print("=" * 60)
        
        try:
            # Step 1: Discover servers
            self.discover_mcp_servers()
            
            # Step 2: Create registry
            self.create_registry()
            
            # Step 3: Create Pulser configuration
            self.create_pulser_config()
            
            # Step 4: Generate startup scripts
            self.generate_startup_scripts()
            
            # Step 5: Check server health (optional)
            try:
                self.check_server_health()
            except Exception as e:
                print(f"⚠️ Health check failed: {e}")
                print("   Servers may not be running yet")
            
            # Step 6: Save status
            self.save_bootstrap_status()
            
            # Summary
            print("\n" + "=" * 60)
            print("✅ BOOTSTRAP COMPLETE!")
            print("=" * 60)
            print(f"📊 Discovered: {len(self.discovered_servers)} MCP servers")
            print(f"📋 Registered: {len(self.registered_servers.get('servers', {}))}")
            print(f"🏥 Healthy: {self.server_status.get('healthy_servers', 0)}")
            print(f"❌ Unhealthy: {self.server_status.get('unhealthy_servers', 0)}")
            print("\n🚀 Next steps:")
            print("   1. ./start_all_servers.sh    # Start all servers")
            print("   2. python pulser_bootstrap.py --health-check")
            print("   3. cat mcp_registry.json     # View registry")
            print("   4. cat pulser_config.yaml    # View configuration")
            
        except Exception as e:
            print(f"\n❌ Bootstrap failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Pulser Bootstrap - MCP Server Registration")
    parser.add_argument("--base-dir", help="Base directory for MCP servers")
    parser.add_argument("--health-check", action="store_true", help="Only run health check")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--registry", action="store_true", help="Show registry")
    
    args = parser.parse_args()
    
    bootstrap = PulserBootstrap(args.base_dir)
    
    if args.health_check:
        bootstrap.discover_mcp_servers()
        health_status = bootstrap.check_server_health()
        print(json.dumps(health_status, indent=2))
        
    elif args.status:
        if bootstrap.status_file.exists():
            with open(bootstrap.status_file, 'r') as f:
                status = json.load(f)
            print(json.dumps(status, indent=2))
        else:
            print("❌ No bootstrap status found. Run bootstrap first.")
            
    elif args.registry:
        if bootstrap.registry_file.exists():
            with open(bootstrap.registry_file, 'r') as f:
                registry = json.load(f)
            print(json.dumps(registry, indent=2))
        else:
            print("❌ No registry found. Run bootstrap first.")
            
    else:
        bootstrap.run_bootstrap()

if __name__ == "__main__":
    main()