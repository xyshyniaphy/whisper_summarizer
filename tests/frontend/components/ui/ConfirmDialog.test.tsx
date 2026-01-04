import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

describe('ConfirmDialog Component', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?'
  }

  describe('Rendering', () => {
    it('renders when isOpen is true', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByText('Confirm Action')).toBeInTheDocument()
      expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      const { container } = render(<ConfirmDialog {...defaultProps} isOpen={false} />)
      expect(container.firstChild).toBe(null)
    })

    it('renders title correctly', () => {
      render(<ConfirmDialog {...defaultProps} title="Delete Item" />)
      expect(screen.getByText('Delete Item')).toBeInTheDocument()
    })

    it('renders string message correctly', () => {
      render(<ConfirmDialog {...defaultProps} message="Delete this file?" />)
      expect(screen.getByText('Delete this file?')).toBeInTheDocument()
    })

    it('renders custom button labels', () => {
      render(
        <ConfirmDialog
          {...defaultProps}
          confirmLabel="Yes, delete it"
          cancelLabel="No, keep it"
        />
      )
      expect(screen.getByRole('button', { name: 'Yes, delete it' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'No, keep it' })).toBeInTheDocument()
    })

    it('defaults to Chinese button labels', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('button', { name: '确定' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument()
    })
  })

  describe('Danger Variant', () => {
    it('shows warning icon when variant is danger', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      // The AlertTriangle icon is a sibling to the message, in a div with text-red-500 class
      const warningIcon = document.querySelector('.text-red-500')
      expect(warningIcon).toBeInTheDocument()
    })

    it('uses danger button variant when variant is danger', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const confirmButton = screen.getByRole('button', { name: '确定' })
      expect(confirmButton).toHaveClass('bg-red-600')
    })

    it('does not show warning icon when variant is default', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      // When variant is default, there should be no AlertTriangle with text-red-500
      const warningIcon = document.querySelector('.text-red-500')
      expect(warningIcon).not.toBeInTheDocument()
    })

    it('uses primary button variant when variant is default', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      const confirmButton = screen.getByRole('button', { name: '确定' })
      // The button uses bg-primary-600 class
      expect(confirmButton).toHaveClass('bg-primary-600')
    })
  })

  describe('Button Actions', () => {
    it('calls onConfirm and closes when confirm button is clicked', async () => {
      const user = userEvent.setup()
      const handleConfirm = vi.fn()
      const handleClose = vi.fn()

      render(
        <ConfirmDialog
          {...defaultProps}
          onConfirm={handleConfirm}
          onClose={handleClose}
        />
      )

      const confirmButton = screen.getByRole('button', { name: '确定' })
      await user.click(confirmButton)

      expect(handleConfirm).toHaveBeenCalledTimes(1)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when cancel button is clicked', async () => {
      const user = userEvent.setup()
      const handleClose = vi.fn()

      render(<ConfirmDialog {...defaultProps} onClose={handleClose} />)

      const cancelButton = screen.getByRole('button', { name: '取消' })
      await user.click(cancelButton)

      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('does not call onConfirm when cancel is clicked', async () => {
      const user = userEvent.setup()
      const handleConfirm = vi.fn()
      const handleClose = vi.fn()

      render(
        <ConfirmDialog
          {...defaultProps}
          onConfirm={handleConfirm}
          onClose={handleClose}
        />
      )

      const cancelButton = screen.getByRole('button', { name: '取消' })
      await user.click(cancelButton)

      expect(handleConfirm).not.toHaveBeenCalled()
      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Message Types', () => {
    it('renders string message as paragraph', () => {
      render(<ConfirmDialog {...defaultProps} message="String message" />)
      const message = screen.getByText('String message')
      expect(message.tagName).toBe('P')
    })

    it('renders React node message', () => {
      render(
        <ConfirmDialog
          {...defaultProps}
          message={
            <div>
              <span>Custom message</span>
              <strong> with formatting</strong>
            </div>
          }
        />
      )
      expect(screen.getByText('Custom message')).toBeInTheDocument()
      expect(screen.getByText('with formatting')).toBeInTheDocument()
    })
  })

  describe('Layout and Styling', () => {
    it('has proper button layout', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const buttons = screen.getAllByRole('button')
      expect(buttons).toHaveLength(3) // Close, Cancel, Confirm
    })

    it('has proper spacing for action buttons', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const container = screen.getByRole('button', { name: '取消' }).parentElement
      expect(container).toHaveClass('flex', 'justify-end', 'gap-3')
    })

    it('has border top on action section', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const container = screen.getByRole('button', { name: '取消' }).parentElement
      expect(container).toHaveClass('border-t', 'dark:border-gray-700')
    })
  })

  describe('Dark Mode', () => {
    it('applies dark mode classes to message', () => {
      render(<ConfirmDialog {...defaultProps} message="Dark mode test" />)
      const message = screen.getByText('Dark mode test')
      expect(message).toHaveClass('dark:text-gray-300')
    })
  })

  describe('Integration with Modal', () => {
    it('closes modal when confirm is clicked', async () => {
      const user = userEvent.setup()
      const handleClose = vi.fn()

      render(<ConfirmDialog {...defaultProps} onClose={handleClose} />)

      const confirmButton = screen.getByRole('button', { name: '确定' })
      await user.click(confirmButton)

      expect(handleClose).toHaveBeenCalled()
    })

    it('closes modal when cancel is clicked', async () => {
      const user = userEvent.setup()
      const handleClose = vi.fn()

      render(<ConfirmDialog {...defaultProps} onClose={handleClose} />)

      const cancelButton = screen.getByRole('button', { name: '取消' })
      await user.click(cancelButton)

      expect(handleClose).toHaveBeenCalled()
    })

    it('closes modal when close button (X) is clicked', async () => {
      const user = userEvent.setup()
      const handleClose = vi.fn()

      render(<ConfirmDialog {...defaultProps} onClose={handleClose} />)

      const closeButton = screen.getByLabelText('Close')
      await user.click(closeButton)

      expect(handleClose).toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('has proper heading for title', () => {
      render(<ConfirmDialog {...defaultProps} title="Accessibility Test" />)
      const heading = screen.getByRole('heading', { level: 2 })
      expect(heading).toHaveTextContent('Accessibility Test')
    })

    it('has proper button roles', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('button', { name: '确定' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument()
    })

    it('close button has aria-label', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByLabelText('Close')).toBeInTheDocument()
    })
  })

  describe('Warning Icon Display', () => {
    it('displays AlertTriangle icon in danger variant', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      // The AlertTriangle icon has class text-red-500
      const icon = screen.getByText('Are you sure you want to proceed?')
        .parentElement?.parentElement?.querySelector('.text-red-500')
      expect(icon).toBeInTheDocument()
    })

    it('does not display icon in default variant', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      const icons = screen.getByText('Are you sure you want to proceed?')
        .parentElement?.parentElement?.querySelectorAll('.text-red-500')
      expect(icons?.length ?? 0).toBe(0)
    })
  })
})
