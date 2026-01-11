---
name: prd_debug
description: Production server remote debugging and testing. SSH connects using id_ed25519 key, executes commands inside Docker containers with localhost auth bypass. View logs, test APIs, query database, upload audio files, and monitor job processing.
---

# prd_debug - Production Server Debugging

## Purpose

Provides quick remote debugging and testing capabilities for the production server via SSH and Docker exec:

- **No authentication required** - Uses localhost auth bypass inside container
- **Bypasses Cloudflare** - Direct container access avoids CDN protection
- **Quick diagnostics** - Check status, logs, API endpoints without leaving terminal
- **Audio testing** - Upload and process audio files for testing

## Quick Start

```bash
# View all transcriptions (formatted)
/prd_debug transcriptions

# Check server health
/prd_debug status

# View server logs (last 50 lines)
/prd_debug logs

# View logs with custom line count
/prd_debug logs 100

# Test a specific API endpoint
/prd_debug api /health

# Upload audio file for testing
/prd_debug upload /path/to/audio.m4a

# Test chat streaming on a transcription
/prd_debug chat <transcription_id> "总结内容"

# Open interactive shell in container
/prd_debug shell

# View current session.json
/prd_debug session

# Query database
/prd_debug db "SELECT id, file_name, status FROM transcriptions LIMIT 5"

# Monitor job processing
/prd_debug watch
```

## Server Configuration

**Location**: `ssh -i ~/.ssh/id_ed25519 root@192.3.249.169`
**SSH Key**: `~/.ssh/id_ed25519`
**Project Path**: `/root/whisper_summarizer`
**URL**: https://w.198066.xyz

### Container Names

| Container | Name |
|-----------|------|
| Server | `whisper_server_prd` |
| PostgreSQL | `whisper_postgres_prd` |
| Frontend | `whisper_web_prd` |

## Commands Reference

### status

Show server and container status:

```bash
/prd_debug status
```

Output:
```
CONTAINER ID   NAME                    STATUS         PORTS
abc123def456   whisper_server_prd      Up 2 hours      0.0.0.0:8000->8000/tcp
ghi789jkl012   whisper_postgres_prd    Up 2 hours      5432/tcp
mno345pqr678   whisper_web_prd         Up 2 hours      0.0.0.0:80->80/tcp
```

### transcriptions

List all transcriptions with status:

```bash
/prd_debug transcriptions
```

### logs

View server logs:

```bash
# Last 50 lines (default)
/prd_debug logs

# Last 100 lines
/prd_debug logs 100

# Follow logs (tail -f)
/prd_debug logs --follow
```

### api

Test any API endpoint using localhost bypass:

```bash
/prd_debug api /health
/prd_debug api /api/transcriptions
/prd_debug api /api/runner/jobs?status=pending
```

**Note**: All API calls use localhost auth bypass - no authentication required.

### upload

Upload audio file for testing:

```bash
/prd_debug upload /path/to/audio.m4a
```

This will:
1. Copy file to server via SCP
2. Upload via API inside container
3. Return transcription ID for monitoring

### chat

Test chat streaming on a transcription:

```bash
/prd_debug chat <transcription_id> "your question here"
```

Example:
```bash
/prd_debug chat abc123-def4-5678-90ab-cdef12345678 "总结这个转录的主要内容"
```

### shell

Open interactive bash shell in server container:

```bash
/prd_debug shell
```

### session

View or update the test session (auth bypass user):

```bash
/prd_debug session
```

### db

Execute database query:

```bash
/prd_debug db "SELECT * FROM transcriptions ORDER BY created_at DESC LIMIT 5"
```

### watch

Monitor transcriptions as they process:

```bash
/prd_debug watch
```

Shows real-time updates of processing jobs.

## Manual SSH Usage

For advanced operations, SSH manually:

```bash
# Connect to server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Change to project directory
cd /root/whisper_summarizer

# Execute command in container
docker exec whisper_server_prd curl -s http://localhost:8000/api/transcriptions

# View logs
docker logs whisper_server_prd --tail=50

# Interactive database shell
docker exec -it whisper_postgres_prd psql -U postgres -d whisper_summarizer
```

## Authentication Bypass System

The production server has a **localhost authentication bypass** for testing:

**How it works**:
- Requests from `127.0.0.1` or `localhost` bypass Supabase OAuth
- Uses test user from `/app/session.json`
- All bypassed requests logged with `[AuthBypass]` marker

**Security**:
- ❌ External requests (via Cloudflare Tunnel) require normal auth
- ✅ Container-internal requests bypass auth
- ✅ Audit trail maintained in logs

## Common Debugging Scenarios

### Check transcription status

```bash
docker exec whisper_server_prd curl -s http://localhost:8000/api/transcriptions | \
  jq '.[] | {id, file_name, status, created_at}'
```

### Test runner API

```bash
# Check pending jobs
docker exec whisper_server_prd curl -s http://localhost:8000/api/runner/jobs?status=pending

# Check active jobs
docker exec whisper_server_prd curl -s http://localhost:8000/api/runner/jobs?status=processing
```

### Monitor job processing

```bash
watch -n 2 'docker exec whisper_server_prd curl -s http://localhost:8000/api/transcriptions | \
  jq -r ".[] | select(.status == \"processing\") | {file_name, status}"'
```

### Query database directly

```bash
docker exec whisper_postgres_prd psql -U postgres -d whisper_summarizer -c \
  "SELECT id, file_name, status FROM transcriptions ORDER BY created_at DESC LIMIT 10;"
```

### Upload and test audio file

```bash
# From local machine
scp -i ~/.ssh/id_ed25519 test.m4a root@192.3.249.169:/tmp/test.m4a

# On server
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169
docker cp /tmp/test.m4a whisper_server_prd:/tmp/test.m4a
docker exec whisper_server_prd curl -X POST \
  http://localhost:8000/api/audio/upload \
  -F "file=@/tmp/test.m4a"
```

### View session.json

```bash
docker exec whisper_server_prd cat /app/session.json | jq .
```

### Update session (switch test user)

```bash
docker exec whisper_server_prd sh -c 'cat > /app/session.json << EOF
{
  "version": "1.0",
  "test_user": {
    "id": "new-user-id",
    "email": "newuser@example.com",
    "is_admin": true,
    "is_active": true
  },
  "test_channels": [],
  "test_transcriptions": []
}
EOF'

# Restart server to reload
docker compose -f docker-compose.prod.yml restart server
```

## Troubleshooting

### "401 Unauthorized" with localhost request

**Problem**: Auth bypass not working

**Solution**:
- Verify you're inside the container: `docker exec whisper_server_prd curl ...`
- Check server logs: `docker logs whisper_server_prd --tail=50 | grep AuthBypass`

### Session file not found

**Problem**: `/app/session.json` missing

**Solution**:
```bash
# Check if file exists
docker exec whisper_server_prd ls -la /app/session.json

# Restart server to auto-create
docker compose -f docker-compose.prod.yml restart server
```

### Container access denied

**Problem**: Can't access container

**Solution**:
```bash
# Verify you're SSH'd into production server first
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Check container is running
docker ps | grep whisper_server_prd
```

### SSH key issues

**Problem**: "Permission denied (publickey)"

**Solution**:
```bash
# Check key exists and has correct permissions
ls -la ~/.ssh/id_ed25519
# Should show: -rw------- (600)

# Fix permissions if needed
chmod 600 ~/.ssh/id_ed25519
```

## Production Deployment Info

**Server**: Low-spec VPS without GPU
**URL**: https://w.198066.xyz
**Note**: DO NOT build images on production server

### Related Skills

```bash
# Run automated tests on production
/test_prd

# Test backup and restore scripts
/check_backup
```

## See Also

- [CLAUDE.md - Remote Production Debugging](../../CLAUDE.md#remote-production-debugging)
- [CLAUDE.md - Production Deployment](../../CLAUDE.md#production-deployment)
