#!/bin/bash
# Audio Length Test Script
# Tests transcription system with audio files of varying lengths
# Following testdata/test_plan_audio_len.md specification

set -e

# Configuration
SERVER_URL="${SERVER_URL:-http://localhost:8000}"
API_KEY="${SUPABASE_SERVICE_ROLE_KEY:-sb_secret_tyVEUssAuqX_Ndte6R2GQg_z2kjnLvN}"
TEST_DIR="/home/lmr/ws/whisper_summarizer/testdata"
REPORT_DIR="/home/lmr/ws/whisper_summarizer/testdata/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Test files
declare -A TEST_FILES=(
    ["2_min"]="2_min.m4a"
    ["20_min"]="20_min.m4a"
    ["60_min"]="60_min.m4a"
    ["210_min"]="210_min.m4a"
)

# Create report directory
mkdir -p "$REPORT_DIR"

# Report file
REPORT_FILE="$REPORT_DIR/audio_length_test_${TIMESTAMP}.md"

# Helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$REPORT_FILE"
}

log_section() {
    echo "" | tee -a "$REPORT_FILE"
    echo "## $1" | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
}

upload_file() {
    local name=$1
    local filename=$2
    local filepath="$TEST_DIR/$filename"

    log "Uploading $name ($filename)..."

    # Get file size
    local filesize=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath")

    # Upload file
    local response=$(curl -s -X POST "${SERVER_URL}/api/audio/upload" \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@${filepath}" \
        -w "\n%{http_code}")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')

    if [ "$http_code" != "201" ]; then
        log "❌ Upload failed: HTTP $http_code"
        log "Response: $body"
        return 1
    fi

    local id=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null || echo "")

    if [ -z "$id" ]; then
        log "❌ Failed to extract transcription ID"
        return 1
    fi

    log "✅ Upload successful: ID=$id, Size=$filesize bytes"
    echo "$id"
}

poll_status() {
    local id=$1
    local max_wait=${2:-7200}  # Default 2 hours
    local start_time=$(date +%s)

    log "Polling status for transcription $id..."

    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -gt $max_wait ]; then
            log "❌ Timeout waiting for completion (${max_wait}s)"
            return 1
        fi

        local response=$(curl -s "${SERVER_URL}/api/transcriptions/${id}" \
            -H "Authorization: Bearer ${API_KEY}")

        local status=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")

        case "$status" in
            "completed")
                log "✅ Status: completed (elapsed: ${elapsed}s)"
                return 0
                ;;
            "failed")
                log "❌ Status: failed"
                log "Response: $response"
                return 1
                ;;
            "pending"|"processing")
                log "⏳ Status: $status (${elapsed}s elapsed)..."
                sleep 10
                ;;
            *)
                log "⚠️  Unknown status: $status"
                sleep 10
                ;;
        esac
    done
}

verify_storage() {
    local id=$1

    log "Verifying storage files for $id..."

    local storage_files=(
        "${id}.txt.gz"
        "${id}.segments.json.gz"
        "${id}.original.json.gz"
        "${id}.formatted.txt.gz"
    )

    local all_exist=true

    for file in "${storage_files[@]}"; do
        if docker exec whisper_server_dev test -f "/app/data/transcribes/$file"; then
            local size=$(docker exec whisper_server_dev stat -c%s "/app/data/transcribes/$file" 2>/dev/null || echo "0")
            log "✅ $file exists (${size} bytes)"
        else
            log "❌ $file missing"
            all_exist=false
        fi
    done

    if [ "$all_exist" = true ]; then
        log "✅ All storage files verified"
        return 0
    else
        log "❌ Some storage files missing"
        return 1
    fi
}

get_transcription_details() {
    local id=$1

    curl -s "${SERVER_URL}/api/transcriptions/${id}" \
        -H "Authorization: Bearer ${API_KEY}" | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Status: {data.get('status', 'unknown')}\")
print(f\"Language: {data.get('language', 'unknown')}\")
print(f\"Duration: {data.get('duration_seconds', 0)}s\")
print(f\"Runner ID: {data.get('runner_id', 'none')}\")
print(f\"Error: {data.get('error_message', 'none')}\")
" 2>/dev/null || echo "Failed to parse response"
}

# Main test execution
main() {
    log "# Audio Length Test Report"
    log ""
    log "**Date**: $(date)"
    log "**Server**: ${SERVER_URL}"
    log ""
    log "## Test Environment"
    log ""
    log "- Server: whisper_server_dev"
    log "- Runner: whisper_runner_dev"
    log "- Database: whisper_postgres_dev"
    log ""

    # Check services
    log_section "Service Health Check"

    if curl -s "${SERVER_URL}/health" | grep -q "healthy"; then
        log "✅ Server is healthy"
    else
        log "❌ Server is not healthy"
        exit 1
    fi

    if docker ps | grep -q "whisper_runner_dev.*healthy"; then
        log "✅ Runner is healthy"
    else
        log "❌ Runner is not healthy"
        exit 1
    fi

    # Run tests sequentially
    for test_name in "2_min" "20_min" "60_min" "210_min"; do
        log_section "Test: ${test_name}"

        local filename="${TEST_FILES[$test_name]}"
        local upload_start=$(date +%s)

        # Upload file
        local id
        if ! id=$(upload_file "$test_name" "$filename"); then
            log "❌ Upload failed for $test_name"
            continue
        fi

        local upload_end=$(date +%s)
        local upload_time=$((upload_end - upload_start))
        log "Upload time: ${upload_time}s"

        # Wait for completion
        local processing_start=$(date +%s)
        if ! poll_status "$id" 7200; then
            log "❌ Processing failed for $test_name (ID: $id)"
            get_transcription_details "$id"
            continue
        fi
        local processing_end=$(date +%s)
        local processing_time=$((processing_end - processing_start))
        log "Processing time: ${processing_time}s"

        # Verify storage
        if ! verify_storage "$id"; then
            log "❌ Storage verification failed for $test_name"
        fi

        # Get details
        log "Transcription details:"
        get_transcription_details "$id"

        local total_time=$((upload_time + processing_time))
        log "✅ Total time: ${total_time}s"

        # Wait between tests to avoid overwhelming the runner
        if [ "$test_name" != "210_min" ]; then
            log ""
            log "Waiting 30 seconds before next test..."
            sleep 30
        fi
    done

    log_section "Test Summary"
    log "All tests completed. Check detailed logs above."
    log ""
    log "**Report saved to**: $REPORT_FILE"
}

# Run main function
main "$@"
