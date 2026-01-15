# E2E Testing Guide

## Overview

This project supports E2E testing against both development and production environments using Playwright.

## Development E2E Testing

**Usage:** `./run_test.sh e2e-dev` or `./tests/run_e2e_dev.sh`

Development E2E tests run against the local development environment (`docker-compose.dev.yml`).

**How it works:**
1. Tests run in `e2e-test` container on the same Docker network as dev services
2. Direct access to `http://whisper_frontend_dev:3000`
3. Localhost auth bypass triggered via `localStorage.setItem('e2e-test-mode', 'true')`
4. No proxy needed - same network, localhost detection works

**Prerequisites:**
- Dev environment running: `./run_dev.sh up-d`
- Tests built: `./run_test.sh build` (or auto-build on first run)

**Examples:**
```bash
# Run all E2E tests
./run_test.sh e2e-dev

# Run specific test pattern
./run_test.sh e2e-dev authentication
```

## Production E2E Testing

**Usage:** `./run_test.sh e2e-prd` or `./tests/run_e2e_prd.sh`

Production E2E tests run against the live production server via SSH tunnel + SOCKS5 proxy.

**How it works:**
```
[Local Machine]                 [Production Server]
     |                                  |
     | ssh -D 3480 (SOCKS5 proxy)       |
     |--------------------------------->|
     |                                  |
[Playwright Browser]              [FastAPI Server]
     |                                  |
     | --(traffic via proxy)-->        |
     |                                  |
     |  Request appears as 127.0.0.1    |
     |  Triggers localhost auth bypass  |
```

**Architecture:**
1. SSH tunnel creates SOCKS5 proxy on `localhost:3480`
2. Playwright browser routes traffic through proxy
3. Requests emerge from production server as `127.0.0.1`
4. Server-side localhost auth bypass detects 127.0.0.1
5. Returns hardcoded test user `lmr@lmr.com`
6. Client-side `e2e-test-mode` localStorage enables frontend test mode

**Prerequisites:**
- SSH access to production server: `root@192.3.249.169`
- SSH key: `~/.ssh/id_ed25519`
- Production URL: `https://w.198066.xyz`

**Examples:**
```bash
# Run all E2E tests against production
./run_test.sh e2e-prd

# Run specific test pattern
./run_test.sh e2e-prd -k authentication

# Custom proxy port and server
./run_test.sh e2e-prd -p 9999 -s root@custom.server.com
```

**Environment Variables:**
- `FRONTEND_URL`: Production frontend URL (default: `https://w.198066.xyz`)
- `PRODUCTION_SERVER`: SSH server (default: `root@192.3.249.169`)
- `PROXY_PORT`: SOCKS5 proxy port (default: `3480`)

## Test User Configuration

### Development (Local)
- Email: `test@example.com`
- User ID: `fc47855d-6973-4931-b6fd-bd28515bec0d`
- Role: Admin

### Production (E2E Only)
- Email: `lmr@lmr.com`
- User ID: `e2e-prod-user-id`
- Role: Admin

**Security Note:** Production E2E test user is only accessible via SSH tunnel from localhost. External requests cannot use this bypass.

## Troubleshooting

### SSH Tunnel Issues

**"SSH key not found"**
```bash
ls -la ~/.ssh/id_ed25519
SSH_KEY=~/.ssh/custom_key ./run_test.sh e2e-prd
```

**"Connection refused"**
```bash
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169
ping 192.3.249.169
```

**"Port 3480 already in use"**
```bash
lsof -ti:3480 | xargs kill -9
./run_test.sh e2e-prd -p 9999
```

### Test Failures

**Tests timeout connecting to production**
```bash
curl https://w.198066.xyz/api/health
```

**Auth bypass not working**
```bash
docker logs whisper_server_prd | grep "AuthBypass"
lsof -i:3480
```

## See Also

- `CLAUDE.md` - Project overview and development commands
- `/whisper-e2e` skill - E2E testing patterns and common scenarios
- `tests/e2e/tests/` - Example E2E test files
- `server/app/core/auth_bypass.py` - Localhost auth bypass implementation
- `frontend/src/hooks/useAuth.ts` - Frontend auth with E2E mode detection
