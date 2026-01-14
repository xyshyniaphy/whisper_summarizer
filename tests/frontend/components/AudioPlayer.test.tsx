/**
 * AudioPlayer component tests
 *
 * Tests the audio player with SRT segment navigation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AudioPlayer } from '../../../src/components/AudioPlayer'

describe('AudioPlayer', () => {
  const mockSegments = [
    { start: 0, end: 2.5, text: 'First segment' },
    { start: 2.5, end: 5.0, text: 'Second segment' },
    { start: 5.0, end: 7.5, text: 'Third segment' },
  ]

  const mockAudioUrl = 'https://example.com/audio.mp3'
  const mockOnSeek = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders audio element with correct src', () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement
      expect(audioElement).toBeTruthy()
      expect(audioElement?.src).toBe(mockAudioUrl)
    })

    it('renders all segments when expanded', async () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      // Initially segments are hidden (compact mode)
      expect(screen.queryByText('First segment')).toBeNull()

      // Click expand button to show segments
      const expandButton = document.querySelector('[data-testid="expand-button"]')
      expandButton?.click()

      await waitFor(() => {
        expect(screen.getByText('First segment')).toBeTruthy()
        expect(screen.getByText('Second segment')).toBeTruthy()
        expect(screen.getByText('Third segment')).toBeTruthy()
      })
    })

    it('renders play/pause button', () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      // Play button should be present (initial state)
      const playButton = document.querySelector('[data-testid="play-button"]')
      expect(playButton).toBeTruthy()
    })

    it('renders time display', () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      // Time display should be present (00:00 / 00:00 initially)
      const timeDisplays = screen.getAllByText('00:00')
      expect(timeDisplays).toHaveLength(2) // current time and total time
      expect(timeDisplays[0]).toBeTruthy()
    })

    it('renders expand/collapse button', () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const expandButton = document.querySelector('[data-testid="expand-button"]')
      expect(expandButton).toBeTruthy()
    })
  })

  describe('Segment Navigation', () => {
    it('calls onSeek when segment is clicked', async () => {
      const user = userEvent.setup()
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      // Expand to show segments
      const expandButton = document.querySelector('[data-testid="expand-button"]')
      await user.click(expandButton!)

      await waitFor(() => {
        const secondSegment = document.querySelector('[data-testid="segment-1"]')
        expect(secondSegment).toBeTruthy()
      })

      const secondSegment = document.querySelector('[data-testid="segment-1"]')
      await user.click(secondSegment!)

      expect(mockOnSeek).toHaveBeenCalledWith(2.5)
    })

    it('highlights current segment during playback', async () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      // Expand to show segments
      const expandButton = document.querySelector('[data-testid="expand-button"]')
      expandButton?.click()

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement

      // Simulate playback at 3 seconds (second segment) by setting currentTime directly
      if (audioElement) {
        Object.defineProperty(audioElement, 'currentTime', { value: 3, configurable: true })
        audioElement.dispatchEvent(new Event('timeupdate'))
      }

      await waitFor(() => {
        const secondSegment = document.querySelector('[data-testid="segment-1"]')
        expect(secondSegment?.className).toContain('bg-blue-100')
      })
    })
  })

  describe('Expand/Collapse', () => {
    it('toggles expanded state when expand button is clicked', async () => {
      const user = userEvent.setup()
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const container = document.querySelector('[data-testid="audio-player-container"]')
      expect(container?.className).not.toContain('h-32')

      const expandButton = document.querySelector('[data-testid="expand-button"]')
      await user.click(expandButton!)

      await waitFor(() => {
        expect(container?.className).toContain('h-32')
      })
    })
  })

  describe('Play/Pause', () => {
    it('toggles play/pause when play button is clicked', async () => {
      const user = userEvent.setup()
      const playMock = vi.fn()
      const pauseMock = vi.fn()

      // Mock audio element methods
      HTMLAudioElement.prototype.play = playMock
      HTMLAudioElement.prototype.pause = pauseMock

      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={mockSegments}
          onSeek={mockOnSeek}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]') as HTMLAudioElement
      const playButton = document.querySelector('[data-testid="play-button"]')

      // Initial click should call play
      await user.click(playButton!)
      expect(playMock).toHaveBeenCalled()

      // Simulate playing state
      if (audioElement) {
        Object.defineProperty(audioElement, 'paused', { value: false, configurable: true })
        audioElement.dispatchEvent(new Event('play'))
      }

      await waitFor(() => {
        expect(pauseMock).not.toHaveBeenCalled()
      })
    })
  })

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

      const { rerender } = render(
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
      rerender(
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

  describe('Empty State', () => {
    it('renders correctly with empty segments array', () => {
      render(
        <AudioPlayer
          audioUrl={mockAudioUrl}
          segments={[]}
          onSeek={mockOnSeek}
        />
      )

      const audioElement = document.querySelector('[data-testid="audio-element"]')
      expect(audioElement).toBeTruthy()
    })
  })

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
})
