/**
 * VirtualizedSrtList component tests
 *
 * Tests virtual scrolling performance, auto-scroll, and segment navigation
 * for large transcription files (1000+ segments).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock cn utility first (before component import)
vi.mock('../../utils/cn', () => ({
  cn: (...classes: (string | undefined | null | false)[]) => {
    return classes.filter(Boolean).join(' ')
  }
}))

// Import component (the mock is in tests/setup.ts)
import VirtualizedSrtList from '../VirtualizedSrtList'

// Constants from component
const SEGMENT_HEIGHT = 80 // Estimated height per segment (padding + text + timestamp)

describe('VirtualizedSrtList Component', () => {
  const mockSegments = [
    { start: 0, end: 5, text: 'First segment' },
    { start: 5, end: 10, text: 'Second segment' },
    { start: 10, end: 15, text: 'Third segment' }
  ]

  const mockOnSeek = vi.fn()
  const mockUseVirtualizer = (global as any).mockUseVirtualizer

  beforeEach(() => {
    mockOnSeek.mockClear()
    if (mockUseVirtualizer) {
      mockUseVirtualizer.mockClear()
    }
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('should render empty state when no segments', () => {
      const mockVirtualizer = {
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      render(<VirtualizedSrtList segments={[]} currentTime={0} onSeek={mockOnSeek} />)

      expect(screen.getByText('暂无字幕数据')).toBeInTheDocument()
    })

    it('should call useVirtualizer with correct config', () => {
      const mockVirtualizer = {
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      render(<VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />)

      expect(mockUseVirtualizer).toHaveBeenCalledWith({
        count: 3,
        getScrollElement: expect.any(Function),
        estimateSize: expect.any(Function),
        overscan: 5,
      })
    })

    it('should render virtual items from virtualizer', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: SEGMENT_HEIGHT },
        { key: 'item-2', index: 2, start: SEGMENT_HEIGHT * 2 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 3,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      expect(container.querySelector('[data-index="0"]')).toBeInTheDocument()
      expect(container.querySelector('[data-index="1"]')).toBeInTheDocument()
      expect(container.querySelector('[data-index="2"]')).toBeInTheDocument()
    })
  })

  describe('Click to Seek', () => {
    it('should call onSeek when segment is clicked', async () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: SEGMENT_HEIGHT },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 2,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

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
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-2', index: 2, start: SEGMENT_HEIGHT * 2 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 3,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

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

  describe('Auto-scroll', () => {
    it('should call scrollToIndex when current segment changes', async () => {
      const mockScrollToIndex = vi.fn()
      const mockVirtualizer = {
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: mockScrollToIndex,
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

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
      const mockScrollToIndex = vi.fn()
      const mockVirtualizer = {
        getVirtualItems: () => [],
        getTotalSize: () => 0,
        scrollToIndex: mockScrollToIndex,
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

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

  describe('Keyboard Navigation', () => {
    it('should call onSeek when Enter key is pressed', async () => {
      const mockVirtualItems = [
        { key: 'item-1', index: 1, start: SEGMENT_HEIGHT },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 2,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

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
      const mockVirtualItems = [
        { key: 'item-2', index: 2, start: SEGMENT_HEIGHT * 2 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 3,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

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
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      // Spy on preventDefault before rendering
      const preventDefaultSpy = vi.fn()
      const originalPreventDefault = KeyboardEvent.prototype.preventDefault
      KeyboardEvent.prototype.preventDefault = preventDefaultSpy

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelector('[data-segment-index="0"]')

      // Trigger Space key
      if (segment) {
        await userEvent.type(segment, ' ')

        // Verify preventDefault was called (onSeek should also be called)
        await waitFor(() => {
          expect(mockOnSeek).toHaveBeenCalled()
          expect(preventDefaultSpy).toHaveBeenCalled()
        })
      }

      // Restore original
      KeyboardEvent.prototype.preventDefault = originalPreventDefault
    })
  })

  describe('Current Segment Highlighting', () => {
    it('should highlight current segment based on currentTime', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: SEGMENT_HEIGHT },
        { key: 'item-2', index: 2, start: SEGMENT_HEIGHT * 2 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 3,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={7} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments[1]).toHaveAttribute('data-current', 'true')
      expect(segments[0]).toHaveAttribute('data-current', 'false')
      expect(segments[2]).toHaveAttribute('data-current', 'false')
    })

    it('should display pulse indicator for current segment', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      render(<VirtualizedSrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />)

      const pulseIndicator = document.querySelector('.animate-pulse')
      expect(pulseIndicator).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA role on list container', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const list = container.querySelector('[role="list"]')
      expect(list).toBeInTheDocument()
    })

    it('should have aria-label on list container', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const list = container.querySelector('[role="list"]')
      expect(list).toHaveAttribute('aria-label', '字幕列表')
    })

    it('should have aria-label on each segment', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: SEGMENT_HEIGHT },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 2,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        expect(segment).toHaveAttribute('aria-label')
      })
    })

    it('should have aria-current="true" for current segment', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
        { key: 'item-1', index: 1, start: SEGMENT_HEIGHT },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 2,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={7} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments[1]).toHaveAttribute('aria-current', 'true')
      expect(segments[0]).not.toHaveAttribute('aria-current')
    })

    it('should have tabIndex={0} for keyboard navigation', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        expect(segment).toHaveAttribute('tabIndex', '0')
      })
    })
  })

  describe('Responsive Design', () => {
    it('should have minimum touch target size (48px) for segments', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        // Should have min-h-[48px] class
        expect(segment.className).toContain('min-h-')
        expect(segment.className).toContain('48')
      })
    })

    it('should have responsive padding (p-3 sm:p-4)', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        expect(segment.className).toContain('p-3')
        expect(segment.className).toContain('sm:p-4')
      })
    })

    it('should have responsive text size (text-sm sm:text-base)', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        const textDiv = segment.querySelector('.flex-1')
        expect(textDiv?.className).toContain('text-sm')
        expect(textDiv?.className).toContain('sm:text-base')
      })
    })

    it('should have responsive Clock icon size', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const allSvgs = container.querySelectorAll('svg')
      expect(allSvgs.length).toBeGreaterThan(0)

      allSvgs.forEach(icon => {
        const classes = icon.className.toString()
        if (classes.includes('w-3') || classes.includes('w-4')) {
          expect(classes).toContain('w-3')
          expect(classes).toContain('h-3')
          expect(classes).toContain('sm:w-4')
          expect(classes).toContain('sm:h-4')
        }
      })
    })

    it('should have responsive pulse indicator size', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      render(<VirtualizedSrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />)

      const pulseIndicator = document.querySelector('.animate-pulse')
      expect(pulseIndicator).toBeInTheDocument()
      expect(pulseIndicator?.className).toContain('w-2')
      expect(pulseIndicator?.className).toContain('h-2')
      expect(pulseIndicator?.className).toContain('sm:w-3')
      expect(pulseIndicator?.className).toContain('sm:h-3')
    })
  })

  describe('Edge Cases', () => {
    it('should handle negative currentTime gracefully', () => {
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={-5} onSeek={mockOnSeek} />
      )

      // Should not highlight any segment
      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        expect(segment).toHaveAttribute('data-current', 'false')
      })
    })

    it('should handle single segment', () => {
      const singleSegment = [{ start: 0, end: 5, text: 'Only segment' }]
      const mockVirtualItems = [
        { key: 'item-0', index: 0, start: 0 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={singleSegment} currentTime={2} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments.length).toBe(1)
      expect(segments[0]).toHaveAttribute('data-current', 'true')
    })

    it('should handle currentTime after last segment', () => {
      const mockVirtualItems = [
        { key: 'item-2', index: 2, start: SEGMENT_HEIGHT * 2 },
      ]
      const mockVirtualizer = {
        getVirtualItems: () => mockVirtualItems,
        getTotalSize: () => SEGMENT_HEIGHT * 3,
        scrollToIndex: vi.fn(),
      }
      mockUseVirtualizer.mockReturnValue(mockVirtualizer)

      const { container } = render(
        <VirtualizedSrtList segments={mockSegments} currentTime={999} onSeek={mockOnSeek} />
      )

      // Should not highlight any segment when currentTime is beyond all segments
      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        expect(segment).toHaveAttribute('data-current', 'false')
      })
    })

    it('should handle empty segments array', () => {
      render(<VirtualizedSrtList segments={[]} currentTime={0} onSeek={mockOnSeek} />)

      expect(screen.getByText('暂无字幕数据')).toBeInTheDocument()
    })
  })
})
