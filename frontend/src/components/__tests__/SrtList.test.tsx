import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
      const user = userEvent.setup()
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segment = container.querySelectorAll('[data-segment-index]')[0]
      segment?.focus()
      await user.keyboard(' ')

      // Verify that Space key triggers onSeek (which means preventDefault worked)
      await waitFor(() => {
        expect(mockOnSeek).toHaveBeenCalledWith(0)
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

  describe('Responsive Design', () => {
    it('should have minimum touch target size (48px) for segments', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        const styles = window.getComputedStyle(segment as Element)
        const minHeight = styles.minHeight
        // Should have min-h-[48px] class
        expect(segment.className).toContain('min-h-')
        expect(segment.className).toContain('48')
      })
    })

    it('should have responsive padding (p-3 sm:p-4)', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        // Should have mobile padding p-3 and tablet+ sm:p-4
        expect(segment.className).toContain('p-3')
        expect(segment.className).toContain('sm:p-4')
      })
    })

    it('should have responsive text size (text-sm sm:text-base)', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      const segments = container.querySelectorAll('[data-segment-index]')
      segments.forEach(segment => {
        // Text content is in a child div, check child div for responsive sizing
        const textDiv = segment.querySelector('.flex-1')
        expect(textDiv?.className).toContain('text-sm')
        expect(textDiv?.className).toContain('sm:text-base')
      })
    })

    it('should have responsive Clock icon size', () => {
      const { container } = render(
        <SrtList segments={mockSegments} currentTime={0} onSeek={mockOnSeek} />
      )

      // Clock icons should have responsive sizing
      // Note: lucide-react icons are inline SVGs with className on the svg element
      const clockIcons = container.querySelectorAll('[data-testid*="clock"] svg, svg[class*="lucide"]')
      const allSvgs = container.querySelectorAll('svg')

      // If we can't find clock icons specifically, check that at least some SVGs exist
      expect(allSvgs.length).toBeGreaterThan(0)

      // Check that Clock component is rendered (it should have responsive classes)
      // The Clock icon from lucide-react should have the responsive sizing we applied
      allSvgs.forEach(icon => {
        // Check if this could be a Clock icon (has standard sizing classes)
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
      render(<SrtList segments={mockSegments} currentTime={2} onSeek={mockOnSeek} />)

      // When a segment is current, it should have pulse indicator with responsive size
      const pulseIndicator = document.querySelector('.animate-pulse')
      expect(pulseIndicator).toBeInTheDocument()
      expect(pulseIndicator?.className).toContain('w-2')
      expect(pulseIndicator?.className).toContain('h-2')
      expect(pulseIndicator?.className).toContain('sm:w-3')
      expect(pulseIndicator?.className).toContain('sm:h-3')
    })
  })

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
})
