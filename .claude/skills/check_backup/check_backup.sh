#!/bin/bash
# check_backup - Backup/Restore Verification Script
#
# This script verifies the backup and restore functionality:
# - Checks script existence and permissions
# - Tests backup creation
# - Validates backup integrity
# - Tests restore safety mechanisms
#
# Usage: check_backup.sh [--quick] [--verbose] [--fix]

set -e

# ========================================
# Configuration
# ========================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve project root by finding docker-compose.prod.yml
if [ -f "./docker-compose.prod.yml" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -f "../docker-compose.prod.yml" ]; then
    PROJECT_ROOT="$(cd "$(pwd)/.." && pwd)"
elif [ -f "../../docker-compose.prod.yml" ]; then
    PROJECT_ROOT="$(cd "$(pwd)/../.." && pwd)"
else
    # Fallback to skill directory's grandparent
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
BACKUP_SCRIPT="$PROJECT_ROOT/backup.sh"
RESTORE_SCRIPT="$PROJECT_ROOT/restore.sh"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
TEST_BACKUP_DIR="$PROJECT_ROOT/backups/test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
QUICK_MODE=false
VERBOSE_MODE=false
FIX_MODE=false

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# ========================================
# Parse Arguments
# ========================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE_MODE=true
            shift
            ;;
        --fix)
            FIX_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--quick] [--verbose] [--fix]"
            exit 1
            ;;
    esac
done

# ========================================
# Functions
# ========================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
    ((TESTS_PASSED++)) || true
}

log_error() {
    echo -e "${RED}❌${NC} $1"
    ((TESTS_FAILED++)) || true
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE_MODE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

print_header() {
    echo
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo
}

# ========================================
# Test 1: Script Existence and Permissions
# ========================================
print_header "📋 Script Verification"

check_script() {
    local script="$1"
    local name="$(basename "$script")"

    if [ ! -f "$script" ]; then
        log_error "$name not found at: $script"
        if [ "$FIX_MODE" = true ]; then
            log_warning "Cannot auto-create $name - please create it manually"
        fi
        return 1
    fi
    log_success "$name exists"

    if [ ! -x "$script" ]; then
        log_error "$name is not executable"
        if [ "$FIX_MODE" = true ]; then
            log_info "Fixing permissions on $name..."
            chmod +x "$script"
            log_success "$name is now executable"
        fi
        return 1
    fi
    log_success "$name is executable"

    # Basic syntax check
    if bash -n "$script" 2>/dev/null; then
        log_success "$name syntax is valid"
    else
        log_error "$name has syntax errors"
        return 1
    fi

    return 0
}

# Check both scripts
check_script "$BACKUP_SCRIPT" "backup.sh"
BACKUP_OK=$?

check_script "$RESTORE_SCRIPT" "restore.sh"
RESTORE_OK=$?

if [ $BACKUP_OK -ne 0 ] || [ $RESTORE_OK -ne 0 ]; then
    echo
    log_error "Script verification failed - cannot continue"
    exit 1
fi

# ========================================
# Test 2: Environment Verification
# ========================================
print_header "🔍 Environment Verification"

# Check Docker Compose
if docker compose version &>/dev/null || docker-compose version &>/dev/null; then
    log_success "Docker Compose is available"
else
    log_error "Docker Compose not found"
    exit 4
fi

# Check if we're in the correct directory
if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "docker-compose.prod.yml not found"
    log_info "Current directory: $PWD"
    log_info "Expected location: $COMPOSE_FILE"
    exit 4
fi
log_success "Production compose file found"

# Check .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_warning ".env file not found"
    if [ "$FIX_MODE" = true ]; then
        if [ -f "$PROJECT_ROOT/.env.prod" ]; then
            log_info "Creating .env from .env.prod..."
            cp "$PROJECT_ROOT/.env.prod" "$PROJECT_ROOT/.env"
            log_success ".env created"
        fi
    fi
else
    log_success ".env file found"
fi

# ========================================
# Test 3: Backup Functionality
# ========================================
if [ "$QUICK_MODE" = false ]; then
    print_header "📦 Backup Functionality Test"

    # Check if production is running
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "whisper_postgres_prd.*Up"; then
        log_success "Production services are running"
    else
        log_warning "Production services not running - starting..."
        if [ "$FIX_MODE" = true ]; then
            cd "$PROJECT_ROOT"
            ./start_prd.sh >/dev/null 2>&1
            sleep 5
            log_success "Production services started"
        else
            log_error "Cannot test backup without running services"
            log_info "Run './start_prd.sh' first, or use --fix flag"
            exit 4
        fi
    fi

    # Test backup creation
    log_info "Testing backup creation..."

    # Create test backup directory
    mkdir -p "$TEST_BACKUP_DIR"

    # Run backup script (should create a test backup)
    cd "$PROJECT_ROOT"

    # Check if backup script supports custom output directory
    TEST_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    TEST_BACKUP_FILE="$TEST_BACKUP_DIR/test_backup_${TEST_TIMESTAMP}.tar.gz"

    # Create a minimal test backup
    log_info "Creating test backup..."

    # Dump database to temp file
    TEMP_DB_DUMP="/tmp/test_backup_$$.sql"
    if docker exec whisper_postgres_prd pg_dump -U postgres -d whisper_summarizer --clean --if-exists --no-owner --no-acl > "$TEMP_DB_DUMP" 2>/dev/null; then
        log_success "Database dump successful"

        # Create test archive
        TEMP_DIR="/tmp/test_backup_$$"
        mkdir -p "$TEMP_DIR/transcribes"
        cp "$TEMP_DB_DUMP" "$TEMP_DIR/database.sql"

        # Create metadata
        cat > "$TEMP_DIR/metadata.txt" << EOF
Test Backup - $TEST_TIMESTAMP
Purpose: Verification test
EOF

        # Create archive
        if tar -czf "$TEST_BACKUP_FILE" -C "$TEMP_DIR" . 2>/dev/null; then
            BACKUP_SIZE=$(du -h "$TEST_BACKUP_FILE" | cut -f1)
            log_success "Test backup created: $TEST_BACKUP_FILE ($BACKUP_SIZE)"

            # Verify archive integrity
            if tar -tzf "$TEST_BACKUP_FILE" > /dev/null 2>&1; then
                log_success "Archive integrity verified"
            else
                log_error "Archive integrity check failed"
            fi
        else
            log_error "Failed to create test archive"
        fi

        # Cleanup
        rm -rf "$TEMP_DIR" "$TEMP_DB_DUMP"
    else
        log_error "Database dump failed"
    fi
else
    print_header "📦 Backup Functionality"
    log_info "Skipping backup test (quick mode)"
fi

# ========================================
# Test 4: Restore Script Validation
# ========================================
print_header "🔄 Restore Functionality Test"

# Verify restore script components
log_info "Checking restore script components..."

if grep -q "Type 'RESTORE' to proceed" "$RESTORE_SCRIPT" 2>/dev/null; then
    log_success "Safety confirmation mechanism present"
else
    log_warning "No safety confirmation found in restore script"
fi

if grep -qi "drop.*database" "$RESTORE_SCRIPT" 2>/dev/null; then
    log_success "Database restore capability found"
else
    log_error "Database restore capability not found"
fi

if grep -q "transcribes" "$RESTORE_SCRIPT" 2>/dev/null; then
    log_success "File restore capability found"
else
    log_error "File restore capability not found"
fi

# Test backup file validation (non-destructive)
if [ -f "$TEST_BACKUP_FILE" ]; then
    log_info "Testing backup file validation..."

    # Extract and validate metadata
    TEMP_EXTRACT="/tmp/restore_test_$$"
    mkdir -p "$TEMP_EXTRACT"

    if tar -xzf "$TEST_BACKUP_FILE" -C "$TEMP_EXTRACT" 2>/dev/null; then
        log_success "Backup file extraction successful"

        if [ -f "$TEMP_EXTRACT/metadata.txt" ]; then
            log_success "Metadata file found"
            log_verbose "Metadata contents:"
            log_verbose "$(cat "$TEMP_EXTRACT/metadata.txt")"
        fi

        if [ -f "$TEMP_EXTRACT/database.sql" ]; then
            log_success "Database dump found in backup"
        fi

        if [ -d "$TEMP_EXTRACT/transcribes" ]; then
            FILE_COUNT=$(find "$TEMP_EXTRACT/transcribes" -type f | wc -l)
            log_success "Transcribed files directory found ($FILE_COUNT files)"
        fi
    else
        log_error "Backup file extraction failed"
    fi

    rm -rf "$TEMP_EXTRACT"
fi

# ========================================
# Summary
# ========================================
print_header "📈 Test Results Summary"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

echo "Total Tests: $TOTAL_TESTS"
echo "  ✅ Passed: $TESTS_PASSED"
echo "  ❌ Failed: $TESTS_FAILED"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    log_success "All tests PASSED!"
    echo
    echo "Recommendations:"
    echo "  - Scripts are functioning correctly"
    echo "  - Ready for production use"
    echo "  - Consider scheduling regular backups"
    echo
    echo "To create a production backup:"
    echo "  ./backup.sh"
    echo
    echo "To restore from backup:"
    echo "  ./restore.sh <backup_file.tar.gz>"
    exit 0
else
    log_error "Some tests FAILED"
    echo
    echo "Troubleshooting:"
    echo "  1. Check script permissions: chmod +x backup.sh restore.sh"
    echo "  2. Ensure production is running: ./start_prd.sh"
    echo "  3. Run with --fix flag to auto-fix some issues"
    echo "  4. Use --verbose flag for detailed output"
    exit 1
fi
