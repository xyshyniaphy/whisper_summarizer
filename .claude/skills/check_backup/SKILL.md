---
name: check_backup
description: Verify backup and restore scripts functionality. Tests backup.sh and restore.sh scripts exist, are executable, and work correctly. Performs backup creation test, validates archive integrity, and reports status.
---

# check_backup - Backup/Restore Verification Skill

## Purpose

Validates the Whisper Summarizer backup and restore functionality by:
- Checking script existence and permissions
- Verifying backup script can create archives
- Validating backup archive integrity
- Testing restore script safety mechanisms
- Reporting comprehensive status

## When to Use

Use this skill when you need to:

```bash
# Verify backup/restore scripts are working
check_backup

# After modifying backup.sh or restore.sh
check_backup

# Before production deployment
check_backup

# As part of system health check
check_backup
```

## Input Parameters

### Optional
- `--quick`: Skip time-consuming tests (archive creation/restore)
- `--verbose`: Show detailed test output
- `--fix`: Attempt to fix common issues (permissions, missing files)

## Output

### Console Output

```
========================================
Backup/Restore Verification
========================================

📋 Script Verification
✅ backup.sh exists
✅ backup.sh is executable
✅ restore.sh exists
✅ restore.sh is executable

📦 Backup Functionality Test
✅ Production services check
✅ Backup directory creation
✅ Database dump capability
✅ Archive creation

✅ Archive integrity verified
📊 Test archive: test_backup_20260109_203000.tar.gz (125KB)

🔄 Restore Functionality Test
✅ Backup validation
✅ Safety confirmation mechanism
✅ Database restore capability
✅ File restore capability

📈 Test Results Summary
✅ All tests PASSED (15/15)

Recommendations:
- Scripts are functioning correctly
- Ready for production use
- Consider scheduling regular backups
```

## Test Coverage

### 1. Script Existence Check
- ✅ `backup.sh` exists in project root
- ✅ `restore.sh` exists in project root
- ✅ Scripts have correct permissions (755)

### 2. Backup Script Validation
- ✅ Checks production services status
- ✅ Verifies backup directory can be created
- ✅ Tests database dump functionality
- ✅ Validates archive creation
- ✅ Verifies backup file integrity (tar -tzf test)

### 3. Restore Script Validation
- ✅ Validates backup file format
- ✅ Checks safety confirmation mechanism
- ✅ Verifies database restore capability
- ✅ Tests file restore functionality

### 4. Environment Verification
- ✅ Docker Compose availability
- ✅ Production containers status
- ✅ Database connectivity
- ✅ Storage path accessibility

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Script(s) missing or not executable |
| 2 | Backup test failed |
| 3 | Restore test failed |
| 4 | Environment not ready (Docker/DB issues) |

## Implementation Notes

### Script Location
The skill expects scripts in the project root:
- `./backup.sh`
- `./restore.sh`

### Production Services
Tests require production services to be running:
```bash
# Start services if needed
./start_prd.sh
```

### Test Backup Creation
Creates a small test backup:
- File: `test_backup_YYYYMMDD_HHMMSS.tar.gz`
- Location: `backups/test/`
- Contains: Minimal database dump + metadata

### Cleanup
Test artifacts are automatically cleaned up:
```bash
rm -f backups/test/test_backup_*.tar.gz
```

## Common Issues and Fixes

### Issue: Scripts not executable
**Fix:** Run `chmod +x backup.sh restore.sh`

### Issue: Production services not running
**Fix:** Run `./start_prd.sh` first

### Issue: Permission denied on data directory
**Fix:** Check ownership of `data/transcribes/`
```bash
ls -la data/transcribes/
# If owned by root, either:
# 1. Run with sudo (not recommended)
# 2. Fix ownership: sudo chown -R $USER:$USER data/transcribes/
```

### Issue: Database connection failed
**Fix:** Verify PostgreSQL container is healthy
```bash
docker compose -f docker-compose.prod.yml ps postgres
```

## Example Usage

### Basic verification
```bash
check_backup
```

### Quick check (skip backup creation)
```bash
check_backup --quick
```

### Verbose output with auto-fix
```bash
check_backup --verbose --fix
```

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/backup-test.yml
name: Backup/Restore Test
on: [push, pull_request]

jobs:
  backup-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start Production
        run: ./start_prd.sh
      - name: Verify Backup/Restore
        run: check_backup --verbose
```

## Related Commands

```bash
# Create a real backup
./backup.sh

# Restore from backup
./restore.sh backups/whisper_prd_backup_20260109_120000.tar.gz

# View backup logs
./logs_prd.sh | grep backup

# Check disk space
df -h /home/lmr/ws/whisper_summarizer/backups/
```

## Maintenance

### Regular Backup Schedule
Consider setting up cron jobs:

```bash
# Daily backup at 2 AM
0 2 * * * cd /home/lmr/ws/whisper_summarizer && ./backup.sh

# Weekly backup on Sunday at 3 AM
0 3 * * 0 cd /home/lmr/ws/whisper_summarizer && ./backup.sh

# Monthly cleanup (keep last 30 days)
0 4 1 * * find /home/lmr/ws/whisper_summarizer/backups/ -name "*.tar.gz" -mtime +30 -delete
```

### Monitoring
- Monitor backup file sizes for anomalies
- Alert if backup fails (check exit code)
- Regular restore testing (monthly recommended)
