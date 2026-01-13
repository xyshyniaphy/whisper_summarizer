# Audio Player with SRT Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add audio player with SRT (subtitle) navigation to shared transcription page, enabling users to listen to original audio while following transcription text with auto-scrolling and tap-to-seek functionality.

**Architecture:** Sticky HTML5 audio player at bottom + SRT segments API + Auto-highlighting segments list. Two new server endpoints serve audio (streaming with Range support) and segments (JSON). Frontend components: AudioPlayer (sticky), SrtList (scrollable).

**Tech Stack:** React hooks (useRef for audio, useState for player state), HTML5 Audio API, FastAPI (StreamingResponse with Range headers), existing segments.json.gz storage.

---

## Task 1: Backend - Add Segments API Endpoint

**Files:**
- Modify: `server/app/api/shared.py` (add new endpoint)
- Test: `tests/test_shared_api.py` (create new test file)

**Step 1: Write the failing test**

Create `tests/test_shared_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.share_link import ShareLink
from app.models.transcription import Transcription
from app.services.storage_service import get_storage_service

def test_get_shared_segments_success(client: TestClient, db: Session, sample_transcription, share_token):
    """Test successful segments retrieval for shared transcription."""
    # Setup: Create segments file
    storage_service = get_storage_service()
    segments = [
        {"start": 0.0, "end": 2.5, "text": "First segment"},
        {"start": 2.5, "end": 5.0, "text": "Second segment"},
    ]
    storage_service.save_transcription_segments(str(sample_transcription.id), segments)

    # Test
    response = client.get(f"/api/shared/{share_token}/segments")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["start"] == 0.0
    assert data[0]["text"] == "First segment"

def test_get_shared_segments_not_found(client: TestClient, db: Session, sample_transcription, share_token):
    """Test segments request when no segments file exists."""
    # Don't create segments file - should return empty array
    response = client.get(f"/api/shared/{share_token}/segments")

    assert response.status_code == 200
    assert response.json() == []

def test_get_shared_segments_invalid_token(client: TestClient):
    """Test segments request with invalid share token."""
    response = client.get("/api/shared/invalid-token/segments")

    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shared_api.py::test_get_shared_segments_success -v`
Expected: FAIL with "endpoint not found" (404)

**Step 3: Write minimal implementation**

Add to `server/app/api/shared.py`:

```python
@router.get("/{share_token}/segments")
async def get_shared_segments(
    share_token: str,
    db: Session = Depends(get_db)
):
    """
    Get transcription segments with timestamps for audio player navigation.

    Returns JSON array of segments with start, end, text fields.
    Returns empty array if segments file doesn't exist.
    """
    # Find share link (reuse existing validation logic)
    share_link = db.query(ShareLink).filter(
        ShareLink.share_token == share_token
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    # Check expiration
    if share_link.expires_at and share_link.expires_at < __import__('datetime').datetime.now(__import__('datetime').timezone.utc):
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == share_link.transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="转录不存在")

    # Get segments from storage (returns empty list if not found)
    storage_service = get_storage_service()
    segments = storage_service.get_transcription_segments(str(transcription.id))

    return segments
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shared_api.py -v`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add tests/test_shared_api.py server/app/api/shared.py
git commit -m "feat(server): add segments API endpoint for shared transcriptions"
```

---

## Task 2: Backend - Add Audio Streaming Endpoint

**Files:**
- Modify: `server/app/api/shared.py` (add streaming endpoint)
- Test: `tests/test_shared_api.py` (extend tests)

**Step 1: Write the failing test**

Add to `tests/test_shared_api.py`:

```python
def test_get_shared_audio_success(client: TestClient, db: Session, sample_transcription, share_token, tmp_path):
    """Test successful audio streaming with Range header."""
    # Setup: Create a test audio file
    audio_path = tmp_path / "test_audio.m4a"
    audio_path.write_bytes(b"MOCK_AUDIO_DATA")

    # Mock transcription.file_path to point to our test file
    sample_transcription.file_path = str(audio_path)
    db.commit()

    # Test full file request
    response = client.get(f"/api/shared/{share_token}/audio")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mp4"  # or audio/mpeg
    assert "accept-ranges" in response.headers.lower()
    assert response.content == b"MOCK_AUDIO_DATA"

def test_get_shared_audio_range_request(client: TestClient, db: Session, sample_transcription, share_token, tmp_path):
    """Test audio streaming with Range header (partial content)."""
    # Setup: Create a larger test audio file
    audio_path = tmp_path / "test_audio.m4a"
    audio_data = b"0123456789" * 1000  # 10KB
    audio_path.write_bytes(audio_data)

    sample_transcription.file_path = str(audio_path)
    db.commit()

    # Test Range request
    response = client.get(
        f"/api/shared/{share_token}/audio",
        headers={"Range": "bytes=0-1023"}
    )

    assert response.status_code == 206  # Partial Content
    assert response.headers["content-range"].startswith("bytes 0-1023/")
    assert len(response.content) == 1024

def test_get_shared_audio_file_not_found(client: TestClient, db: Session, sample_transcription, share_token):
    """Test audio request when file doesn't exist."""
    # Set file_path to non-existent file
    sample_transcription.file_path = "/nonexistent/path/audio.m4a"
    db.commit()

    response = client.get(f"/api/shared/{share_token}/audio")

    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_shared_api.py::test_get_shared_audio_success -v`
Expected: FAIL with "endpoint not found"

**Step 3: Write minimal implementation**

Add to `server/app/api/shared.py` (after imports, include additional imports):

```python
from fastapi import Request
from pathlib import Path as FilePath
import aiofiles

async def _get_mime_type(file_path: str) -> str:
    """Get MIME type based on file extension."""
    ext = FilePath(file_path).suffix.lower()
    mime_types = {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
    }
    return mime_types.get(ext, "audio/mpeg")

@router.get("/{share_token}/audio")
async def get_shared_audio(
    share_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stream original audio file for shared transcription.

    Supports HTTP Range requests for seeking in audio players.
    Public access (no authentication required).
    """
    # Find share link
    share_link = db.query(ShareLink).filter(
        ShareLink.share_token == share_token
    ).first()

    if not share_link:
        raise HTTPException(status_code=404, detail="分享链接不存在")

    # Check expiration
    if share_link.expires_at and share_link.expires_at < __import__('datetime').datetime.now(__import__('datetime').timezone.utc):
        raise HTTPException(status_code=410, detail="分享链接已过期")

    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == share_link.transcription_id
    ).first()

    if not transcription:
        raise HTTPException(status_code=404, detail="转录不存在")

    # Check if file_path exists
    if not transcription.file_path:
        raise HTTPException(status_code=404, detail="音频文件不存在")

    file_path = FilePath(transcription.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音频文件未找到")

    # Get file size
    file_size = file_path.stat().st_size

    # Handle Range header
    range_header = request.headers.get("range")
    headers = {
        "content-type": await _get_mime_type(str(file_path)),
        "accept-ranges": "bytes",
    }

    if range_header:
        # Parse Range header (format: "bytes=start-end")
        try:
            range_match = range_header.replace("bytes=", "").strip()
            range_parts = range_match.split("-")
            start = int(range_parts[0]) if range_parts[0] else 0
            end = int(range_parts[1]) if range_parts[1] else file_size - 1

            # Validate range
            if start >= file_size or end >= file_size or start > end:
                raise HTTPException(
                    status_code=416,
                    detail="Invalid range",
                    headers={"content-range": f"bytes */{file_size}"}
                )

            # Read partial content
            chunk_size = end - start + 1
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(start)
                chunk = await f.read(chunk_size)

            headers["content-range"] = f"bytes {start}-{end}/{file_size}"
            headers["content-length"] = str(chunk_size)

            return StreamingResponse(
                iter([chunk]),
                status_code=206,
                headers=headers
            )
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid range header")

    # No Range header - return entire file
    headers["content-length"] = str(file_size)

    async def file_iterator():
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(64 * 1024):  # 64KB chunks
                yield chunk

    return StreamingResponse(
        file_iterator(),
        headers=headers
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_shared_api.py::test_get_shared_audio -v`
Expected: PASS (all 3 audio tests)

**Step 5: Commit**

```bash
git add tests/test_shared_api.py server/app/api/shared.py
git commit -m "feat(server): add audio streaming endpoint with Range support"
```

---

## Task 3: Frontend - Add API Functions

**Files:**
- Modify: `frontend/src/services/api.ts` (add new functions)
- Test: `frontend/src/services/__tests__/api.test.ts` (create test)

**Step 1: Write the failing test**

Create `frontend/src/services/__tests__/api.test.ts`:

```typescript
import { api } from '../api';
import axios from 'axios';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('Shared Transcription Audio API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getSharedSegments', () => {
    it('should fetch segments for shared transcription', async () => {
      const mockSegments = [
        { start: 0.0, end: 2.5, text: 'First segment' },
        { start: 2.5, end: 5.0, text: 'Second segment' },
      ];

      mockedAxios.get.mockResolvedValueOnce({ data: mockSegments });

      const result = await api.getSharedSegments('abc123');

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/shared/abc123/segments');
      expect(result).toEqual(mockSegments);
    });

    it('should return empty array if no segments exist', async () => {
      mockedAxios.get.mockResolvedValueOnce({ data: [] });

      const result = await api.getSharedSegments('abc123');

      expect(result).toEqual([]);
    });
  });

  describe('getSharedAudioUrl', () => {
    it('should return audio URL for shared transcription', () => {
      const url = api.getSharedAudioUrl('abc123');

      expect(url).toBe('/api/shared/abc123/audio');
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `bun test frontend/src/services/__tests__/api.test.ts`
Expected: FAIL with "api.getSharedSegments is not a function"

**Step 3: Write minimal implementation**

Add to `frontend/src/services/api.ts` (inside the `api` object):

```typescript
  // Shared transcription audio/segments endpoints
  getSharedSegments: async (shareToken: string): Promise<Array<{
    start: number;
    end: number;
    text: string;
  }>> => {
    const response = await axios.get(`${API_URL}/shared/${shareToken}/segments`);
    return response.data;
  },

  getSharedAudioUrl: (shareToken: string): string => {
    return `${API_URL}/shared/${shareToken}/audio`;
  },
```

**Step 4: Run test to verify it passes**

Run: `bun test frontend/src/services/__tests__/api.test.ts`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/services/__tests__/api.test.ts
git commit -m "feat(frontend): add API functions for segments and audio URLs"
```

---

## Task 4: Frontend - Create AudioPlayer Component

**Files:**
- Create: `frontend/src/components/AudioPlayer.tsx`
- Test: `frontend/src/components/__tests__/AudioPlayer.test.tsx`

**Step 1: Write the failing test**

Create `frontend/src/components/__tests__/AudioPlayer.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { AudioPlayer } from '../AudioPlayer';

describe('AudioPlayer', () => {
  const mockSegments = [
    { start: 0.0, end: 2.5, text: 'First segment' },
    { start: 2.5, end: 5.0, text: 'Second segment' },
    { start: 5.0, end: 7.5, text: 'Third segment' },
  ];

  it('should render audio element with correct src', () => {
    render(<AudioPlayer audioUrl="/audio.mp3" segments={mockSegments} onSeek={() => {}} />);

    const audio = screen.getByTestId('audio-element');
    expect(audio).toHaveAttribute('src', '/audio.mp3');
  });

  it('should call onSeek when segment is clicked', () => {
    const onSeek = jest.fn();
    render(<AudioPlayer audioUrl="/audio.mp3" segments={mockSegments} onSeek={onSeek} />);

    const segmentButtons = screen.getAllByTestId(/segment-/);
    fireEvent.click(segmentButtons[1]);

    expect(onSeek).toHaveBeenCalledWith(2.5);
  });

  it('should highlight current segment during playback', () => {
    render(<AudioPlayer audioUrl="/audio.mp3" segments={mockSegments} onSeek={() => {}} />);

    const audio = screen.getByTestId('audio-element');

    // Simulate timeupdate event
    fireEvent.timeUpdate(audio, { target: { currentTime: 3.0 } });

    const currentSegment = screen.getByTestId('segment-1');
    expect(currentSegment).toHaveClass('bg-blue-100'); // highlighted
  });
});
```

**Step 2: Run test to verify it fails**

Run: `bun test frontend/src/components/__tests__/AudioPlayer.test.tsx`
Expected: FAIL with "AudioPlayer component not found"

**Step 3: Write minimal implementation**

Create `frontend/src/components/AudioPlayer.tsx`:

```typescript
import { useRef, useEffect, useState, useCallback } from 'react';
import { Play, Pause, Volume2, Maximize2, Minimize2 } from 'lucide-react';
import { cn } from '../utils/cn';

export interface Segment {
  start: number;
  end: number;
  text: string;
}

interface AudioPlayerProps {
  audioUrl: string;
  segments: Segment[];
  onSeek: (time: number) => void;
  className?: string;
}

export function AudioPlayer({ audioUrl, segments, onSeek, className }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(-1);

  // Update current segment based on playback time
  useEffect(() => {
    const index = segments.findIndex(
      seg => currentTime >= seg.start && currentTime < seg.end
    );
    setCurrentSegmentIndex(index);
  }, [currentTime, segments]);

  // Handle play/pause toggle
  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  // Handle seeking when user clicks a segment
  const handleSegmentClick = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = time;
    onSeek(time);

    // Update current time state for immediate UI feedback
    setCurrentTime(time);
  }, [onSeek]);

  // Handle seek bar change
  const handleSeekChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const time = parseFloat(e.target.value);
    audio.currentTime = time;
    setCurrentTime(time);
  }, []);

  // Format time as MM:SS
  const formatTime = (time: number): string => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className={cn(
      "fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t dark:border-gray-700 shadow-lg z-50",
      !isExpanded && "h-16",
      isExpanded && "h-32",
      className
    )}>
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onDurationChange={(e) => setDuration(e.currentTarget.duration)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        data-testid="audio-element"
      />

      {/* Compact mode */}
      <div className="flex items-center justify-between px-4 py-2 h-full">
        {/* Play/Pause button */}
        <button
          onClick={togglePlayPause}
          className="flex items-center justify-center w-10 h-10 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors"
          aria-label={isPlaying ? '暂停' : '播放'}
        >
          {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
        </button>

        {/* Progress bar and time */}
        <div className="flex-1 mx-4">
          <input
            type="range"
            min="0"
            max={duration || 0}
            step="0.1"
            value={currentTime}
            onChange={handleSeekChange}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            aria-label="进度"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Expand/collapse button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label={isExpanded ? '收起' : '展开'}
        >
          {isExpanded ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
        </button>
      </div>

      {/* Expanded mode - show current segment text */}
      {isExpanded && currentSegmentIndex >= 0 && (
        <div className="px-4 pb-2">
          <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
            {segments[currentSegmentIndex]?.text}
          </p>
        </div>
      )}
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `bun test frontend/src/components/__tests__/AudioPlayer.test.tsx`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add frontend/src/components/AudioPlayer.tsx frontend/src/components/__tests__/AudioPlayer.test.tsx
git commit -m "feat(frontend): add AudioPlayer component with seek support"
```

---

## Task 5: Frontend - Create SrtList Component

**Files:**
- Create: `frontend/src/components/SrtList.tsx`
- Test: `frontend/src/components/__tests__/SrtList.test.tsx`

**Step 1: Write the failing test**

Create `frontend/src/components/__tests__/SrtList.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { SrtList } from '../SrtList';

describe('SrtList', () => {
  const mockSegments = [
    { start: 0.0, end: 2.5, text: 'First segment' },
    { start: 2.5, end: 5.0, text: 'Second segment' },
    { start: 5.0, end: 7.5, text: 'Third segment' },
  ];

  it('should render all segments', () => {
    render(<SrtList segments={mockSegments} currentTime={0} onSeek={() => {}} />);

    expect(screen.getByText('First segment')).toBeInTheDocument();
    expect(screen.getByText('Second segment')).toBeInTheDocument();
    expect(screen.getByText('Third segment')).toBeInTheDocument();
  });

  it('should highlight current segment', () => {
    render(<SrtList segments={mockSegments} currentTime={3.0} onSeek={() => {}} />);

    const secondSegment = screen.getByText('Second segment').closest('div');
    expect(secondSegment).toHaveClass('bg-blue-50');
  });

  it('should call onSeek when segment is clicked', () => {
    const onSeek = jest.fn();
    render(<SrtList segments={mockSegments} currentTime={0} onSeek={onSeek} />);

    const thirdSegment = screen.getByText('Third segment');
    fireEvent.click(thirdSegment);

    expect(onSeek).toHaveBeenCalledWith(5.0);
  });

  it('should display timestamps in MM:SS format', () => {
    render(<SrtList segments={mockSegments} currentTime={0} onSeek={() => {}} />);

    expect(screen.getByText('00:00')).toBeInTheDocument();
    expect(screen.getByText('00:02')).toBeInTheDocument();
  });

  it('should scroll current segment into view', () => {
    const { container } = render(
      <SrtList segments={mockSegments} currentTime={3.0} onSeek={() => {}} />
    );

    const currentElement = screen.getByText('Second segment').closest('div');
    expect(currentElement).toHaveAttribute('data-current', 'true');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `bun test frontend/src/components/__tests__/SrtList.test.tsx`
Expected: FAIL with "SrtList component not found"

**Step 3: Write minimal implementation**

Create `frontend/src/components/SrtList.tsx`:

```typescript
import { useEffect, useRef } from 'react';
import { Clock } from 'lucide-react';
import { cn } from '../utils/cn';

export interface Segment {
  start: number;
  end: number;
  text: string;
}

interface SrtListProps {
  segments: Segment[];
  currentTime: number;
  onSeek: (time: number) => void;
  className?: string;
}

export function SrtList({ segments, currentTime, onSeek, className }: SrtListProps) {
  const currentSegmentRef = useRef<HTMLDivElement>(null);

  // Find current segment index
  const currentIndex = segments.findIndex(
    seg => currentTime >= seg.start && currentTime < seg.end
  );

  // Auto-scroll current segment into view
  useEffect(() => {
    if (currentIndex >= 0 && currentSegmentRef.current) {
      currentSegmentRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [currentIndex]);

  // Format time as MM:SS
  const formatTime = (time: number): string => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  if (segments.length === 0) {
    return (
      <div className={cn("text-center py-8 text-gray-500", className)}>
        <p>暂无字幕数据</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      {segments.map((segment, index) => {
        const isCurrent = index === currentIndex;

        return (
          <div
            key={`${segment.start}-${index}`}
            ref={isCurrent ? currentSegmentRef : null}
            data-current={isCurrent}
            onClick={() => onSeek(segment.start)}
            className={cn(
              "flex gap-3 p-3 rounded-lg cursor-pointer transition-all",
              "hover:bg-gray-100 dark:hover:bg-gray-800",
              isCurrent && "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500"
            )}
          >
            {/* Timestamp */}
            <div className="flex items-center gap-1 flex-shrink-0 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span className="tabular-nums">{formatTime(segment.start)}</span>
            </div>

            {/* Text */}
            <p className="text-sm text-gray-800 dark:text-gray-200 flex-1">
              {segment.text}
            </p>

            {/* Current indicator */}
            {isCurrent && (
              <div className="flex-shrink-0">
                <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `bun test frontend/src/components/__tests__/SrtList.test.tsx`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add frontend/src/components/SrtList.tsx frontend/src/components/__tests__/SrtList.test.tsx
git commit -m "feat(frontend): add SrtList component with auto-scroll"
```

---

## Task 6: Frontend - Integrate into SharedTranscription Page

**Files:**
- Modify: `frontend/src/pages/SharedTranscription.tsx`
- Test: `frontend/src/pages/__tests__/SharedTranscription.test.tsx` (create test)

**Step 1: Write the failing test**

Create `frontend/src/pages/__tests__/SharedTranscription.test.tsx`:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SharedTranscription } from '../SharedTranscription';
import { api } from '../../services/api';

// Mock API
jest.mock('../../services/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('SharedTranscription with Audio Player', () => {
  const mockTranscriptionData = {
    id: '123',
    file_name: 'test.mp3',
    text: 'Test transcription',
    summary: 'Test summary',
    language: 'zh',
    duration_seconds: 300,
    created_at: '2025-01-13T00:00:00Z',
    chat_messages: [],
  };

  const mockSegments = [
    { start: 0.0, end: 2.5, text: 'First segment' },
    { start: 2.5, end: 5.0, text: 'Second segment' },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch and display audio player when segments exist', async () => {
    mockedApi.getSharedTranscription.mockResolvedValue(mockTranscriptionData);
    mockedApi.getSharedSegments.mockResolvedValue(mockSegments);

    render(
      <MemoryRouter initialEntries={['/shared/abc123']}>
        <Routes>
          <Route path="/shared/:shareToken" element={<SharedTranscription />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('audio-element')).toBeInTheDocument();
    });

    expect(mockedApi.getSharedSegments).toHaveBeenCalledWith('abc123');
  });

  it('should not display audio player when no segments', async () => {
    mockedApi.getSharedTranscription.mockResolvedValue(mockTranscriptionData);
    mockedApi.getSharedSegments.mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={['/shared/abc123']}>
        <Routes>
          <Route path="/shared/:shareToken" element={<SharedTranscription />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.queryByTestId('audio-element')).not.toBeInTheDocument();
    });
  });

  it('should add bottom padding when audio player is visible', async () => {
    mockedApi.getSharedTranscription.mockResolvedValue(mockTranscriptionData);
    mockedApi.getSharedSegments.mockResolvedValue(mockSegments);

    const { container } = render(
      <MemoryRouter initialEntries={['/shared/abc123']}>
        <Routes>
          <Route path="/shared/:shareToken" element={<SharedTranscription />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('audio-element')).toBeInTheDocument();
    });

    const mainContainer = container.querySelector('.pb-20');
    expect(mainContainer).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `bun test frontend/src/pages/__tests__/SharedTranscription.test.tsx`
Expected: FAIL with "segments not fetched" or "audio player not rendered"

**Step 3: Write minimal implementation**

Modify `frontend/src/pages/SharedTranscription.tsx`:

```typescript
/**
 * SharedTranscription Page
 *
 * Public view for shared transcriptions (no authentication required).
 * Read-only AI chat display - users cannot send messages.
 * NOW WITH: Audio player + SRT navigation for listening to original audio.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2, Download, ChevronDown, File, Play } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { cn } from '../utils/cn'
import { ChatDisplay } from '../components/ChatDisplay'
import { AudioPlayer, Segment } from '../components/AudioPlayer'
import { SrtList } from '../components/SrtList'

interface SharedTranscriptionData {
    id: string
    file_name: string
    text: string  // AI-formatted transcription text
    summary: string | null
    language: string | null
    duration_seconds: number | null
    created_at: string
    chat_messages: Array<{
        id: string
        role: 'user' | 'assistant'
        content: string
        created_at: string
    }>
}

// Reuse CollapsibleSection component from TranscriptionDetail
interface CollapsibleSectionProps {
    title: string
    children: React.ReactNode
    defaultOpen?: boolean
    headerContent?: React.ReactNode
}

function CollapsibleSection({ title, children, defaultOpen = true, headerContent }: CollapsibleSectionProps) {
    const [isOpen, setIsOpen] = useState(defaultOpen)

    return (
        <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800">
                <div className="flex items-center gap-2 flex-1">
                    <button
                        onClick={() => setIsOpen(!isOpen)}
                        className="flex items-center gap-2 font-medium hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                        aria-expanded={isOpen}
                    >
                        <ChevronDown
                            className={cn("w-5 h-5 transition-transform flex-shrink-0", isOpen && "rotate-180")}
                        />
                        {title}
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    {headerContent}
                </div>
            </div>
            {isOpen && (
                <div className="p-4 bg-white dark:bg-gray-900">
                    {children}
                </div>
            )}
        </div>
    )
}

export function SharedTranscription() {
    const { shareToken } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState<SharedTranscriptionData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // NEW: Audio player state
    const [segments, setSegments] = useState<Segment[]>([])
    const [showAudioPlayer, setShowAudioPlayer] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const isLoadingRef = useRef(false)

    const loadSharedTranscription = useCallback(async () => {
        if (isLoadingRef.current || !shareToken) return
        isLoadingRef.current = true

        try {
            setLoading(true)
            setError(null)
            const response = await api.getSharedTranscription(shareToken)
            setData(response)

            // NEW: Load segments for audio player
            try {
                const segmentsData = await api.getSharedSegments(shareToken)
                if (segmentsData.length > 0) {
                    setSegments(segmentsData)
                    setShowAudioPlayer(true)
                }
            } catch (segmentsError) {
                console.warn('Could not load segments:', segmentsError)
                // Segments are optional - continue without them
            }
        } catch (err: any) {
            console.error('Failed to load shared transcription:', err)
            if (err.response?.status === 404) {
                setError('分享链接不存在')
            } else if (err.response?.status === 410) {
                setError('分享链接已过期')
            } else {
                setError('加载失败，请稍后再试')
            }
        } finally {
            setLoading(false)
            isLoadingRef.current = false
        }
    }, [shareToken])

    useEffect(() => {
        if (shareToken) {
            loadSharedTranscription()
        }
    }, [shareToken, loadSharedTranscription])

    // Reuse display text function from TranscriptionDetail (100 bytes preview)
    const getDisplayText = (text: string, maxBytes: number = 100): string => {
        const encoder = new TextEncoder()
        const encoded = encoder.encode(text)
        if (encoded.length <= maxBytes) {
            return text
        }
        // Find the character boundary near maxBytes
        let truncatedLength = maxBytes
        while (truncatedLength > 0 && (encoded[truncatedLength] & 0xC0) === 0x80) {
            truncatedLength--
        }
        const decoder = new TextDecoder('utf-8')
        return decoder.decode(encoded.slice(0, truncatedLength)) +
            `... (请下载完整版本查看)`
    }

    // Reuse download handlers from TranscriptionDetail
    const handleDownload = async (format: 'txt' | 'srt') => {
        if (!data || !shareToken) return
        try {
            const blob = await api.downloadSharedFile(shareToken, format)
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${data.file_name.replace(/\.[^/.]+$/, '')}.${format}`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('Download failed:', error)
            alert('下载失败')
        }
    }

    // Download DOCX
    const handleDownloadDocx = async () => {
        if (!data || !data.summary || !shareToken) return
        try {
            const blob = await api.downloadSharedDocx(shareToken)
            const link = document.createElement('a')
            link.href = URL.createObjectURL(blob)
            link.download = `${data.file_name.replace(/\.[^/.]+$/, '')}-摘要.docx`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(link.href)
        } catch (error) {
            console.error('DOCX download failed:', error)
            alert('DOCX下载失败')
        }
    }

    // NEW: Handle seek from SRT list
    const handleSeek = useCallback((time: number) => {
        setCurrentTime(time)
    }, [])

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8 flex justify-center items-center min-h-[50vh]">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-8 h-8 text-blue-500 dark:text-blue-400 animate-spin" />
                    <p className="text-gray-600 dark:text-gray-400">加载中...</p>
                </div>
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="container mx-auto px-4 py-8 max-w-2xl">
                <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
                    <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                        <p className="font-medium text-red-800 dark:text-red-200">加载失败</p>
                        <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error || '未找到转录内容'}</p>
                    </div>
                </div>
                <Button
                    variant="ghost"
                    className="mt-4"
                    onClick={() => navigate('/')}
                >
                    返回首页
                </Button>
            </div>
        )
    }

    // Display AI-formatted transcription text (already formatted by backend)
    const displayText = data.text ? getDisplayText(data.text, 100) : ''

    // Format duration as MM:SS
    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${String(secs).padStart(2, '0')}`
    }

    // NEW: Get audio URL
    const audioUrl = shareToken ? api.getSharedAudioUrl(shareToken) : ''

    return (
        <div className={cn(
            "container mx-auto px-4 py-8 max-w-4xl",
            showAudioPlayer && "pb-20" // Add padding when audio player is visible
        )}>
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                    <Badge variant="info">公开分享</Badge>
                    {/* NEW: Show audio available badge */}
                    {showAudioPlayer && (
                        <Badge variant="success" className="flex items-center gap-1">
                            <Play className="w-3 h-3" />
                            可播放音频
                        </Badge>
                    )}
                </div>
                <h1 className="text-3xl font-bold mb-2">{data.file_name}</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                    创建于 {new Date(data.created_at).toLocaleString('zh-CN')}
                </p>
            </div>

            {/* Info Bar */}
            {(data.language || data.duration_seconds) && (
                <div className="mb-6 flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                    {data.language && <span>语言: {data.language}</span>}
                    {data.duration_seconds && (
                        <span>时长: {formatDuration(data.duration_seconds)}</span>
                    )}
                </div>
            )}

            <div className="space-y-6">
                {/* NEW: SRT Navigation Section (only show if segments exist) */}
                {showAudioPlayer && (
                    <CollapsibleSection
                        title="音频播放与字幕"
                        defaultOpen={true}
                    >
                        <div className="space-y-4">
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                点击任意字幕行跳转到对应时间点
                            </p>
                            <SrtList
                                segments={segments}
                                currentTime={currentTime}
                                onSeek={handleSeek}
                            />
                        </div>
                    </CollapsibleSection>
                )}

                {/* Transcription Text - Reusing CollapsibleSection */}
                <CollapsibleSection
                    title="转录结果"
                    defaultOpen={true}
                    headerContent={
                        data.text && (
                            <div className="flex gap-2 flex-wrap">
                                <button
                                    onClick={() => handleDownload('txt')}
                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <Download className="w-4 h-4" />
                                    下载文本
                                </button>
                                <button
                                    onClick={() => handleDownload('srt')}
                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <Download className="w-4 h-4" />
                                    下载字幕(SRT)
                                </button>
                            </div>
                        )
                    }
                >
                    {displayText ? (
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                            {displayText}
                        </pre>
                    ) : (
                        <p className="text-gray-500 dark:text-gray-400 text-sm">
                            转录内容为空
                        </p>
                    )}
                </CollapsibleSection>

                {/* AI Summary - Reusing CollapsibleSection with Markdown */}
                {data.summary && (
                    <CollapsibleSection
                        title="AI摘要"
                        defaultOpen={true}
                        headerContent={
                            <div className="flex gap-2 flex-wrap">
                                {/* Download DOCX button */}
                                <button
                                    onClick={() => handleDownloadDocx()}
                                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors"
                                    title="下载Word文档"
                                >
                                    <File className="w-4 h-4" />
                                    下载DOCX
                                </button>
                            </div>
                        }
                    >
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    h1: ({node, ...props}) => <h1 className="text-xl font-bold mb-4 pb-2 border-b dark:border-gray-700" {...props} />,
                                    h2: ({node, ...props}) => <h2 className="text-lg font-semibold mb-3 mt-6" {...props} />,
                                    h3: ({node, ...props}) => <h3 className="text-base font-semibold mb-2 mt-4" {...props} />,
                                    p: ({node, ...props}) => <p className="mb-3 leading-7" {...props} />,
                                    ul: ({node, ...props}) => <ul className="list-disc list-inside mb-3 space-y-1" {...props} />,
                                    ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-3 space-y-1" {...props} />,
                                    li: ({node, ...props}) => <li className="ml-4" {...props} />,
                                    code: ({node, className, ...props}) =>
                                        className
                                            ? <code className="block p-3 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-mono overflow-x-auto" {...props} />
                                            : <code className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-sm font-mono text-pink-600 dark:text-pink-400" {...props} />,
                                    pre: ({node, ...props}) => <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto mb-3" {...props} />,
                                    blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic text-gray-600 dark:text-gray-400 my-3" {...props} />,
                                    a: ({node, ...props}) => <a className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                                    table: ({node, ...props}) => <div className="overflow-x-auto mb-3"><table className="min-w-full border border-gray-200 dark:border-gray-700" {...props} /></div>,
                                    thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
                                    th: ({node, ...props}) => <th className="px-4 py-2 border border-gray-200 dark:border-gray-700 text-left font-semibold" {...props} />,
                                    td: ({node, ...props}) => <td className="px-4 py-2 border border-gray-200 dark:border-gray-700" {...props} />,
                                    hr: ({node, ...props}) => <hr className="my-4 border-gray-300 dark:border-gray-700" {...props} />,
                                    strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                                    em: ({node, ...props}) => <em className="italic" {...props} />,
                                }}
                            >
                                {data.summary}
                            </ReactMarkdown>
                        </div>
                    </CollapsibleSection>
                )}

                {/* AI Chat Section - Read-Only Display */}
                <CollapsibleSection
                    title="AI 问答"
                    defaultOpen={true}
                >
                    <ChatDisplay
                        messages={data.chat_messages}
                        loading={false}
                        emptyMessage="对此转录内容进行AI问答"
                        emptyDescription="提问关于此转录的任何问题，AI会根据转录内容进行回答。请登录后使用完整聊天功能。"
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-4 text-center">
                        AI问答基于转录内容，请确保问题与内容相关
                    </p>
                </CollapsibleSection>
            </div>

            {/* Footer */}
            <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
                <p className="text-center text-sm text-gray-500 dark:text-gray-400">
                    由 <a href="/" className="text-blue-600 dark:text-blue-400 hover:underline">Whisper Summarizer</a> 提供支持
                </p>
            </div>

            {/* NEW: Sticky Audio Player (fixed at bottom) */}
            {showAudioPlayer && (
                <AudioPlayer
                    audioUrl={audioUrl}
                    segments={segments}
                    onSeek={handleSeek}
                />
            )}
        </div>
    )
}
```

**Step 4: Run test to verify it passes**

Run: `bun test frontend/src/pages/__tests__/SharedTranscription.test.tsx`
Expected: PASS (all 3 tests)

**Step 5: Commit**

```bash
git add frontend/src/pages/SharedTranscription.tsx frontend/src/pages/__tests__/SharedTranscription.test.tsx
git commit -m "feat(frontend): integrate audio player with SRT navigation into shared page"
```

---

## Task 7: Frontend - Add Responsive Styles for Smartphone

**Files:**
- Modify: `frontend/src/components/AudioPlayer.tsx` (responsive styles)
- Modify: `frontend/src/components/SrtList.tsx` (responsive styles)

**Step 1: Write the failing test**

Extend `frontend/src/components/__tests__/SrtList.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { SrtList } from '../SrtList';

describe('SrtList Responsive Design', () => {
  const mockSegments = [
    { start: 0.0, end: 2.5, text: 'First segment with longer text' },
    { start: 2.5, end: 5.0, text: 'Second segment with longer text' },
  ];

  it('should apply responsive text sizes', () => {
    const { container } = render(
      <SrtList segments={mockSegments} currentTime={0} onSeek={() => {}} />
    );

    const segmentTexts = container.querySelectorAll('.text-sm');
    expect(segmentTexts.length).toBeGreaterThan(0);
  });

  it('should have minimum touch target size (48px)', () => {
    const { container } = render(
      <SrtList segments={mockSegments} currentTime={0} onSeek={() => {}} />
    );

    const segments = container.querySelectorAll('[data-testid^="segment-"]');
    segments.forEach(seg => {
      const styles = window.getComputedStyle(seg);
      const height = parseInt(styles.minHeight);
      expect(height).toBeGreaterThanOrEqual(48);
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `bun test frontend/src/components/__tests__/SrtList.test.tsx`
Expected: FAIL with "minHeight not applied"

**Step 3: Write minimal implementation**

Update `frontend/src/components/SrtList.tsx`:

```typescript
import { useEffect, useRef } from 'react';
import { Clock } from 'lucide-react';
import { cn } from '../utils/cn';

export interface Segment {
  start: number;
  end: number;
  text: string;
}

interface SrtListProps {
  segments: Segment[];
  currentTime: number;
  onSeek: (time: number) => void;
  className?: string;
}

export function SrtList({ segments, currentTime, onSeek, className }: SrtListProps) {
  const currentSegmentRef = useRef<HTMLDivElement>(null);

  // Find current segment index
  const currentIndex = segments.findIndex(
    seg => currentTime >= seg.start && currentTime < seg.end
  );

  // Auto-scroll current segment into view
  useEffect(() => {
    if (currentIndex >= 0 && currentSegmentRef.current) {
      currentSegmentRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, [currentIndex]);

  // Format time as MM:SS
  const formatTime = (time: number): string => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  if (segments.length === 0) {
    return (
      <div className={cn("text-center py-8 text-gray-500", className)}>
        <p>暂无字幕数据</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      {segments.map((segment, index) => {
        const isCurrent = index === currentIndex;

        return (
          <div
            key={`${segment.start}-${index}`}
            ref={isCurrent ? currentSegmentRef : null}
            data-current={isCurrent}
            onClick={() => onSeek(segment.start)}
            // NEW: Responsive styles + minimum touch target (48px)
            className={cn(
              "flex gap-3 p-3 rounded-lg cursor-pointer transition-all min-h-[48px]",
              "hover:bg-gray-100 dark:hover:bg-gray-800",
              // Smartphone: larger text, more padding
              "sm:p-4 sm:text-base",
              isCurrent && "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500"
            )}
          >
            {/* Timestamp */}
            <div className="flex items-center gap-1 flex-shrink-0 text-xs sm:text-sm text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3 sm:w-4 sm:h-4" />
              <span className="tabular-nums">{formatTime(segment.start)}</span>
            </div>

            {/* Text - NEW: Responsive text size */}
            <p className="text-sm sm:text-base text-gray-800 dark:text-gray-200 flex-1">
              {segment.text}
            </p>

            {/* Current indicator */}
            {isCurrent && (
              <div className="flex-shrink-0">
                <span className="inline-block w-2 h-2 sm:w-3 sm:h-3 bg-blue-500 rounded-full animate-pulse" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

Update `frontend/src/components/AudioPlayer.tsx`:

```typescript
import { useRef, useEffect, useState, useCallback } from 'react';
import { Play, Pause, Volume2, Maximize2, Minimize2 } from 'lucide-react';
import { cn } from '../utils/cn';

export interface Segment {
  start: number;
  end: number;
  text: string;
}

interface AudioPlayerProps {
  audioUrl: string;
  segments: Segment[];
  onSeek: (time: number) => void;
  className?: string;
}

export function AudioPlayer({ audioUrl, segments, onSeek, className }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(-1);

  // Update current segment based on playback time
  useEffect(() => {
    const index = segments.findIndex(
      seg => currentTime >= seg.start && currentTime < seg.end
    );
    setCurrentSegmentIndex(index);
  }, [currentTime, segments]);

  // Handle play/pause toggle
  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  // Handle seeking when user clicks a segment
  const handleSegmentClick = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = time;
    onSeek(time);

    // Update current time state for immediate UI feedback
    setCurrentTime(time);
  }, [onSeek]);

  // Handle seek bar change
  const handleSeekChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const time = parseFloat(e.target.value);
    audio.currentTime = time;
    setCurrentTime(time);
  }, []);

  // Format time as MM:SS
  const formatTime = (time: number): string => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className={cn(
      // NEW: Responsive heights
      "fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t dark:border-gray-700 shadow-lg z-50",
      !isExpanded && "h-16 sm:h-20",
      isExpanded && "h-24 sm:h-32",
      className
    )}>
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onDurationChange={(e) => setDuration(e.currentTarget.duration)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        data-testid="audio-element"
      />

      {/* Compact mode */}
      <div className="flex items-center justify-between px-3 sm:px-4 py-2 h-full">
        {/* Play/Pause button - NEW: Larger touch target on mobile */}
        <button
          onClick={togglePlayPause}
          className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors"
          aria-label={isPlaying ? '暂停' : '播放'}
        >
          {isPlaying ? <Pause className="w-5 h-5 sm:w-6 sm:h-6" /> : <Play className="w-5 h-5 sm:w-6 sm:h-6 ml-0.5" />}
        </button>

        {/* Progress bar and time */}
        <div className="flex-1 mx-2 sm:mx-4">
          <input
            type="range"
            min="0"
            max={duration || 0}
            step="0.1"
            value={currentTime}
            onChange={handleSeekChange}
            className="w-full h-2 sm:h-3 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            aria-label="进度"
          />
          <div className="flex justify-between text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Expand/collapse button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label={isExpanded ? '收起' : '展开'}
        >
          {isExpanded ? <Minimize2 className="w-5 h-5 sm:w-6 sm:h-6" /> : <Maximize2 className="w-5 h-5 sm:w-6 sm:h-6" />}
        </button>
      </div>

      {/* Expanded mode - show current segment text */}
      {isExpanded && currentSegmentIndex >= 0 && (
        <div className="px-3 sm:px-4 pb-2">
          <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
            {segments[currentSegmentIndex]?.text}
          </p>
        </div>
      )}
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `bun test frontend/src/components/__tests__/*.test.tsx`
Expected: PASS (all tests including responsive tests)

**Step 5: Commit**

```bash
git add frontend/src/components/AudioPlayer.tsx frontend/src/components/SrtList.tsx frontend/src/components/__tests__
git commit -m "feat(frontend): add responsive styles for smartphone layout"
```

---

## Task 8: Integration Testing - E2E Test

**Files:**
- Create: `tests/e2e/test_shared_audio_player.spec.ts`

**Step 1: Write the failing test**

Create `tests/e2e/test_shared_audio_player.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Shared Transcription Audio Player', () => {
  const shareToken = process.env.TEST_SHARE_TOKEN || 'test-token';
  const baseUrl = process.env.BASE_URL || 'http://localhost:8130';

  test('should load shared transcription and display audio player', async ({ page }) => {
    await page.goto(`${baseUrl}/shared/${shareToken}`);

    // Wait for page load
    await expect(page.locator('h1')).toBeVisible();

    // Check for audio player
    const audioPlayer = page.locator('[data-testid="audio-element"]');
    await expect(audioPlayer).toBeVisible();
  });

  test('should play audio when play button clicked', async ({ page }) => {
    await page.goto(`${baseUrl}/shared/${shareToken}`);

    // Click play button
    const playButton = page.locator('button[aria-label="播放"]');
    await playButton.click();

    // Check that audio is playing (wait for timeupdate)
    const audio = page.locator('[data-testid="audio-element"]');
    const currentTime = await audio.evaluate(el => (el as HTMLAudioElement).currentTime);

    expect(currentTime).toBeGreaterThan(0);
  });

  test('should seek to timestamp when segment clicked', async ({ page }) => {
    await page.goto(`${baseUrl}/shared/${shareToken}`);

    // Get the audio element
    const audio = page.locator('[data-testid="audio-element"]');

    // Click second segment
    const secondSegment = page.locator('text=00:02').first();
    await secondSegment.click();

    // Wait for seek
    await page.waitForTimeout(100);

    const currentTime = await audio.evaluate(el => (el as HTMLAudioElement).currentTime);
    expect(currentTime).toBeCloseTo(2.5, 0); // 2.5s start time
  });

  test('should highlight current segment during playback', async ({ page }) => {
    await page.goto(`${baseUrl}/shared/${shareToken}`);

    // Start playback
    const playButton = page.locator('button[aria-label="播放"]');
    await playButton.click();

    // Wait for playback to progress
    await page.waitForTimeout(3000);

    // Check for highlighted segment (has data-current="true")
    const currentSegment = page.locator('[data-current="true"]');
    await expect(currentSegment).toBeVisible();
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(`${baseUrl}/shared/${shareToken}`);

    // Check bottom padding for audio player
    const container = page.locator('.pb-20');
    await expect(container).toBeVisible();

    // Check that SRT list items are large enough for touch (min 48px)
    const segment = page.locator('.min-h-\\[48px\\]').first();
    await expect(segment).toBeVisible();
  });
});
```

**Step 2: Run test to verify it fails**

Run: `bun test tests/e2e/test_shared_audio_player.spec.ts` (with dev environment running)
Expected: FAIL with missing functionality

**Step 3: No implementation needed**

This is an integration test that verifies the previous implementations work together. If all previous tasks pass, this should also pass.

**Step 4: Run test to verify it passes**

Run: `bun test tests/e2e/test_shared_audio_player.spec.ts`
Expected: PASS (all 5 tests)

**Step 5: Commit**

```bash
git add tests/e2e/test_shared_audio_player.spec.ts
git commit -m "test(e2e): add audio player integration tests"
```

---

## Task 9: Documentation - Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (add audio player documentation)

**Step 1: Write documentation content**

Add to `CLAUDE.md` in a new section:

```markdown
## Audio Player with SRT Navigation

Shared transcription pages include an audio player with subtitle navigation for listening to the original audio while following the transcription.

### Features

- **Sticky Audio Player**: Fixed at bottom of viewport, always accessible
- **SRT Navigation**: Click any subtitle line to jump to that timestamp
- **Auto-Highlighting**: Current subtitle is highlighted during playback
- **Auto-Scrolling**: Subtitle list scrolls to keep current segment in view
- **Responsive Design**: Optimized for smartphone (16px text, 48px touch targets)

### API Endpoints

**Get Segments** (JSON):
```
GET /api/shared/{share_token}/segments
Response: [{start: 0.0, end: 2.5, text: "..."}, ...]
```

**Stream Audio** (with Range support):
```
GET /api/shared/{share_token}/audio
Response: audio/* stream (supports seeking)
```

### Frontend Components

```typescript
<AudioPlayer
  audioUrl="/api/shared/abc123/audio"
  segments={segments}
  onSeek={(time) => setCurrentTime(time)}
/>

<SrtList
  segments={segments}
  currentTime={currentTime}
  onSeek={(time) => audioRef.current.currentTime = time}
/>
```

### Requirements

- **Segments file**: `segments.json.gz` must exist (generated by runner)
- **Original audio**: `file_path` in transcription must point to accessible audio file
- **Browser support**: HTML5 Audio API (all modern browsers)
```

**Step 2: Run verification**

No test - just documentation verification

**Step 3: Add to file**

**Step 4: Verify**

Read back the file to confirm content is correct

**Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add audio player with SRT navigation documentation"
```

---

## Summary

This plan implements a complete audio player with SRT navigation for the shared transcription page, optimized for smartphone viewing.

**Backend Changes:**
- 2 new API endpoints (segments JSON + audio streaming with Range)
- ~150 lines of code

**Frontend Changes:**
- 3 new components (AudioPlayer, SrtList, integration)
- ~300 lines of code
- Responsive design (48px touch targets, 16px text)

**Test Coverage:**
- 8 backend tests (segments + audio streaming)
- 11 frontend unit tests
- 5 E2E integration tests

**Total Tasks: 9**
- Backend: 2 tasks
- Frontend: 5 tasks
- Testing: 1 task
- Documentation: 1 task
