#!/bin/bash
# Automated Backup and Disaster Recovery Script for MCP Ecosystem
# Supports local and S3 backups with encryption

set -e

echo "🔄 MCP Backup and Disaster Recovery System"
echo "=========================================="

# Configuration
BACKUP_DIR="/var/backups/mcp"
S3_BUCKET=${BACKUP_S3_BUCKET:-"mcp-backups"}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
ENCRYPTION_KEY=${BACKUP_ENCRYPTION_KEY:-$(openssl rand -hex 32)}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="mcp_backup_${TIMESTAMP}"

# Services to backup
SERVICES=(
    "scout_local_mcp"
    "creative_rag_mcp" 
    "financial_analyst_mcp"
    "voice_agent_mcp"
    "unified_mcp"
    "synthetic_data_mcp"
    "briefvault_rag_mcp"
    "deep_researcher_mcp"
    "video_rag_mcp"
    "audio_analysis_mcp"
    "shared_memory_mcp"
)

# Function to check prerequisites
check_prerequisites() {
    echo "📋 Checking prerequisites..."
    
    # Check for required tools
    for tool in docker tar openssl aws; do
        if ! command -v $tool &> /dev/null; then
            echo "❌ $tool is not installed"
            exit 1
        fi
    done
    
    # Check AWS credentials if S3 backup enabled
    if [ "$ENABLE_S3_BACKUP" = "true" ]; then
        if ! aws s3 ls &> /dev/null; then
            echo "❌ AWS credentials not configured"
            exit 1
        fi
    fi
    
    echo "✅ Prerequisites satisfied"
}

# Function to backup Docker volumes
backup_volumes() {
    echo "📦 Backing up Docker volumes..."
    
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME/volumes"
    
    # Get all MCP volumes
    volumes=$(docker volume ls --format '{{.Name}}' | grep -E 'mcp_|scout_|creative_|financial_|voice_|unified_|synthetic_|briefvault_|researcher_|video_|audio_|memory_|qdrant_|neo4j_|redis_')
    
    for volume in $volumes; do
        echo "  📁 Backing up volume: $volume"
        
        # Create temporary container to access volume
        docker run --rm \
            -v "$volume:/data:ro" \
            -v "$BACKUP_DIR/$BACKUP_NAME/volumes:/backup" \
            alpine tar czf "/backup/${volume}.tar.gz" -C /data .
    done
    
    echo "✅ Volume backup complete"
}

# Function to backup databases
backup_databases() {
    echo "💾 Backing up databases..."
    
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME/databases"
    
    # Backup Neo4j
    if docker ps --format '{{.Names}}' | grep -q neo4j; then
        echo "  📊 Backing up Neo4j..."
        docker exec mcp_neo4j neo4j-admin database dump neo4j \
            --to-path=/backup/neo4j_${TIMESTAMP}.dump
        docker cp mcp_neo4j:/backup/neo4j_${TIMESTAMP}.dump \
            "$BACKUP_DIR/$BACKUP_NAME/databases/"
    fi
    
    # Backup Redis
    if docker ps --format '{{.Names}}' | grep -q redis; then
        echo "  🗄️ Backing up Redis..."
        docker exec mcp_redis redis-cli \
            --rdb /backup/redis_${TIMESTAMP}.rdb \
            BGSAVE
        sleep 5  # Wait for background save
        docker cp mcp_redis:/backup/redis_${TIMESTAMP}.rdb \
            "$BACKUP_DIR/$BACKUP_NAME/databases/"
    fi
    
    echo "✅ Database backup complete"
}

# Function to backup configurations
backup_configs() {
    echo "⚙️ Backing up configurations..."
    
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME/configs"
    
    # Backup important configuration files
    configs=(
        "/etc/mcp/nginx.conf"
        "/etc/mcp/proxy.conf"
        ".env.production"
        "docker-compose.yml"
        "monitoring/prometheus.yml"
        "monitoring/loki-config.yaml"
    )
    
    for config in "${configs[@]}"; do
        if [ -f "$config" ]; then
            cp "$config" "$BACKUP_DIR/$BACKUP_NAME/configs/"
        fi
    done
    
    # Backup service configurations
    for service in "${SERVICES[@]}"; do
        if [ -d "$service/config" ]; then
            cp -r "$service/config" "$BACKUP_DIR/$BACKUP_NAME/configs/${service}_config"
        fi
    done
    
    echo "✅ Configuration backup complete"
}

# Function to create backup manifest
create_manifest() {
    echo "📝 Creating backup manifest..."
    
    cat > "$BACKUP_DIR/$BACKUP_NAME/manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
    "services": $(printf '%s\n' "${SERVICES[@]}" | jq -R . | jq -s .),
    "volumes": $(ls "$BACKUP_DIR/$BACKUP_NAME/volumes" | jq -R . | jq -s .),
    "databases": $(ls "$BACKUP_DIR/$BACKUP_NAME/databases" 2>/dev/null | jq -R . | jq -s .),
    "configs": $(ls "$BACKUP_DIR/$BACKUP_NAME/configs" | jq -R . | jq -s .),
    "encryption": "AES-256",
    "checksum": ""
}
EOF
    
    echo "✅ Manifest created"
}

# Function to encrypt backup
encrypt_backup() {
    echo "🔐 Encrypting backup..."
    
    cd "$BACKUP_DIR"
    tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME/"
    
    # Encrypt with OpenSSL
    openssl enc -aes-256-cbc \
        -salt \
        -in "${BACKUP_NAME}.tar.gz" \
        -out "${BACKUP_NAME}.tar.gz.enc" \
        -k "$ENCRYPTION_KEY"
    
    # Calculate checksum
    CHECKSUM=$(sha256sum "${BACKUP_NAME}.tar.gz.enc" | awk '{print $1}')
    
    # Update manifest with checksum
    jq ".checksum = \"$CHECKSUM\"" "$BACKUP_NAME/manifest.json" > "$BACKUP_NAME/manifest.tmp"
    mv "$BACKUP_NAME/manifest.tmp" "$BACKUP_NAME/manifest.json"
    
    # Clean up unencrypted files
    rm -rf "$BACKUP_NAME" "${BACKUP_NAME}.tar.gz"
    
    echo "✅ Backup encrypted"
}

# Function to upload to S3
upload_to_s3() {
    if [ "$ENABLE_S3_BACKUP" != "true" ]; then
        return
    fi
    
    echo "☁️ Uploading to S3..."
    
    aws s3 cp \
        "$BACKUP_DIR/${BACKUP_NAME}.tar.gz.enc" \
        "s3://$S3_BUCKET/backups/${BACKUP_NAME}.tar.gz.enc" \
        --storage-class STANDARD_IA
    
    # Store encryption key in AWS Secrets Manager
    aws secretsmanager create-secret \
        --name "mcp-backup-key-${TIMESTAMP}" \
        --secret-string "$ENCRYPTION_KEY" \
        --description "Encryption key for MCP backup ${TIMESTAMP}" \
        || true
    
    echo "✅ Backup uploaded to S3"
}

# Function to clean old backups
cleanup_old_backups() {
    echo "🧹 Cleaning old backups..."
    
    # Clean local backups
    find "$BACKUP_DIR" -name "mcp_backup_*.tar.gz.enc" -mtime +$RETENTION_DAYS -delete
    
    # Clean S3 backups if enabled
    if [ "$ENABLE_S3_BACKUP" = "true" ]; then
        aws s3 ls "s3://$S3_BUCKET/backups/" | \
        while read -r line; do
            createDate=$(echo $line | awk '{print $1" "$2}')
            createDate=$(date -d "$createDate" +%s)
            olderThan=$(date -d "$RETENTION_DAYS days ago" +%s)
            if [[ $createDate -lt $olderThan ]]; then
                fileName=$(echo $line | awk '{print $4}')
                if [[ $fileName == mcp_backup_* ]]; then
                    aws s3 rm "s3://$S3_BUCKET/backups/$fileName"
                fi
            fi
        done
    fi
    
    echo "✅ Cleanup complete"
}

# Function to restore from backup
restore_backup() {
    local backup_file=$1
    local restore_dir="/tmp/mcp_restore_$$"
    
    echo "🔄 Restoring from backup: $backup_file"
    
    # Decrypt backup
    echo "🔓 Decrypting backup..."
    read -sp "Enter encryption key: " DECRYPT_KEY
    echo
    
    openssl enc -aes-256-cbc -d \
        -in "$backup_file" \
        -out "/tmp/restore.tar.gz" \
        -k "$DECRYPT_KEY"
    
    # Extract backup
    mkdir -p "$restore_dir"
    tar xzf "/tmp/restore.tar.gz" -C "$restore_dir"
    
    # Find backup directory
    backup_dir=$(find "$restore_dir" -name "mcp_backup_*" -type d | head -1)
    
    if [ ! -d "$backup_dir" ]; then
        echo "❌ Invalid backup file"
        exit 1
    fi
    
    # Show manifest
    echo "📋 Backup manifest:"
    jq . "$backup_dir/manifest.json"
    
    # Confirm restore
    read -p "⚠️  This will OVERWRITE current data. Continue? (yes/NO): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "❌ Restore cancelled"
        exit 1
    fi
    
    # Stop services
    echo "🛑 Stopping services..."
    docker-compose down
    
    # Restore volumes
    echo "📦 Restoring volumes..."
    for volume_backup in "$backup_dir/volumes"/*.tar.gz; do
        volume_name=$(basename "$volume_backup" .tar.gz)
        echo "  📁 Restoring volume: $volume_name"
        
        # Remove existing volume
        docker volume rm "$volume_name" 2>/dev/null || true
        docker volume create "$volume_name"
        
        # Restore data
        docker run --rm \
            -v "$volume_name:/data" \
            -v "$volume_backup:/backup.tar.gz:ro" \
            alpine tar xzf /backup.tar.gz -C /data
    done
    
    # Restore databases
    echo "💾 Restoring databases..."
    
    # Start database services
    docker-compose up -d neo4j redis
    sleep 10  # Wait for services to start
    
    # Restore Neo4j
    if [ -f "$backup_dir/databases/neo4j_"*.dump ]; then
        echo "  📊 Restoring Neo4j..."
        neo4j_dump=$(ls "$backup_dir/databases/neo4j_"*.dump | head -1)
        docker cp "$neo4j_dump" mcp_neo4j:/backup/
        docker exec mcp_neo4j neo4j-admin database load neo4j \
            --from-path="/backup/$(basename $neo4j_dump)"
    fi
    
    # Restore Redis
    if [ -f "$backup_dir/databases/redis_"*.rdb ]; then
        echo "  🗄️ Restoring Redis..."
        redis_dump=$(ls "$backup_dir/databases/redis_"*.rdb | head -1)
        docker cp "$redis_dump" mcp_redis:/data/dump.rdb
        docker restart mcp_redis
    fi
    
    # Restore configurations
    echo "⚙️ Restoring configurations..."
    if [ -d "$backup_dir/configs" ]; then
        # Backup current configs
        mkdir -p "/tmp/config_backup_$$"
        cp -r /etc/mcp "/tmp/config_backup_$$/" 2>/dev/null || true
        
        # Restore configs
        cp -r "$backup_dir/configs"/* . 2>/dev/null || true
    fi
    
    # Start all services
    echo "🚀 Starting all services..."
    docker-compose up -d
    
    # Cleanup
    rm -rf "$restore_dir" "/tmp/restore.tar.gz"
    
    echo "✅ Restore complete!"
    echo "📝 Previous configs backed up to: /tmp/config_backup_$$"
}

# Function to verify backup
verify_backup() {
    local backup_file=$1
    
    echo "🔍 Verifying backup: $backup_file"
    
    # Check file exists
    if [ ! -f "$backup_file" ]; then
        echo "❌ Backup file not found"
        return 1
    fi
    
    # Verify checksum
    actual_checksum=$(sha256sum "$backup_file" | awk '{print $1}')
    
    # Decrypt to check manifest
    read -sp "Enter encryption key: " VERIFY_KEY
    echo
    
    # Extract just the manifest
    openssl enc -aes-256-cbc -d \
        -in "$backup_file" \
        -out "/tmp/verify.tar.gz" \
        -k "$VERIFY_KEY" 2>/dev/null
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to decrypt backup"
        return 1
    fi
    
    # Extract manifest
    tar -xzf "/tmp/verify.tar.gz" -O "*/manifest.json" 2>/dev/null > /tmp/manifest.json
    
    if [ ! -s /tmp/manifest.json ]; then
        echo "❌ Invalid backup structure"
        rm -f /tmp/verify.tar.gz /tmp/manifest.json
        return 1
    fi
    
    expected_checksum=$(jq -r .checksum /tmp/manifest.json)
    
    if [ "$actual_checksum" = "$expected_checksum" ]; then
        echo "✅ Backup verified successfully"
        jq . /tmp/manifest.json
    else
        echo "❌ Checksum mismatch!"
        echo "Expected: $expected_checksum"
        echo "Actual: $actual_checksum"
    fi
    
    rm -f /tmp/verify.tar.gz /tmp/manifest.json
}

# Main script logic
case "${1:-backup}" in
    backup)
        check_prerequisites
        mkdir -p "$BACKUP_DIR"
        
        echo "🚀 Starting backup process..."
        backup_volumes
        backup_databases
        backup_configs
        create_manifest
        encrypt_backup
        upload_to_s3
        cleanup_old_backups
        
        echo ""
        echo "✅ Backup complete!"
        echo "📁 Backup saved to: $BACKUP_DIR/${BACKUP_NAME}.tar.gz.enc"
        echo "🔑 Encryption key: $ENCRYPTION_KEY"
        echo ""
        echo "⚠️  IMPORTANT: Store the encryption key securely!"
        ;;
        
    restore)
        if [ -z "$2" ]; then
            echo "Usage: $0 restore <backup_file>"
            exit 1
        fi
        restore_backup "$2"
        ;;
        
    verify)
        if [ -z "$2" ]; then
            echo "Usage: $0 verify <backup_file>"
            exit 1
        fi
        verify_backup "$2"
        ;;
        
    list)
        echo "📋 Available backups:"
        echo ""
        echo "Local backups:"
        ls -lh "$BACKUP_DIR"/mcp_backup_*.tar.gz.enc 2>/dev/null || echo "  No local backups found"
        
        if [ "$ENABLE_S3_BACKUP" = "true" ]; then
            echo ""
            echo "S3 backups:"
            aws s3 ls "s3://$S3_BUCKET/backups/" | grep mcp_backup_ || echo "  No S3 backups found"
        fi
        ;;
        
    schedule)
        echo "📅 Setting up automated backups..."
        
        # Create cron job
        SCRIPT_PATH=$(realpath "$0")
        CRON_SCHEDULE=${BACKUP_SCHEDULE:-"0 2 * * *"}
        
        # Add to crontab
        (crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_SCHEDULE $SCRIPT_PATH backup >> /var/log/mcp_backup.log 2>&1") | crontab -
        
        echo "✅ Automated backups scheduled: $CRON_SCHEDULE"
        echo "📝 Logs will be saved to: /var/log/mcp_backup.log"
        ;;
        
    *)
        echo "Usage: $0 {backup|restore|verify|list|schedule}"
        echo ""
        echo "Commands:"
        echo "  backup              Create a new backup"
        echo "  restore <file>      Restore from backup file"
        echo "  verify <file>       Verify backup integrity"
        echo "  list               List available backups"
        echo "  schedule           Set up automated backups"
        exit 1
        ;;
esac