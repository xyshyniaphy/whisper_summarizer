# Service Migration Analysis
## Old Backend vs Current Server/Runner Architecture

**Analysis Date**: 2026-01-10
**Old Backend**: `backend.backup.20250108/app/services/`
**Current Server**: `server/app/services/`
**Current Runner**: `runner/app/services/`

---

## Service Comparison Matrix

| Service | Old Backend | Current Server | Current Runner | Status | Notes |
|---------|-------------|-----------------|-----------------|--------|-------|
| **whisper_service.py** | ✅ | ❌ | ✅ | **MOVED** | GPU transcription moved to runner |
| **transcription_processor.py** | ✅ | ❌ | ✅ | **MOVED** | Orchestration moved to runner |
| **formatting_service.py** | ✅ | ✅ (unused) | ✅ | **MOVED** | Text formatting + summary generation |
| **storage_service.py** | ✅ | ✅ | ✅ | **DUPLICATE** | Exists in both (should be server-only) |
| **process_audio.py** | ✅ | ✅ (unused) | ❌ | **UNUSED** | Audio processing utilities |
| **notebooklm_service.py** | ✅ | ✅ (unused) | ❌ | **BROKEN** | Service exists but not integrated |
| **pptx_service.py** | ✅ | ✅ (unused) | ❌ | **BROKEN** | Service exists but not integrated |

---

## Detailed Analysis

### 1. whisper_service.py ✅ MOVED
**Location**: `runner/app/services/whisper_service.py`
- **Purpose**: faster-whisper GPU transcription
- **Status**: Properly migrated to runner
- **Dependencies**: CUDA, faster-whisper, cuDNN
- **Correct**: ✅ GPU processing should be in runner

### 2. transcription_processor.py ✅ MOVED
**Location**: `runner/app/services/transcription_processor.py`
- **Purpose**: Orchestrate transcription workflow (transcribe → format → summarize)
- **Status**: Properly migrated to runner
- **Functions**:
  - `process_audio()` - Main entry point
  - `_transcribe()` - Whisper transcription
  - `_format_text()` - LLM formatting
  - `_summarize_with_retry()` - GLM summarization (was missing, now fixed)
  - `_generate_notebooklm_guideline()` - NotebookLM guideline
- **Correct**: ✅ Orchestration moved to runner

### 3. formatting_service.py ✅ MOVED + ENHANCED
**Location**: `runner/app/services/formatting_service.py`
- **Purpose**: Text formatting and summary generation
- **Status**: Enhanced to include summary generation
- **Changes**:
  - Old: Only formatted text (punctuation, paragraphs)
  - New: Formats text + generates summary via GLM API
- **Recent Fix**: Added `_generate_summary()` method
- **Correct**: ✅ Now generates summaries as expected

### 4. storage_service.py ⚠️ DUPLICATE
**Locations**:
- `server/app/services/storage_service.py`
- `runner/app/services/storage_service.py`

**Purpose**: File storage (transcriptions, segments, guidelines)

**Status**: DUPLICATE - Should be server-only

**Functions**:
- `save_transcription_text()` - Save transcribed text
- `save_transcription_segments()` - Save timestamp segments
- `save_original_output()` - Save debug output
- `save_formatted_text()` - Save formatted text
- `save_notebooklm_guideline()` - Save NotebookLM guideline
- `get_transcription_text()` - Retrieve text
- Various delete methods

**Issue**: Runner doesn't need storage_service - it should send results to server via API
**Recommendation**: Remove from runner, keep in server only

### 5. process_audio.py ❌ UNUSED
**Location**: `server/app/services/process_audio.py`
- **Purpose**: Audio processing utilities (SRT parsing, health check)
- **Functions**:
  - `parse_srt()` - Parse SRT subtitle files
  - `health_check()` - Check ffmpeg availability
- **Status**: Exists but not used in current architecture
- **Impact**: Low - utility functions only
- **Recommendation**: Can be removed or kept for future use

### 6. notebooklm_service.py ❌ BROKEN
**Location**: `server/app/services/notebooklm_service.py`
- **Purpose**: Generate NotebookLM guidelines for presentation slides
- **Status**: Service exists but NOT integrated into workflow
- **Integration Points**:
  - `runner/app/services/transcription_processor.py:324` - Called in `_generate_notebooklm_guideline()`
  - `server/app/api/transcriptions.py` - Has `download_notebooklm` endpoint
- **Issue**:
  - Runner has the code to generate guidelines (`_generate_notebooklm_guideline()`)
  - But runner sends results to server via API
  - Server doesn't have a way to receive/store guidelines from runner
  - `transcription.pptx_status` field exists but never updated
- **Database Schema**:
  ```sql
  pptx_status VARCHAR DEFAULT 'not-started'  -- not-started, generating, ready, error
  pptx_error_message TEXT
  ```
- **Impact**: HIGH - Feature is partially implemented but non-functional
- **Recommendation**:
  - Option 1: Move NotebookLM generation to server (after transcription completes)
  - Option 2: Add guideline to JobResult schema so runner can send it
  - Option 3: Remove this feature entirely if not needed

### 7. pptx_service.py ❌ BROKEN
**Location**: `server/app/services/pptx_service.py`
- **Purpose**: Generate PowerPoint presentations from transcriptions
- **Status**: Service exists but NOT integrated into workflow
- **Integration Points**:
  - Linked to `pptx_status` field in transcriptions table
  - No API endpoint to trigger generation
  - No automated workflow
- **Issue**: Same as NotebookLM - partially implemented but non-functional
- **Impact**: HIGH - Feature is partially implemented but non-functional
- **Recommendation**: Same as NotebookLM

---

## Missing Features

### 1. NotebookLM Guideline Generation
**Expected Flow**:
1. User uploads audio
2. Runner transcribes and formats
3. Runner generates NotebookLM guideline
4. User downloads guideline from API

**Actual Flow**:
- Step 3 happens (runner generates guideline)
- But guideline is NOT sent to server (not in JobResult schema)
- Server never receives or stores the guideline
- Download endpoint exists but returns 404

**Fix Required**:
```python
# runner/app/models/job_schemas.py
class JobResult(BaseModel):
    text: str
    summary: Optional[str] = None
    notebooklm_guideline: Optional[str] = None  # ADD THIS
    processing_time_seconds: int
```

### 2. PPTX Generation
**Expected Flow**:
1. User clicks "Generate PPTX"
2. Server generates PowerPoint from transcription
3. User downloads PPTX file

**Actual Flow**:
- Step 1 doesn't exist (no API endpoint)
- Service exists but never called
- `pptx_status` always "not-started"

**Fix Required**:
- Add API endpoint to trigger PPTX generation
- Call `pptx_service` from that endpoint
- Update `pptx_status` during generation

---

## Architecture Recommendations

### Current State
```
┌─────────────────┐
│   Frontend      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│     Server      │◄────►│     Runner      │
│  (Lightweight)   │      │   (GPU Worker)   │
│                 │      │                 │
│  - API routes   │      │ - whisper       │
│  - Database     │      │ - formatting    │
│  - Auth         │      │ - summary       │
│  - storage*     │      │ - storage*      │
│                 │      │                 │
│  Unused:        │      │ Broken:         │
│  - notebooklm   │      │ - notebooklm    │
│  - pptx         │      │   (generated    │
│  - process_audio│      │    not sent)     │
└─────────────────┘      └─────────────────┘
```

### Recommended State
```
┌─────────────────┐
│   Frontend      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│     Server      │◄────►│     Runner      │
│  (Lightweight)   │      │   (GPU Worker)   │
│                 │      │                 │
│  - API routes   │      │ - whisper       │
│  - Database     │      │ - formatting    │
│  - Auth         │      │ - summary       │
│  - storage      │      │ - notebooklm    │
│                 │      │   (send to API)  │
│  Features:      │      │                 │
│  - notebooklm   │      │                 │
│  - pptx         │      │                 │
│  (async jobs)   │      │                 │
└─────────────────┘      └─────────────────┘
```

---

## Action Items

### High Priority
1. ✅ **FIXED**: Add summary generation to runner
2. 🔲 **TODO**: Fix NotebookLM guideline delivery to server
   - Add `notebooklm_guideline` to JobResult schema
   - Update server API to receive and store guidelines
3. 🔲 **TODO**: Implement PPTX generation
   - Add API endpoint to trigger generation
   - Implement async job processing
   - Update `pptx_status` properly

### Medium Priority
4. 🔲 **TODO**: Remove storage_service from runner
   - Runner should send results via API only
   - Server should handle all storage
5. 🔲 **TODO**: Clean up unused services
   - Remove or document `process_audio.py`
   - Decide on notebooklm/pptx services

### Low Priority
6. 🔲 **TODO**: Consider moving NotebookLM/PPTX to async background jobs
   - Don't block transcription completion
   - Generate on-demand via user action
   - Use task queue (Celery/RQ) or WebSocket notifications

---

## Conclusion

The server/runner split is **mostly working correctly**:

**✅ Working:**
- Transcription (whisper) - moved to runner
- Text formatting - moved to runner
- Summary generation - recently fixed, now working
- Storage - duplicated but functional

**❌ Broken:**
- NotebookLM guideline - generated by runner but not sent to server
- PPTX generation - service exists but no API endpoint to trigger it

**🔲 Cleanup Needed:**
- Remove duplicate storage_service from runner
- Remove or document unused process_audio.py
