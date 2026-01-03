/**
 * Tests for Modal component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Modal } from '@/components/ui/Modal'

describe('Modal Component', () => {
  let originalOverflow: string

  beforeEach(() => {
    originalOverflow = document.body.style.overflow
  })

  afterEach(() => {
    document.body.style.overflow = originalOverflow
  })

  describe('Open/Close State', () => {
    it('does not render when isOpen is false', () => {
      render(<Modal isOpen={false} onClose={vi.fn()}>Content</Modal>)
      expect(screen.queryByText('Content')).not.toBeInTheDocument()
    })

    it('renders when isOpen is true', () => {
      render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('renders title when provided', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Modal Title">
          Content
        </Modal>
      )
      expect(screen.getByText('Modal Title')).toBeInTheDocument()
    })

    it('does not render title when not provided', () => {
      render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      expect(screen.queryByText('Modal Title')).not.toBeInTheDocument()
    })
  })

  describe('Body Scroll Lock', () => {
    it('sets body overflow to hidden when open', async () => {
      render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })
    })

    it('restores body overflow when closed', async () => {
      const { rerender } = render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })

      rerender(<Modal isOpen={false} onClose={vi.fn()}>Content</Modal>)

      await waitFor(() => {
        expect(document.body.style.overflow).toBe('unset')
      })
    })

    it('restores body overflow on unmount', async () => {
      const { unmount } = render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })

      unmount()

      await waitFor(() => {
        expect(document.body.style.overflow).toBe('unset')
      })
    })
  })

  describe('Overlay Click', () => {
    it('calls onClose when overlay is clicked', async () => {
      const handleClose = vi.fn()
      render(<Modal isOpen={true} onClose={handleClose}>Content</Modal>)
      
      const overlay = screen.getByText('Content').parentElement?.firstElementChild
      await userEvent.click(overlay!)
      
      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Close Button', () => {
    it('renders close button when title is provided', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Title">
          Content
        </Modal>
      )
      const closeButton = screen.getByLabelText('Close')
      expect(closeButton).toBeInTheDocument()
    })

    it('calls onClose when close button is clicked', async () => {
      const handleClose = vi.fn()
      render(
        <Modal isOpen={true} onClose={handleClose} title="Title">
          Content
        </Modal>
      )
      
      const closeButton = screen.getByLabelText('Close')
      await userEvent.click(closeButton)
      
      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Content Rendering', () => {
    it('renders children content', () => {
      render(<Modal isOpen={true} onClose={vi.fn()}>Modal Content</Modal>)
      expect(screen.getByText('Modal Content')).toBeInTheDocument()
    })

    it('renders complex children', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          <h1>Heading</h1>
          <p>Paragraph</p>
        </Modal>
      )
      expect(screen.getByText('Heading')).toBeInTheDocument()
      expect(screen.getByText('Paragraph')).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies base modal classes', () => {
      render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      const modal = screen.getByText('Content').parentElement
      expect(modal).toHaveClass('bg-white', 'dark:bg-gray-800', 'rounded-lg', 'shadow-xl')
    })

    it('merges custom className', () => {
      render(<Modal isOpen={true} onClose={vi.fn()} className="custom-class">Content</Modal>)
      const modal = screen.getByText('Content').parentElement
      expect(modal).toHaveClass('custom-class')
    })

    it('applies overlay classes', () => {
      render(<Modal isOpen={true} onClose={vi.fn()}>Content</Modal>)
      const overlay = screen.getByText('Content').parentElement?.parentElement?.firstElementChild
      expect(overlay).toHaveClass('bg-black/50')
    })
  })

  describe('Accessibility', () => {
    it('has aria-label on close button', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Title">
          Content
        </Modal>
      )
      const closeButton = screen.getByRole('button', { name: /close/i })
      expect(closeButton).toBeInTheDocument()
    })
  })

  describe('Conditional Return', () => {
    it('uses conditional return to avoid hooks violation', () => {
      // This test verifies the component uses conditional return (not early return)
      // which preserves hook order
      const { rerender } = render(
        <Modal isOpen={false} onClose={vi.fn()}>
          Content
        </Modal>
      )

      // Rerender with isOpen true should not cause hooks order issues
      rerender(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )

      expect(screen.getByText('Content')).toBeInTheDocument()
    })
  })
})
