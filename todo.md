# Whisper Summarizer - Development Tasks

**Last Updated**: 2026-01-05
**Project Status**: Active Development

---

## Active Work: Frontend Test Fixes (PRIORITY)

**Status**: In Progress - Phase 1-2 Complete ✅
**Goal**: Fix 162 failing frontend tests and achieve 100% coverage

### Progress Summary

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Test Pass Rate | 1.2% (2/164) | **62.4% (186/298)** | 100% |
| Files Passing | 0% (0/59) | **20% (4/20)** | 100% |

### Completed ✅

- [x] **Phase 1**: Fix jsdom environment
  - [x] Update vitest.config.ts with jsdom options
  - [x] Add jsdom safety check in tests/setup.ts
  - [x] Fix syntax errors in cn.test.tsx

- [x] **Phase 2**: Fix React 19 compatibility
  - [x] Verify @testing-library/react works with React 19
  - [x] Confirm Modal tests pass (11/11)
  - [x] Confirm utils tests pass (25/26)

### In Progress 🔄

- [ ] **Phase 3**: Fix remaining 112 test failures
  - [ ] Fix test expectation mismatches (~50 tests)
  - [ ] Fix Jotai atom mocking issues (~30 tests)
  - [ ] Fix async timing issues (~20 tests)
  - [ ] Fix other component issues (~12 tests)

### Pending ⏳

- [ ] **Phase 4**: Add missing test cases
  - [ ] Channel components (Badge, Filter, AssignModal)
  - [ ] Dashboard components (UsersTab, ChannelsTab, AudioTab)
  - [ ] Error boundary tests
  - [ ] Export feature tests (DOCX, PPTX, Markdown)

- [ ] **Phase 5**: E2E test fixes
  - [ ] Fix file upload tests (use API calls)
  - [ ] Fix authentication flow
  - [ ] Fix dynamic content waits

- [ ] **Phase 6**: Achieve 100% coverage
  - [ ] Run coverage report
  - [ ] Identify remaining gaps
  - [ ] Write missing tests

### Documentation

- [x] Created `FRONTEND_TEST_FIXES.md` - Comprehensive 9-phase fix plan
- [x] Preserved `SERVER_RUNNER_SPLIT_PLAN.md` - Original server/runner architecture plan

---

## Server Tests (COMPLETE)

**Status**: ✅ All tests passing (107/107)
**Coverage**: 100%

### Created Test Files

- [x] `server/tests/conftest.py` - Main pytest configuration
- [x] `server/tests/backend/conftest.py` - Backend fixtures
- [x] `server/tests/backend/test_runner_api.py` - 35 tests for 6 runner endpoints
- [x] `server/tests/backend/test_audio_upload.py` - Audio upload tests
- [x] `server/tests/backend/test_health.py` - Health check tests

---

## Backend Tests (COMPLETE)

**Status**: ✅ All tests passing (107/107)
**Coverage**: 100%

---

## On Hold: Server/Runner Split

**Status**: Planned (see `SERVER_RUNNER_SPLIT_PLAN.md`)

The server/runner split architecture implementation plan is documented in `SERVER_RUNNER_SPLIT_PLAN.md`. This work is on hold while we focus on fixing frontend tests first.

**Key Points**:
- Split monolithic backend into lightweight server + GPU runner
- Server runs on cheap VPS (no GPU needed)
- Runner processes audio with faster-whisper + GLM API
- HTTP-based job queue communication

**Estimated Time**: 8-12 hours (when ready to implement)

---

## Quick Reference

### Test Commands

```bash
# Frontend tests
cd frontend
npm test                          # Run tests
npm run test:coverage            # Coverage report
npx vitest run --reporter=verbose # Detailed output

# Backend tests (legacy - being replaced by server/)
cd backend
pytest tests/backend/ -v

# Server tests
cd server
pytest tests/backend/ -v

# All tests
./run_test.sh all
```

### Test Status Dashboard

```
┌─────────────────────┬─────────┬──────────┬─────────┐
│ Component           │ Passing │ Failing  │ Coverage│
├─────────────────────┼─────────┼──────────┼─────────┤
│ Frontend Utils      │   25    │    1     │   96%   │
│ Frontend UI         │  100+   │   ~60    │   ~70%  │
│ Frontend Pages      │   ~30   │   ~30    │   ~50%  │
│ Frontend Services   │    2    │   ~20    │   ~10%  │
│ Server (new)        │   35+   │    0     │  100%   │
│ Backend (legacy)    │  107    │    0     │  100%   │
└─────────────────────┴─────────┴──────────┴─────────┘
```

---

## Priority Order

1. **HIGHEST**: Fix remaining 112 frontend test failures
2. **HIGH**: Add missing frontend test cases
3. **MEDIUM**: E2E test fixes
4. **LOW**: Server/Runner split implementation

---

## Notes

- **Test Environment**: Vitest with jsdom for frontend, pytest for backend
- **Frontend Framework**: React 19 + Vite + TypeScript
- **Backend Framework**: FastAPI + SQLAlchemy
- **Key Issues**: React 19 compatibility, Jotai mocking, async timing
- **Documentation**: See `FRONTEND_TEST_FIXES.md` for detailed fix plan

---

**Next Action**: Continue fixing remaining 112 frontend test failures (Phase 3)
