#!/bin/bash
# Centralized Logging Setup for MCP Ecosystem
# Configures all servers to send logs to Loki

set -e

echo "📊 MCP Centralized Logging Setup"
echo "================================"

# Base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to patch Python logging
patch_python_logging() {
    local server_dir=$1
    local server_name=$2
    
    echo "📝 Patching $server_name for Loki logging..."
    
    # Create logging configuration
    cat > "$server_dir/src/logging_config.py" << 'EOF'
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Try to import Loki handler
try:
    from python_logging_loki import LokiHandler
    LOKI_AVAILABLE = True
except ImportError:
    LOKI_AVAILABLE = False
    print("Warning: python-logging-loki not installed, using file logging only")

def setup_logging(service_name: str):
    """Configure centralized logging for MCP service"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with detailed format
    console_handler = logging.StreamHandler(sys.stdout)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f'{service_name}.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Loki handler if available
    loki_url = os.getenv('LOG_HANDLER', '')
    if LOKI_AVAILABLE and loki_url.startswith('loki://'):
        try:
            loki_host = loki_url.replace('loki://', '')
            loki_handler = LokiHandler(
                url=f"http://{loki_host}/loki/api/v1/push",
                tags={"service": service_name, "environment": os.getenv('ENV', 'production')},
                version="1"
            )
            logger.addHandler(loki_handler)
            logger.info(f"Loki logging enabled for {service_name}")
        except Exception as e:
            logger.error(f"Failed to setup Loki logging: {e}")
    
    # Log uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    return logger

# Request logging middleware
async def log_requests(request, call_next):
    """Log all incoming requests"""
    start_time = datetime.utcnow()
    
    # Log request
    logger = logging.getLogger("request")
    logger.info(f"{request.method} {request.url.path} - Client: {request.client.host}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.utcnow() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.3f}s"
    )
    
    return response
EOF

    # Patch server file to use centralized logging
    local server_file="$server_dir/src/$(ls $server_dir/src | grep '_server.py' | head -1)"
    if [ -f "$server_file" ]; then
        # Create backup
        cp "$server_file" "$server_file.backup"
        
        # Add logging import after other imports
        sed -i '1a\
from logging_config import setup_logging, log_requests\
\
# Setup logging\
logger = setup_logging("'$server_name'")\
' "$server_file"
        
        # Add request logging middleware after app creation
        sed -i '/app = FastAPI/a\
\
# Add request logging middleware\
@app.middleware("http")\
async def log_middleware(request, call_next):\
    return await log_requests(request, call_next)\
' "$server_file"
        
        echo "  ✅ Logging configured for $server_name"
    else
        echo "  ⚠️ Server file not found for $server_name"
    fi
}

# Function to update requirements
update_requirements() {
    local server_dir=$1
    local req_file="$server_dir/requirements.txt"
    
    if [ -f "$req_file" ]; then
        # Add logging dependencies if not present
        if ! grep -q "python-logging-loki" "$req_file"; then
            echo "python-logging-loki==1.3.1" >> "$req_file"
        fi
        if ! grep -q "prometheus-client" "$req_file"; then
            echo "prometheus-client==0.19.0" >> "$req_file"
        fi
    fi
}

# Function to create Loki configuration
create_loki_config() {
    echo "📝 Creating Loki configuration..."
    
    mkdir -p "$BASE_DIR/monitoring"
    
    cat > "$BASE_DIR/monitoring/loki-config.yaml" << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093

analytics:
  reporting_enabled: false

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  max_entries_limit_per_query: 5000

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: true
  retention_period: 168h
EOF
    
    echo "✅ Loki configuration created"
}

# Function to create Prometheus configuration
create_prometheus_config() {
    echo "📝 Creating Prometheus configuration..."
    
    cat > "$BASE_DIR/monitoring/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'mcp-servers'
    static_configs:
      - targets:
          - 'scout_local_mcp:8000'
          - 'creative_rag_mcp:8001'
          - 'financial_analyst_mcp:8002'
          - 'voice_agent_mcp:8003'
          - 'unified_mcp:8004'
          - 'synthetic_data_mcp:8005'
          - 'briefvault_rag_mcp:8006'
          - 'deep_researcher_mcp:8007'
          - 'video_rag_mcp:8008'
          - 'audio_analysis_mcp:8009'
          - 'shared_memory_mcp:5700'
    metrics_path: '/metrics'
    
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:9121']
      
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']
EOF
    
    echo "✅ Prometheus configuration created"
}

# Function to create Grafana dashboards
create_grafana_dashboards() {
    echo "📝 Creating Grafana dashboards..."
    
    mkdir -p "$BASE_DIR/monitoring/dashboards"
    
    # MCP Overview Dashboard
    cat > "$BASE_DIR/monitoring/dashboards/mcp-overview.json" << 'EOF'
{
  "dashboard": {
    "title": "MCP Ecosystem Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{service}} - p95"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "{{service}}"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total[5m]) * 100",
            "legendFormat": "{{container_name}}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "container_memory_usage_bytes / 1024 / 1024 / 1024",
            "legendFormat": "{{container_name}}"
          }
        ]
      }
    ]
  }
}
EOF
    
    # Create datasource configuration
    mkdir -p "$BASE_DIR/monitoring/datasources"
    
    cat > "$BASE_DIR/monitoring/datasources/prometheus.yaml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
EOF
    
    echo "✅ Grafana dashboards created"
}

# Function to create log aggregation script
create_log_scripts() {
    echo "📝 Creating log management scripts..."
    
    # Log viewer script
    cat > "$BASE_DIR/view_logs.sh" << 'EOF'
#!/bin/bash
# View logs from all MCP services

SERVICE=${1:-all}
TAIL_LINES=${2:-100}

if [ "$SERVICE" = "all" ]; then
    echo "📋 Showing logs from all services (last $TAIL_LINES lines each)..."
    for log in logs/*.log; do
        if [ -f "$log" ]; then
            echo -e "\n========== $(basename $log) =========="
            tail -n $TAIL_LINES "$log"
        fi
    done
else
    LOG_FILE="logs/${SERVICE}.log"
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Showing logs for $SERVICE (last $TAIL_LINES lines)..."
        tail -n $TAIL_LINES "$LOG_FILE"
    else
        echo "❌ Log file not found: $LOG_FILE"
        echo "Available services:"
        ls logs/*.log 2>/dev/null | xargs -n1 basename | sed 's/.log$//'
    fi
fi
EOF
    chmod +x "$BASE_DIR/view_logs.sh"
    
    # Log search script
    cat > "$BASE_DIR/search_logs.sh" << 'EOF'
#!/bin/bash
# Search logs across all MCP services

PATTERN="$1"
SERVICE=${2:-all}

if [ -z "$PATTERN" ]; then
    echo "Usage: $0 <search_pattern> [service]"
    exit 1
fi

echo "🔍 Searching for: $PATTERN"

if [ "$SERVICE" = "all" ]; then
    grep -n "$PATTERN" logs/*.log 2>/dev/null | while IFS=: read -r file line content; do
        echo "$(basename $file):$line: $content"
    done
else
    LOG_FILE="logs/${SERVICE}.log"
    if [ -f "$LOG_FILE" ]; then
        grep -n "$PATTERN" "$LOG_FILE"
    else
        echo "❌ Log file not found: $LOG_FILE"
    fi
fi
EOF
    chmod +x "$BASE_DIR/search_logs.sh"
    
    echo "✅ Log management scripts created"
}

# Main execution
main() {
    echo "Starting centralized logging setup..."
    
    # Create monitoring directory
    mkdir -p "$BASE_DIR/monitoring"
    
    # Patch all MCP servers
    for server_dir in "$BASE_DIR"/*_mcp; do
        if [ -d "$server_dir" ]; then
            server_name=$(basename "$server_dir")
            patch_python_logging "$server_dir" "$server_name"
            update_requirements "$server_dir"
        fi
    done
    
    # Create configurations
    create_loki_config
    create_prometheus_config
    create_grafana_dashboards
    create_log_scripts
    
    echo ""
    echo "✅ Centralized logging setup complete!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Rebuild Docker images: docker-compose build"
    echo "2. Start monitoring stack: docker-compose up -d loki prometheus grafana"
    echo "3. Access Grafana: https://mcp.insightpulseai.com/grafana"
    echo "4. View logs: ./view_logs.sh [service_name]"
    echo "5. Search logs: ./search_logs.sh 'pattern' [service_name]"
    echo ""
    echo "📊 Monitoring URLs:"
    echo "- Grafana: http://localhost:3000 (admin/admin)"
    echo "- Prometheus: http://localhost:9090"
    echo "- Loki: http://localhost:3100"
}

# Run main function
main