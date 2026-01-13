---
name: whisper-chunking
description: Audio chunking architecture for Whisper Summarizer. Segments-first approach preserves Whisper timestamps for accurate SRT export. VAD split, parallel processing, timestamp-based merge.
---

# whisper-chunking - Audio Chunking Architecture

## Purpose

Explains the **segments-first approach** used for optimal transcription performance:
- **Preserves Whisper timestamps** throughout the pipeline
- **Parallel processing** for faster transcription
- **Accurate SRT export** with real timestamps
- **VAD-based smart chunking** at silence points

## Quick Start

```bash
# View chunking configuration
/whisper-chunking config

# Test chunking on audio file
/whisper-chunking test /path/to/audio.m4a
```

## Data Flow

```
Whisper Transcription (10-min chunks, parallel)
    ↓
Segments: [{start: 0.0, end: 2.5, text: "..."}, ...]
    ↓
Runner sends segments (NOT concatenated text)
    ↓
Server saves segments.json.gz
    ↓
LLM formatting: Text extracted → chunked by 5000 bytes → GLM → formatted
    ↓
SRT export: Uses original segments.json.gz with real timestamps ✅
```

## Architecture

### Segments-First Approach

**Key Insight**: Preserve individual Whisper segments throughout the pipeline instead of concatenating text.

**Why**:
1. **Accurate SRT timestamps** - Original Whisper timing preserved
2. **No fake timestamps** - Real timestamps from Whisper model
3. **Accurate alignment** - Text matches audio timing perfectly

### Chunking Strategy

For faster transcription of long files (10+ min):

1. **VAD Split** - Split audio at VAD-detected silence points
2. **FFmpeg Extract** - Extract chunks with FFmpeg
3. **Parallel Transcribe** - Transcribe in parallel (ThreadPoolExecutor)
4. **Merge Results** - Merge with timestamp-based merge (O(n), fast)

## Configuration

### Key Settings

```yaml
# Audio Chunking
ENABLE_CHUNKING=true
CHUNK_SIZE_MINUTES=5                         # 5-10 minute chunks
CHUNK_OVERLAP_SECONDS=15                     # Overlap for deduplication
MAX_CONCURRENT_CHUNKS=4                      # GPU: 4-8 recommended
USE_VAD_SPLIT=true                           # Use VAD for smart chunking
MERGE_STRATEGY=lcs                           # Timestamp-based for >=10 chunks

# Text Formatting
MAX_FORMAT_CHUNK=5000                        # Max bytes per GLM request
```

### Recommended Settings

| Hardware | CHUNK_SIZE_MINUTES | MAX_CONCURRENT_CHUNKS |
|----------|-------------------|----------------------|
| CPU | 10 | 2 |
| RTX 3060/3060 Ti (12GB) | 5-10 | 4 |
| RTX 3080 (8GB) | 5-10 | 4-6 |
| RTX 3090/4080 (10GB+) | 10-15 | 6-8 |
| RTX 4090 (24GB) | 10-15 | 8-12 |

## VAD Split (Voice Activity Detection)

VAD splits audio at silence points for smarter chunking:

```yaml
USE_VAD_SPLIT: true
VAD_SILENCE_THRESHOLD: -30
VAD_MIN_SILENCE_DURATION: 0.5
```

**Benefits**:
- Reduces transcription of silence
- Improves accuracy
- Creates more natural chunk boundaries

**How it works**:
1. Analyze audio for silence regions
2. Split at silence points (minimum 0.5s duration)
3. Group smaller chunks into target chunk size (5-10 min)

## Parallel Processing

### ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor

def transcribe_with_chunks(audio_path, chunk_size_minutes=5):
    chunks = create_chunks(audio_path, chunk_size_minutes)

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(transcribe_chunk, chunks)

    return merge_results(list(results))
```

**Benefits**:
- Multiple chunks processed simultaneously
- Better GPU utilization (80-95% vs 25%)
- 4x faster than sequential processing

### Performance Comparison

| Mode | 21 Chunks | GPU Utilization | Time |
|------|-----------|-----------------|------|
| **Sequential** | 1 at a time | 25% | ~70 min |
| **Parallel (4 workers)** | 4 at a time | 95% | ~18 min |

## Merge Strategies

### Auto-Selection Logic

```python
if chunk_count >= 10:
    use_timestamp_merge()  # O(n) - fast
else:
    use_lcs_merge()  # O(n²) - better deduplication
```

### Timestamp Merge (O(n))

**Use for**: >=10 chunks (large files)

**Algorithm**:
1. Sort all segments by start time
2. Remove overlaps (keep later segment)
3. Filter duplicates by timestamp proximity

**Pros**: Fast O(n) complexity
**Cons**: Less aggressive deduplication

### LCS Merge (O(n²))

**Use for**: <10 chunks (small files)

**Algorithm**: Longest Common Subsequence to remove overlapping text

**Pros**: Better deduplication
**Cons**: O(n²) complexity - slow for many chunks

## SRT Generation

The SRT export uses the **original Whisper segments** with their individual timestamps:

```
1
00:00:00,000 --> 00:00:02,500
第一段字幕内容

2
00:00:02,500 --> 00:00:05,000
第二段字幕内容
```

**Benefits**:
- Each subtitle line has precise timing from Whisper
- No fake timestamps at chunk boundaries
- Accurate alignment between audio and text

## Storage

### segments.json.gz

**Location**: `/app/data/segments/{transcription_id}.json.gz`

**Format**:
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "第一段字幕内容"
    },
    {
      "start": 2.5,
      "end": 5.0,
      "text": "第二段字幕内容"
    }
  ]
}
```

**Compression**: Gzip-compressed to save space

## Text Formatting Pipeline

### Extraction & Chunking

```python
# Extract text from segments
text = "\n".join(seg["text"] for seg in segments)

# Chunk by 5000 bytes (avoid GLM timeout)
chunks = chunk_text_by_bytes(text, max_bytes=5000)

# Format each chunk
formatted_parts = [glm_format(chunk) for chunk in chunks]
formatted_text = ''.join(formatted_parts)
```

**Why chunk**: GLM-4.5-Air has timeout issues with payloads >5000 bytes

## Code Examples

### Create Chunks with VAD

```python
def create_chunks_with_vad(audio_path, chunk_size_minutes=5):
    """Split audio using VAD-detected silence"""
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent

    audio = AudioSegment.from_file(audio_path)
    nonsilent = detect_nonsilent(
        audio,
        min_silence_len=500,
        silence_thresh=audio.dBFS - 30,
        seek_step=100
    )

    # Group into target chunk size
    chunks = []
    current_chunk = []
    current_duration = 0
    target_duration = chunk_size_minutes * 60 * 1000  # ms

    for start, end in nonsilent:
        current_chunk.append((start, end))
        current_duration += end - start

        if current_duration >= target_duration:
            chunks.append(current_chunk)
            current_chunk = []
            current_duration = 0

    return chunks
```

### Parallel Transcription

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def transcribe_parallel(chunks, max_workers=4):
    """Transcribe chunks in parallel"""
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(transcribe_chunk, chunk): i
            for i, chunk in enumerate(chunks)
        }

        for future in as_completed(futures):
            chunk_idx = futures[future]
            results[chunk_idx] = future.result()

    # Sort by original chunk order
    return [results[i] for i in range(len(chunks))]
```

### Timestamp Merge

```python
def merge_by_timestamp(all_segments):
    """O(n) timestamp-based merge"""
    # Sort by start time
    sorted_segments = sorted(all_segments, key=lambda s: s['start'])

    # Remove overlaps
    merged = []
    for seg in sorted_segments:
        if not merged:
            merged.append(seg)
        else:
            last = merged[-1]
            # Overlap detected
            if seg['start'] < last['end']:
                # Keep segment with higher confidence
                if seg.get('confidence', 0) > last.get('confidence', 0):
                    merged[-1] = seg
            else:
                merged.append(seg)

    return merged
```

## Troubleshooting

### Issue: Too many chunks

**Symptoms**: 100+ chunks for 60-min file

**Solution**:
```yaml
CHUNK_SIZE_MINUTES=10  # Increase chunk size
```

### Issue: Poor SRT timestamps

**Symptoms**: Subtitles don't match audio timing

**Diagnosis**:
```bash
# Check segments file exists
docker exec whisper_server_prd ls -la /app/data/segments/

# Verify segments format
zcat /app/data/segments/{id}.json.gz | jq .
```

**Solution**:
- Verify runner is sending segments (not just text)
- Check segments.json.gz is being saved
- Ensure merge strategy preserves timestamps

### Issue: Slow merging

**Symptoms**: Merge takes longer than transcription

**Solution**:
```yaml
# For large files (>10 chunks), use timestamp merge
MERGE_STRATEGY=timestamp  # O(n) instead of O(n²)
```

## Related Skills

```bash
# Performance optimization
/whisper-performance

# Audio player with SRT navigation
/whisper-player
```

## See Also

- [CLAUDE.md - Audio Chunking](../../CLAUDE.md#audio-chunking-segments-first-architecture)
- [runner/app/services/whisper_service.py](../../runner/app/services/whisper_service.py)
