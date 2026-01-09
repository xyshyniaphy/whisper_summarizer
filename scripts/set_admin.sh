#!/bin/bash
# set_admin.sh
#
# Promote a user to admin and activate their account.
# Usage: ./scripts/set_admin.sh <user_email>
#
# Supports both development and production environments.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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
echo " Set User as Admin"
echo "========================================"
echo

USER_EMAIL=$1

if [ -z "$USER_EMAIL" ]; then
  log_error "Email parameter is required"
  echo ""
  echo "Usage: $0 <user_email>"
  echo ""
  echo "Example:"
  echo "  ./scripts/set_admin.sh admin@example.com"
  echo ""
  exit 1
fi

# Validate email format
if [[ ! "$USER_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
  log_error "Invalid email format: $USER_EMAIL"
  exit 1
fi

log_info "Setting user ($USER_EMAIL) as admin..."
echo

# Load environment
if [ -f ".env" ]; then
  export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
  log_info "Loaded environment from .env"
else
  log_warning ".env file not found, using system environment"
fi

# Function to run SQL in PostgreSQL
run_sql() {
  local sql="$1"

  # Try development database first
  if docker ps | grep -q "whisper_postgres_dev"; then
    docker exec -i whisper_postgres_dev psql -U postgres -d whisper_summarizer -t <<SQL
$sql
SQL
  elif docker ps | grep -q "whisper_postgres_prd"; then
    docker exec -i whisper_postgres_prd psql -U postgres -d whisper_summarizer -t <<SQL
$sql
SQL
  else
    # Production mode - use DATABASE_URL
    if [ -z "$DATABASE_URL" ]; then
      log_error "DATABASE_URL not set and no local PostgreSQL container found"
      echo ""
      echo "Please ensure:"
      echo "  1. Development/production environment is running, OR"
      echo "  2. DATABASE_URL environment variable is set"
      exit 1
    fi
    psql "$DATABASE_URL" -t -c "$sql"
  fi
}

# Check if user exists (including soft-deleted users)
log_info "Checking if user exists..."
USER_DATA=$(run_sql "SELECT email, is_admin, is_active, deleted_at IS NOT NULL as deleted FROM users WHERE email = '${USER_EMAIL}';" 2>/dev/null | tr -d ' ' || echo "")

if [ -z "$USER_DATA" ]; then
  log_error "User with email '${USER_EMAIL}' not found in database"
  echo ""
  echo "Hint: The user must exist in Supabase auth first."
  echo "      Have they logged in via Google OAuth at least once?"
  exit 1
fi

# Parse user data
IS_ADMIN=$(echo "$USER_DATA" | awk -F'|' '{print $2}')
IS_ACTIVE=$(echo "$USER_DATA" | awk -F'|' '{print $3}')
IS_DELETED=$(echo "$USER_DATA" | awk -F'|' '{print $4}')

# Check if user is soft deleted
if [ "$IS_DELETED" = "t" ]; then
  log_warning "User was soft deleted (deleted_at is set)"
  echo ""
  read -p "Restore this user and make them admin? (yes/no): " CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    log_info "Operation cancelled"
    exit 0
  fi
  log_info "Restoring soft-deleted user..."
fi

# Check if already admin
if [ "$IS_ADMIN" = "t" ]; then
  log_warning "User is already an admin"
  echo ""
  echo "Current user status:"
  run_sql "SELECT email, is_admin, is_active, activated_at FROM users WHERE email = '${USER_EMAIL}';" 2>/dev/null
  echo ""
  read -p "Re-activate and update admin status anyway? (yes/no): " CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    log_info "No changes made"
    exit 0
  fi
fi

# Update user to be admin and active
log_info "Updating user to admin and activating account..."

run_sql "
UPDATE users
SET
  is_admin = TRUE,
  is_active = TRUE,
  activated_at = CASE WHEN activated_at IS NULL THEN NOW() ELSE activated_at END,
  deleted_at = NULL
WHERE email = '${USER_EMAIL}';
" 2>/dev/null

# Verify the update
log_info "Verifying update..."
RESULT=$(run_sql "SELECT email, is_admin, is_active, activated_at FROM users WHERE email = '${USER_EMAIL}';" 2>/dev/null)

echo ""
echo "========================================"
log_success "User ${USER_EMAIL} is now admin and activated"
echo "========================================"
echo ""
echo "Current user status:"
echo "$RESULT" | while read line; do
  if [ -n "$line" ]; then
    email=$(echo "$line" | awk -F'|' '{print $1}' | tr -d ' ')
    is_admin=$(echo "$line" | awk -F'|' '{print $2}' | tr -d ' ')
    is_active=$(echo "$line" | awk -F'|' '{print $3}' | tr -d ' ')
    activated_at=$(echo "$line" | awk -F'|' '{print $4}' | tr -d ' ')
    echo "  Email:        ${email}"
    echo "  Is Admin:     ${is_admin}"
    echo "  Is Active:    ${is_active}"
    echo "  Activated At: ${activated_at}"
  fi
done
echo ""
echo "========================================"
