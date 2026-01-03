# todo-v2-frontend-fixes.md

**Created**: 2026-01-04 03:41 UTC
**Purpose**: Resolve 90 failing frontend tests and improve overall test coverage
**Based on**: todo.md (completed) - 2026-01-03 17:53 UTC
**Current Status**: 209 passing / 90 failing (69.9% pass rate)

---

## Executive Summary

The original **todo.md** successfully created 123 frontend tests and achieved 69.9% pass rate. This **todo-v2** focuses on:

1. **Fix 90 failing frontend tests** to improve pass rate from 69.9% to 90%+
2. **Fix test infrastructure issues** (import paths, missing files, transform errors)
3. **Fix component-specific test failures** (DOM selectors, assertions, mocks)
4. **Fix page-level tests** (Router context, data loading, integration)

---

## Current Test Status

| Category | Tests | Passing | Failing | Pass Rate | Target |
|----------|-------|---------|---------|-----------|--------|
| Frontend Unit | 299 | 209 | 90 | 69.9% | 90%+ |
| Backend Services | 248 | 225 | 23 | 90.7% | 95%+ |
| Backend API | 107 | 107 | 0 | 100% | 100% |
| **TOTAL** | **654** | **541** | **113** | **82.7%** | **90%+** |

---

## Frontend Test Failure Analysis

### Category 1: Test Infrastructure Issues (High Priority)

#### 1.1 Import Path Errors (3 files, ~15 tests)

**Files Affected**:
- `tests/frontend/pages/Login.test.tsx`
- `tests/frontend/components/ui/UIComponents.test.tsx`
- `tests/frontend/utils/cn.test.ts`

**Issues**:
```
Error: Failed to resolve import "../../src/pages/Login" from "tests/frontend/pages/Login.test.tsx"
Error: Failed to resolve import "../../../src/components/ui/Button" from "tests/frontend/components/ui/UIComponents.test.tsx"
```

**Root Cause**: Test files use relative imports that don't match actual file structure

**Fix Strategy**:
1. Verify actual component locations in `frontend/src/`
2. Update import paths to use correct relative paths
3. Consider using path aliases (`@/`) for consistency

**Estimated Effort**: 1-2 hours
**Expected Impact**: +15 tests passing

---

#### 1.2 Transform Errors (2 files, ~10 tests)

**Files Affected**:
- `tests/frontend/atoms/atoms.test.ts`
- `tests/frontend/hooks/useAuth.test.ts`

**Issues**:
```
Error: Transform failed with 1 error
```

**Root Cause**: JSX/TypeScript syntax in files that Vitest cannot parse

**Fix Strategy**:
1. Check if `.tsx` extension is used incorrectly
2. Verify vitest.config.ts has proper transformers
3. Ensure JSX imports are correct

**Estimated Effort**: 1-2 hours
**Expected Impact**: +10 tests passing

---

#### 1.3 API Client Mock Issues (1 file, ~10 tests)

**File Affected**:
- `tests/frontend/services/api.test.ts`

**Issue**:
```
TypeError: undefined is not an object (evaluating 'apiClient.interceptors')
```

**Root Cause**: apiClient mock not properly set up

**Fix Strategy**:
1. Review how apiClient is mocked
2. Add proper interceptor mock setup
3. Ensure axios mock is properly configured

**Estimated Effort**: 1-2 hours
**Expected Impact**: +10 tests passing

---

### Category 2: Component Test Failures (Medium Priority)

#### 2.1 Channel Components (1 file, ~30 tests)

**File Affected**:
- `tests/frontend/components/channel/ChannelComponents.test.tsx`

**Issues**:
```
Error: Unable to find an accessible element with the role: "textbox"
Error: Unable to find an accessible element with the role: "combobox"
Error: expected null to be truthy (cancel button not found)
```

**Tests Failing**:
- ChannelAssignModal: ~30 tests
- ChannelFilter: ~10 tests
- ChannelBadge: passing (28 tests, 89% pass rate)

**Root Cause**: Component uses different DOM structure than expected

**Fix Strategy**:
1. Inspect actual component DOM structure
2. Update selectors to use correct roles/classes
3. Check if loading state affects DOM rendering
4. Verify Chinese text matches ('取消', '选择所有')

**Estimated Effort**: 3-4 hours
**Expected Impact**: +30 tests passing

---

#### 2.2 UI Components (3 files, ~5 tests)

**Files Affected**:
- `tests/frontend/components/ui/Accordion.test.tsx` (1 failure)
- `tests/frontend/components/ui/Modal.test.tsx` (2 failures)
- `tests/frontend/components/ui/ConfirmDialog.test.tsx` (2 failures)

**Specific Issues**:

**Accordion.test.tsx**:
```typescript
// Expected: bg-white dark:bg-gray-900 p-4
// Received: border dark:border-gray-700 rounded-lg overflow-hidden
// Fix: Parent element has the class, not content wrapper
```

**ConfirmDialog.test.tsx**:
```typescript
// Issue: Warning icon not found in message area
// Fix: Icon is in separate container, check correct parent
```

**Modal.test.tsx**:
```typescript
// Issue: Overlay and padding selectors incorrect
// Fix: Use correct DOM traversal for portal-rendered content
```

**Estimated Effort**: 1-2 hours
**Expected Impact**: +5 tests passing

---

#### 2.3 AudioUploader Component (1 file, ~10 tests)

**File Affected**:
- `tests/frontend/components/AudioUploader.test.tsx`

**Issues**:
```
TypeError: Failed to set the 'files' property on 'HTMLInputElement': The provided value is not of type 'FileList'.
```

**Root Cause**: FileList object not properly created in tests

**Fix Strategy**:
1. Create proper DataTransfer object for modern browsers
2. Update file upload mock to use correct FileList API
3. Test with actual File objects wrapped in FileList

**Code Pattern**:
```typescript
// Instead of:
input.files = [file] as any

// Use:
const dataTransfer = new DataTransfer()
dataTransfer.items.add(file)
input.files = dataTransfer.files
```

**Estimated Effort**: 2-3 hours
**Expected Impact**: +10 tests passing

---

### Category 3: Page-Level Test Failures (Low Priority)

#### 3.1 Router Context Issues (2 files, ~40 tests)

**Files Affected**:
- `tests/frontend/pages/TranscriptionDetail.test.tsx` (~30 tests)
- `tests/frontend/pages/TranscriptionList.test.tsx` (~10 tests)

**Issue**:
```
Error: useRoutes() may be used only in the context of a <Router> component.
```

**Root Cause**: Pages tested without RouterProvider wrapper

**Fix Strategy**:
1. Update test setup to include Router context
2. Use createMemoryRouter for isolated page testing
3. Mock useNavigate and useParams hooks

**Code Pattern**:
```typescript
// In test setup:
const router = createMemoryRouter([{
  path: '/transcriptions/:id',
  element: <TranscriptionDetail />
}], {
  initialEntries: ['/transcriptions/test-id']
})

render(
  <RouterProvider router={router} />
)
```

**Estimated Effort**: 4-6 hours
**Expected Impact**: +40 tests passing

---

### Category 4: Skipped Jotai-Dependent Tests (Documented)

The following components are **intentionally not tested** at unit level due to Jotai dependencies:

- ChannelFilter.tsx
- ChannelAssignModal.tsx
- UserManagementTab.tsx
- ChannelManagementTab.tsx
- AudioManagementTab.tsx

**Reason**: Jotai atoms require full React context and cannot be easily mocked
**Alternative**: E2E tests (116 scenarios, 100% passing)

---

## IMPROVEMENT PHASES

### Phase 1: Fix Test Infrastructure (Quick Wins)

**Priority**: HIGH
**Effort**: 3-6 hours
**Impact**: +35 tests passing

#### Tasks
1. [ ] Fix import paths in Login.test.tsx
2. [ ] Fix import paths in UIComponents.test.tsx
3. [ ] Fix transform errors in atoms.test.ts and useAuth.test.ts
4. [ ] Fix apiClient mock in api.test.ts
5. [ ] Verify all test files can be parsed

**Acceptance Criteria**:
- All import errors resolved
- All transform errors resolved
- Tests can run without infrastructure errors

---

### Phase 2: Fix Component Tests (Medium Effort)

**Priority**: HIGH
**Effort**: 6-9 hours
**Impact**: +45 tests passing

#### Tasks

**Channel Components** (3-4 hours, +30 tests):
1. [ ] Fix ChannelAssignModal DOM selectors
2. [ ] Fix ChannelFilter loading states
3. [ ] Update Chinese text assertions
4. [ ] Verify all channel component tests pass

**UI Components** (1-2 hours, +5 tests):
1. [ ] Fix Accordion padding assertion
2. [ ] Fix ConfirmDialog icon selector
3. [ ] Fix Modal overlay selector
4. [ ] Verify all UI component tests pass

**AudioUploader** (2-3 hours, +10 tests):
1. [ ] Fix FileList creation in tests
2. [ ] Update file upload mock pattern
3. [ ] Test drag-drop with DataTransfer
4. [ ] Verify all AudioUploader tests pass

**Acceptance Criteria**:
- Component tests target 95%+ pass rate
- All DOM selectors use correct roles/classes
- File upload tests work with modern FileList API

---

### Phase 3: Fix Page-Level Tests (Higher Effort)

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Impact**: +40 tests passing

#### Tasks

**Router Context Setup** (2-3 hours):
1. [ ] Create router test utility function
2. [ ] Update TranscriptionDetail.test.tsx with Router
3. [ ] Update TranscriptionList.test.tsx with Router
4. [ ] Mock navigation and routing hooks

**Data Integration** (2-3 hours):
1. [ ] Fix data loading in TranscriptionList
2. [ ] Fix data display in TranscriptionDetail
3. [ ] Verify date formatting tests
4. [ ] Verify status badge tests

**Acceptance Criteria**:
- Page tests have proper Router context
- Data loading mocks work correctly
- All page-level tests pass

---

## TARGET METRICS

### Success Criteria

| Metric | Current | Target | Delta |
|--------|---------|--------|-------|
| **Frontend Pass Rate** | 69.9% | 90%+ | +20.1% |
| **Frontend Passing Tests** | 209 | 270+ | +61 |
| **Overall Pass Rate** | 82.7% | 90%+ | +7.3% |
| **Test Infrastructure** | Broken | Fixed | 100% |

### Phase Completion Goals

| Phase | Tests Fixed | Pass Rate | Status |
|-------|-------------|-----------|--------|
| Phase 1: Infrastructure | +35 | 81.6% | Pending |
| Phase 2: Components | +45 | 93.1% | Pending |
| Phase 3: Pages | +40 | 95%+ | Pending |
| **TOTAL** | **+120** | **95%+** | - |

---

## IMPLEMENTATION GUIDELINES

### Test File Structure

```
tests/
├── frontend/
│   ├── components/
│   │   ├── ui/           # Button, Modal, Accordion, etc.
│   │   ├── channel/      # ChannelBadge, ChannelFilter, etc.
│   │   └── AudioUploader.test.tsx
│   ├── pages/            # Login, Dashboard, TranscriptionList, TranscriptionDetail
│   ├── hooks/            # useAuth
│   ├── atoms/            # Jotai atoms (may skip)
│   ├── services/         # API client
│   └── utils/            # cn utility
```

### Running Tests

```bash
# Run all frontend tests
./run_test.sh frontend

# Run specific test file
bun test tests/frontend/components/ui/Button.test.tsx

# Run with coverage
bun test --coverage

# Watch mode
bun test --watch
```

### Debugging Failed Tests

```bash
# Run with verbose output
bun test --reporter=verbose

# Run only failed tests from last run
bun test --run --bail

# Run specific test pattern
bun test --grep "Accordion"
```

---

## TRACKING PROGRESS

### Phase 1 Checklist: Test Infrastructure

- [ ] Fix import paths (3 files, ~15 tests)
  - [ ] Login.test.tsx import path
  - [ ] UIComponents.test.tsx import path
  - [ ] cn.test.ts imports
- [ ] Fix transform errors (2 files, ~10 tests)
  - [ ] atoms.test.ts transform
  - [ ] useAuth.test.ts transform
- [ ] Fix API mock (1 file, ~10 tests)
  - [ ] api.test.ts apiClient mock

**Expected Result**: +35 tests passing (81.6% pass rate)

---

### Phase 2 Checklist: Component Tests

- [ ] Fix Channel components (1 file, ~30 tests)
  - [ ] ChannelAssignModal selectors
  - [ ] ChannelFilter states
  - [ ] Text assertions (Chinese)
- [ ] Fix UI components (3 files, ~5 tests)
  - [ ] Accordion padding
  - [ ] ConfirmDialog icon
  - [ ] Modal overlay
- [ ] Fix AudioUploader (1 file, ~10 tests)
  - [ ] FileList creation
  - [ ] DataTransfer pattern

**Expected Result**: +45 tests passing (93.1% pass rate)

---

### Phase 3 Checklist: Page Tests

- [ ] Fix Router context (2 files, ~40 tests)
  - [ ] TranscriptionDetail.test.tsx Router
  - [ ] TranscriptionList.test.tsx Router
- [ ] Fix data integration
  - [ ] Data loading mocks
  - [ ] Date formatting
  - [ ] Status badges

**Expected Result**: +40 tests passing (95%+ pass rate)

---

## ESTIMATED TOTAL EFFORT

| Phase | Files | Tests | Effort | Priority |
|-------|-------|-------|--------|----------|
| Phase 1: Infrastructure | 6 | +35 | 3-6 hours | HIGH |
| Phase 2: Components | 5 | +45 | 6-9 hours | HIGH |
| Phase 3: Pages | 2 | +40 | 4-6 hours | MEDIUM |
| **TOTAL** | **13** | **+120** | **13-21 hours** | - |

**Conservative Estimate**: Complete in 2-3 days with focused development

---

## NOTES

### Why Focus on Frontend First

1. **Quick Wins**: Infrastructure fixes are fast and high-impact
2. **Broken Tests**: 90/299 failing frontend tests = 30% failure rate
3. **Backend Already Good**: 90.7% pass rate, 100% API pass rate
4. **User Experience**: Frontend tests directly impact UI reliability

### What About Backend Tests

Backend tests are already in good shape:
- Backend Services: 90.7% pass rate (225/248)
- Backend API: 100% pass rate (107/107)

The 23 failing backend tests can be addressed in a future **todo-v3-backend-fixes.md**

---

**Status**: 📋 **PLANNED** - 2026-01-04 03:41 UTC
**Based On**: todo.md (completed 2026-01-03 17:53 UTC)
**Owner**: Development Team
**Priority**: **HIGH** - Improve frontend pass rate from 69.9% to 90%+

---

## NEXT STEPS

### Immediate Actions (Today)

1. ✅ **Read todo.md** (completed - all tasks done)
2. ✅ **Analyze failing tests** (completed - 90 failures categorized)
3. ✅ **Create todo-v2-frontend-fixes.md** (this file)
4. [ ] **Start Phase 1**: Fix test infrastructure issues

### This Week

1. Complete Phase 1 (Infrastructure)
2. Complete Phase 2 (Component Tests)
3. Start Phase 3 (Page Tests)

### Success Metrics

- [x] Current: 209/299 passing (69.9%)
- [ ] Target: 270+/299 passing (90%+)
- [ ] Goal: All infrastructure errors fixed
- [ ] Goal: All component tests passing
- [ ] Goal: Page tests with Router context
