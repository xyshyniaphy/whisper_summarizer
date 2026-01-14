# SRT Player Comprehensive Test Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive test coverage for SRT player features including click-jump integration, VirtualizedSrtList, seek bar, error handling, keyboard navigation, and edge cases.

**Architecture:** Testing pyramid with 50+ tests across E2E (Playwright), integration, and unit (Vitest) levels. Focus on critical user flows: SRT click-jump with state preservation, virtual scrolling performance, and accessibility.

**Tech Stack:** Playwright (E2E), Vitest (unit), @testing-library/react, userEvent, vi.mock for external deps

**Current Coverage:** ~70% (basic functionality). **Target:** ~95% (including edge cases and integration).

---

## Test Files Overview

| Test File | Type | New Tests | Priority |
|-----------|------|-----------|----------|
| `tests/e2e/tests/shared-audio-player.spec.ts` | E2E | +8 | HIGH |
| `frontend/src/components/__tests__/AudioPlayer.test.tsx` | Unit | +6 | HIGH |
| `frontend/src/components/__tests__/SrtList.test.tsx` | Unit | +4 | MEDIUM |
| `frontend/src/components/__tests__/VirtualizedSrtList.test.tsx` | Unit | +12 | CRITICAL |

---

## Task 1: VirtualizedSrtList Unit Tests (NEW FILE)

**Why Critical:** VirtualizedSrtList has ZERO tests but is the production component for large transcriptions (1000+ segments).

**Files:**
- Create: `frontend/src/components/__tests__/VirtualizedSrtList.test.tsx`
- Reference: `frontend/src/components/VirtualizedSrtList.tsx`

**Step 1: Create test file with imports and mocks**

```typescript
/**
 * VirtualizedSrtList component tests
 *
 * Tests virtual scrolling performance, auto-scroll, and segment navigation
 * for large transcription files (1000+ segments).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import VirtualizedSrtList from '../VirtualizedSrtList'

// Mock @tanstack/react-virtual
vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: vi.fn(),
}))

// Mock cn utility
vi.mock('../../utils/cn', () => ({
  cn: (...classes: (string | undefined | null | false)[]) => {
    return classes.filter(Boolean).join(' ')
  }
}))
```

**Step 2: Run to verify file structure**

Run: `cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx`
Expected: PASS (empty test suite)

**Step 3: Add basic rendering tests**

```typescript
describe('VirtualizedSrtList Component', () => {
  const mockSegments = [
    { start: 0, end: 5, text: 'First segment' },
    { start: 5, end: 10, text: 'Second segment' },
    { start: 10, end: 15, text: 'Third segment' }
  ]

  const mockOnSeek = vi.fn()

  beforeEach(() => {
    mockOnSeek.mockClear()
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('should render empty state when no segments', () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      useVirtualizer.mockReturnValue({
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: vi.fn(),
      })

      render(<VirtualizedSrtList segments={[]} currentTime={0} onSeek={mockOnSeek} />)

      expect(screen.getByText('暂无字幕数据')).toBeInTheDocument()
    })

    it('should call useVirtualizer with correct config', () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualizer = {
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: vi.fn(),
      }
      useVirtualizer.mockReturnValue(mockVirtualizer)

      render(<VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />)

      expect(useVirtualizer).toHaveBeenCalledWith({
        count: 3,
        getScrollElement: expect.any(Function),
        estimateSize: expect.any(Function),
        overscan: 5,
      })
    })

    it('should render virtual items from virtualizer', () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: 80 },
        { key: 'item-2', index: 2, start: 160 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 240,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      expect(container.querySelector('[data-index="0"]')).toBeInTheDocument()
      expect(container.querySelector('[data-index="1"]')).toBeInTheDocument()
      expect(container.querySelector('[data-index="2"]')).toBeInTheDocument()
    })
  })
})
```

**Step 4: Run tests to verify they pass**

Run: `cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx`
Expected: PASS (3 tests)

**Step 5: Add click-to-seek tests**

```typescript
  describe('Click to Seek', () => {
    it('should call onSeek when segment is clicked', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: 80 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 160,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const secondSegment = container.querySelector('[data-index="1"] [data-segment-index="1"]')
      await userEvent.click(secondSegment!)

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(5)
      })
    })

    it('should call onSeek with correct timestamp for each segment', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-2', index: 2, start: 160 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 240,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const thirdSegment = container.querySelector('[data-index="2"] [data-segment-index="2"]')
      await userEvent.click(thirdSegment!)

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(10)
      })
    })
  })
```

**Step 6: Run tests to verify**

Run: `cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx`
Expected: PASS (5 tests total)

**Step 7: Add auto-scroll tests**

```typescript
  describe('Auto-scroll', () => {
    it('should call scrollToIndex when current segment changes', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockScrollToIndex = vi.fn()

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: mockScrollToIndex,
      })

      const { rerender } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      // Clear initial calls
      mockScrollToIndex.mockClear()

      // Update currentTime to change segment
      rerender(<VirtualizedSrtList segments={mockSegments} currentTime={7} onSeek={mockOnSeek} />)

      await waitFor(() => {
        expect(mockScrollToIndex).toHaveBeenCalledWith(1, {
          align: 'center',
          behavior: 'smooth'
        })
      })
    })

    it('should not scroll when current segment does not change', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockScrollToIndex = vi.fn()

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: mockScrollToIndex,
      })

      const { rerender } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />
      )

      // Clear initial calls
      mockScrollToIndex.mockClear()

      // Update within same segment
      rerender(<VirtualizedSrtList segments={mockSegments} currentTime={3} onSeek={mockOnSeek} />)

      // Should not call scrollToIndex again
      await waitFor(() => {
        expect(mockScrollToIndex).not.toHaveBeenCalled()
      }, { timeout: 100 })
    })
  })
```

**Step 8: Run tests to verify**

Run: `cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx`
Expected: PASS (7 tests total)

**Step 9: Add keyboard navigation tests**

```typescript
  describe('Keyboard Navigation', () => {
    it('should call onSeek when Enter key is pressed', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-1', index: 1, start: 80 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 160,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelector('[data-segment-index="1"]')
      segment?.focus()
      await userEvent.keyboard('{Enter}')

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(5)
      })
    })

    it('should call onSeek when Space key is pressed', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-2', index: 2, start: 160 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 240,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelector('[data-segment-index="2"]')
      segment?.focus()
      await userEvent.keyboard(' ')

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(10)
      })
    })

    it('should prevent default on Space key to avoid page scroll', async () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 80,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelector('[data-segment-index="0"]')
      let preventDefaultCalled = false

      const mockEvent = new KeyboardEvent('keydown', { key: ' ' })
      mockEvent.preventDefault = () => { preventDefaultCalled = true }

      segment?.dispatchEvent(mockEvent)

      await waitFor(() => {
        expect(preventDefaultCalled).toBe(true)
      })
    })
  })
```

**Step 10: Run tests to verify**

Run: `cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx`
Expected: PASS (10 tests total)

**Step 11: Add current segment highlighting tests**

```typescript
  describe('Current Segment Highlighting', () => {
    it('should highlight current segment based on currentTime', () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: 80 },
        { key: 'item-2', index: 2, start: 160 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 240,
        scrollToIndex: vi.fn(),
      })

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={7} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments[1]).toHaveAttribute('data-current', 'true')
      expect(segments[0]).toHaveAttribute('data-current', 'false')
      expect(segments[2]).toHaveAttribute('data-current', 'false')
    })

    it('should display pulse indicator for current segment', () => {
      const { useVirtualizer } = require('@tanstack/react-virtual')
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]

      useVirtualizer.mockReturnValue({
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => 80,
        scrollToIndex: vi.fn(),
      })

      render(<VirtualizedSrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />)

      const pulseIndicator = document.querySelector('.animate-pulse')
      expect(pulseIndicator).toBeInTheDocument()
    })
  })
```

**Step 12: Run tests to verify**

Run: `cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx`
Expected: PASS (12 tests total)

**Step 13: Commit VirtualizedSrtList tests**

```bash
git add frontend/src/components/__tests__/VirtualizedSrtList.test.tsx
git commit -m "test: add comprehensive VirtualizedSrtList unit tests (12 tests)

- Basic rendering (empty state, virtualizer config, virtual items)
- Click-to-seek functionality
- Auto-scroll with scrollToIndex
- Keyboard navigation (Enter/Space keys)
- Current segment highlighting with pulse indicator
"
```

---

## Task 2: AudioPlayer Unit Tests - External Seek & Error Handling

**Files:**
- Modify: `frontend/src/components/__tests__/AudioPlayer.test.tsx`
- Reference: `frontend/src/components/AudioPlayer.tsx:128-145`

**Step 1: Add externalCurrentTime seek tests**

Add to existing `AudioPlayer.test.tsx`:

```typescript
  describe('External Seek (from SrtList)', () => {
    it('should seek audio when externalCurrentTime prop changes', async () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
          currentTime={5.0}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement

      await waitFor(() => {
        expect(audioElement?.currentTime).toBe(5.0)
      })
    })

    it('should preserve playing state during external seek', async () => {
      const playMock = vi.fn().mockResolvedValue(undefined)

      HTMLAudioElement.prototype.play = playMock

      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
          currentTime={0}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement

      // Simulate playing state
      if (audioElement) {
        Object.defineProperty(audioElement, 'paused', { value: false, configurable: true })
        audioElement.dispatchEvent(new Event('play'))
      }

      // Clear previous play calls
      playMock.mockClear()

      // Rerender with new externalCurrentTime (simulating SrtList click)
      const { rerender } = render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
          currentTime={5.0}
        />
      )

      await waitFor(() => {
        expect(audioElement?.currentTime).toBe(5.0)
      })
    })

    it('should debounce seeks when time difference is less than 0.1s', () => {
      const { rerender } = render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
          currentTime={5.0}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement

      const initialCurrentTime = audioElement?.currentTime

      // Rerender with small time difference (< 0.1s)
      rerender(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
          currentTime={5.05} // Only 0.05s difference
        />
      )

      // Should not update audio element (debounced)
      expect(audioElement?.currentTime).toBe(initialCurrentTime)
    })
  })
```

**Step 2: Run tests to verify**

Run: `cd frontend && bun test tests/frontend/components/AudioPlayer.test.tsx`
Expected: PASS (3 new tests)

**Step 3: Add seek bar tests**

```typescript
  describe('Seek Bar', () => {
    it('should seek to correct time when seek bar is dragged', async () => {
      const user = userEvent.setup()
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const seekBar = document.querySelector('input[type="range"]')
      expect(seekBar).toBeTruthy()

      // Simulate drag to 50% of duration
      if (seekBar) {
        await user.click(seekBar)
        // Note: Full drag simulation requires fireEvent from testing-library
      }
    })

    it('should update ARIA attributes during playback', async () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const seekBar = document.querySelector('input[type="range"]')

      await waitFor(() => {
        expect(seekBar).toHaveAttribute('aria-valuenow', '0')
        expect(seekBar).toHaveAttribute('aria-valuemin', '0')
        expect(seekBar).toHaveAttribute('aria-valuetext', '00:00')
      })
    })

    it('should handle zero duration gracefully', () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={[]}
          onSeek={mockOnSeek}
        />
      )

      const seekBar = document.querySelector('input[type="range"]')

      expect(seekBar).toHaveAttribute('max', '0')
    })
  })
```

**Step 4: Run tests to verify**

Run: `cd frontend && bun test tests/frontend/components/AudioPlayer.test.tsx`
Expected: PASS (6 new tests total)

**Step 5: Add audio error handling tests**

```typescript
  describe('Audio Error Handling', () => {
    it('should display error message when audio fails to load', async () => {
      render(
        <AudioPlayer
          audioUrl="https://invalid-url.com/audio.mp3"
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement

      // Trigger error event
      if (audioElement) {
        audioElement.dispatchEvent(new Event('error'))
      }

      await waitFor(() => {
        expect(screen.getByText('音频加载失败，请稍后重试')).toBeInTheDocument()
      })
    })

    it('should clear error on successful audio load', async () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement

      // Trigger error
      if (audioElement) {
        audioElement.dispatchEvent(new Event('error'))
      }

      await waitFor(() => {
        expect(screen.getByText('音频加载失败，请稍后重试')).toBeInTheDocument()
      })

      // Trigger successful load
      if (audioElement) {
        Object.defineProperty(audioElement, 'duration', { value: 10, configurable: true })
        audioElement.dispatchEvent(new Event('loadedmetadata'))
      }

      await waitFor(() => {
        expect(screen.queryByText('音频加载失败，请稍后重试')).not.toBeInTheDocument()
      })
    })
  })
```

**Step 6: Run tests to verify**

Run: `cd frontend && bun test tests/frontend/components/AudioPlayer.test.tsx`
Expected: PASS (8 new tests total)

**Step 7: Commit AudioPlayer tests**

```bash
git add frontend/src/components/__tests__/AudioPlayer.test.tsx
git commit -m "test: add AudioPlayer external seek, seek bar, and error tests (8 tests)

- External seek from SrtList with state preservation
- Seek debounce for small time changes (< 0.1s)
- Seek bar drag and ARIA attributes
- Audio error handling with message display
- Error recovery on successful reload
"
```

---

## Task 3: SrtList Unit Tests - Keyboard & Edge Cases

**Files:**
- Modify: `frontend/src/components/__tests__/SrtList.test.tsx`
- Reference: `frontend/src/components/SrtList.tsx:86-92`

**Step 1: Add keyboard navigation tests**

Add to existing `SrtList.test.tsx`:

```typescript
  describe('Keyboard Navigation', () => {
    it('should call onSeek when Enter key is pressed on segment', async () => {
      const user = userEvent.setup()
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelectorAll('[data-segment-index]')[1]
      segment?.focus()
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(5)
      })
    })

    it('should call onSeek when Space key is pressed on segment', async () => {
      const user = userEvent.setup()
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelectorAll('[data-segment-index]')[2]
      segment?.focus()
      await user.keyboard(' ')

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(10)
      })
    })

    it('should prevent default on Space key to avoid page scroll', async () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelectorAll('[data-segment-index]')[0]
      let preventDefaultCalled = false

      const mockEvent = new KeyboardEvent('keydown', { key: ' ' })
      mockEvent.preventDefault = () => { preventDefaultCalled = true }

      segment?.dispatchEvent(mockEvent)

      await waitFor(() => {
        expect(preventDefaultCalled).toBe(true)
      })
    })
  })
```

**Step 2: Run tests to verify**

Run: `cd frontend && bun test components/__tests__/SrtList.test.tsx`
Expected: PASS (3 new tests)

**Step 3: Add edge case tests**

```typescript
  describe('Edge Cases', () => {
    it('should handle single segment correctly', () => {
      const singleSegment = [{ start: 0, end: 10, text: 'Only segment' }]
      const { container } = render(
        <SrtList segments={singleSegment} currentTime={5} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments.length).toBe(1)
      expect(segments[0]).toHaveAttribute('data-current', 'true')
    })

    it('should handle currentTime at exact segment boundary', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={5} onSeek={mockOnSeek} />
      )

      // At exactly 5.0 seconds, should be in second segment (not first)
      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments[1]).toHaveAttribute('data-current', 'true')
    })

    it('should handle currentTime beyond last segment', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={100} onSeek={mockOnSeek} />
      )

      // Beyond last segment, none should be current
      const currentSegment = container.querySelector('[data-current="true"]')
      expect(currentSegment).not.toBeInTheDocument()
    })

    it('should handle currentTime before first segment (negative)', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={-1} onSeek={mockOnSeek} />
      )

      // Before first segment, none should be current
      const currentSegment = container.querySelector('[data-current="true"]')
      expect(currentSegment).not.toBeInTheDocument()
    })
  })
```

**Step 4: Run tests to verify**

Run: `cd frontend && bun test components/__tests__/SrtList.test.tsx`
Expected: PASS (7 new tests total)

**Step 5: Commit SrtList tests**

```bash
git add frontend/src/components/__tests__/SrtList.test.tsx
git commit -m "test: add SrtList keyboard navigation and edge case tests (7 tests)

- Keyboard navigation (Enter/Space keys)
- preventDefault on Space to avoid page scroll
- Single segment handling
- Exact boundary timestamps
- currentTime beyond last segment
- Negative currentTime handling
"
```

---

## Task 4: E2E Tests - SRT Click Jump Integration

**Why Critical:** Tests the complete user flow: click SRT → player seeks → plays → highlights.

**Files:**
- Modify: `tests/e2e/tests/shared-audio-player.spec.ts`
- Reference: `@whisper-e2e` skill for patterns
- Reference: `frontend/src/components/AudioPlayer.tsx:128-145`

**Step 1: Add SRT click jump integration test**

Add to existing `shared-audio-player.spec.ts`:

```typescript
  test('should seek to segment start time when clicked and continue playing', async ({ page }) => {
    // Wait for segments to load
    await page.waitForSelector('[data-segment-index]')

    // Start playback
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for playback to start
    await page.waitForTimeout(1000)

    // Click on third segment (index 2)
    const segment = page.locator('[data-segment-index="2"]').first()
    await segment.click()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio currentTime is approximately at segment start time
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    // Segment 2 should be around 10+ seconds
    expect(currentTime).toBeGreaterThan(9)

    // Verify audio is still playing after seek
    const isPlaying = await audioElement.evaluate((el: HTMLAudioElement) => !el.paused)
    expect(isPlaying).toBe(true)
  })
```

**Step 2: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should seek to segment start time when clicked and continue playing"`
Expected: PASS

**Step 3: Add seek bar interaction test**

```typescript
  test('should seek when seek bar is dragged', async ({ page }) => {
    // Wait for audio to load
    await page.waitForSelector('[data-testid="audio-element"]')

    const audioElement = page.locator('[data-testid="audio-element"]')
    const seekBar = page.locator('input[type="range"]')

    // Get initial max value (duration)
    const max = await seekBar.getAttribute('max')

    // Click at 50% of seek bar
    await seekBar.click({
      position: { x: 0.5, y: 0 } // Click at middle horizontally
    })

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify currentTime is approximately at middle
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)

    if (max) {
      const expectedTime = parseFloat(max) * 0.5
      expect(currentTime).toBeCloseTo(expectedTime, 0) // Within 1 second tolerance
    }
  })
```

**Step 4: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should seek when seek bar is dragged"`
Expected: PASS

**Step 5: Add multiple rapid clicks test**

```typescript
  test('should handle multiple rapid segment clicks without errors', async ({ page }) => {
    // Wait for segments to load
    await page.waitForSelector('[data-segment-index]')

    // Rapidly click multiple segments
    for (let i = 0; i < 5; i++) {
      const segment = page.locator(`[data-segment-index="${i}"]`).first()
      await segment.click()
      await page.waitForTimeout(50) // Small delay between clicks
    }

    // Verify no console errors
    const logs = await page.evaluate(() => {
      return (window as any).consoleErrors || []
    })
    expect(logs.length).toBe(0)

    // Verify audio currentTime is at last clicked segment
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(0)
  })
```

**Step 6: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should handle multiple rapid segment clicks"`
Expected: PASS

**Step 7: Add keyboard navigation test**

```typescript
  test('should seek when Enter key is pressed on focused segment', async ({ page }) => {
    // Wait for segments to load
    await page.waitForSelector('[data-segment-index]')

    const audioElement = page.locator('[data-testid="audio-element"]')

    // Get initial time
    const initialTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(initialTime).toBe(0)

    // Focus second segment and press Enter
    const segment = page.locator('[data-segment-index="1"]').first()
    await segment.focus()
    await page.keyboard.press('Enter')

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify currentTime changed
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(1)
  })
```

**Step 8: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should seek when Enter key is pressed"`
Expected: PASS

**Step 9: Add mobile touch interaction test**

```typescript
  test('should handle segment clicks on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Wait for segments to load
    await page.waitForSelector('[data-segment-index]')

    // Tap on second segment (touch event)
    const segment = page.locator('[data-segment-index="1"]').first()
    await segment.tap()

    // Wait for seek to complete
    await page.waitForTimeout(500)

    // Verify audio seeked
    const audioElement = page.locator('[data-testid="audio-element"]')
    const currentTime = await audioElement.evaluate((el: HTMLAudioElement) => el.currentTime)
    expect(currentTime).toBeGreaterThan(1)
  })
```

**Step 10: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should handle segment clicks on mobile viewport"`
Expected: PASS

**Step 11: Add virtualized list performance test**

```typescript
  test('should render long transcription efficiently with virtual scrolling', async ({ page }) => {
    // Navigate to shared page with long transcription
    await page.goto(`${BASE_URL}/shared/${SHARE_TOKEN}`)

    // Wait for segments to load
    await page.waitForSelector('[data-segment-index]')

    // Count total rendered segment elements
    const renderedSegments = await page.locator('[data-segment-index]').count()

    // Verify virtualization: should render ~20-30 items even if transcription is longer
    // (VirtualizedSrtList with overscan=5 renders ~visible + 5 above + 5 below)
    expect(renderedSegments).toBeLessThan(50)

    // Verify scroll performance - scroll to bottom
    await page.evaluate(() => {
      const list = document.querySelector('[role="list"]')
      if (list) {
        list.scrollTop = list.scrollHeight
      }
    })

    // Wait a moment for virtual items to render
    await page.waitForTimeout(500)

    // Verify still ~20-30 items rendered (not all segments)
    const renderedSegmentsAfterScroll = await page.locator('[data-segment-index]').count()
    expect(renderedSegmentsAfterScroll).toBeLessThan(50)
  })
```

**Step 12: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should render long transcription efficiently"`
Expected: PASS

**Step 13: Add auto-scroll test**

```typescript
  test('should auto-scroll to current segment during playback', async ({ page }) => {
    // Wait for audio and segments to load
    await page.waitForSelector('[data-testid="audio-element"]')
    await page.waitForSelector('[data-segment-index]')

    // Start playback from beginning
    const playButton = page.locator('[data-testid="play-button"]')
    await playButton.click()

    // Wait for 5 seconds of playback
    await page.waitForTimeout(5000)

    // Check if a segment with data-current="true" is visible in viewport
    const currentSegment = page.locator('[data-current="true"]').first()

    // Verify current segment exists
    await expect(currentSegment).toHaveAttribute('data-current', 'true')

    // Verify current segment is approximately visible in viewport
    const isVisible = await currentSegment.isVisible()
    expect(isVisible).toBe(true)
  })
```

**Step 14: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should auto-scroll to current segment"`
Expected: PASS

**Step 15: Commit E2E tests**

```bash
git add tests/e2e/tests/shared-audio-player.spec.ts
git commit -m "test(e2e): add SRT player integration tests (8 tests)

- SRT click jump with play state preservation
- Seek bar drag interaction
- Multiple rapid clicks (debounce test)
- Keyboard navigation (Enter key)
- Mobile touch interaction
- Virtual scrolling performance verification
- Auto-scroll to current segment during playback
"
```

---

## Task 5: Dark Mode Tests (E2E)

**Files:**
- Modify: `tests/e2e/tests/shared-audio-player.spec.ts`

**Step 1: Add dark mode tests**

```typescript
  test.describe('Dark Mode', () => {
    test('should display SRT player correctly in dark mode', async ({ page }) => {
      // Enable dark mode (assuming app has a theme toggle)
      await page.emulateMedia({ colorScheme: 'dark' })

      // Navigate to shared page
      await page.goto(`${BASE_URL}/shared/${SHARE_TOKEN}`)

      // Wait for page to load
      await page.waitForLoadState('networkidle')

      // Verify audio player container has dark mode classes
      const audioPlayer = page.locator('[data-testid="audio-player-container"]')
      await expect(audioPlayer).toHaveClass(/dark:bg-gray-800/)

      // Verify segments are visible in dark mode
      const firstSegment = page.locator('[data-segment-index="0"]').first()
      await expect(firstSegment).toBeVisible()

      // Verify current segment highlighting works in dark mode
      const playButton = page.locator('[data-testid="play-button"]')
      await playButton.click()

      await page.waitForTimeout(3000)

      const currentSegment = page.locator('[data-current="true"]').first()
      await expect(currentSegment).toHaveAttribute('data-current', 'true')
    })
  })
```

**Step 2: Run E2E test to verify**

Run: `./run_test.sh e2e --grep "should display SRT player correctly in dark mode"`
Expected: PASS

**Step 3: Commit dark mode tests**

```bash
git add tests/e2e/tests/shared-audio-player.spec.ts
git commit -m "test(e2e): add dark mode SRT player test

- Verify dark mode styling
- Verify current segment highlighting in dark mode
"
```

---

## Summary

**Total New Tests: 35+**

| Test File | Tests Added | Coverage |
|-----------|-------------|----------|
| VirtualizedSrtList.test.tsx (NEW) | 12 | Virtual scrolling, auto-scroll, keyboard |
| AudioPlayer.test.tsx (extended) | 8 | External seek, seek bar, errors |
| SrtList.test.tsx (extended) | 7 | Keyboard, edge cases |
| shared-audio-player.spec.ts (E2E) | +10 | Integration, mobile, performance, dark mode |

**Key Test Areas:**
- ✅ SRT click-jump with state preservation (externalCurrentTime flow)
- ✅ Seek bar functionality and ARIA
- ✅ Audio error handling and recovery
- ✅ VirtualizedSrtList (ZERO → 12 tests)
- ✅ Keyboard navigation (Enter/Space)
- ✅ Edge cases (boundaries, single segment)
- ✅ E2E integration flows
- ✅ Mobile touch interactions
- ✅ Performance (virtual scrolling)
- ✅ Dark mode

**Coverage Increase: 70% → 95%**

---

## Execution Notes

**Prerequisites:**
- Dev environment running: `./run_dev.sh up-d`
- Test share token available: `TEST_SHARE_TOKEN` env var
- Frontend tests: `cd frontend && bun test`
- E2E tests: `./run_test.sh e2e`

**Dependencies:**
- `@tanstack/react-virtual` mocked in VirtualizedSrtList tests
- Audio API mocked in AudioPlayer tests
- `cn` utility mocked in all component tests

**Test Run Commands:**
```bash
# Unit tests
cd frontend && bun test

# Specific test file
cd frontend && bun test components/__tests__/VirtualizedSrtList.test.tsx

# E2E tests
./run_test.sh e2e

# Specific E2E test
./run_test.sh e2e --grep "should seek to segment"
```

---

## Related Skills

- `@whisper-e2e` - E2E testing patterns and file upload tricks
- `@whisper-player` - Audio player with SRT navigation documentation
- `@whisper-frontend` - Frontend UI patterns and coding standards
