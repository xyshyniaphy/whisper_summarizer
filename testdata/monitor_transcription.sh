#!/bin/bash

ID=$1
MAX_CHECKS=300  # 300 * 10s = 50 minutes

echo "Monitoring transcription: $ID"
echo ""

for i in $(seq 1 $MAX_CHECKS); do
    result=$(curl -s http://localhost:3000/api/transcriptions/$ID)
    stage=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('stage','unknown'))")
    error=$(echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('error_message','') or '')")

    mins=$((i / 6))
    secs=$((i % 6 * 10))

    if [ "$stage" = "completed" ]; then
        echo "[$mins:${secs}0] ✓ COMPLETED!"
        echo "$result" | python3 -m json.tool | grep -E "storage_path|language|duration_seconds"
        break
    elif [ "$stage" = "failed" ] || [ -n "$error" ]; then
        echo "[$mins:${secs}0] ✗ FAILED: $error"
        break
    else
        echo "[$mins:${secs}0] Stage: $stage"
    fi
    sleep 10
done
