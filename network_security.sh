#!/bin/bash
# Network Security Configuration for MCP Ecosystem
# Implements firewall rules, TLS setup, and network isolation

set -e

echo "🔒 MCP Network Security Configuration"
echo "====================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Configuration
DOMAIN=${MCP_DOMAIN:-"mcp.insightpulseai.com"}
INTERNAL_NETWORK=${INTERNAL_NETWORK:-"10.0.0.0/8"}
CERT_EMAIL=${CERT_EMAIL:-"admin@insightpulseai.com"}

echo "📋 Configuration:"
echo "  Domain: $DOMAIN"
echo "  Internal Network: $INTERNAL_NETWORK"
echo "  Certificate Email: $CERT_EMAIL"
echo ""

# Function to setup UFW firewall
setup_firewall() {
    echo "🔥 Setting up UFW firewall rules..."
    
    # Install UFW if not present
    if ! command -v ufw &> /dev/null; then
        apt-get update && apt-get install -y ufw
    fi
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (adjust port as needed)
    ufw allow 22/tcp comment "SSH"
    
    # Allow HTTP/HTTPS for certbot and reverse proxy
    ufw allow 80/tcp comment "HTTP for certbot"
    ufw allow 443/tcp comment "HTTPS"
    
    # Allow MCP ports only from internal network
    for port in 5700 8000 8001 8002 8003 8004 8005 8006 8007 8008 8009; do
        ufw allow from $INTERNAL_NETWORK to any port $port proto tcp comment "MCP port $port"
    done
    
    # Allow Docker internal communication
    ufw allow from 172.16.0.0/12 comment "Docker internal"
    
    # Enable UFW
    ufw --force enable
    
    echo "✅ Firewall configured"
    ufw status verbose
}

# Function to setup TLS certificates
setup_tls() {
    echo "🔐 Setting up TLS certificates..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
    
    # Stop any services on port 80
    systemctl stop nginx 2>/dev/null || true
    systemctl stop apache2 2>/dev/null || true
    
    # Obtain certificate
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email $CERT_EMAIL \
        -d $DOMAIN \
        --expand
    
    # Create certificate directory for Docker
    mkdir -p /etc/mcp/certs
    
    # Copy certificates
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/mcp/certs/
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /etc/mcp/certs/
    
    # Set permissions
    chmod 644 /etc/mcp/certs/fullchain.pem
    chmod 600 /etc/mcp/certs/privkey.pem
    
    echo "✅ TLS certificates obtained"
    
    # Setup auto-renewal
    echo "0 2 * * * root certbot renew --quiet --post-hook 'cp /etc/letsencrypt/live/$DOMAIN/*.pem /etc/mcp/certs/ && docker-compose restart nginx'" > /etc/cron.d/certbot-renewal
    
    echo "✅ Auto-renewal configured"
}

# Function to create Nginx reverse proxy configuration
setup_nginx() {
    echo "🌐 Setting up Nginx reverse proxy..."
    
    # Create Nginx configuration
    cat > /etc/mcp/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_status 429;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml application/atom+xml image/svg+xml;
    
    # Upstream definitions
    upstream scout_local { server scout_local_mcp:8000; }
    upstream creative_rag { server creative_rag_mcp:8001; }
    upstream financial_analyst { server financial_analyst_mcp:8002; }
    upstream voice_agent { server voice_agent_mcp:8003; }
    upstream unified_mcp { server unified_mcp:8004; }
    upstream synthetic_data { server synthetic_data_mcp:8005; }
    upstream briefvault_rag { server briefvault_rag_mcp:8006; }
    upstream deep_researcher { server deep_researcher_mcp:8007; }
    upstream video_rag { server video_rag_mcp:8008; }
    upstream audio_analysis { server audio_analysis_mcp:8009; }
    upstream shared_memory { server shared_memory_mcp:5700; }
    
    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name ${DOMAIN};
        
        ssl_certificate /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;
        
        # Security
        client_max_body_size 100M;
        client_body_timeout 300s;
        
        # API v1 routing
        location /api/v1/scout/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://scout_local/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/creative/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://creative_rag/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/financial/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://financial_analyst/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/voice/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://voice_agent/api/v1/;
            include /etc/nginx/proxy.conf;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        
        location /api/v1/unified/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://unified_mcp/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/synthetic/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://synthetic_data/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/briefvault/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://briefvault_rag/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/researcher/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://deep_researcher/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/video/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://video_rag/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/audio/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://audio_analysis/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        location /api/v1/memory/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://shared_memory/api/v1/;
            include /etc/nginx/proxy.conf;
        }
        
        # Health check endpoint (no auth required)
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
        
        # Root
        location / {
            return 404;
        }
    }
    
    # HTTP redirect to HTTPS
    server {
        listen 80;
        server_name ${DOMAIN};
        return 301 https://$server_name$request_uri;
    }
}
EOF

    # Create proxy configuration
    cat > /etc/mcp/proxy.conf << 'EOF'
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $server_name;
proxy_read_timeout 300s;
proxy_connect_timeout 75s;
EOF

    echo "✅ Nginx configuration created"
}

# Function to create Docker network
setup_docker_network() {
    echo "🐳 Setting up Docker network isolation..."
    
    # Create isolated network
    docker network create \
        --driver bridge \
        --subnet=172.20.0.0/16 \
        --opt com.docker.network.bridge.name=mcp_bridge \
        mcp_network 2>/dev/null || true
    
    echo "✅ Docker network configured"
}

# Function to create security scripts
create_security_scripts() {
    echo "📝 Creating security maintenance scripts..."
    
    # Create certificate check script
    cat > /etc/mcp/check_certs.sh << 'EOF'
#!/bin/bash
# Check certificate expiration

DOMAIN="mcp.insightpulseai.com"
CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

if [ -f "$CERT_FILE" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))
    
    echo "Certificate expires: $EXPIRY"
    echo "Days left: $DAYS_LEFT"
    
    if [ $DAYS_LEFT -lt 30 ]; then
        echo "⚠️ WARNING: Certificate expires in less than 30 days!"
    fi
else
    echo "❌ Certificate not found!"
fi
EOF
    chmod +x /etc/mcp/check_certs.sh
    
    # Create security audit script
    cat > /etc/mcp/security_audit.sh << 'EOF'
#!/bin/bash
# Security audit script

echo "🔍 MCP Security Audit"
echo "===================="

echo -e "\n1. Checking open ports..."
ss -tuln | grep LISTEN

echo -e "\n2. Checking firewall status..."
ufw status numbered

echo -e "\n3. Checking failed login attempts..."
grep "Failed password" /var/log/auth.log | tail -10

echo -e "\n4. Checking certificate status..."
/etc/mcp/check_certs.sh

echo -e "\n5. Checking Docker containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n6. Checking disk usage..."
df -h | grep -E '^/dev/'

echo -e "\nAudit complete!"
EOF
    chmod +x /etc/mcp/security_audit.sh
    
    echo "✅ Security scripts created"
}

# Main execution
main() {
    echo "Starting network security setup..."
    
    # Create directories
    mkdir -p /etc/mcp/{certs,scripts}
    
    # Setup components
    setup_firewall
    setup_docker_network
    setup_tls
    setup_nginx
    create_security_scripts
    
    echo ""
    echo "✅ Network security configuration complete!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Update DNS to point $DOMAIN to this server"
    echo "2. Test HTTPS access: curl https://$DOMAIN/health"
    echo "3. Run security audit: /etc/mcp/security_audit.sh"
    echo "4. Monitor logs: tail -f /var/log/nginx/*.log"
    echo ""
    echo "🔒 Security reminders:"
    echo "- Regularly update system packages: apt update && apt upgrade"
    echo "- Monitor certificate expiration: /etc/mcp/check_certs.sh"
    echo "- Review firewall rules: ufw status verbose"
    echo "- Check for suspicious activity in logs"
}

# Run main function
main