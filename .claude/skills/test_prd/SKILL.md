---
name: test_prd
description: Automated remote testing and debugging for production servers. SSH connects to remote server using id_ed25519 key, runs tests via docker exec, and applies intelligent fix-verify loop with UltraThink integration, Docker build/push, and Git commit/push.
---

# test_prd - Production Server Testing Skill

## Purpose

Automates end-to-end testing and debugging workflow for remote production servers:

1. Reads server configuration from `prd_server_info`
2. Starts local test container (`tests/docker-compose.test.prd.yml`)
3. SSH connects to remote server using `id_ed25519` key
4. Runs tests and analyzes results
5. **If failures detected**: Applies intelligent fix loop
   - Analyzes failures with UltraThink
   - Applies fixes
   - Rebuilds Docker images
   - Pushes images and commits to Git
   - Triggers remote server pull and restart
   - Re-runs tests
6. Continues until tests pass or max retries reached

## When to Use

Use this skill when you need to:

```bash
# Run full test cycle with automated fixes
/test_prd

# Run tests only (no fix loop)
/test_prd --test-only

# Set maximum fix-verify iterations
/test_prd --max-retries 5

# Enable verbose logging
/test_prd --verbose

# Use custom config file
/test_prd --config /path/to/prd_server_info
```

## Input Parameters

### Required (via prd_server_info file)
- `server.host`: Remote server IP address or hostname
- `server.user`: SSH username (default: root)
- `server.port`: SSH port (default: 22)
- `ssh.key_path`: Path to id_ed25519 private key

### Optional
- `--config, -c`: Path to prd_server_info configuration file (default: `prd_server_info` in project root)
- `--test-only`: Run tests only, skip fix loop (default: false)
- `--verbose, -v`: Enable verbose logging (default: false)
- `--max-retries`: Maximum fix-verify iterations (default: 3)

## Output

### Console Output

```
============================================================
  Test on Remote - Automated Testing & Debugging
============================================================

[INFO] Loading configuration from prd_server_info...
[INFO] Connecting to root@192.3.249.169...
[SUCCESS] SSH connection established

[INFO] Starting local test container...
[SUCCESS] Test container ready

[INFO] Running remote tests...
[PASS] test_health_check
[PASS] test_list_transcriptions
[FAIL] test_download_docx (404: Not Found)

[ULTRATHINK] Analyzing failure pattern...
  Thought 1/5: The 404 error indicates the endpoint isn't registered
  Thought 2/5: Checking route configuration...
  Thought 3/5: Found missing import in transcriptions.py
  Thought 4/5: Fix strategy: Add import and restart server
  Thought 5/5: Ready to apply fix

[INFO] Applying fix...
[INFO] Building docker image...
[INFO] Pushing to registry...
[SUCCESS] Git commit: abc123 Fix missing route import
[SUCCESS] Git push complete

[INFO] Triggering remote deployment...
[INFO] Remote: Pulling images...
[INFO] Remote: Restarting containers...
[SUCCESS] Remote deployment complete

[INFO] Re-running tests...
[PASS] test_download_docx

============================================================
  Results: 21 passed, 0 failed, 92 skipped
  Iterations: 1
  Status: SUCCESS
============================================================
```

## Test Coverage

### 1. SSH Remote Execution
- Secure connection using Ed25519 keys
- Command execution with timeout handling
- Container log streaming
- Health check monitoring

### 2. Intelligent Fix Loop
- **UltraThink Integration**: AI-powered failure analysis
- **Smart Detection**: Distinguishes between new and existing failures
- **Safe Deployment**: Automatic rollback on critical failures
- **Progressive Fix**: Fixes issues incrementally

### 3. Docker Management
- Local test container lifecycle
- Remote image pull and restart
- Change detection for targeted builds
- Registry push support

### 4. Git Integration
- Automatic commit generation
- Conventional commit messages
- Branch management
- Push with conflict detection

## Configuration

Create a `prd_server_info` file in your project root (TOML format):

```toml
[server]
host = "192.3.249.169"
user = "root"
port = 22

[ssh]
key_path = "~/.ssh/id_ed25519"
known_hosts_path = "~/.ssh/known_hosts"
connect_timeout = 30
command_timeout = 300

[containers]
server = "whisper_server_prd"
runner = "whisper_runner_prd"
frontend = "whisper_frontend_prd"

[docker]
compose_file = "docker-compose.prod.yml"
project_name = "whisper"
image_prefix = "whisper-"

[testing]
test_compose = "tests/docker-compose.test.prd.yml"
test_timeout = 300
max_retries = 3
test_path = "tests/integration"
pytest_args = "-v --tb=short"

[git]
auto_commit = true
auto_push = true
commit_prefix = "[test-on-remote]"
branch = "main"
coauthor = "Claude <noreply@anthropic.com>"

[ultrathink]
enabled = true
max_thoughts = 10
timeout = 60
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Tests failed after max retries |
| 2 | Configuration error |
| 3 | SSH connection failed |
| 4 | Docker operation failed |
| 5 | Git operation failed |

## Implementation Notes

### SSH Authentication
Uses Ed25519 key authentication for secure remote access:
- Default key: `~/.ssh/id_ed25519`
- Supports custom key path via `ssh.key_path` in config
- Automatically loads known_hosts for verification

### Test Execution
Tests run via Docker exec on remote container:
- Local test runner connects to remote server
- Executes pytest inside production container
- Parses output for structured results

### UltraThink Analysis
When tests fail, UltraThink analyzes:
- Error patterns and stack traces
- Code changes that caused failures
- Most likely fix strategies
- Whether to continue or stop

### Safety Features
- **Dry Run Mode**: Preview changes without applying
- **Rollback Protection**: Automatic rollback on critical failures
- **Idempotent Operations**: Safe to re-run
- **Progressive Deployment**: One service at a time
- **Health Check Verification**: Wait for services to be healthy

## Common Issues and Fixes

### Issue: SSH connection refused
**Fix:** Verify server is reachable and SSH port is open
```bash
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169
```

### Issue: Permission denied (publickey)
**Fix:** Check key path and permissions
```bash
ls -la ~/.ssh/id_ed25519
# Should be -rw------- (600)
chmod 600 ~/.ssh/id_ed25519
```

### Issue: Container not found
**Fix:** Verify container names in config match actual containers
```bash
docker ps --format "{{.Names}}"
```

### Issue: Tests timeout
**Fix:** Increase timeout in config or check network connectivity
```toml
[ssh]
command_timeout = 600  # 10 minutes
```

### Issue: Git push fails
**Fix:** Check remote branch and permissions
```bash
git status
git log origin/main..HEAD
```

## Example Usage

### Basic test run
```bash
test_prd
```

### Test only (no fixes)
```bash
test_prd --test-only
```

### Verbose output with custom retries
```bash
test_prd --verbose --max-retries 5
```

### Use custom configuration
```bash
test_prd --config ~/my_server_config
```

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/test-production.yml
name: Production Tests
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  test-production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r .claude/skills/test_prd/requirements.txt
      - name: Run production tests
        run: test_prd --verbose
```

## Related Commands

```bash
# View production logs
./logs_prd.sh

# Check container status
docker ps --filter "name=whisper"

# Restart services
./restart_prd.sh

# View server info
cat prd_server_info
```

## Maintenance

### Regular Testing Schedule
Consider setting up cron jobs:

```bash
# Hourly health check
0 * * * * cd /home/lmr/ws/whisper_summarizer && test_prd --test-only

# Daily full test with fixes
0 2 * * * cd /home/lmr/ws/whisper_summarizer && test_prd

# Weekly verbose test
0 3 * * 0 cd /home/lmr/ws/whisper_summarizer && test_prd --verbose
```

### Monitoring
- Monitor test results for patterns
- Alert on repeated failures
- Review UltraThink analysis for insights
- Keep test suite updated with new features

## Requirements

- Python 3.12+
- paramiko (SSH)
- docker (Docker Python SDK)
- GitPython
- toml
- pydantic

Install with:
```bash
pip install -r .claude/skills/test_prd/requirements.txt
```
