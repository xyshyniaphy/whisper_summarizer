---
name: whisper-player
description: Audio player with SRT (subtitle) navigation for shared transcription pages. Sticky player, click-to-seek, auto-highlighting, auto-scrolling, responsive design.
---

# whisper-player - Audio Player with SRT Navigation

## Purpose

Interactive audio player with synchronized subtitle navigation for shared transcription pages:
- **Sticky Audio Player** - Fixed at bottom for continuous access
- **SRT Navigation** - Click subtitle to jump to timestamp
- **Auto-Highlighting** - Current subtitle highlighted during playback
- **Auto-Scrolling** - List scrolls to keep current segment visible
- **Responsive Design** - Optimized for desktop and smartphone

## Quick Start

```bash
# Test audio player locally
cd frontend && bun run dev

# Navigate to shared transcription
open http://localhost:3000/shared/{share_token}
```

## Overview

The audio player feature enables a seamless listening experience:
- **Sticky positioning** - Player stays visible while scrolling
- **Click-to-seek** - Tap any subtitle to jump to that timestamp
- **Visual feedback** - Clear distinction between played/current/upcoming
- **Smooth scrolling** - Auto-scrolls to current segment
- **Mobile optimized** - Touch-friendly controls

## API Endpoints

### Get SRT Segments

```http
GET /api/shared/{share_token}/segments
```

**Response** (JSON):
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

### Get Audio File

```http
GET /api/shared/{share_token}/audio
```

**Features**:
- Supports HTTP Range requests for seeking
- Streams audio in chunks
- Compatible with HTML5 Audio API
- Returns appropriate Content-Type based on format

**Response Headers**:
```
Content-Type: audio/mpeg
Accept-Ranges: bytes
Content-Length: 12345678
Content-Range: bytes 0-1023/12345678
```

## Frontend Components

### AudioPlayer Component

```tsx
interface AudioPlayerProps {
  audioUrl: string;          // URL to audio file
  segments: SrtSegment[];    // Array of subtitle segments
  onTimeUpdate?: (time: number) => void;
  onSegmentClick?: (segment: SrtSegment) => void;
}

interface SrtSegment {
  start: number;    // Start time in seconds
  end: number;      // End time in seconds
  text: string;     // Subtitle text
}
```

**Example Usage**:
```tsx
<AudioPlayer
  audioUrl={`/api/shared/${shareToken}/audio`}
  segments={segments}
  onSegmentClick={(segment) => {
    audioRef.current?.seekTo(segment.start);
  }}
/>
```

### SrtList Component

```tsx
interface SrtListProps {
  segments: SrtSegment[];
  currentTime: number;
  onSegmentClick: (segment: SrtSegment) => void;
  autoScroll?: boolean;  // Default: true
}

// Segment styling states:
// - past: Already played (dimmed)
// - current: Currently playing (highlighted)
// - future: Not yet played (normal)
```

**Example Usage**:
```tsx
<SrtList
  segments={segments}
  currentTime={currentTime}
  onSegmentClick={(segment) => handleSegmentClick(segment)}
  autoScroll={true}
/>
```

## Features

### Sticky Audio Player

Fixed position at bottom of screen:

```css
.audio-player {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border-top: 1px solid #e5e7eb;
}
```

**Benefits**:
- Always visible regardless of scroll position
- Collapsible on mobile to save screen space

### SRT Navigation

Click subtitle to seek audio:

```tsx
const handleSegmentClick = (segment: SrtSegment) => {
  if (audioRef.current) {
    audioRef.current.currentTime = segment.start;
  }
};
```

**Visual feedback**:
- Highlight clicked segment temporarily
- Smooth scroll to selected segment

### Auto-Highlighting

Current subtitle highlighted during playback:

```tsx
const getCurrentSegment = (currentTime: number) => {
  return segments.find(
    seg => currentTime >= seg.start && currentTime < seg.end
  );
};
```

**Styling**:
```css
.segment-past { opacity: 0.5; }
.segment-current {
  background: #dbeafe;
  border-left: 4px solid #3b82f6;
}
.segment-future { opacity: 1; }
```

### Auto-Scrolling

List scrolls to keep current segment visible:

```tsx
useEffect(() => {
  if (autoScroll && currentSegment) {
    const element = document.querySelector(`[data-segment-index="${currentSegment.index}"]`);
    element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}, [currentSegment, autoScroll]);
```

**Smart behavior**:
- Only scrolls when current segment changes
- Respects user scroll position (doesn't interrupt manual scrolling)
- Configurable offset for better visibility

## Responsive Design

### Desktop Layout

```tsx
<div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg">
  <AudioControls />
  <SrtList className="max-h-96 overflow-y-auto" />
</div>
```

### Smartphone Layout

```tsx
<div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg">
  <div className="flex items-center justify-between p-4">
    <AudioControls />
    <button onClick={toggleList}>
      {isExpanded ? <ChevronDown /> : <ChevronUp />}
    </button>
  </div>
  {isExpanded && (
    <SrtList className="max-h-64 overflow-y-auto" />
  )}
</div>
```

**Mobile optimizations**:
- Player minimized to bottom bar by default
- Expandable subtitle list with toggle button
- Touch-friendly controls (larger tap targets)
- Prevents page scroll when interacting with player

## Requirements

### Server-Side

1. **Segments File**: `segments.json.gz` must exist
   - Location: `/app/data/segments/{transcription_id}.json.gz`
   - Generated by runner during transcription
   - Gzip-compressed JSON array of SRT segments
   - Contains accurate Whisper timestamps

2. **Original Audio**: `file_path` must be accessible
   - Stored in `/app/data/uploads/` or shared storage
   - Must be readable by server process
   - Supported formats: MP3, M4A, WAV, OGG, etc.

3. **Share Token**: Valid share token in database
   - Token must not be expired
   - Transcription must have `status=completed`

### Client-Side

1. **Browser Support**: HTML5 Audio API
   - Chrome/Edge: Full support
   - Firefox: Full support
   - Safari: Full support (iOS 13+)
   - Mobile browsers: Full support

2. **JavaScript Features**:
   - ES6+ (async/await, arrow functions)
   - React 18+ hooks (useState, useEffect, useRef)
   - CSS Scroll Snap module for smooth scrolling

## Implementation Details

### Segment Synchronization

Audio player's `timeupdate` event triggers highlight updates:

```tsx
useEffect(() => {
  const audio = audioRef.current;
  if (!audio) return;

  const handleTimeUpdate = () => {
    setCurrentTime(audio.currentTime);
  };

  audio.addEventListener('timeupdate', handleTimeUpdate);
  return () => audio.removeEventListener('timeupdate', handleTimeUpdate);
}, []);
```

Current segment determined by:
```typescript
currentTime >= segment.start && currentTime < segment.end
```

### Auto-Scroll Logic

```tsx
const scrollToSegment = (segment: SrtSegment) => {
  const element = segmentRefs.current[segment.index];
  if (element) {
    element.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
      inline: 'nearest'
    });
  }
};
```

**Respects user scroll**:
- Only scrolls when segment changes
- Checks if user is manually scrolling
- Configurable scroll offset

### Performance Optimizations

- **Segments loaded once** on component mount
- **Audio streaming** - no full download
- **Highlight updates debounced** to 100ms
- **Auto-scroll uses `requestAnimationFrame`** for smooth 60fps

## Testing

### Manual Testing Checklist

- [ ] Audio plays from beginning
- [ ] Clicking subtitle seeks to correct timestamp
- [ ] Current subtitle highlights during playback
- [ ] List scrolls to keep current segment visible
- [ ] Player remains visible when scrolling page
- [ ] Responsive design works on mobile
- [ ] Audio works with Range requests (seeking)
- [ ] Expired/invalid tokens show error

### E2E Test Example

```typescript
test('audio player with SRT navigation', async ({ page }) => {
  // Navigate to shared transcription
  await page.goto('/shared/abc123');

  // Wait for audio to load
  await page.waitForSelector('audio');

  // Click a subtitle segment
  await page.click('[data-segment-index="5"]');

  // Verify audio seeked to correct time
  const currentTime = await page.evaluate(() => {
    return document.querySelector('audio')?.currentTime;
  });
  expect(currentTime).toBeCloseTo(expectedTime, 1);

  // Verify segment is highlighted
  const segment = await page.locator('[data-segment-index="5"]');
  await expect(segment).toHaveClass(/segment-current/);
});
```

## Troubleshooting

### Audio Not Playing

**Checks**:
- Browser console for CORS errors
- Audio file exists at `file_path`
- Server sends correct `Content-Type` header
- Audio file is valid format

**Solution**:
```nginx
# Ensure proper MIME types in nginx
types {
    audio/mpeg m4a;
    audio/mp4 m4a;
}
```

### Segments Not Loading

**Checks**:
- `segments.json.gz` exists in `/app/data/segments/`
- Gzip compression is working
- Runner generated segments during transcription
- API response is successful

**Debug**:
```bash
# Check segments file
docker exec whisper_server_prd ls -la /app/data/segments/

# Test API
curl http://localhost:8130/api/shared/{token}/segments
```

### Auto-Scroll Not Working

**Checks**:
- `autoScroll` prop is `true`
- Browser supports `scrollIntoView()`
- Container has `overflow-y: auto`
- No CSS conflicts with scroll behavior

**Solution**:
```css
.srt-list {
  overflow-y: auto;
  scroll-behavior: smooth;
}
```

### Mobile Issues

**Checks**:
- Test on actual device (emulator may be inaccurate)
- Viewport meta tag configuration
- Touch events not blocked by other elements
- Player has high z-index for visibility

**Meta tag**:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

## Related Skills

```bash
# Audio chunking architecture
/whisper-chunking

# Frontend UI patterns
/whisper-frontend

# E2E testing patterns
/whisper-e2e
```

## See Also

- [CLAUDE.md - Audio Player with SRT Navigation](../../CLAUDE.md#audio-player-with-srt-navigation)
- [frontend/src/components/AudioPlayer.tsx](../../frontend/src/components/AudioPlayer.tsx)
- [frontend/src/components/SrtList.tsx](../../frontend/src/components/SrtList.tsx)
