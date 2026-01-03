# Test Fixes TODO

## Overview
Fix all failing test cases to achieve full test suite coverage and passing status.

## Test Results Summary

### Backend Tests
**Status**: 98 passed, 36 failed (138 total)
**Coverage**: 51.96% (target: 70%)

### Frontend Tests
**Status**: 78 passed, 73 failed (151 total)

---

## Backend Test Fixes

### Critical Fixes (Blocking Tests)

#### 1. Auth API Tests (`tests/backend/api/test_auth_api.py`)
**Issues**:
- `test_signup_success` - Module `app.api.auth` has no attribute 'sign_up'
- `test_signup_invalid_email` - Returns 404 instead of 422
- `test_login_success` - Module has no attribute 'sign_in'
- `test_login_wrong_password` - Module has no attribute 'sign_in'
- `test_protected_endpoint_with_real_auth_client` - Returns 401

**Root Cause**: Auth endpoints were migrated to Supabase, tests expect old custom auth

**Action**: Update tests to use Supabase auth flow or mark as deprecated

---

#### 2. Audio API Tests (`tests/backend/api/test_audio_api.py`)
**Issues**:
- `test_upload_audio_success` - Returns 401 (Unauthorized)
- `test_get_transcriptions_list` - Returns 401
- `test_delete_transcription` - TypeError: string indices must be integers

**Root Cause**: Authentication middleware changes

**Action**: Fix auth token setup in test fixtures

---

#### 3. Transcription Channels API (`tests/backend/api/test_transcription_channels_api.py`)
**Issues**:
- Multiple tests: `NameError: name 'status' is not defined`
- `test_assign_to_multiple_channels` - InvalidRequestError: UUID type mismatch
- `test_scenario_create_channels_if_not_exist_and_assign` - Expects 200, gets 201
- Multiple tests: InvalidRequestError with UUID matching issues

**Root Cause**:
1. Missing `status` variable import
2. UUID type conversion issues in database queries
3. HTTP status code expectations wrong (201 is correct for created)

**Actions**:
- Add missing `status` import
- Fix UUID type handling in database queries
- Update expected status codes (201 not 200)

---

#### 4. Summarize API Tests (`tests/backend/api/test_summarize_api.py`)
**Issues**:
- All tests: `AttributeError: property 'original_text' of 'Transcription' object has no setter`

**Root Cause**: `original_text` is a read-only property

**Action**: Update tests to not try to set `original_text`, use proper model methods

---

#### 5. Markdown API Tests (`tests/backend/api/test_markdown_api.py`)
**Issues**:
- All tests: Returns 404 (endpoint doesn't exist)

**Root Cause**: Markdown endpoints may have been removed or moved

**Action**: Verify if endpoints exist, update or remove tests

---

#### 6. Share API Tests (`tests/backend/api/test_share_api.py`)
**Issues**:
- Multiple tests: `PendingRollbackError` due to ForeignKeyViolation
- `transcriptions_user_id_fkey` violation - user_id not present in users table

**Root Cause**: Test creates transcription without first creating user

**Action**: Fix test fixtures to ensure user exists before creating transcriptions

---

#### 7. Chat API Tests (`tests/backend/api/test_chat_api.py`)
**Issues**:
- `test_get_chat_history_success` - PendingRollbackError from UUID type mismatch
- `test_send_chat_message_empty_content` - Expects 422, gets 400
- `test_stream_chat_success` - `AttributeError: module 'app.services' has no attribute 'api'`

**Root Cause**:
1. UUID type mismatch in database queries
2. Validation error code mismatch
3. Import error in services module

**Actions**:
- Fix UUID type handling
- Update expected error code (400 is valid for empty content)
- Fix import statement

---

#### 8. Users API Tests (`tests/backend/api/test_users_api.py`)
**Issues**:
- All tests: Return 401 (Unauthorized)

**Root Cause**: Authentication setup issues

**Action**: Fix auth token in test fixtures

---

#### 9. Transcriptions CRUD Tests (`tests/backend/api/test_transcriptions_crud.py`)
**Issues**:
- `test_list_transcriptions_success` - Returns 401
- `test_list_transcriptions_filters_by_stage` - Returns 401

**Root Cause**: Authentication issues

**Action**: Fix auth token setup

---

#### 10. Full Workflow Integration Test (`tests/backend/integration/test_full_workflow.py`)
**Issue**:
- `test_full_transcription_workflow` - Test file not found: `/app/testdata/audio1074124412.conved_2min.m4a`

**Root Cause**: Test audio file missing

**Action**: Either add the test file or update test to use a different approach

---

## Frontend Test Fixes

### Critical Issues

#### 1. Test Timeouts (73 tests)
**Issue**: Most TranscriptionDetail tests timeout after 5 seconds
**Root Cause**: Tests may be making actual HTTP requests instead of using mocks

**Action**:
- Increase timeout or fix mocking
- Ensure MSW (Mock Service Worker) is properly configured
- Check for infinite loops or pending promises

---

#### 2. API Connection Errors
**Issue**: `ECONNREFUSED` errors in multiple tests
**Root Cause**: Tests trying to make real HTTP requests instead of using mocks

**Action**:
- Verify MSW setup in test configuration
- Check that API calls are properly mocked
- Ensure test environment doesn't have live API endpoints

---

#### 3. Router Warnings
**Issue**: "No routes matched location '/'" in many tests
**Root Cause**: React Router not properly mocked in test environment

**Action**:
- Add proper routing mock in test setup
- Use MemoryRouter in tests that require routing
- Update test setup files

---

#### 4. Unhandled Errors
**Issue**: 1 unhandled error during test run
**Action**: Investigate and fix the error source

---

## Priority Order

### Phase 1: Core Infrastructure (High Priority)
1. Fix authentication/authorization in test fixtures (affects 30+ tests)
2. Fix UUID type handling in database queries (affects 10+ tests)
3. Fix test mocking infrastructure for frontend (affects 70+ tests)

### Phase 2: API Tests (Medium Priority)
4. Update auth API tests for Supabase migration
5. Fix transcription channels API tests
6. Fix summarize API tests (original_text property)
7. Fix chat API tests

### Phase 3: Integration Tests (Low Priority)
8. Fix share API tests (foreign key issues)
9. Fix markdown API tests (verify endpoints)
10. Fix full workflow integration test (missing file)

### Phase 4: Coverage Improvements
11. Add tests for uncovered code paths
12. Increase coverage from 51.96% to 70%

---

## Files to Modify

### Backend
- `tests/backend/conftest.py` - Fix auth fixtures
- `tests/backend/api/test_auth_api.py` - Update for Supabase
- `tests/backend/api/test_transcription_channels_api.py` - Fix imports and status codes
- `tests/backend/api/test_summarize_api.py` - Fix property setter issues
- `tests/backend/api/test_chat_api.py` - Fix imports and validation
- `tests/backend/integration/test_full_workflow.py` - Add missing test file or update

### Frontend
- `tests/frontend/setup.ts` - Fix MSW configuration
- `tests/frontend/components/NavBar.test.tsx` - Fix routing
- `tests/frontend/pages/TranscriptionDetail.test.tsx` - Fix timeouts and API mocking
- `tests/frontend/pages/TranscriptionList.test.tsx` - Fix API mocking

---

## Testing Strategy

1. **Fix by Category**: Group related test failures and fix together
2. **Incremental Validation**: Run tests after each fix to prevent regressions
3. **Mock Verification**: Ensure all external dependencies are properly mocked
4. **Fixture Updates**: Keep test fixtures in sync with codebase changes

---

## Success Criteria

- [ ] All backend tests passing (138/138)
- [ ] All frontend tests passing (151/151)
- [ ] Coverage at 70% or higher
- [ ] No timeout errors
- [ ] No unhandled errors
- [ ] All tests use proper mocks (no live API calls)

---

## Notes

- Many test failures are due to codebase evolution (Supabase migration, faster-whisper migration)
- Some tests may be obsolete and need removal rather than fixing
- Focus on fixing test infrastructure first, then individual tests
- Consider updating tests to match current API contracts rather than changing working code
