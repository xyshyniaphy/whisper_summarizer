#!/bin/bash
# Production Backup Script for Whisper Summarizer
#
# This script creates a complete backup of production data:
# - PostgreSQL database (all tables: users, transcriptions, channels, etc.)
# - Transcribed text files (gzip compressed)
#
# The backup is created as a timestamped tar.gz archive
#
# Usage: ./backup.sh [output_directory]
#   output_directory: Optional, defaults to ./backups

set -e

# ========================================
# Configuration
# ========================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${1:-$SCRIPT_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="whisper_prd_backup_${TIMESTAMP}"
TEMP_DIR="/tmp/whisper_backup_${TIMESTAMP}"

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
echo " Whisper Summarizer - Production Backup"
echo "========================================"
echo

# Check if production is running
log_info "Checking if production services are running..."

DOCKER_COMPOSE="docker compose"
if ! docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
fi

# Check if postgres container exists and is running
if ! docker ps | grep -q "whisper_postgres_prd"; then
    log_error "Production PostgreSQL container is not running"
    echo
    echo "Please start production services first:"
    echo "  ./start_prd.sh"
    exit 1
fi

log_success "Production services are running"

# Create backup directory
log_info "Creating backup directory..."
mkdir -p "$BACKUP_DIR"
log_success "Backup directory: $BACKUP_DIR"

# Create temporary directory for backup files
log_info "Creating temporary directory..."
mkdir -p "$TEMP_DIR"

# Get database credentials from .env
log_info "Reading database credentials from .env..."
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
# Step 1: Dump PostgreSQL Database
# ========================================
log_info "Step 1/4: Dumping PostgreSQL database..."

DB_DUMP_FILE="$TEMP_DIR/database.sql"

docker exec whisper_postgres_prd pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    > "$DB_DUMP_FILE" 2>&1

if [ $? -ne 0 ]; then
    log_error "Database dump failed"
    rm -rf "$TEMP_DIR"
    exit 1
fi

DB_SIZE=$(du -h "$DB_DUMP_FILE" | cut -f1)
log_success "Database dump created: $DB_SIZE"

# ========================================
# Step 2: Copy Transcribed Text Files
# ========================================
log_info "Step 2/4: Copying transcribed text files..."

TRANSCRIBES_DIR="$SCRIPT_DIR/data/transcribes"
TRANSCRIBES_BACKUP_DIR="$TEMP_DIR/transcribes"

if [ -d "$TRANSCRIBES_DIR" ]; then
    # Count files
    FILE_COUNT=$(find "$TRANSCRIBES_DIR" -type f | wc -l)

    if [ $FILE_COUNT -gt 0 ]; then
        cp -r "$TRANSCRIBES_DIR" "$TRANSCRIBES_BACKUP_DIR"
        log_success "Copied $FILE_COUNT transcribed files"
    else
        log_warning "No transcribed files found to backup"
        mkdir -p "$TRANSCRIBES_BACKUP_DIR"
    fi
else
    log_warning "Transcribes directory not found, creating empty backup"
    mkdir -p "$TRANSCRIBES_BACKUP_DIR"
fi

# ========================================
# Step 3: Create Metadata File
# ========================================
log_info "Step 3/4: Creating backup metadata..."

METADATA_FILE="$TEMP_DIR/metadata.txt"

cat > "$METADATA_FILE" << EOF
Whisper Summarizer - Production Backup
=======================================
Backup Name: $BACKUP_NAME
Timestamp: $TIMESTAMP
Created: $(date)

Database Information:
- Database Name: $DB_NAME
- Database User: $DB_USER

Backup Contents:
- PostgreSQL database dump: database.sql
- Transcribed text files: transcribes/

Files Included:
EOF

# Add file count to metadata
if [ -d "$TRANSCRIBES_BACKUP_DIR" ]; then
    FILE_COUNT=$(find "$TRANSCRIBES_BACKUP_DIR" -type f | wc -l)
    echo "Transcribed Files: $FILE_COUNT" >> "$METADATA_FILE"
fi

log_success "Metadata file created"

# ========================================
# Step 4: Create Compressed Archive
# ========================================
log_info "Step 4/4: Creating compressed archive..."

ARCHIVE_FILE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"

tar -czf "$ARCHIVE_FILE" -C "$TEMP_DIR" .

if [ $? -ne 0 ]; then
    log_error "Failed to create archive"
    rm -rf "$TEMP_DIR"
    exit 1
fi

ARCHIVE_SIZE=$(du -h "$ARCHIVE_FILE" | cut -f1)

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

log_success "Archive created: $ARCHIVE_FILE ($ARCHIVE_SIZE)"

# ========================================
# Verification
# ========================================
log_info "Verifying backup integrity..."

if ! tar -tzf "$ARCHIVE_FILE" > /dev/null 2>&1; then
    log_error "Backup verification failed - archive is corrupted"
    exit 1
fi

log_success "Backup verification passed"

# ========================================
# Summary
# ========================================
echo
echo "========================================"
echo " Backup Complete"
echo "========================================"
echo
echo "Backup File: $ARCHIVE_FILE"
echo "Size: $ARCHIVE_SIZE"
echo "Timestamp: $TIMESTAMP"
echo
echo "Contents:"
echo "  - PostgreSQL database dump"
echo "  - Transcribed text files"
echo "  - Backup metadata"
echo
echo "To restore this backup:"
echo "  ./restore.sh $ARCHIVE_FILE"
echo
log_success "Backup completed successfully!"

# List recent backups
echo
log_info "Recent backups in $BACKUP_DIR:"
ls -lht "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -5 || echo "  No previous backups found"
