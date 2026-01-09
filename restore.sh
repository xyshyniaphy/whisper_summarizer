#!/bin/bash
# Production Restore Script for Whisper Summarizer
#
# This script restores production data from a backup archive:
# - PostgreSQL database (all tables: users, transcriptions, channels, etc.)
# - Transcribed text files (gzip compressed)
#
# ⚠️  WARNING: This will OVERWRITE all existing production data!
#
# Usage: ./restore.sh <backup_file.tar.gz>
#
# Example: ./restore.sh backups/whisper_prd_backup_20260109_120000.tar.gz

set -e

# ========================================
# Configuration
# ========================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEMP_DIR="/tmp/whisper_restore_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# Functions
# ========================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo "========================================"
echo " Whisper Summarizer - Production Restore"
echo "========================================"
echo

# Check arguments
if [ $# -ne 1 ]; then
    log_error "Usage: $0 <backup_file.tar.gz>"
    echo
    echo "Example: $0 backups/whisper_prd_backup_20260109_120000.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check if backup file is valid
log_info "Validating backup file..."
if ! tar -tzf "$BACKUP_FILE" > /dev/null 2>&1; then
    log_error "Backup file is corrupted or not a valid tar.gz archive"
    exit 1
fi

# Show backup info
log_info "Backup file: $BACKUP_FILE"
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_info "Size: $BACKUP_SIZE"

# Extract metadata if available
log_info "Reading backup metadata..."
TEMP_METADATA="/tmp/whisper_restore_metadata_${TIMESTAMP}"
mkdir -p "$TEMP_METADATA"
tar -xzf "$BACKUP_FILE" -C "$TEMP_METADATA" metadata.txt 2>/dev/null || true

if [ -f "$TEMP_METADATA/metadata.txt" ]; then
    echo
    echo "========================================"
    echo " Backup Information"
    echo "========================================"
    cat "$TEMP_METADATA/metadata.txt"
    echo "========================================"
    echo
fi

rm -rf "$TEMP_METADATA"

# ========================================
# Safety Confirmation
# ========================================
log_warning "⚠️  WARNING: This will OVERWRITE all existing production data!"
echo
echo "This action will:"
echo "  - Drop and recreate the PostgreSQL database"
echo "  - Replace all transcribed text files"
echo "  - All existing data will be LOST"
echo
echo "Backup to restore: $BACKUP_FILE"
echo

# Double confirmation
read -p "Type 'RESTORE' to proceed: " confirmation
if [ "$confirmation" != "RESTORE" ]; then
    log_warning "Restore cancelled by user"
    exit 0
fi

read -p "Are you REALLY sure? This cannot be undone! (yes/no): " final_confirmation
if [ "$final_confirmation" != "yes" ]; then
    log_warning "Restore cancelled by user"
    exit 0
fi

echo

# ========================================
# Setup Docker Compose Command
# ========================================
DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

# ========================================
# Step 1: Stop Production Services
# ========================================
log_info "Step 1/6: Stopping production services..."

# Check if services are running
if $DOCKER_COMPOSE -f "$SCRIPT_DIR/docker-compose.prod.yml" ps | grep -q "Up"; then
    log_info "Stopping production services..."
    $DOCKER_COMPOSE -f "$SCRIPT_DIR/docker-compose.prod.yml" down
    log_success "Production services stopped"
else
    log_warning "Production services were not running"
fi

# Wait for containers to stop
sleep 3

# ========================================
# Step 2: Extract Backup Archive
# ========================================
log_info "Step 2/6: Extracting backup archive..."

mkdir -p "$TEMP_DIR"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

if [ $? -ne 0 ]; then
    log_error "Failed to extract backup archive"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log_success "Backup extracted to: $TEMP_DIR"

# Verify expected files exist
if [ ! -f "$TEMP_DIR/database.sql" ]; then
    log_error "Backup does not contain database.sql"
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -d "$TEMP_DIR/transcribes" ]; then
    log_error "Backup does not contain transcribes directory"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# ========================================
# Step 3: Get Database Credentials
# ========================================
log_info "Step 3/6: Reading database credentials..."

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    log_error ".env file not found"
    rm -rf "$TEMP_DIR"
    exit 1
fi

source "$SCRIPT_DIR/.env"

DB_NAME="${POSTGRES_DB:-whisper_summarizer}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

if [ -z "$DB_PASSWORD" ]; then
    log_error "POSTGRES_PASSWORD not set in .env"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log_success "Database: $DB_NAME"

# ========================================
# Step 4: Restore PostgreSQL Database
# ========================================
log_info "Step 4/6: Restoring PostgreSQL database..."

# Start only PostgreSQL container
log_info "Starting PostgreSQL container..."
$DOCKER_COMPOSE -f "$SCRIPT_DIR/docker-compose.prod.yml" up -d postgres

# Wait for PostgreSQL to be ready
log_info "Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker exec whisper_postgres_prd pg_isready -U "$DB_USER" -d "$DB_NAME" &> /dev/null; then
        log_success "PostgreSQL is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    log_error "PostgreSQL failed to start"
    $DOCKER_COMPOSE -f "$SCRIPT_DIR/docker-compose.prod.yml" logs postgres
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Drop existing database and recreate
log_info "Dropping existing database..."
docker exec whisper_postgres_prd psql \
    -U "$DB_USER" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS $DB_NAME;" \
    > /dev/null 2>&1 || true

log_info "Creating fresh database..."
docker exec whisper_postgres_prd psql \
    -U "$DB_USER" \
    -d postgres \
    -c "CREATE DATABASE $DB_NAME;" \
    > /dev/null 2>&1

# Restore database from dump
log_info "Restoring database from dump..."
cat "$TEMP_DIR/database.sql" | docker exec -i whisper_postgres_prd psql \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    > /dev/null 2>&1

if [ $? -ne 0 ]; then
    log_error "Database restore failed"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log_success "Database restored successfully"

# Verify tables were restored
TABLE_COUNT=$(docker exec whisper_postgres_prd psql \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t \
    -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" \
    2>/dev/null | tr -d ' ')

log_info "Restored $TABLE_COUNT tables"

# ========================================
# Step 5: Restore Transcribed Text Files
# ========================================
log_info "Step 5/6: Restoring transcribed text files..."

TRANSCRIBES_DIR="$SCRIPT_DIR/data/transcribes"

# Clear existing transcribed files
if [ -d "$TRANSCRIBES_DIR" ]; then
    log_info "Clearing existing transcribed files..."
    rm -rf "${TRANSCRIBES_DIR:?}"/*
fi

# Copy restored files
if [ -d "$TEMP_DIR/transcribes" ]; then
    FILE_COUNT=$(find "$TEMP_DIR/transcribes" -type f | wc -l)

    if [ $FILE_COUNT -gt 0 ]; then
        mkdir -p "$TRANSCRIBES_DIR"
        cp -r "$TEMP_DIR/transcribes"/* "$TRANSCRIBES_DIR/"
        chmod 644 "$TRANSCRIBES_DIR"/*
        log_success "Restored $FILE_COUNT transcribed files"
    else
        log_warning "No transcribed files in backup"
    fi
else
    log_warning "Transcribes directory not found in backup"
fi

# ========================================
# Step 6: Start All Production Services
# ========================================
log_info "Step 6/6: Starting all production services..."

$DOCKER_COMPOSE -f "$SCRIPT_DIR/docker-compose.prod.yml" up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
echo

# Wait for API server
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -sf http://localhost:3080/health &> /dev/null; then
        log_success "API server is ready"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    log_warning "API server health check failed, but services are starting"
fi

echo
log_success "All production services started"

# Cleanup
rm -rf "$TEMP_DIR"

# ========================================
# Verification Summary
# ========================================
log_info "Running verification checks..."
echo

# Check database
echo "========================================"
echo " Database Verification"
echo "========================================"

docker exec whisper_postgres_prd psql \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -c "SELECT
        schemaname,
        tablename,
        n_live_tup as row_count
    FROM pg_stat_user_tables
    ORDER BY schemaname, tablename;" \
    2>/dev/null || echo "Could not retrieve table counts"

echo
echo "========================================"
echo " File Count Verification"
echo "========================================"

TRANSCRIBES_COUNT=$(find "$TRANSCRIBES_DIR" -type f 2>/dev/null | wc -l)
echo "Transcribed files: $TRANSCRIBES_COUNT"

echo

# ========================================
# Final Summary
# ========================================
echo "========================================"
echo " Restore Complete"
echo "========================================"
echo
echo "Restored from: $BACKUP_FILE"
echo "Completed at: $(date)"
echo
echo "Services Status:"
echo "  ✅ PostgreSQL restored"
echo "  ✅ Transcribed files restored"
echo "  ✅ All services started"
echo
echo "Access the application at:"
echo "  🌐 http://localhost:3080"
echo
echo "To view logs:"
echo "  $DOCKER_COMPOSE -f docker-compose.prod.yml logs -f"
echo
log_success "Restore completed successfully!"
