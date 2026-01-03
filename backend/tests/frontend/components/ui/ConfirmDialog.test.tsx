/**
 * Tests for ConfirmDialog component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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
    it('renders title when open', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByText('Confirm Action')).toBeInTheDocument()
    })

    it('renders message when provided as string', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument()
    })

    it('renders message when provided as ReactNode', () => {
      const customMessage = <div>Custom Message Content</div>
      render(<ConfirmDialog {...defaultProps} message={customMessage} />)
      expect(screen.getByText('Custom Message Content')).toBeInTheDocument()
    })

    it('renders default button labels', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('button', { name: '确定' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument()
    })

    it('renders custom button labels when provided', () => {
      render(
        <ConfirmDialog
          {...defaultProps}
          confirmLabel="删除"
          cancelLabel="保留"
        />
      )
      expect(screen.getByRole('button', { name: '删除' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '保留' })).toBeInTheDocument()
    })
  })

  describe('Variant Styling', () => {
    it('shows warning icon when variant is danger', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const icon = screen.getByText('Confirm Action').parentElement?.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('text-red-500')
    })

    it('does not show warning icon when variant is default', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      const icon = screen.getByText('Confirm Action').parentElement?.querySelector('svg')
      expect(icon).not.toBeInTheDocument()
    })

    it('uses danger variant for confirm button when variant is danger', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const confirmButton = screen.getByRole('button', { name: '确定' })
      expect(confirmButton).toHaveClass('bg-red-600')
    })

    it('uses primary variant for confirm button when variant is default', () => {
      render(<ConfirmDialog {...defaultProps} variant="default" />)
      const confirmButton = screen.getByRole('button', { name: '确定' })
      expect(confirmButton).not.toHaveClass('bg-red-600')
    })
  })

  describe('Button Actions', () => {
    it('calls onConfirm and closes when confirm button is clicked', async () => {
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
      await userEvent.click(confirmButton)

      expect(handleConfirm).toHaveBeenCalledTimes(1)
      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('calls onClose when cancel button is clicked', async () => {
      const handleClose = vi.fn()
      render(<ConfirmDialog {...defaultProps} onClose={handleClose} />)

      const cancelButton = screen.getByRole('button', { name: '取消' })
      await userEvent.click(cancelButton)

      expect(handleClose).toHaveBeenCalledTimes(1)
      expect(defaultProps.onConfirm).not.toHaveBeenCalled()
    })
  })

  describe('Chinese Labels', () => {
    it('uses Chinese confirm label by default', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('button', { name: '确定' })).toBeInTheDocument()
    })

    it('uses Chinese cancel label by default', () => {
      render(<ConfirmDialog {...defaultProps} />)
      expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    it('renders message and icon in flex container', () => {
      render(<ConfirmDialog {...defaultProps} variant="danger" />)
      const messageContainer = screen.getByText('Are you sure you want to proceed?').parentElement
      expect(messageContainer).toHaveClass('flex', 'items-start', 'gap-3')
    })

    it('renders buttons with right alignment', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const buttonContainer = screen.getByRole('button', { name: '取消' }).parentElement
      expect(buttonContainer).toHaveClass('flex', 'justify-end', 'gap-3')
    })
  })

  describe('Dark Mode', () => {
    it('includes dark mode classes for message text', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const message = screen.getByText('Are you sure you want to proceed?')
      expect(message).toHaveClass('dark:text-gray-300')
    })
  })

  describe('Accessibility', () => {
    it('has proper heading for title', () => {
      render(<ConfirmDialog {...defaultProps} />)
      const title = screen.getByText('Confirm Action')
      expect(title.tagName).toBe('H2')
    })
  })
})
