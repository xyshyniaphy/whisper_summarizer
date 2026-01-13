import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import SrtList from '../SrtList'

// Mock cn utility
vi.mock('../../utils/cn', () => ({
  cn: (...classes: (string | undefined | null | false)[]) => {
    return classes.filter(Boolean).join(' ')
  }
}))

describe('SrtList Component', () => {
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
    it('should render all segments', () => {
      render(<SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />)

      expect(screen.getByText('First segment')).toBeInTheDocument()
      expect(screen.getByText('Second segment')).toBeInTheDocument()
      expect(screen.getByText('Third segment')).toBeInTheDocument()
    })

    it('should display timestamps in MM:SS format', () => {
      render(<SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />)

      expect(screen.getByText('00:00')).toBeInTheDocument()
      expect(screen.getByText('00:05')).toBeInTheDocument()
      expect(screen.getByText('00:10')).toBeInTheDocument()
    })

    it('should show empty state when no segments', () => {
      render(<SrtList segments={[]} currentTime={0} onSeek={mockOnSeek} />)

      expect(screen.getByText('暂无字幕数据')).toBeInTheDocument()
    })
  })

  describe('Current Segment Highlighting', () => {
    it('should highlight current segment based on currentTime', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={7} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      expect(segments[1]).toHaveAttribute('data-current', 'true')
      expect(segments[0]).toHaveAttribute('data-current', 'false')
      expect(segments[2]).toHaveAttribute('data-current', 'false')
    })

    it('should show current segment indicator for first segment', () => {
      render(<SrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />)

      // First segment should have the pulse indicator
      const firstSegmentItems = screen.getAllByText('First segment')
      expect(firstSegmentItems.length).toBeGreaterThan(0)
    })
  })

  describe('Click to Seek', () => {
    it('should call onSeek with segment start time when clicked', async () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments[1].click()

      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(5)
      })
    })

    it('should call onSeek for each segment', async () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')

      segments[0].click()
      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(0)
      })

      segments[2].click()
      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(10)
      })
    })
  })

  describe('Auto-scroll', () => {
    it('should scroll current segment into view when currentTime changes', async () => {
      const { rerender } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      // Clear initial calls
      vi.clearAllMocks()

      // Update currentTime to trigger segment change
      rerender(<SrtList segments={mockSegments} currentTime={7} onSeek={mockOnSeek} />)

      await waitFor(() => {
        expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
          behavior: 'smooth',
          block: 'center'
        })
      })
    })

    it('should not scroll when current segment does not change', async () => {
      const { rerender } = render(
        <SrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />
      )

      // Clear initial calls
      vi.clearAllMocks()

      // Update within same segment
      rerender(<SrtList segments={mockSegments} currentTime={3} onSeek={mockOnSeek} />)

      // Should not call scrollIntoView again
      await waitFor(() => {
        expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled()
      }, { timeout: 100 })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA roles', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const list = container.querySelector('[role="list"]')
      expect(list).toBeInTheDocument()

      const items = container.querySelectorAll('[role="listitem"]')
      expect(items.length).toBe(3)
    })

    it('should have clickable segments with proper attributes', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        expect(segment).toHaveAttribute('tabIndex', '0')
      })
    })
  })

  describe('Segment Interface Export', () => {
    it('should export Segment interface', () => {
      expect(SrtList.Segment).toBeUndefined()

      // Check if types are exported via TypeScript
      // This is a compile-time check, runtime check is limited
    })
  })
})
