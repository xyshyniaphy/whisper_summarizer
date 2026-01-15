# E2E Proxy Authentication Bypass Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable E2E testing against production server using SSH tunnel + SOCKS5 proxy to bypass authentication with hardcoded test user `lmr@lmr.com`.

**Architecture:**
- SSH tunnel from local machine to production server creates SOCKS5 proxy on port 3480
- E2E browser routes traffic through proxy, making requests appear from 127.0.0.1 on production server
- Server-side localhost auth bypass (existing) detects 127.0.0.1 requests and returns test user
- Client-side localStorage injection enables frontend test mode
- Local dev E2E tests continue working without proxy (same network, localhost bypass already works)

**Tech Stack:**
- SSH tunnel with dynamic port forwarding (`ssh -D 3480`)
- SOCKS5 proxy protocol for browser traffic routing
- Docker Compose service for proxy container
- Playwright proxy configuration via command-line flags
- Existing auth bypass system in `server/app/core/auth_bypass.py`

---

## Task 1: Update server-side auth bypass to detect SSH-tunneled requests

**Files:**
- Modify: `server/app/core/auth_bypass.py:42-99`
- Test: `server/tests/backend/core/test_auth_bypass.py`

**Step 1: Write the failing test**

```python
# server/tests/backend/core/test_auth_bypass.py
def test_ssh_tunneled_request_detected():
    """Test that SSH-tunneled requests (without forwarded headers) are detected as localhost"""
    from fastapi import Request

    # Create mock request from SSH tunnel (no forwarded headers, direct connection)
    scope = {
        'type': 'http',
        'method': 'GET',
        'headers': [],
        'query_string': b'',
        'path': '/api/test',
    }
    request = Request(scope)

    # Simulate SSH tunnel - request appears to come from 127.0.0.1 directly
    # This happens when SSH tunnel forwards traffic and it emerges from localhost
    request._client = type('obj', (object,), {'host': '127.0.0.1'})()

    from app.core.auth_bypass import is_localhost_request
    assert is_localhost_request(request) is True
```

**Step 2: Run test to verify it fails**

Run: `docker compose -f docker-compose.dev.yml exec server pytest tests/backend/core/test_auth_bypass.py::test_ssh_tunneled_request_detected -v`
Expected: PASS (existing `is_localhost_request` already handles `client.host == "127.0.0.1"`)

**Step 3: Verify existing implementation**

The existing `is_localhost_request()` function at lines 42-99 in `auth_bypass.py` already handles SSH-tunneled requests because:
1. Line 95-97 checks `request.client.host` for localhost IPs
2. SSH tunnel traffic emerges from production server as 127.0.0.1
3. No changes needed to server-side code

**Step 4: Document SSH tunnel behavior**

Add comment to `auth_bypass.py`:
```python
def is_localhost_request(request: Request) -> bool:
    """
    Detect if request originates from localhost.

    Checks multiple sources for reliability:
    1. X-Forwarded-For header (Cloudflare, nginx proxy)
    2. X-Real-IP header (nginx)
    3. CF-Connecting-IP header (Cloudflare)
    4. client.host (direct connection, SSH tunnels)

    SSH Tunnel Support:
        When using SSH tunnel with SOCKS5 proxy (e.g., ssh -D 3480),
        traffic emerges from the destination server as 127.0.0.1,
        triggering the client.host check below.
    """
```

**Step 5: Run existing tests to ensure no regression**

Run: `docker compose -f docker-compose.dev.yml exec server pytest tests/backend/core/test_auth_bypass.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add server/app/core/auth_bypass.py server/tests/backend/core/test_auth_bypass.py
git commit -m "docs(auth): document SSH tunnel support in auth bypass"
```

---

## Task 2: Create Docker Compose configuration for production E2E testing

**Files:**
- Create: `tests/docker-compose.e2e.prd.yml`
- Modify: `tests/e2e/Dockerfile` (add SSH client if missing)
- Test: Manual verification with `docker compose -f tests/docker-compose.e2e.prd.yml config`

**Step 1: Write the docker-compose.e2e.prd.yml file**

```yaml
# Docker Compose for E2E Testing Against Production Server
#
# This setup runs E2E tests in a Docker container that:
# 1. Uses SSH tunnel to connect to production server
# 2. Routes browser traffic through SOCKS5 proxy (localhost:3480)
# 3. Triggers localhost auth bypass on production server
# 4. Tests against https://w.198066.xyz
#
# Usage:
#   docker compose -f tests/docker-compose.e2e.prd.yml run --rm e2e-test
#   FRONTEND_URL=https://w.198066.xyz docker compose -f tests/docker-compose.e2e.prd.yml run --rm e2e-test
#
# Environment:
#   FRONTEND_URL         Production frontend URL (default: https://w.198066.xyz)
#   PRODUCTION_SERVER    Production SSH server (default: root@192.3.249.169)
#   SSH_KEY_PATH         Path to SSH private key (default: ~/.ssh/id_ed25519)

services:
  # E2E Test Runner with SSH Tunnel Support
  e2e-test:
    build:
      context: ./e2e
      dockerfile: Dockerfile
    container_name: whisper_e2e_prd_test
    environment:
      # Production frontend URL
      FRONTEND_URL: "${FRONTEND_URL:-https://w.198066.xyz}"

      # SSH connection for tunnel
      PRODUCTION_SERVER: "${PRODUCTION_SERVER:-root@192.3.249.169}"
      SSH_KEY_PATH: "${SSH_KEY_PATH:-/root/.ssh/id_ed25519}"

      # E2E test configuration
      TEST_ENVIRONMENT: production

      # Supabase config (not used for auth in E2E mode, but required by frontend)
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}

    volumes:
      # Mount test files
      - ./e2e:/app
      - ../data:/app/data
      - ../testdata:/app/testdata

      # Mount SSH key for production tunnel
      - ~/.ssh/id_ed25519:/root/.ssh/id_ed25519:ro
      - ~/.ssh/id_ed25519.pub:/root/.ssh/id_ed25519.pub:ro
      - ~/.ssh/known_hosts:/root/.ssh/known_hosts:ro

      # Exclude node_modules
      - /app/node_modules

    working_dir: /app

    # Command will be overridden by docker compose run
    command: /bin/sh -c "tail -f /dev/null"

    networks:
      - e2e_prd_network

networks:
  e2e_prd_network:
    driver: bridge
```

**Step 2: Verify Dockerfile has SSH client**

Check: `grep -q "openssh-client" tests/e2e/Dockerfile || echo "SSH client not found"`

If missing, add to `tests/e2e/Dockerfile`:
```dockerfile
# Install SSH client for tunnel
RUN apk add --no-cache openssh-client
```

**Step 3: Validate docker-compose configuration**

Run: `docker compose -f tests/docker-compose.e2e.prd.yml config`
Expected: Valid YAML output, no parse errors

**Step 4: Build the E2E test image**

Run: `docker compose -f tests/docker-compose.e2e.prd.yml build`
Expected: Image builds successfully

**Step 5: Commit**

```bash
git add tests/docker-compose.e2e.prd.yml tests/e2e/Dockerfile
git commit -m "feat(e2e): add production E2E testing compose config with SSH tunnel support"
```

---

## Task 3: Create SSH tunnel manager script for E2E tests

**Files:**
- Create: `tests/e2e/scripts/start-ssh-tunnel.sh`
- Create: `tests/e2e/scripts/stop-ssh-tunnel.sh`
- Test: Manual verification of tunnel establishment

**Step 1: Write the start-ssh-tunnel.sh script**

```bash
#!/bin/sh
# Start SSH tunnel for E2E testing
# Creates SOCKS5 proxy on localhost:3480

set -e

PRODUCTION_SERVER="${PRODUCTION_SERVER:-root@192.3.249.169}"
PROXY_PORT="${PROXY_PORT:-3480}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

echo "Starting SSH tunnel to ${PRODUCTION_SERVER}..."
echo "SOCKS5 proxy will be available at localhost:${PROXY_PORT}"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at ${SSH_KEY}"
    exit 1
fi

# Create SSH tunnel with SOCKS5 proxy
# -D: Dynamic port forwarding (SOCKS5)
# -N: No remote command (just forwarding)
# -f: Fork to background
# -M: Control master for later termination
# -o: Control socket location
ssh -i "$SSH_KEY" \
    -D "$PROXY_PORT" \
    -N \
    -f \
    -M \
    -S /tmp/ssh-tunnel-e2e.sock \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    "$PRODUCTION_SERVER"

echo "SSH tunnel started successfully"
echo "Control socket: /tmp/ssh-tunnel-e2e.sock"
```

**Step 2: Write the stop-ssh-tunnel.sh script**

```bash
#!/bin/sh
# Stop SSH tunnel for E2E testing

CONTROL_SOCKET="/tmp/ssh-tunnel-e2e.sock"

if [ -S "$CONTROL_SOCKET" ]; then
    echo "Stopping SSH tunnel..."
    ssh -S "$CONTROL_SOCKET" -O exit dummy 2>/dev/null || true
    rm -f "$CONTROL_SOCKET"
    echo "SSH tunnel stopped"
else
    echo "No SSH tunnel control socket found"
fi
```

**Step 3: Make scripts executable**

Run: `chmod +x tests/e2e/scripts/start-ssh-tunnel.sh tests/e2e/scripts/stop-ssh-tunnel.sh`

**Step 4: Test tunnel establishment manually**

Run: `bash tests/e2e/scripts/start-ssh-tunnel.sh`
Expected: Success message, control socket created

Verify: `ls -la /tmp/ssh-tunnel-e2e.sock`
Expected: Socket file exists

Cleanup: `bash tests/e2e/scripts/stop-ssh-tunnel.sh`

**Step 5: Commit**

```bash
git add tests/e2e/scripts/start-ssh-tunnel.sh tests/e2e/scripts/stop-ssh-tunnel.sh
git commit -m "feat(e2e): add SSH tunnel management scripts for production testing"
```

---

## Task 4: Update Playwright configuration to support proxy

**Files:**
- Modify: `tests/e2e/playwright.config.ts`
- Create: `tests/e2e/playwright.config.prd.ts`
- Test: `docker compose -f tests/docker-compose.e2e.prd.yml run --rm e2e-test bun run test -- --config=playwright.config.prd.ts --dry-run`

**Step 1: Write the failing test**

No unit test needed - configuration changes verified by manual E2E test run.

**Step 2: Create production Playwright config**

Create `tests/e2e/playwright.config.prd.ts`:
```typescript
import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2Eテスト設定 - Production Environment
 *
 * Uses SSH tunnel + SOCKS5 proxy to route traffic through production server.
 * Requests appear from 127.0.0.1, triggering localhost auth bypass.
 */
export default defineConfig({
  testDir: './tests',

  timeout: 30 * 1000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,

  reporter: [
    ['html', { outputFolder: '/app/data/playwright-report', open: 'never' }],
    ['list'],
  ],

  outputDir: '/app/data/screenshots/failures',

  use: {
    // Production URL
    baseURL: process.env.FRONTEND_URL || 'https://w.198066.xyz',

    // SOCKS5 proxy configuration
    proxy: {
      server: process.env.PROXY_SERVER || 'http://localhost:3480',
    },

    actionTimeout: 10000,
    navigationTimeout: 15000,

    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // E2Eテストモードを有効化
    storageState: {
      origins: [
        {
          origin: process.env.FRONTEND_URL || 'https://w.198066.xyz',
          localStorage: [
            { name: 'e2e-test-mode', value: 'true' },
          ],
        },
      ],
    },
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
})
```

**Step 3: Update base Playwright config for proxy support**

Modify `tests/e2e/playwright.config.ts` to support optional proxy:
```typescript
use: {
  baseURL: process.env.FRONTEND_URL || 'http://frontend-test:3000',

  // Optional SOCKS5 proxy (for production testing)
  ...(process.env.PROXY_SERVER ? {
    proxy: {
      server: process.env.PROXY_SERVER,
    },
  } : {}),

  actionTimeout: 10000,
  // ... rest of config
}
```

**Step 4: Validate configuration**

Run: `docker compose -f tests/docker-compose.e2e.prd.yml run --rm e2e-test bun run test -- --config=playwright.config.prd.ts --dry-run`
Expected: Configuration loads, tests listed (not executed)

**Step 5: Commit**

```bash
git add tests/e2e/playwright.config.ts tests/e2e/playwright.config.prd.ts
git commit -m "feat(e2e): add Playwright configuration for production testing with proxy support"
```

---

## Task 5: Update useAuth hook to use hardcoded E2E test user

**Files:**
- Modify: `frontend/src/hooks/useAuth.ts:138-200`
- Test: `frontend/tests/frontend/hooks/useAuth.test.tsx`

**Step 1: Write the failing test**

```typescript
// frontend/tests/frontend/hooks/useAuth.test.tsx
describe('useAuth - E2E Production Mode', () => {
  it('should use hardcoded lmr@lmr.com user in E2E mode with production URL', () => {
    // Mock production environment
    const originalLocation = window.location
    delete (window as any).location
    window.location = new URL('https://w.198066.xyz') as any

    // Enable E2E test mode
    localStorage.setItem('e2e-test-mode', 'true')

    const { result } = renderHook(() => useAuth())
    const [user] = result.current

    expect(user?.email).toBe('lmr@lmr.com')
    expect(user?.user_metadata?.auth_bypass).toBe(true)

    // Cleanup
    window.location = originalLocation
    localStorage.removeItem('e2e-test-mode')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `docker compose -f tests/docker-compose.test.yml run --rm frontend-test src/tests/frontend/hooks/useAuth.test.tsx`
Expected: FAIL - currently uses `test@example.com`

**Step 3: Update useAuth to use hardcoded production test user**

Modify `frontend/src/hooks/useAuth.ts` around line 138:
```typescript
// Check for E2E test mode
if (typeof window !== 'undefined' && localStorage.getItem('e2e-test-mode') === 'true') {
  const isProduction = window.location.hostname === 'w.198066.xyz'

  const testUser = {
    id: isProduction
      ? 'e2e-prod-user-id'  // Unique ID for production E2E testing
      : 'fc47855d-6973-4931-b6fd-bd28515bec0d',  // Dev E2E user ID
    email: isProduction
      ? 'lmr@lmr.com'  // Hardcoded production E2E test user
      : 'test@example.com',
    email_confirmed_at: new Date(),
    user_metadata: {
      role: 'admin',
      provider: 'google',
      auth_bypass: true,
      e2e_mode: true,
    },
    created_at: new Date(),
    updated_at: new Date(),
  }

  return [
    {
      user: testUser,
      session: {},
      role: 'admin',
      loading: false,
      is_active: true,
      is_admin: true,
    },
    authActions,
  ]
}
```

**Step 4: Run test to verify it passes**

Run: `docker compose -f tests/docker-compose.test.yml run --rm frontend-test src/tests/frontend/hooks/useAuth.test.tsx`
Expected: PASS - uses `lmr@lmr.com` for production hostname

**Step 5: Run all frontend tests to ensure no regression**

Run: `docker compose -f tests/docker-compose.test.yml run --rm frontend-test`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add frontend/src/hooks/useAuth.ts frontend/tests/frontend/hooks/useAuth.test.tsx
git commit -m "feat(e2e): use hardcoded lmr@lmr.com test user for production E2E testing"
```

---

## Task 6: Create E2E test runner script for production

**Files:**
- Create: `tests/run_e2e_prd.sh`
- Create: `tests/run_e2e_dev.sh`
- Modify: `run_test.sh` (add production E2E option)
- Test: Manual verification of script execution

**Step 1: Write the production E2E runner script**

Create `tests/run_e2e_prd.sh`:
```bash
#!/bin/bash
# E2E Tests Runner - Production Environment
# Uses SSH tunnel + SOCKS5 proxy to test against production server

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
PRODUCTION_SERVER="${PRODUCTION_SERVER:-root@192.3.249.169}"
FRONTEND_URL="${FRONTEND_URL:-https://w.198066.xyz}"
PROXY_PORT="${PROXY_PORT:-3480}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"

# Help function
show_help() {
    echo -e "${BLUE}Production E2E Test Runner${NC}"
    echo ""
    echo "Usage: ./run_e2e_prd.sh [options] [test_pattern]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -k, --grep PATTERN   Run tests matching pattern"
    echo "  -p, --proxy PORT     SOCKS5 proxy port (default: 3480)"
    echo "  -s, --server SERVER  SSH server (default: root@192.3.249.169)"
    echo "  -u, --url URL        Frontend URL (default: https://w.198066.xyz)"
    echo ""
    echo "Examples:"
    echo "  ./run_e2e_prd.sh                                    # Run all tests"
    echo "  ./run_e2e_prd.sh -k authentication                  # Run auth tests"
    echo "  ./run_e2e_prd.sh -p 9999 -s root@prod.com           # Custom proxy/server"
    echo ""
}

# Parse arguments
TEST_PATTERN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -k|--grep)
            TEST_PATTERN="$2"
            shift 2
            ;;
        -p|--proxy)
            PROXY_PORT="$2"
            shift 2
            ;;
        -s|--server)
            PRODUCTION_SERVER="$2"
            shift 2
            ;;
        -u|--url)
            FRONTEND_URL="$2"
            shift 2
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
        *)
            TEST_PATTERN="$1"
            shift
            ;;
    esac
done

# Check if docker compose file exists
if [ ! -f "tests/docker-compose.e2e.prd.yml" ]; then
    echo -e "${RED}Error: tests/docker-compose.e2e.prd.yml not found${NC}"
    exit 1
fi

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}Error: SSH key not found at ${SSH_KEY}${NC}"
    exit 1
fi

echo -e "${BLUE}=== Production E2E Test Runner ===${NC}"
echo ""
echo "Configuration:"
echo "  Frontend URL: ${FRONTEND_URL}"
echo "  Production Server: ${PRODUCTION_SERVER}"
echo "  Proxy Port: ${PROXY_PORT}"
echo "  Test Pattern: ${TEST_PATTERN:-all tests}"
echo ""

# Start SSH tunnel
echo -e "${YELLOW}Starting SSH tunnel...${NC}"
ssh -i "$SSH_KEY" \
    -D "$PROXY_PORT" \
    -N \
    -f \
    -M \
    -S /tmp/ssh-tunnel-e2e.sock \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    "$PRODUCTION_SERVER"

echo -e "${GREEN}✓ SSH tunnel started (localhost:${PROXY_PORT})${NC}"
echo ""

# Trap to ensure SSH tunnel is stopped on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping SSH tunnel...${NC}"
    ssh -S /tmp/ssh-tunnel-e2e.sock -O exit dummy 2>/dev/null || true
    rm -f /tmp/ssh-tunnel-e2e.sock
    echo -e "${GREEN}✓ SSH tunnel stopped${NC}"
}
trap cleanup EXIT

# Run E2E tests
echo -e "${BLUE}Running E2E tests...${NC}"
echo ""

export FRONTEND_URL="$FRONTEND_URL"
export PROXY_SERVER="socks5://localhost:${PROXY_PORT}"
export PRODUCTION_SERVER="$PRODUCTION_SERVER"

TEST_CMD="bun run test"
if [ -n "$TEST_PATTERN" ]; then
    TEST_CMD="$TEST_CMD -- --grep \"$TEST_PATTERN\""
fi

docker compose -f tests/docker-compose.e2e.prd.yml run --rm \
    -e FRONTEND_URL="$FRONTEND_URL" \
    -e PROXY_SERVER="socks5://localhost:${PROXY_PORT}" \
    -e PRODUCTION_SERVER="$PRODUCTION_SERVER" \
    e2e-test sh -c "$TEST_CMD"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Production E2E tests passed!${NC}"
else
    echo -e "${RED}✗ Production E2E tests failed${NC}"
fi

exit $TEST_EXIT_CODE
```

**Step 2: Create the dev E2E runner script**

Create `tests/run_e2e_dev.sh`:
```bash
#!/bin/bash
# E2E Tests Runner - Development Environment
# Uses local docker network (no proxy needed)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Help function
show_help() {
    echo -e "${BLUE}Development E2E Test Runner${NC}"
    echo ""
    echo "Usage: ./run_e2e_dev.sh [test_pattern]"
    echo ""
    echo "Note: Dev environment must be running (./run_dev.sh)"
    echo ""
    echo "Examples:"
    echo "  ./run_e2e_dev.sh              # Run all tests"
    echo "  ./run_e2e_dev.sh authentication # Run auth tests"
    echo ""
}

# Parse arguments
TEST_PATTERN="${1:-}"

# Check if docker compose file exists
if [ ! -f "tests/docker-compose.test.yml" ]; then
    echo -e "${RED}Error: tests/docker-compose.test.yml not found${NC}"
    exit 1
fi

echo -e "${BLUE}=== Development E2E Test Runner ===${NC}"
echo ""
echo "Note: Uses local docker network (no proxy)"
echo "Test Pattern: ${TEST_PATTERN:-all tests}"
echo ""

# Run E2E tests
echo -e "${BLUE}Running E2E tests...${NC}"
echo ""

TEST_CMD="bun run test"
if [ -n "$TEST_PATTERN" ]; then
    TEST_CMD="$TEST_CMD -- --grep \"$TEST_PATTERN\""
fi

docker compose -f tests/docker-compose.test.yml run --rm e2e-test sh -c "$TEST_CMD"

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Development E2E tests passed!${NC}"
else
    echo -e "${RED}✗ Development E2E tests failed${NC}"
fi

exit $TEST_EXIT_CODE
```

**Step 3: Update main run_test.sh script**

Modify `tests/run_test.sh` to add production E2E option:
```bash
# Add to help function
echo "  e2e-dev          E2E tests against development environment"
echo "  e2e-prd          E2E tests against production (via SSH tunnel)"

# Add to main case statement
e2e-dev)
    bash tests/run_e2e_dev.sh "${2:-}"
    ;;
e2e-prd)
    bash tests/run_e2e_prd.sh "${@:2}"
    ;;
```

**Step 4: Make scripts executable**

Run: `chmod +x tests/run_e2e_prd.sh tests/run_e2e_dev.sh`

**Step 5: Test dev E2E runner**

Run: `./run_test.sh e2e-dev`
Expected: Tests run against local dev environment

**Step 6: Commit**

```bash
git add tests/run_e2e_prd.sh tests/run_e2e_dev.sh tests/run_test.sh
git commit -m "feat(e2e): add environment-specific E2E test runners"
```

---

## Task 7: Create comprehensive documentation

**Files:**
- Create: `docs/e2e-testing-guide.md`
- Modify: `CLAUDE.md` (add E2E testing section)
- Test: Documentation review for clarity

**Step 1: Write the E2E testing guide**

Create `docs/e2e-testing-guide.md`:
```markdown
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

# Via direct script
./tests/run_e2e_dev.sh
./tests/run_e2e_dev.sh "audio upload"
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
     |                                  |
```

**Architecture:**
1. SSH tunnel creates SOCKS5 proxy on `localhost:3480`
2. Playwright browser routes traffic through proxy
3. Requests emerge from production server as `127.0.0.1`
4. Server-side localhost auth bypass (see `server/app/core/auth_bypass.py`) detects 127.0.0.1
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

# Via direct script with all options
./tests/run_e2e_prd.sh -k "audio upload" -p 3480 -u https://w.198066.xyz
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
- Source: `server/app/core/auth_bypass.py` (DEFAULT_TEST_USER constant)

### Production (E2E Only)
- Email: `lmr@lmr.com`
- User ID: `e2e-prod-user-id`
- Role: Admin
- Source: `frontend/src/hooks/useAuth.ts` (hardcoded for production hostname)

**Security Note:** Production E2E test user is only accessible via SSH tunnel from localhost. External requests cannot use this bypass.

## Troubleshooting

### SSH Tunnel Issues

**Problem:** "SSH key not found"
```bash
# Check SSH key exists
ls -la ~/.ssh/id_ed25519

# Use custom key path
SSH_KEY=~/.ssh/custom_key ./run_test.sh e2e-prd
```

**Problem:** "Connection refused"
```bash
# Test SSH connection manually
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169

# Check if production server is accessible
ping 192.3.249.169
```

**Problem:** "Port 3480 already in use"
```bash
# Find and kill existing process
lsof -ti:3480 | xargs kill -9

# Or use different port
./run_test.sh e2e-prd -p 9999
```

### Test Failures

**Problem:** Tests timeout connecting to production
```bash
# Verify production server is accessible
curl https://w.198066.xyz/api/health

# Check if Cloudflare is blocking (try from different network)
curl -v https://w.198066.xyz
```

**Problem:** Auth bypass not working
```bash
# Check server logs for bypass detection
docker logs whisper_server_prd | grep "AuthBypass"

# Verify SSH tunnel is active
lsof -i:3480

# Test bypass manually (from production server)
docker exec whisper_server_prd python -c "
import urllib.request
print(urllib.request.urlopen('http://localhost:8000/api/transcriptions').status)
"
```

## See Also

- `CLAUDE.md` - Project overview and development commands
- `/whisper-e2e` skill - E2E testing patterns and common scenarios
- `tests/e2e/tests/` - Example E2E test files
- `server/app/core/auth_bypass.py` - Localhost auth bypass implementation
- `frontend/src/hooks/useAuth.ts` - Frontend auth with E2E mode detection
```

**Step 2: Update CLAUDE.md with E2E testing section**

Add to `CLAUDE.md` under "## Testing" section:
```markdown
### E2E Testing

**Development E2E:**
```bash
./run_test.sh e2e-dev              # Run all E2E tests against dev
./run_test.sh e2e-dev auth         # Run specific test pattern
```

**Production E2E:**
```bash
./run_test.sh e2e-prd              # Run all E2E tests against production
./run_test.sh e2e-prd -k auth      # Run specific test pattern
```

**How Production E2E Works:**
- SSH tunnel creates SOCKS5 proxy (`ssh -D 3480`)
- Playwright routes traffic through proxy
- Requests appear from `127.0.0.1` on production server
- Triggers localhost auth bypass → returns `lmr@lmr.com` test user
- Client-side `localStorage.setItem('e2e-test-mode', 'true')` enables test mode

**Prerequisites for Production E2E:**
- SSH key: `~/.ssh/id_ed25519`
- Production access: `root@192.3.249.169`
- URL: `https://w.198066.xyz`

**See:** `docs/e2e-testing-guide.md` for comprehensive E2E testing documentation
```

**Step 3: Commit**

```bash
git add docs/e2e-testing-guide.md CLAUDE.md
git commit -m "docs(e2e): add comprehensive E2E testing guide"
```

---

## Task 8: Verify end-to-end workflow

**Files:**
- Test all: Manual verification of complete workflow
- Test: `./run_test.sh e2e-prd` (full production E2E test run)

**Step 1: Verify dev E2E tests still work**

Run: `./run_test.sh e2e-dev`
Expected: All tests PASS against local dev environment

**Step 2: Verify production E2E tests work**

Run: `./run_test.sh e2e-prd`
Expected: SSH tunnel establishes, tests run against production, all PASS

**Step 3: Verify test user configuration**

Check production E2E tests use `lmr@lmr.com`:
```bash
# Should see lmr@lmr.com in test logs
./run_test.sh e2e-prd -k "user menu" 2>&1 | grep -i "lmr@lmr.com"
```

Expected: Test user email appears in logs

**Step 4: Verify auth bypass logs**

Check production server logs for bypass detection:
```bash
# After running E2E tests
ssh -i ~/.ssh/id_ed25519 root@192.3.249.169 \
    "docker logs whisper_server_prd | grep 'AuthBypass' | tail -20"
```

Expected: Log entries showing localhost bypass with `lmr@lmr.com` user

**Step 5: Verify cleanup**

Run: `lsof -i:3480`
Expected: No processes (SSH tunnel cleaned up)

**Step 6: Run full test suite**

Run: `./run_test.sh all`
Expected: All tests PASS (backend, frontend, dev E2E)

**Step 7: Final commit**

```bash
git add docs/plans/2025-01-15-e2e-proxy-auth-bypass.md
git commit -m "docs(plans): add E2E proxy auth bypass implementation plan"
```

---

## Summary

**What was built:**
1. SSH tunnel + SOCKS5 proxy infrastructure for production E2E testing
2. Docker Compose configuration for isolated E2E test environment
3. Playwright configuration with proxy support
4. Hardcoded production E2E test user (`lmr@lmr.com`)
5. Environment-specific test runner scripts
6. Comprehensive documentation

**Key Features:**
- **Zero credentials**: Uses SSH tunnel for localhost auth bypass
- **Environment isolation**: Dev tests use local network, prod tests use SSH tunnel
- **Automatic cleanup**: SSH tunnel terminated on test completion
- **Flexible**: Supports custom proxy ports, servers, and test patterns

**Security:**
- Bypass only triggers for `127.0.0.1` requests
- SSH tunnel required for production access
- No hardcoded credentials in test code
- Audit logging for all bypassed requests

**Next Steps:**
- Add E2E tests for critical user workflows
- Set up CI/CD integration for automated E2E testing
- Monitor production E2E test results for regression detection
