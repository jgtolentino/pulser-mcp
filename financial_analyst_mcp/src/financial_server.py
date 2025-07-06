#!/usr/bin/env python3
"""
Financial Analyst MCP Server - Marketing KPI forecasting and analysis
Powered by CrewAI for orchestration and secure code execution
"""

import os
import json
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from crewai import Agent, Task, Crew
import logging
import docker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SANDBOX_IMAGE = "python:3.11-slim"
MAX_EXECUTION_TIME = 60  # seconds
PLOT_OUTPUT_DIR = Path(__file__).parent.parent / "data" / "plots"
PLOT_OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# FastAPI app

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

app = FastAPI(title="Financial Analyst MCP Server")

from fastapi import APIRouter

# Create versioned router
api_v1 = APIRouter(prefix="/api/v1")

# Pydantic models
class AnalysisRequest(BaseModel):
    query: str
    data_source: str = "supabase"  # supabase, yfinance, csv
    timeframe: Optional[str] = "1M"  # 1D, 1W, 1M, 3M, 1Y
    metrics: Optional[List[str]] = ["revenue", "engagement", "conversion"]
    brands: Optional[List[str]] = []

class CodeGenerationRequest(BaseModel):
    analysis_type: str  # forecast, trend, comparison, correlation
    parameters: Dict[str, Any]
    output_format: str = "plot"  # plot, data, report

class CodeExecutionRequest(BaseModel):
    code: str
    timeout: Optional[int] = 30
    sandbox: bool = True

# Docker client for sandboxed execution
docker_client = None

def init_docker():
    """Initialize Docker client for sandboxed execution"""
    global docker_client
    try:
        docker_client = docker.from_env()
        # Pull sandbox image if not present
        try:
            docker_client.images.get(SANDBOX_IMAGE)
        except:
            logger.info(f"Pulling Docker image: {SANDBOX_IMAGE}")
            docker_client.images.pull(SANDBOX_IMAGE)
    except Exception as e:
        logger.warning(f"Docker not available: {e}. Falling back to subprocess.")

# CrewAI Agents
class FinancialAnalystCrew:
    def __init__(self):
        self.query_parser = Agent(
            role="Query Parser",
            goal="Parse and understand financial analysis queries",
            backstory="Expert at interpreting marketing KPI analysis requests",
            verbose=True
        )
        
        self.code_writer = Agent(
            role="Code Writer",
            goal="Generate Python code for financial analysis",
            backstory="Skilled Python developer specializing in data analysis and visualization",
            verbose=True
        )
        
        self.code_executor = Agent(
            role="Code Executor",
            goal="Safely execute analysis code and return results",
            backstory="Security-focused executor ensuring safe code execution",
            verbose=True
        )

# MCP Tools
class MCPTools:
    @staticmethod
    async def analyze_kpis(request: AnalysisRequest) -> Dict[str, Any]:
        """Analyze marketing KPIs with financial methods"""
        try:
            # Mock data generation (replace with actual data source)
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            
            data = {
                'date': dates,
                'revenue': np.random.normal(100000, 15000, 30).cumsum(),
                'engagement': np.random.normal(0.05, 0.01, 30),
                'conversion': np.random.normal(0.02, 0.005, 30),
                'brand': np.random.choice(request.brands or ['Brand A'], 30)
            }
            
            df = pd.DataFrame(data)
            
            # Calculate financial metrics
            metrics = {
                'total_revenue': float(df['revenue'].sum()),
                'avg_daily_revenue': float(df['revenue'].mean()),
                'revenue_growth': float((df['revenue'].iloc[-1] - df['revenue'].iloc[0]) / df['revenue'].iloc[0]),
                'avg_engagement': float(df['engagement'].mean()),
                'avg_conversion': float(df['conversion'].mean()),
                'roi_estimate': float(df['revenue'].sum() / (df['revenue'].sum() * 0.3))  # Mock ROI
            }
            
            # Generate forecast
            from sklearn.linear_model import LinearRegression
            X = np.arange(len(df)).reshape(-1, 1)
            y = df['revenue'].values
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Forecast next 7 days
            future_X = np.arange(len(df), len(df) + 7).reshape(-1, 1)
            forecast = model.predict(future_X)
            
            metrics['forecast_7d'] = forecast.tolist()
            metrics['forecast_trend'] = 'increasing' if model.coef_[0] > 0 else 'decreasing'
            
            return {
                "success": True,
                "query": request.query,
                "metrics": metrics,
                "data_points": len(df),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing KPIs: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def generate_code(request: CodeGenerationRequest) -> Dict[str, Any]:
        """Generate analysis code based on requirements"""
        try:
            code_templates = {
                "forecast": """
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

# Load data
{data_loading}

# Prepare data for forecasting
X = np.arange(len(df)).reshape(-1, 1)
y = df['{metric}'].values

# Train model
model = LinearRegression()
model.fit(X, y)

# Generate forecast
forecast_periods = {periods}
future_X = np.arange(len(df), len(df) + forecast_periods).reshape(-1, 1)
forecast = model.predict(future_X)

# Plot results
plt.figure(figsize=(12, 6))
plt.plot(df.index, y, label='Historical', color='blue')
plt.plot(range(len(df), len(df) + forecast_periods), forecast, 
         label='Forecast', color='red', linestyle='--')
plt.title('{title}')
plt.xlabel('Time Period')
plt.ylabel('{metric}')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('forecast.png', dpi=300)
plt.close()

# Return metrics
metrics = {{
    'last_value': float(y[-1]),
    'forecast_values': forecast.tolist(),
    'trend': 'increasing' if model.coef_[0] > 0 else 'decreasing',
    'slope': float(model.coef_[0])
}}
print(json.dumps(metrics))
""",
                "trend": """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
{data_loading}

# Calculate rolling metrics
df['rolling_mean'] = df['{metric}'].rolling(window=7).mean()
df['rolling_std'] = df['{metric}'].rolling(window=7).std()

# Plot trend analysis
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

# Main trend
ax1.plot(df.index, df['{metric}'], label='Daily', alpha=0.5)
ax1.plot(df.index, df['rolling_mean'], label='7-day Average', linewidth=2)
ax1.fill_between(df.index, 
                 df['rolling_mean'] - df['rolling_std'],
                 df['rolling_mean'] + df['rolling_std'],
                 alpha=0.2, label='±1 STD')
ax1.set_title('{title} - Trend Analysis')
ax1.set_ylabel('{metric}')
ax1.legend()
ax1.grid(True)

# Distribution
ax2.hist(df['{metric}'], bins=30, edgecolor='black')
ax2.set_title('Distribution of {metric}')
ax2.set_xlabel('{metric}')
ax2.set_ylabel('Frequency')

plt.tight_layout()
plt.savefig('trend_analysis.png', dpi=300)
plt.close()

# Calculate statistics
stats = {{
    'mean': float(df['{metric}'].mean()),
    'std': float(df['{metric}'].std()),
    'min': float(df['{metric}'].min()),
    'max': float(df['{metric}'].max()),
    'trend_direction': 'up' if df['{metric}'].iloc[-7:].mean() > df['{metric}'].iloc[-14:-7].mean() else 'down'
}}
print(json.dumps(stats))
"""
            }
            
            # Select template
            template = code_templates.get(request.analysis_type, code_templates['trend'])
            
            # Fill template
            params = request.parameters
            code = template.format(
                data_loading=params.get('data_loading', "df = pd.read_csv('data.csv')"),
                metric=params.get('metric', 'revenue'),
                periods=params.get('periods', 7),
                title=params.get('title', 'Marketing KPI Analysis')
            )
            
            # Add necessary imports
            full_code = "import json\n" + code
            
            return {
                "success": True,
                "code": full_code,
                "analysis_type": request.analysis_type,
                "estimated_runtime": "10-30 seconds"
            }
            
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def execute_code(request: CodeExecutionRequest) -> Dict[str, Any]:
        """Execute analysis code in sandboxed environment"""
        try:
            if request.sandbox and docker_client:
                # Docker sandbox execution
                return await MCPTools._execute_in_docker(request.code, request.timeout)
            else:
                # Fallback to subprocess (less secure)
                return await MCPTools._execute_subprocess(request.code, request.timeout)
                
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _execute_in_docker(code: str, timeout: int) -> Dict[str, Any]:
        """Execute code in Docker container"""
        try:
            # Create temporary directory for code and outputs
            with tempfile.TemporaryDirectory() as tmpdir:
                code_file = Path(tmpdir) / "analysis.py"
                code_file.write_text(code)
                
                # Run container
                container = docker_client.containers.run(
                    SANDBOX_IMAGE,
                    f"python /code/analysis.py",
                    volumes={tmpdir: {'bind': '/code', 'mode': 'rw'}},
                    working_dir="/code",
                    detach=True,
                    mem_limit="512m",
                    cpu_quota=50000  # 50% CPU
                )
                
                # Wait for completion
                result = container.wait(timeout=timeout)
                logs = container.logs().decode('utf-8')
                container.remove()
                
                # Check for generated files
                outputs = {}
                for file in Path(tmpdir).glob("*.png"):
                    # Move to permanent storage
                    dest = PLOT_OUTPUT_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.name}"
                    file.rename(dest)
                    outputs[file.name] = str(dest)
                
                # Parse JSON output if present
                metrics = {}
                for line in logs.split('\n'):
                    if line.strip().startswith('{'):
                        try:
                            metrics = json.loads(line.strip())
                            break
                        except:
                            pass
                
                return {
                    "success": True,
                    "exit_code": result['StatusCode'],
                    "outputs": outputs,
                    "metrics": metrics,
                    "logs": logs[-1000:]  # Last 1000 chars
                }
                
        except Exception as e:
            return {"success": False, "error": f"Docker execution failed: {str(e)}"}
    
    @staticmethod
    async def _execute_subprocess(code: str, timeout: int) -> Dict[str, Any]:
        """Execute code using subprocess (fallback)"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                code_file = Path(tmpdir) / "analysis.py"
                code_file.write_text(code)
                
                # Execute with timeout
                proc = await asyncio.create_subprocess_exec(
                    'python', str(code_file),
                    cwd=tmpdir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), 
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return {"success": False, "error": "Execution timeout"}
                
                # Check outputs
                outputs = {}
                for file in Path(tmpdir).glob("*.png"):
                    dest = PLOT_OUTPUT_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.name}"
                    file.rename(dest)
                    outputs[file.name] = str(dest)
                
                # Parse metrics
                metrics = {}
                for line in stdout.decode().split('\n'):
                    if line.strip().startswith('{'):
                        try:
                            metrics = json.loads(line.strip())
                            break
                        except:
                            pass
                
                return {
                    "success": proc.returncode == 0,
                    "exit_code": proc.returncode,
                    "outputs": outputs,
                    "metrics": metrics,
                    "stdout": stdout.decode()[-1000:],
                    "stderr": stderr.decode()[-1000:]
                }
                
        except Exception as e:
            return {"success": False, "error": f"Subprocess execution failed: {str(e)}"}

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    init_docker()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "active", "service": "Financial Analyst MCP Server"}

@api_v1.post("/mcp/tools/analyze_kpis")
async def analyze_kpis(request: AnalysisRequest, current_user: str = Depends(verify_token)):
    """Analyze marketing KPIs"""
    result = await MCPTools.analyze_kpis(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/generate_code")
async def generate_code(request: CodeGenerationRequest, current_user: str = Depends(verify_token)):
    """Generate analysis code"""
    result = await MCPTools.generate_code(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.post("/mcp/tools/execute_code")
async def execute_code(request: CodeExecutionRequest, current_user: str = Depends(verify_token)):
    """Execute analysis code safely"""
    result = await MCPTools.execute_code(request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@api_v1.get("/mcp/tools/list_plots")
async def list_plots(current_user: str = Depends(verify_token)):
    """List available plot outputs"""
    plots = []
    for file in PLOT_OUTPUT_DIR.glob("*.png"):
        plots.append({
            "filename": file.name,
            "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
            "size": file.stat().st_size
        })
    return {"plots": sorted(plots, key=lambda x: x['created'], reverse=True)}

# MCP metadata endpoint
@api_v1.get("/mcp/metadata")
async def get_metadata(current_user: str = Depends(verify_token)):
    """Return MCP server metadata"""
    return {
        "name": "financial-analyst-mcp",
        "version": "1.0.0",
        "description": "Marketing KPI forecasting and financial analysis",
        "tools": [
            {
                "name": "analyze_kpis",
                "description": "Analyze marketing KPIs with financial methods",
                "parameters": {
                    "query": "string",
                    "data_source": "string (supabase, yfinance, csv)",
                    "timeframe": "string (1D, 1W, 1M, 3M, 1Y)",
                    "metrics": "array[string]",
                    "brands": "array[string]"
                }
            },
            {
                "name": "generate_code",
                "description": "Generate Python analysis code",
                "parameters": {
                    "analysis_type": "string (forecast, trend, comparison, correlation)",
                    "parameters": "object",
                    "output_format": "string (plot, data, report)"
                }
            },
            {
                "name": "execute_code",
                "description": "Execute analysis code in sandbox",
                "parameters": {
                    "code": "string",
                    "timeout": "integer (optional)",
                    "sandbox": "boolean (default: true)"
                }
            }
        ]
    }


# Include API v1 router
app.include_router(api_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)