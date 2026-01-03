#!/bin/bash
#
# set_first_admin.sh
#
# Promote the first user to admin and activate their account.
# Usage: ./scripts/set_first_admin.sh <user_email>
#

set -e

USER_EMAIL=$1

if [ -z "$USER_EMAIL" ]; then
  echo "Usage: $0 <user_email>"
  echo ""
  echo "Example: ./scripts/set_first_admin.sh admin@example.com"
  exit 1
fi

echo "Setting user ($USER_EMAIL) as admin and activating account..."

# Load environment
if [ -f ".env" ]; then
  export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# Function to run SQL in PostgreSQL
run_sql() {
  local sql="$1"
  if docker ps | grep -q "whisper_postgres_dev"; then
    echo "Using development database..."
    docker exec -i whisper_postgres_dev psql -U postgres -d whisper_summarizer <<SQL
$sql
SQL
  else
    # Production mode - use DATABASE_URL
    if [ -z "$DATABASE_URL" ]; then
      echo "Error: DATABASE_URL not set and no local PostgreSQL found"
      exit 1
    fi
    echo "Using production database..."
    psql "$DATABASE_URL" -c "$sql"
  fi
}

# Check if user exists
USER_EXISTS=$(run_sql "SELECT COUNT(*) FROM users WHERE email = '${USER_EMAIL}' AND deleted_at IS NULL;" | awk 'NR==3 {print $1}')

if [ "$USER_EXISTS" -eq 0 ]; then
  echo "Error: User with email '${USER_EMAIL}' not found"
  exit 1
fi

# Update user to be admin and active
run_sql "
UPDATE users
SET
  is_admin = TRUE,
  is_active = TRUE,
  activated_at = NOW()
WHERE email = '${USER_EMAIL}'
AND deleted_at IS NULL;
"

# Verify the update
RESULT=$(run_sql "SELECT email, is_admin, is_active, activated_at FROM users WHERE email = '${USER_EMAIL}' AND deleted_at IS NULL;")

echo ""
echo "✓ User ${USER_EMAIL} is now admin and activated"
echo ""
echo "Current user status:"
echo "$RESULT"
