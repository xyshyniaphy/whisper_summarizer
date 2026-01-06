# Whisper Summarizer - Test Cases To Implement

**Last Updated**: 2026-01-06

---

## Current Test Status

| Suite | Tests | Status |
|-------|-------|--------|
| **Frontend** | 314/340 (92.4%) | 26 skipped (architectural issues) |
| **Backend** | 107/149 (71.8%) | 42 skipped (permanent/integration) |

---

## Frontend Tests To Create

### api.test.ts (16 tests - Mock Redesign Required)

**Issue**: Axios mock initialization causes timeout. Requires complete mock architecture redesign.

```
uploadAudio(file)
- should upload audio file with FormData
- should set Content-Type header to multipart/form-data
- should handle upload errors
- should return transcription data on success

getTranscriptions(params)
- should fetch transcriptions list
- should pass pagination parameters
- should pass status filter parameters
- should handle API errors

getTranscription(id)
- should fetch single transcription
- should handle 404 errors
- should handle malformed UUID

deleteTranscription(id)
- should delete transcription
- should handle delete errors

getDownloadUrl(id, format)
- should generate correct URL for TXT format
- should generate correct URL for SRT format
- should handle invalid formats
```

### useAuth.test.tsx (8 tests - Hook Refactoring Required)

**Issue**: `isUnitTestMode()` check prevents auth calls. Requires hook refactoring.

```
isUnitTestMode()
- should detect Vitest environment
- should detect NODE_ENV=test
- should return true when global.vi exists
- should return false in production

signInWithGoogle()
- should call Supabase signInWithOAuth with correct params
- should handle OAuth errors
- should update user state on success

signOut()
- should call Supabase signOut
- should clear user state
- should handle signOut errors
```

### Dashboard.test.tsx (2 tests - Separate Test Files Required)

**Issue**: Tests require `vi.doMock` which doesn't work inside test blocks.

```
Access Control
- should redirect non-admin users from dashboard
- should show admin panel only to admin users

Loading State
- should show loading spinner while fetching data
- should render content after data loads
```

---

## Backend Tests To Create

### app/api/transcriptions.py (Increase coverage from 48% to 70%)

**Lines needing tests**: 50-58, 87, 112-122, 160-161, 197-248, 267-268, 286-304, 322-323, 335-347, 378-461, 489-626, 651-699, 715-716, 749-751, 848-850, 864-865, 913-938, 988-989, 1007-1010, 1071

```
POST /api/transcriptions/{id}/chat/stream
- should handle SSE streaming errors
- should validate message content
- should handle transcription not found
- should handle missing transcription text
- should rate limit requests

GET /api/transcriptions/{id}/download
- should handle missing summary
- should validate format parameter
- should handle export errors
- should generate correct content-type headers

DELETE /api/transcriptions/all
- should only delete user's own transcriptions
- should handle empty list
- should validate admin permission
```

### app/services/formatting_service.py (Increase coverage from 12% to 70%)

**Lines needing tests**: 70-72, 76-82, 97-144, 159-218, 230-254, 264-267

```
format_text_as_srt()
- should handle empty text
- should handle long text (>1000 lines)
- should validate timestamp format
- should handle unicode characters
- should handle overlapping timestamps

format_text_as_txt()
- should preserve line breaks
- should handle empty text
- should strip excessive whitespace

format_text_as_docx()
- should handle chinese characters
- should handle empty text
- should validate document structure
```

### app/services/notebooklm_service.py (Increase coverage from 26% to 70%)

**Lines needing tests**: 75-86, 95-96, 115-166, 176-179

```
generate_guidelines()
- should handle missing API key
- should validate API response
- should handle rate limiting
- should handle malformed response
- should cache results

create_notebooklm_guide()
- should handle missing transcription
- should validate guide format
- should handle API timeout
```

### app/services/storage_service.py (Increase coverage from 49% to 70%)

**Lines needing tests**: 34-36, 73-75, 109-111, 137-139, 151-156, 203-205, 221-240, 260-262, 274-279, 326-328, 343-362, 382-384, 410-427, 442-463, 483-484, 489-491, 507-508, 534-551, 566-587, 607-608, 613-615, 631-632

```
save_transcription_text()
- should handle large files (>10MB)
- should validate compression
- should handle disk full errors
- should validate UUID format

get_transcription_text()
- should handle missing files
- should validate decompression
- should handle corrupted gzip data
- should cache results

delete_transcription_text()
- should validate file existence
- should handle permission errors
- should cleanup cache

get_audio_file_path()
- should validate UUID format
- should handle missing files
- should return absolute path
```

### app/services/transcription_processor.py (Increase coverage from 61% to 70%)

**Lines needing tests**: 90-96, 107-110, 123-124, 151-171, 197, 217, 271-272, 280-284, 292-298, 302-306, 312-316, 319, 325-326, 341-361, 446, 479-483, 506-533, 549-550, 558-559, 584, 622-626, 648-649, 656-682, 698

```
process_transcription()
- should handle audio processing errors
- should validate audio format
- should handle timeout
- should update status correctly
- should cleanup temporary files

_chunk_and_transcribe()
- should handle audio splitting errors
- should validate chunk size
- should handle VAD errors
- should merge results correctly

_generate_summary()
- should handle missing GLM API key
- should validate API response
- should handle rate limiting
- should handle timeout errors
```

### app/tasks/cleanup.py (Increase coverage from 43% to 70%)

**Lines needing tests**: 36-93

```
cleanup_old_transcriptions()
- should respect retention days
- should handle database errors
- should validate file permissions
- should log cleanup actions
- should handle interrupted cleanup
```

---

## Test Execution Commands

### Frontend
```bash
./run_test.sh frontend    # Run all frontend tests
bun run test              # Run with watch mode
```

### Backend
```bash
./run_test.sh backend     # Run all backend tests via Docker
docker compose -f tests/docker-compose.test.yml run --rm backend-test
```

---

## Test Coverage Goals

| Suite | Current | Target | Gap |
|-------|---------|--------|-----|
| Frontend | 73.6% | 100% | 26.4% |
| Backend | 53.84% | 70% | 16.16% |
