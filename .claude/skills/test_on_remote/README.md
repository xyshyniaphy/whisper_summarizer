# Test on Remote Skill

Automated testing and debugging workflow for remote production servers with intelligent fix-verify cycles.

## Quick Start

1. **Install Dependencies**
```bash
pip install paramiko docker GitPython toml pydantic
```

2. **Create Configuration**
```bash
cp prd_server_info.example prd_server_info
# Edit prd_server_info with your server details
```

3. **Run Tests**
```bash
# From skills/test_on_remote directory
python skill.py --help

# Run full test cycle with automated fixes
python skill.py

# Run tests only (no fixes)
python skill.py --test-only

# Verbose mode
python skill.py --verbose

# Override max retries
python skill.py --max-retries 5
```

## Skill Invocation

The skill can be invoked from anywhere in the project:

```bash
# Using Python directly
python skills/test_on_remote/skill.py

# Or as a module
python -m skills.test_on_remote.skill
```

## Configuration

Configuration is loaded from `prd_server_info` in the project root. See `prd_server_info.example` for all options.

### Required Settings

- `[server.host]`: Production server IP
- `[ssh.key_path]`: Path to SSH key (default: `~/.ssh/id_ed25519`)

### Optional Settings

- `[testing.max_retries]`: Maximum fix-verify iterations (default: 3)
- `[docker.registry]`: Docker registry for pushing images
- `[git.auto_commit]`: Automatically commit changes (default: true)
- `[ultrathink.enabled]`: Enable intelligent analysis (default: true)

## Workflow

1. **Load Configuration** - Read `prd_server_info`
2. **Start Test Container** - Local Docker container for tests
3. **SSH Connection** - Connect to production server
4. **Run Tests** - Execute test suite via SSH
5. **Fix Loop** (if failures):
   - Analyze failures with UltraThink
   - Apply fixes to code
   - Build Docker images
   - Push images to registry
   - Commit and push to Git
   - Trigger remote deployment
   - Re-run tests
6. **Report** - Generate final report

## Output

```
============================================================
  Test on Remote - Automated Testing & Debugging
============================================================

[INFO] Loading Configuration...
[SUCCESS] Configuration loaded

[INFO] Initializing Components...
[SUCCESS] Components initialized

============================================================
  Test Environment Setup
============================================================
[INFO] Starting test container...
[SUCCESS] Test container ready

============================================================
  Remote Connection
============================================================
[INFO] Connecting to root@192.3.249.169...
[SUCCESS] Connected

============================================================
  Running Tests
============================================================
[PASS] test_health_check
[FAIL] test_download_docx
...

============================================================
  Fix Cycle
============================================================
[INFO] Iteration 1/3
[INFO] Analyzing failures...
[ULTRATHINK] Thought 1/5: Analyzing failure pattern...
[ULTRATHINK] Thought 2/5: Most failures are auth-related...
[INFO] Fix plan: 3 fixes, priority=high
[INFO] Applying fixes...
[SUCCESS] Fixes applied

============================================================
  Git Commit and Push
============================================================
[INFO] Committing changes...
[SUCCESS] Committed: abc1234
[SUCCESS] Pushed to remote

============================================================
  Remote Deployment
============================================================
[INFO] Restarting containers...
[SUCCESS] Deployment complete

============================================================
  Final Report
============================================================
✅ Status: SUCCESS
   Iterations: 1
   Duration: 245.3s
   Results: 21 passed, 0 failed, 92 skipped
============================================================
```

## Components

### `config/`
Configuration parsing and validation

### `ssh/`
Remote server SSH operations

### `docker/`
Local Docker container management

### `testing/`
Test execution and result parsing

### `git/`
Version control operations

### `utils/`
Logging and UltraThink integration

## Error Handling

The skill handles various error conditions:

- **SSH Connection Failed**: Check server IP, SSH key, and network
- **Container Not Running**: Check container names and Docker status
- **Test Timeout**: Increase `test_timeout` in configuration
- **Build Failed**: Check Docker daemon and disk space
- **Git Push Failed**: Check branch permissions and remote URL

## Safety Features

- **Dry Run Mode**: Use `--test-only` to test without making changes
- **Idempotent**: Safe to re-run if interrupted
- **Rollback Protection**: Won't deploy if critical failures detected
- **Progressive Deployment**: One service at a time
- **Health Verification**: Waits for containers to be healthy

## Advanced Usage

### Custom Test Path
```bash
python skill.py --test-only -- --test-path=tests/backend/integration/test_production_api.py
```

### Verbose Logging
```bash
python skill.py --verbose
```

### Override Configuration
```bash
# Edit prd_server_info.toml and set custom values
[testing]
pytest_args = "-v --tb=long -k 'download'"
max_retries = 5
```

## Troubleshooting

### SSH Key Issues
```bash
# Check key exists
ls -la ~/.ssh/id_ed25519

# Check key permissions (should be 600)
chmod 600 ~/.ssh/id_ed25519

# Test SSH connection
ssh -i ~/.ssh/id_ed25519 root@YOUR_SERVER_IP
```

### Docker Issues
```bash
# Check Docker is running
docker ps

# Check test container status
docker ps -a | grep test

# View test container logs
docker logs whisper_test_prd_runner
```

### Remote Container Issues
```bash
# SSH into server and check containers
ssh root@YOUR_SERVER_IP
docker ps
docker logs whisper_server_prd
```

## Requirements

- Python 3.12+
- `paramiko` - SSH operations
- `docker` - Docker Python SDK
- `GitPython` - Git operations
- `toml` - Configuration parsing
- `pydantic` - Data validation

## License

MIT
