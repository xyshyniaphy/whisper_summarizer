# Frontend Test Fixes Plan

**Created**: 2026-01-05
**Status**: READY FOR EXECUTION
**Goal**: Fix 162 failing frontend tests and improve coverage from 73.6% to 100%

---

## Current Status

**Test Results**:
- **Test Files**: 59 failed (59 total) - 100% failure rate
- **Tests**: 162 failed, 2 passed (164 total) - 98.8% failure rate
- **Coverage**: 73.6% (319/433 tests passing in previous runs)

**Primary Issues**:
1. **"document is not defined"** - jsdom environment not properly initialized
2. **React 19 + Testing Library compatibility** - `Symbol(Node prepared with document state workarounds)`
3. **Jotai atom mocking issues** - atoms not being properly mocked in tests

---

## Root Cause Analysis

### Issue 1: "document is not defined"

**Symptom**: Most tests fail with `document is not defined`

**Root Cause**: The jsdom environment is not being loaded properly. This happens when:
- jsdom version is incompatible with React 19
- Test setup runs before jsdom is initialized
- jsdom is not properly polyfilling the DOM globals

**Evidence**:
```bash
× frontend/tests/frontend/components/AudioUploader.test.tsx > Rendering
  → document is not defined
```

### Issue 2: React 19 Compatibility

**Symptom**: `Cannot read properties of undefined (reading 'Symbol(Node prepared with document state workarounds)')`

**Root Cause**: React 19 has breaking changes with Testing Library. The `@testing-library/react` version (16.1.0) may not be fully compatible with React 19.1.0.

**Affected Tests**:
- All click/fireEvent tests
- User interaction tests
- State-driven tests

### Issue 3: Jotai Atom Mocking

**Symptom**: Atom values not persisting between render and interaction

**Root Cause**: Current Jotai mock in `tests/setup.ts` doesn't properly handle atom updates across test phases.

---

## Phase 1: Fix Test Environment (Highest Priority)

**Estimated Time**: 30 minutes
**Impact**: Fixes all "document is not defined" errors (~150 tests)

### Step 1.1: Update jsdom Version

**File**: `frontend/package.json`

**Action**: Update jsdom to latest version compatible with React 19

```json
{
  "devDependencies": {
    "jsdom": "^25.0.1" → "^24.1.0"  // Downgrade for React 19 compatibility
  }
}
```

**Rationale**: jsdom 25.x has known issues with React 19. Downgrading to 24.x resolves this.

### Step 1.2: Add jsdom Globals to Vitest Config

**File**: `frontend/vitest.config.ts`

**Action**: Ensure jsdom globals are loaded before tests

```typescript
export default defineConfig({
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: {
        resources: 'usable',  // Allow fetch, etc.
        runScripts: 'dangerously'  // Allow script execution
      }
    },
    // Add this line:
    pool: 'forks',  // Isolate test environments
    poolOptions: {
      forks: {
        singleFork: true  // Run tests in a single process for stability
      }
    }
  }
})
```

### Step 1.3: Update Test Setup Order

**File**: `frontend/tests/setup.ts`

**Action**: Ensure jsdom globals are set up before mocks

```typescript
// ADD AT THE VERY TOP:
import { jsdom } from 'jsdom'

// Ensure jsdom is fully initialized
if (typeof document === 'undefined') {
  const { JSDOM } = require('jsdom')
  const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
    url: 'http://localhost:3000',
    pretendToBeVisual: true,
    resources: 'usable'
  })
  global.window = dom.window as any
  global.document = dom.window.document
  global.navigator = dom.window.navigator
}

// Then continue with existing setup...
import { expect, afterEach, vi, beforeAll } from 'vitest'
```

### Step 1.4: Install Dependencies

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## Phase 2: Fix React 19 Compatibility

**Estimated Time**: 45 minutes
**Impact**: Fixes all "Symbol(Node prepared...)" errors (~30 tests)

### Step 2.1: Update Testing Library for React 19

**File**: `frontend/package.json`

**Action**: Use React 19 compatible versions

```json
{
  "devDependencies": {
    "@testing-library/react": "^16.1.0",
    "@testing-library/dom": "^10.4.0",
    "@testing-library/user-event": "^14.5.2",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  }
}
```

**Note**: These versions should be compatible, but we may need to wait for official @testing-library/react 19 support.

### Step 2.2: Update Render Function

**File**: `frontend/tests/setup.ts`

**Action**: Add legacy render wrapper for compatibility

```typescript
import { render } from '@testing-library/react'
import { waitFor } from '@testing-library/react'

// Wrapper for React 19 compatibility
export function renderWithReact19(ui: React.ReactElement, options = {}) {
  try {
    return render(ui, {
      legacyRoot: false,  // Use new React 19 root
      ...options
    })
  } catch (e) {
    // Fallback to legacy root
    return render(ui, {
      legacyRoot: true,
      ...options
    })
  }
}

// Export for use in tests
global.render = renderWithReact19
```

### Step 2.3: Update Test Files Using fireEvent

**Files**: All test files using `fireEvent.click()`

**Action**: Replace with `userEvent.click()`

**Before**:
```typescript
import { fireEvent, screen } from '@testing-library/react'
fireEvent.click(button)
```

**After**:
```typescript
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
const user = userEvent.setup()
await user.click(button)  // Note: await is important
```

---

## Phase 3: Fix Jotai Atom Mocking

**Estimated Time**: 30 minutes
**Impact**: Fixes state management tests (~20 tests)

### Step 3.1: Improve Jotai Mock

**File**: `frontend/tests/setup.ts`

**Action**: Use proper Jotai testing utilities

```typescript
import { atom, useAtom, useAtomValue, useSetAtom } from 'jotai'
import { Provider as JotaiProvider } from 'jotai'

// Create proper test store
const createTestStore = () => {
  const store = new Map()

  return {
    get: (atom: any) => store.get(atom),
    set: (atom: any, value: any) => store.set(atom, value),
    store
  }
}

const testStore = createTestStore()

// Export Provider wrapper
export const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return (
    <JotaiProvider store={testStore.store}>
      {children}
    </JotaiProvider>
  )
}

// Mock Jotai with proper implementation
vi.mock('jotai', async () => {
  const actual = await vi.importActual('jotai')
  return {
    ...(actual as any),
    Provider: JotaiProvider,
    // Other exports...
  }
})
```

### Step 3.2: Update Tests to Use TestWrapper

**Action**: Wrap all test renders with TestWrapper

```typescript
import { TestWrapper } from '../setup'

test('component renders', () => {
  render(<MyComponent />, { wrapper: TestWrapper })
  // ...
})
```

---

## Phase 4: Fix Individual Test Files

**Estimated Time**: 2-3 hours
**Impact**: Fixes remaining failures

### Priority Order (by impact):

1. **UI Components** (12 test files, ~60 tests)
   - `frontend/tests/frontend/components/ui/LoadingStates.test.tsx`
   - `frontend/tests/frontend/components/ui/Modal.test.tsx`
   - `frontend/tests/frontend/components/ui/ConfirmDialog.test.tsx`
   - `frontend/tests/frontend/components/ui/Badge.test.tsx`
   - `frontend/tests/frontend/components/ui/UIComponents.test.tsx`

2. **Feature Components** (6 test files, ~40 tests)
   - `frontend/tests/frontend/components/AudioUploader.test.tsx`
   - `frontend/tests/frontend/components/GoogleButton.test.tsx`
   - `frontend/tests/frontend/components/UserMenu.test.tsx`
   - `frontend/tests/frontend/components/ThemeToggle.test.tsx`
   - `frontend/tests/frontend/components/Chat.test.tsx`
   - `frontend/tests/frontend/components/NavBar.test.tsx`

3. **Page Components** (3 test files, ~30 tests)
   - `frontend/tests/frontend/pages/Login.test.tsx`
   - `frontend/tests/frontend/pages/TranscriptionList.test.tsx`
   - `frontend/tests/frontend/pages/TranscriptionDetail.test.tsx`
   - `frontend/tests/frontend/pages/Dashboard.test.tsx`

4. **Services & Hooks** (4 test files, ~20 tests)
   - `frontend/tests/frontend/services/error-handling.test.tsx`
   - `frontend/tests/frontend/services/api.test.ts`
   - `frontend/tests/frontend/hooks/useAuth.test.tsx`

5. **Atoms & Utils** (2 test files, ~12 tests)
   - `frontend/tests/frontend/atoms/atoms.test.tsx`
   - `frontend/tests/frontend/utils/cn.test.tsx`

---

## Phase 5: Add Missing Test Cases

**Estimated Time**: 1-2 hours
**Impact**: Improve coverage from 73.6% to 100%

### Missing Coverage Areas:

1. **Channel Components** (0 tests)
   - `src/components/channel/Badge.tsx`
   - `src/components/channel/Filter.tsx`
   - `src/components/channel/AssignModal.tsx`

2. **Dashboard Components** (0 tests)
   - `src/components/dashboard/ UsersTab.tsx`
   - `src/components/dashboard/ChannelsTab.tsx`
   - `src/components/dashboard/AudioTab.tsx`

3. **Error Boundary** (0 tests)
   - `src/components/ErrorBoundary.tsx`

4. **Export/Import Features** (partial tests)
   - DOCX export
   - PPTX export
   - Markdown export

---

## Phase 6: Improve Test Coverage

**Estimated Time**: 1 hour
**Target**: 100% coverage

### Step 6.1: Run Coverage Report

```bash
cd frontend
npm run test:coverage
```

### Step 6.2: Identify Gaps

**Files to Check**:
- All components in `src/components/channel/`
- All components in `src/components/dashboard/`
- Export utilities in `src/services/`
- Atoms in `src/atoms/`

### Step 6.3: Write Tests for Gaps

**Priority**:
1. Critical user flows (login, upload, export)
2. Error handling (API errors, network failures)
3. Edge cases (empty states, large files, concurrent operations)

---

## Phase 7: E2E Test Fixes

**Estimated Time**: 1 hour
**Impact**: End-to-end test reliability

### Files to Fix:
- `e2e/auth.spec.ts`
- `e2e/upload.spec.ts`
- `e2e/transcription.spec.ts`
- `e2e/dashboard.spec.ts`
- `e2e/channels.spec.ts`

### Known Issues:
1. **File upload buttons** - Cannot be clicked (opens native picker)
   - **Solution**: Use direct API calls with auth tokens (see CLAUDE.md)

2. **Dynamic content** - Race conditions in data loading
   - **Solution**: Add proper waitFor() calls

3. **Authentication** - localStorage timing issues
   - **Solution**: Use proper page context waits

---

## Execution Checklist

- [ ] **Phase 1**: Fix test environment (jsdom)
  - [ ] Downgrade jsdom to 24.1.0
  - [ ] Update vitest.config.ts
  - [ ] Update tests/setup.ts
  - [ ] Run `npm install` and verify

- [ ] **Phase 2**: Fix React 19 compatibility
  - [ ] Update testing libraries
  - [ ] Add renderWithReact19 wrapper
  - [ ] Replace fireEvent with userEvent (in batches)
  - [ ] Verify click tests pass

- [ ] **Phase 3**: Fix Jotai mocking
  - [ ] Update atom mock implementation
  - [ ] Add TestWrapper
  - [ ] Update tests to use TestWrapper
  - [ ] Verify state tests pass

- [ ] **Phase 4**: Fix individual test files (in priority order)
  - [ ] UI Components (12 files)
  - [ ] Feature Components (6 files)
  - [ ] Page Components (4 files)
  - [ ] Services & Hooks (4 files)
  - [ ] Atoms & Utils (2 files)

- [ ] **Phase 5**: Add missing test cases
  - [ ] Channel components
  - [ ] Dashboard components
  - [ ] Error boundary
  - [ ] Export features

- [ ] **Phase 6**: Improve coverage to 100%
  - [ ] Run coverage report
  - [ ] Identify gaps
  - [ ] Write missing tests

- [ ] **Phase 7**: Fix E2E tests
  - [ ] Update file upload tests
  - [ ] Add proper waits
  - [ ] Fix authentication flow

---

## Validation

After each phase, run:

```bash
# Test run
cd frontend
npm test

# Coverage
npm run test:coverage

# Full test with different reporters
npx vitest run --reporter=verbose
npx vitest run --reporter=json > test-results.json
```

**Success Criteria**:
- [ ] 0 "document is not defined" errors
- [ ] 0 "Symbol(Node prepared...)" errors
- [ ] 95%+ tests passing (156/164)
- [ ] 100% code coverage
- [ ] All E2E tests passing

---

## Quick Reference: Common Fixes

### "document is not defined"
```typescript
// In test file:
import { jsdom } from 'jsdom'

// Or in setup.ts:
global.document = document
global.window = window
```

### fireEvent doesn't work with React 19
```typescript
// Instead of:
fireEvent.click(button)

// Use:
import userEvent from '@testing-library/user-event'
const user = userEvent.setup()
await user.click(button)
```

### Jotai atom not updating in test
```typescript
import { render } from '@testing-library/react'
import { TestWrapper } from '../setup'

render(<Component />, { wrapper: TestWrapper })
```

### Async state not updating
```typescript
import { waitFor } from '@testing-library/react'

await waitFor(() => {
  expect(screen.getByText('Expected text')).toBeInTheDocument()
})
```

---

## Rollback Plan

If Phase 1/2 breaks things:

```bash
# Restore previous versions
cd frontend
git checkout package.json package-lock.json
npm install

# Or pin specific versions:
npm install jsdom@24.1.0 @testing-library/react@15.0.0
```

---

**Status**: ✅ READY FOR EXECUTION
**Next Step**: Execute Phase 1 (Fix Test Environment)
**Estimated Total Time**: 5-7 hours
