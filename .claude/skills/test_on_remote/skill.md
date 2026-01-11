# Test on Remote

Automated remote testing and debugging workflow with intelligent fix-verify cycles and UltraThink integration.

## Overview

This skill automates the end-to-end testing and debugging workflow for remote production servers:

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

## Usage

```bash
# Run full test cycle with automated fix-verify loop
/sc:implement test_on_remote

# Run with specific max retries
/sc:implement test_on_remote --max-retries 5

# Run tests only (no fixes)
/sc:implement test_on_remote --test-only

# Verbose mode with detailed logging
/sc:implement test_on_remote --verbose
```

## Configuration

Create a `prd_server_info` file in your project root (default format is TOML):

```toml
[server]
host = "192.3.249.169"
user = "root"
port = 22

[ssh]
key_path = "~/.ssh/id_ed25519"
known_hosts_path = "~/.ssh/known_hosts"

[containers]
server = "whisper_server_prd"
runner = "whisper_runner_prd"
frontend = "whisper_frontend_prd"

[docker]
compose_file = "docker-compose.prod.yml"
project_name = "whisper"

[testing]
test_compose = "tests/docker-compose.test.prd.yml"
test_timeout = 300
max_retries = 3
test_path = "tests/integration"

[git]
auto_commit = true
auto_push = true
commit_prefix = "[test-on-remote]"

[ultrathink]
enabled = true
max_thoughts = 10
```

## Features

### SSH Remote Execution
- Secure connection using Ed25519 keys
- Command execution with timeout handling
- Container log streaming
- Health check monitoring

### Intelligent Fix Loop
- **UltraThink Integration**: AI-powered failure analysis
- **Smart Detection**: Distinguishes between new and existing failures
- **Safe Deployment**: Automatic rollback on critical failures
- **Progressive Fix**: Fixes issues incrementally

### Docker Management
- Local test container lifecycle
- Remote image pull and restart
- Change detection for targeted builds
- Registry push support

### Git Integration
- Automatic commit generation
- Conventional commit messages
- Branch management
- Push with conflict detection

## Output

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
[PASS] test_download_docx ✓

============================================================
  Results: 21 passed, 0 failed, 92 skipped
  Iterations: 1
  Status: SUCCESS
============================================================
```

## Requirements

- Python 3.12+
- paramiko (SSH)
- docker (Docker Python SDK)
- GitPython
- toml
- pydantic

## Installation

```bash
pip install paramiko docker GitPython toml pydantic
```

## Safety Features

- **Dry Run Mode**: Preview changes without applying
- **Rollback Protection**: Automatic rollback on critical failures
- **Idempotent Operations**: Safe to re-run
- **Progressive Deployment**: One service at a time
- **Health Check Verification**: Wait for services to be healthy

## Exit Codes

- `0`: All tests passed
- `1`: Tests failed after max retries
- `2`: Configuration error
- `3`: SSH connection failed
- `4`: Docker operation failed
- `5`: Git operation failed
