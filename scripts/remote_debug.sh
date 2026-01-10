#!/bin/bash
# ========================================
# Remote Debugging Helper Script
# ========================================
# This script provides convenient commands for debugging
# the production server via SSH + docker exec.
#
# Usage:
#   ./scripts/remote_debug.sh <command> [args...]
#
# Commands:
#   transcriptions    - List all transcriptions
#   upload <file>     - Upload audio file
#   chat <id> <msg>   - Test chat streaming
#   status            - Show server status
#   session           - Show session.json content
#   shell             - Open shell in container
#
# Example:
#   ./scripts/remote_debug.sh transcriptions
#   ./scripts/remote_debug.sh upload test_audio.m4a
#   ./scripts/remote_debug.sh chat <uuid> "总结内容"

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER="${REMOTE_DEBUG_SERVER:-root@192.3.249.169}"
CONTAINER="${REMOTE_DEBUG_CONTAINER:-whisper_server_prd}"
API_BASE="http://localhost:8000"

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Execute curl in remote container
remote_curl() {
    local method=${1:-GET}
    local endpoint=$2
    local data=${3:-}
    local extra_args=${4:-}

    ssh "$SERVER" "docker exec $CONTAINER curl -s -X $method $extra_args $API_BASE$endpoint $data"
}

# Main commands
cmd_transcriptions() {
    log_info "Fetching transcriptions from production server..."
    remote_curl GET "/api/transcriptions" | jq .
}

cmd_upload() {
    local file=$1

    if [ -z "$file" ]; then
        log_error "Usage: $0 upload <file>"
        exit 1
    fi

    if [ ! -f "$file" ]; then
        log_error "File not found: $file"
        exit 1
    fi

    local filename=$(basename "$file")

    log_info "Copying file to remote container: $filename"
    scp "$file" "$SERVER:/tmp/$filename"

    log_info "Uploading to production server..."
    ssh "$SERVER" "docker exec $CONTAINER curl -s -X POST $API_BASE/api/audio/upload -F file=@/tmp/$filename" | jq .
}

cmd_chat() {
    local trans_id=$1
    local message=${2:-"总结内容"}

    if [ -z "$trans_id" ]; then
        log_error "Usage: $0 chat <transcription_id> [message]"
        exit 1
    fi

    log_info "Testing chat stream for transcription: $trans_id"
    log_info "Message: $message"
    echo ""

    ssh "$SERVER" "docker exec $CONTAINER curl -N '$API_BASE/api/transcriptions/$trans_id/chat/stream?message=$(echo "$message" | jq -sRr @uri)'"
}

cmd_status() {
    log_info "Production server status:"
    echo ""

    ssh "$SERVER" "docker exec $CONTAINER curl -s $API_BASE/health" | jq .

    echo ""
    log_info "Container status:"
    ssh "$SERVER" "docker ps --filter 'name=$CONTAINER' --format 'table {{.Names}}\t{{.Status}}'"
}

cmd_session() {
    log_info "Session.json content:"
    echo ""

    ssh "$SERVER" "docker exec $CONTAINER cat /app/session.json 2>/dev/null || echo 'Session file not found'"
}

cmd_shell() {
    log_info "Opening shell in container..."
    ssh "$SERVER" "docker exec -it $CONTAINER /bin/bash"
}

cmd_logs() {
    local lines=${1:-50}
    log_info "Showing last $lines lines of server logs:"
    echo ""

    ssh "$SERVER" "docker logs --tail $lines $CONTAINER"
}

# Help message
show_help() {
    cat << EOF
Remote Debugging Helper for Production Server

Usage: $0 <command> [args...]

Commands:
  transcriptions        List all transcriptions
  upload <file>         Upload audio file to server
  chat <id> [msg]       Test chat streaming (default: "总结内容")
  status                Show server and container status
  session               Show session.json content
  shell                 Open interactive shell in container
  logs [lines]          Show server logs (default: 50 lines)
  help                  Show this help message

Examples:
  $0 transcriptions
  $0 upload test_audio.m4a
  $0 chat fc47855d-6973-4931-b6fd-bd28515bec0d "总结这段内容"
  $0 status
  $0 logs 100

Environment Variables:
  REMOTE_DEBUG_SERVER    SSH server (default: root@192.3.249.169)
  REMOTE_DEBUG_CONTAINER Container name (default: whisper_server_prd)

Configuration: Edit script to change defaults
EOF
}

# Main entry point
COMMAND=${1:-help}

case "$COMMAND" in
    transcriptions)
        cmd_transcriptions
        ;;
    upload)
        cmd_upload "$2"
        ;;
    chat)
        cmd_chat "$2" "$3"
        ;;
    status)
        cmd_status
        ;;
    session)
        cmd_session
        ;;
    shell)
        cmd_shell
        ;;
    logs)
        cmd_logs "${2:-50}"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        echo ""
        show_help
        exit 1
        ;;
esac
