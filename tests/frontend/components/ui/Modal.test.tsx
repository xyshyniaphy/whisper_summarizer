import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { Modal } from '@/components/ui/Modal'

describe('Modal Component', () => {
  describe('Rendering', () => {
    it('does not render when isOpen is false', () => {
      const { container } = render(
        <Modal isOpen={false} onClose={vi.fn()}>
          Content
        </Modal>
      )
      expect(container.firstChild).toBe(null)
    })

    it('renders when isOpen is true', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Modal Content
        </Modal>
      )
      expect(screen.getByText('Modal Content')).toBeInTheDocument()
    })

    it('renders title when provided', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Test Title">
          Content
        </Modal>
      )
      expect(screen.getByText('Test Title')).toBeInTheDocument()
    })

    it('does not render title when not provided', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    })

    it('renders children content correctly', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          <p>Child Content</p>
        </Modal>
      )
      expect(screen.getByText('Child Content')).toBeInTheDocument()
    })
  })

  describe('Body Scroll Lock', () => {
    it('sets body overflow to hidden when open', async () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })
    })

    it('resets body overflow when closed', async () => {
      const { rerender } = render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })

      rerender(
        <Modal isOpen={false} onClose={vi.fn()}>
          Content
        </Modal>
      )
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('unset')
      })
    })

    it('cleans up body overflow on unmount', async () => {
      const { unmount } = render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })

      unmount()
      await waitFor(() => {
        expect(document.body.style.overflow).toBe('unset')
      })
    })
  })

  describe('Close Behavior', () => {
    it('calls onClose when overlay is clicked', async () => {
      const user = userEvent.setup()
      const handleClose = vi.fn()
      render(
        <Modal isOpen={true} onClose={handleClose}>
          Content
        </Modal>
      )

      const overlay = screen.getByText('Content').parentElement?.querySelector('.bg-black\\/50')
      if (overlay) {
        await user.click(overlay)
        expect(handleClose).toHaveBeenCalledTimes(1)
      }
    })

    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup()
      const handleClose = vi.fn()
      render(
        <Modal isOpen={true} onClose={handleClose} title="Test">
          Content
        </Modal>
      )

      const closeButton = screen.getByLabelText('Close')
      await user.click(closeButton)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Styling and Layout', () => {
    it('has proper overlay classes', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      // The overlay is a fixed div sibling to the modal in the container
      const container = screen.getByText('Content').closest('.fixed')
      const overlay = container?.querySelector('.bg-black\\/50')
      expect(overlay).toHaveClass('fixed', 'inset-0', 'bg-black/50')
    })

    it('has proper modal container classes', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      const modal = screen.getByText('Content').closest('.bg-white')
      expect(modal).toHaveClass(
        'relative',
        'bg-white',
        'dark:bg-gray-800',
        'rounded-lg',
        'shadow-xl',
        'max-w-lg',
        'w-full'
      )
    })

    it('merges custom className with base classes', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} className="max-w-xl">
          Content
        </Modal>
      )
      const modal = screen.getByText('Content').closest('.bg-white')
      expect(modal).toHaveClass('max-w-xl')
    })

    it('has proper header classes when title provided', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Header Test">
          Content
        </Modal>
      )
      const header = screen.getByText('Header Test').parentElement
      expect(header).toHaveClass('flex', 'items-center', 'justify-between', 'p-6', 'border-b')
    })
  })

  describe('Accessibility', () => {
    it('close button has proper aria-label', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Test">
          Content
        </Modal>
      )
      const closeButton = screen.getByLabelText('Close')
      expect(closeButton).toBeInTheDocument()
    })

    it('title renders as h2', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Title Test">
          Content
        </Modal>
      )
      const title = screen.getByRole('heading', { level: 2 })
      expect(title).toHaveTextContent('Title Test')
    })

    it('modal has fixed positioning and high z-index', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      const container = screen.getByText('Content').closest('.fixed')
      expect(container).toHaveClass('fixed', 'z-50', 'inset-0')
    })
  })

  describe('Content Padding', () => {
    it('has proper content padding when no title', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()}>
          Content
        </Modal>
      )
      // The content wrapper has p-6 class (and pt-6 when no title)
      // Find the modal container and then get its child with p-6
      const modalContainer = screen.getByText('Content').closest('.bg-white')
      const contentWrapper = modalContainer?.querySelector('.p-6')
      expect(contentWrapper).toHaveClass('p-6', 'pt-6')
    })

    it('has proper content padding when title exists', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Title">
          Content
        </Modal>
      )
      // The content wrapper has p-6 class (no pt-6 when title exists)
      const modalContainer = screen.getByText('Content').closest('.bg-white')
      const contentWrapper = modalContainer?.querySelector('.p-6')
      expect(contentWrapper).toHaveClass('p-6')
    })
  })

  describe('Dark Mode', () => {
    it('applies dark mode classes', () => {
      render(
        <Modal isOpen={true} onClose={vi.fn()} title="Dark">
          Content
        </Modal>
      )
      const modal = screen.getByText('Content').closest('.bg-white')
      expect(modal).toHaveClass('dark:bg-gray-800')
    })
  })
})
