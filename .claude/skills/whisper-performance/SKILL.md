---
name: whisper-performance
description: Performance optimization guide for Whisper Summarizer. GPU-accelerated transcription with faster-whisper + cuDNN. Includes restrictions, best practices, benchmarks, RTF monitoring, and troubleshooting.
---

# whisper-performance - Performance Optimization

## Purpose

Optimal performance guidelines for GPU-accelerated audio transcription:
- **RTX 3080 achieves 11.7x real-time speed** (RTF 0.08)
- **210-min audio processes in ~18 minutes**
- **Critical restrictions** to avoid 3.3x slowdown
- **GPU configuration** for maximum throughput

## Quick Start

```bash
# Check current performance
/whisper-performance check

# Run benchmarks
/whisper-performance benchmark

# Troubleshoot slow processing
/whisper-performance troubleshoot
```

## Performance Metrics

### RTF (Real-Time Factor)

```
RTF = Processing Time / Audio Duration
```

| RTF | Performance | Status |
|-----|-------------|--------|
| < 0.1 | >10x real-time | ✅ Excellent |
| 0.1-0.3 | 3-10x real-time | ✅ Good |
| 0.3-0.5 | 2-3x real-time | ⚠️ Acceptable |
| > 0.5 | <2x real-time | ❌ Investigate |
| > 1.0 | Slower than real-time | 🚨 Critical issue |

### Expected RTF by Audio Duration

| Audio Duration | Expected RTF | Processing Time | Chunks |
|----------------|-------------|-----------------|--------|
| 2 min | 1.0-1.5x | ~2-3 min | 1 |
| 20 min | 0.20-0.30x | ~4-6 min | 5 |
| 60 min | 0.35-0.45x | ~21-27 min | 6-12 |
| 210 min | 0.25-0.35x | ~52-73 min | 21-42 |

**Key Insight**: Longer audio = better RTF (fixed API overhead amortized).

### Benchmarks (RTX 3080, large-v3-turbo, int8_float16)

| Approach | Chunks (210-min) | FFmpeg Calls | RTF | Processing Time |
|----------|------------------|--------------|-----|-----------------|
| **Fixed-Duration (20s)** | 630 | 630 | 0.28 | ~58 min |
| **10-Minute Chunks (4 workers)** | 21 | 21 | 0.08 | ~18 min |

**Performance Impact**: Fixed-duration is **3.3x slower** due to 630 sequential FFmpeg extractions.

## ⚠️ CRITICAL PERFORMANCE RESTRICTIONS

### 1. NEVER Use Fixed-Duration Chunking

**Problem**: Fixed-duration chunks (10-30s) cause massive FFmpeg overhead.

**NEVER do this**:
```python
# ❌ WRONG - Fixed-duration chunking
def transcribe_fixed_chunks(audio_path, chunk_duration=20):
    for i in range(0, total_duration, chunk_duration):
        extract_audio_with_ffmpeg(audio_path, i, i + chunk_duration)  # 630 calls!
```

**ALWAYS do this**:
```python
# ✅ CORRECT - Use 5-10 minute chunks with parallel processing
def transcribe_with_chunks(audio_path, chunk_size_minutes=5):
    chunks = create_chunks(audio_path, chunk_size_minutes)  # Only 21 chunks
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(transcribe_chunk, chunks)  # Parallel!
```

### 2. NEVER Send Large Text Payloads to GLM API

**Problem**: GLM-4.5-Air has timeout issues with payloads >5000 bytes.

**❌ WRONG**:
```python
formatted_text = glm_format(text)  # 10000+ bytes → timeout
```

**✅ CORRECT**:
```python
chunks = chunk_text_by_bytes(text, max_bytes=5000)
formatted_parts = [glm_format(chunk) for chunk in chunks]
formatted_text = ''.join(formatted_parts)
```

**Configuration**: `MAX_FORMAT_CHUNK=5000` (enforced in `docker-compose.dev.yml`)

### 3. NEVER Process Chunks Sequentially for Long Audio

**Problem**: Sequential processing prevents GPU utilization.

| Mode | 21 Chunks | GPU Utilization | Time |
|------|-----------|-----------------|------|
| **Sequential** | 1 at a time | 25% | ~70 min |
| **Parallel (4 workers)** | 4 at a time | 95% | ~18 min |

**Configuration**: `MAX_CONCURRENT_CHUNKS=4-6` (GPU-dependent)

### 4. NEVER Skip Segments Preservation

**Problem**: Segments are required for accurate SRT timestamps.

**❌ WRONG**:
```python
result = JobResult(text=concatenated_text, segments=None)
```

**✅ CORRECT**:
```python
result = JobResult(text=concatenated_text, segments=whisper_segments)
```

## ✅ PERFORMANCE BEST PRACTICES

### 1. Use 5-10 Minute Chunks

Optimal chunk size balances FFmpeg overhead and parallelization:

| Chunk Size | 210-min File | Chunks | Pros | Cons |
|------------|--------------|--------|------|------|
| 5 min | 42 chunks | 42 | ✅ More parallelization | More merge overhead |
| 10 min | 21 chunks | 21 | ✅ Fewer FFmpeg calls | Less parallelization |
| **20s** | 630 chunks | 630 | ❌ **NEVER USE** | **3.3x slower** |

**Recommended**: `CHUNK_SIZE_MINUTES=5-10`

### 2. Match Workers to GPU VRAM

| GPU Model | VRAM | MAX_CONCURRENT_CHUNKS | CHUNK_SIZE_MINUTES |
|-----------|------|----------------------|-------------------|
| RTX 3060/3060 Ti | 12GB | 4 | 5-10 |
| RTX 3080 | 8GB | 4-6 | 5-10 |
| RTX 3090/4080 | 10GB+ | 6-8 | 10-15 |
| RTX 4090 | 24GB | 8-12 | 10-15 |

**Rule of Thumb**: 1 concurrent chunk per 2GB VRAM (minimum 4 for RTX 3080)

### 3. Enable VAD Split for Smart Chunking

VAD (Voice Activity Detection) splits at silence points:

```yaml
USE_VAD_SPLIT: true
VAD_SILENCE_THRESHOLD: -30
VAD_MIN_SILENCE_DURATION: 0.5
```

**Benefit**: Reduces transcription of silence, improves accuracy.

### 4. Use Timestamp-Based Merge for >=10 Chunks

Auto-selection logic in `whisper_service.py`:

```python
if chunk_count >= 10:
    use_timestamp_merge()  # O(n) - fast
else:
    use_lcs_merge()  # O(n²) - better deduplication
```

**Rationale**: LCS merge has O(n²) complexity - unacceptable for 42+ chunks.

### 5. Monitor RTF (Real-Time Factor)

Calculate RTF after each transcription:

```python
rtf = processing_time_seconds / audio_duration_seconds
if rtf > 0.5:
    logger.warning(f"Slow RTF detected: {rtf:.2f}")
```

## Configuration Examples

### Development (CPU)

```yaml
# runner/.env
FASTER_WHISPER_DEVICE=cpu
FASTER_WHISPER_COMPUTE_TYPE=int8
CHUNK_SIZE_MINUTES=10
MAX_CONCURRENT_CHUNKS=2
```

### Production (RTX 3080)

```yaml
# runner/.env
FASTER_WHISPER_DEVICE=cuda
FASTER_WHISPER_COMPUTE_TYPE=int8_float16
CHUNK_SIZE_MINUTES=5
MAX_CONCURRENT_CHUNKS=4
USE_VAD_SPLIT=true
MAX_FORMAT_CHUNK=5000
```

### Production (RTX 4090)

```yaml
# runner/.env
FASTER_WHISPER_DEVICE=cuda
FASTER_WHISPER_COMPUTE_TYPE=int8_float16
CHUNK_SIZE_MINUTES=10
MAX_CONCURRENT_CHUNKS=12
USE_VAD_SPLIT=true
MAX_FORMAT_CHUNK=5000
```

## Troubleshooting

### Issue: RTF > 0.5 (slower than expected)

**Checklist**:
1. ✅ `CHUNK_SIZE_MINUTES` is 5-10 (not 20s)
2. ✅ `MAX_CONCURRENT_CHUNKS` matches GPU VRAM (4-6 for RTX 3080)
3. ✅ `MAX_FORMAT_CHUNK` is 5000 (not 10000)
4. ✅ `USE_VAD_SPLIT` is true
5. ✅ `MERGE_STRATEGY` is `lcs`
6. ✅ GPU is being utilized (`nvidia-smi` shows 80-95% GPU usage)

### Issue: GLM API Timeouts

**Symptoms**: Formatting fails with timeout error

**Solution**:
```yaml
MAX_FORMAT_CHUNK=4000  # or 3000 for very slow connections
```

### Issue: Out of Memory Errors

**Symptoms**: CUDA out of memory, process killed

**Solution**:
```yaml
MAX_CONCURRENT_CHUNKS=2  # Reduce by 1-2 workers
```

### Issue: Low GPU Utilization

**Diagnosis**:
```bash
nvidia-smi dmon -c 100
```

**Expected**: 80-95% GPU utilization during transcription

**If low**:
- Check `MAX_CONCURRENT_CHUNKS` (increase if GPU has headroom)
- Verify `FASTER_WHISPER_DEVICE=cuda`
- Check for CPU bottleneck (disk I/O, preprocessing)

## Code Review Checklist

Before committing performance-related changes:

- [ ] No fixed-duration chunking logic (20-30s chunks)
- [ ] Chunks are processed in parallel (ThreadPoolExecutor)
- [ ] GLM payloads are chunked by 5000 bytes max
- [ ] Whisper segments are preserved throughout pipeline
- [ ] FFmpeg extraction is minimized (21-42 chunks max for 210-min file)
- [ ] Merge strategy auto-selects based on chunk count
- [ ] GPU workers match VRAM capacity (4-6 for RTX 3080)

## Performance Testing

### Manual Test

```bash
# Upload a known audio file
curl -X POST http://localhost:8130/api/audio/upload \
  -F "file=@test.m4a" \
  -H "Authorization: Bearer $TOKEN"

# Monitor processing
docker logs whisper_runner_dev --follow

# Check RTF when complete
# RTF = processing_time / audio_duration
```

### Automated Benchmark

```bash
# Run performance benchmarks
docker exec whisper_runner_dev python -c "
import time
from app.services.whisper_service import transcribe

start = time.time()
result = transcribe('/app/test.m4a')
rtf = (time.time() - start) / result['duration']
print(f'RTF: {rtf:.2f}')
"
```

## Related Skills

```bash
# Audio chunking architecture
/whisper-chunking

# Deploy to production
/whisper-deploy

# Production debugging
/prd_debug
```

## See Also

- [CLAUDE.md - Performance Restrictions & Best Practices](../../CLAUDE.md#performance-restrictions--best-practices)
- [reports/2025-01-13-performance-optimization-report.md](../../reports/2025-01-13-performance-optimization-report.md)
- [runner/app/services/whisper_service.py](../../runner/app/services/whisper_service.py)
