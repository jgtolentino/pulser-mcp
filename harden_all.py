#!/usr/bin/env python3
"""
Production Security Hardening Script for MCP Ecosystem
Implements JWT authentication, environment security, and API versioning
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
import secrets
import re

class MCPSecurityHardener:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.servers = self._discover_servers()
        
    def _discover_servers(self):
        """Discover all MCP servers"""
        servers = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.endswith('_mcp'):
                src_dir = item / "src"
                if src_dir.exists():
                    python_files = list(src_dir.glob("*_server.py"))
                    if python_files:
                        servers.append({
                            'name': item.name,
                            'path': item,
                            'server_file': python_files[0]
                        })
        return servers
    
    def add_jwt_auth(self, jwt_secret=None):
        """Add JWT authentication to all servers"""
        if not jwt_secret:
            jwt_secret = os.getenv('PULSER_JWT_SECRET', secrets.token_urlsafe(32))
        
        print("🔒 Adding JWT authentication to all servers...")
        
        jwt_middleware_code = '''
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# JWT Configuration
SECRET_KEY = os.getenv("PULSER_JWT_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = ["/", "/health", "/auth/token"]
'''
        
        auth_endpoint_code = '''
@app.post("/auth/token")
async def login(username: str, password: str):
    """Authenticate and get access token"""
    # In production, verify against secure user store
    if username == os.getenv("MCP_ADMIN_USER", "admin") and password == os.getenv("MCP_ADMIN_PASS", "change-this"):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
'''
        
        for server in self.servers:
            print(f"  📝 Patching {server['name']}...")
            
            # Read server file
            with open(server['server_file'], 'r') as f:
                content = f.read()
            
            # Check if already has JWT
            if 'HTTPBearer' in content:
                print(f"    ✅ Already has authentication")
                continue
            
            # Add imports
            import_section = "from fastapi import FastAPI, HTTPException"
            new_import = "from fastapi import FastAPI, HTTPException, Depends"
            content = content.replace(import_section, new_import)
            
            # Add JWT code after imports
            insert_pos = content.find("app = FastAPI")
            if insert_pos > 0:
                content = content[:insert_pos] + jwt_middleware_code + "\n" + content[insert_pos:]
            
            # Add auth endpoint
            insert_pos = content.find('@app.get("/health")')
            if insert_pos > 0:
                content = content[:insert_pos] + auth_endpoint_code + "\n" + content[insert_pos:]
            
            # Add dependency to protected endpoints
            # Skip public endpoints
            protected_patterns = [
                r'(@app\.(post|put|delete|patch)\("\/mcp\/tools\/[^"]+"\))',
                r'(@app\.get\("\/mcp\/[^"]+"\))'
            ]
            
            for pattern in protected_patterns:
                matches = re.finditer(pattern, content)
                for match in reversed(list(matches)):
                    decorator = match.group(0)
                    # Find the function definition
                    func_start = match.end()
                    func_match = re.search(r'async def (\w+)\((.*?)\):', content[func_start:], re.DOTALL)
                    if func_match:
                        func_name = func_match.group(1)
                        params = func_match.group(2)
                        
                        # Add auth dependency if not present
                        if 'verify_token' not in params:
                            if params.strip():
                                new_params = f"{params}, current_user: str = Depends(verify_token)"
                            else:
                                new_params = "current_user: str = Depends(verify_token)"
                            
                            new_func_def = f"async def {func_name}({new_params}):"
                            old_func_def = f"async def {func_name}({params}):"
                            content = content.replace(old_func_def, new_func_def)
            
            # Write updated file
            backup_file = server['server_file'].with_suffix('.py.backup')
            with open(backup_file, 'w') as f:
                f.write(content)
            
            with open(server['server_file'], 'w') as f:
                f.write(content)
            
            print(f"    ✅ JWT authentication added")
        
        # Update requirements.txt files
        self._update_requirements()
        
        return jwt_secret
    
    def _update_requirements(self):
        """Add security dependencies to all requirements.txt"""
        security_deps = [
            "python-jose[cryptography]==3.3.0",
            "passlib[bcrypt]==1.7.4",
            "python-multipart==0.0.6"
        ]
        
        for server in self.servers:
            req_file = server['path'] / "requirements.txt"
            if req_file.exists():
                with open(req_file, 'r') as f:
                    existing = f.read()
                
                for dep in security_deps:
                    if dep.split('==')[0] not in existing:
                        existing += f"\n{dep}"
                
                with open(req_file, 'w') as f:
                    f.write(existing.strip() + "\n")
    
    def add_api_versioning(self):
        """Add /api/v1 prefix to all endpoints"""
        print("🔧 Adding API versioning...")
        
        for server in self.servers:
            print(f"  📝 Updating {server['name']}...")
            
            with open(server['server_file'], 'r') as f:
                content = f.read()
            
            # Update FastAPI initialization
            old_init = 'app = FastAPI(title='
            new_init = 'app = FastAPI(title='
            
            # Find and update
            if 'prefix="/api/v1"' not in content:
                # Add versioned router
                router_code = '''
from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")
'''
                
                # Insert after app initialization
                app_pos = content.find("app = FastAPI")
                if app_pos > 0:
                    end_pos = content.find("\n", app_pos)
                    content = content[:end_pos+1] + router_code + content[end_pos+1:]
                
                # Update decorators
                patterns = [
                    (r'@app\.get\("(/mcp/[^"]+)"\)', r'@api_v1.get("\1")'),
                    (r'@app\.post\("(/mcp/[^"]+)"\)', r'@api_v1.post("\1")'),
                    (r'@app\.put\("(/mcp/[^"]+)"\)', r'@api_v1.put("\1")'),
                    (r'@app\.delete\("(/mcp/[^"]+)"\)', r'@api_v1.delete("\1")')
                ]
                
                for old_pattern, new_pattern in patterns:
                    content = re.sub(old_pattern, new_pattern, content)
                
                # Include router
                main_block = 'if __name__ == "__main__":'
                if main_block in content:
                    include_code = "\n# Include API v1 router\napp.include_router(api_v1)\n\n"
                    content = content.replace(main_block, include_code + main_block)
                
                with open(server['server_file'], 'w') as f:
                    f.write(content)
                
                print(f"    ✅ API versioning added")
    
    def create_env_template(self, jwt_secret):
        """Create secure environment template"""
        print("📋 Creating secure environment template...")
        
        env_template = f"""# MCP Ecosystem Environment Configuration
# Generated by harden_all.py

# JWT Authentication
PULSER_JWT_SECRET={jwt_secret}
MCP_ADMIN_USER=admin
MCP_ADMIN_PASS={secrets.token_urlsafe(16)}

# Database Security
REDIS_PASSWORD={secrets.token_urlsafe(16)}
NEO4J_AUTH=neo4j/{secrets.token_urlsafe(16)}
POSTGRES_PASSWORD={secrets.token_urlsafe(16)}

# Service Ports (internal only)
SCOUT_LOCAL_PORT=8000
CREATIVE_RAG_PORT=8001
FINANCIAL_ANALYST_PORT=8002
VOICE_AGENT_PORT=8003
UNIFIED_MCP_PORT=8004
SYNTHETIC_DATA_PORT=8005
BRIEFVAULT_RAG_PORT=8006
DEEP_RESEARCHER_PORT=8007
VIDEO_RAG_PORT=8008
AUDIO_ANALYSIS_PORT=8009
SHARED_MEMORY_PORT=5700

# TLS Configuration
TLS_CERT_PATH=/etc/letsencrypt/live/mcp.insightpulseai.com/fullchain.pem
TLS_KEY_PATH=/etc/letsencrypt/live/mcp.insightpulseai.com/privkey.pem

# Logging
LOG_LEVEL=INFO
LOG_HANDLER=loki://loki:3100
LOKI_LABELS=app=mcp,env=production

# Resource Limits
MAX_WORKERS=4
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30

# Backup Configuration
BACKUP_SCHEDULE="0 2 * * *"
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=mcp-backups
"""
        
        env_file = self.base_dir / ".env.production"
        with open(env_file, 'w') as f:
            f.write(env_template)
        
        print(f"✅ Environment template saved to {env_file}")
        print("⚠️  IMPORTANT: Review and update passwords before deploying!")
        
        return env_file

def main():
    parser = argparse.ArgumentParser(description="Harden MCP servers for production")
    parser.add_argument("--jwt-secret", help="JWT secret key (or set PULSER_JWT_SECRET)")
    parser.add_argument("--skip-versioning", action="store_true", help="Skip API versioning")
    parser.add_argument("--base-dir", help="Base directory for MCP servers")
    
    args = parser.parse_args()
    
    hardener = MCPSecurityHardener(args.base_dir)
    
    print("🔐 MCP Security Hardening Script")
    print("=" * 50)
    
    # Add JWT authentication
    jwt_secret = hardener.add_jwt_auth(args.jwt_secret)
    
    # Add API versioning
    if not args.skip_versioning:
        hardener.add_api_versioning()
    
    # Create environment template
    env_file = hardener.create_env_template(jwt_secret)
    
    print("\n✅ Security hardening complete!")
    print("\n📝 Next steps:")
    print("1. Review and update passwords in .env.production")
    print("2. Set up TLS certificates with: certbot certonly --standalone -d mcp.insightpulseai.com")
    print("3. Configure firewall rules (see network_security.sh)")
    print("4. Set up centralized logging (see logging_setup.sh)")
    print("5. Run tests to ensure nothing broke: pytest tests/")

if __name__ == "__main__":
    main()