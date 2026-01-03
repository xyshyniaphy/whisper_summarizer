import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Badge } from '@/components/ui/Badge'

describe('Badge Component', () => {
  describe('Variant Rendering', () => {
    it('renders success variant with correct classes', () => {
      render(<Badge variant="success">Success</Badge>)
      const badge = screen.getByText('Success')
      expect(badge).toHaveClass('bg-green-100', 'text-green-800')
    })

    it('renders error variant with correct classes', () => {
      render(<Badge variant="error">Error</Badge>)
      const badge = screen.getByText('Error')
      expect(badge).toHaveClass('bg-red-100', 'text-red-800')
    })

    it('renders info variant with correct classes', () => {
      render(<Badge variant="info">Info</Badge>)
      const badge = screen.getByText('Info')
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-800')
    })

    it('renders warning variant with correct classes', () => {
      render(<Badge variant="warning">Warning</Badge>)
      const badge = screen.getByText('Warning')
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800')
    })

    it('renders gray variant with correct classes', () => {
      render(<Badge variant="gray">Gray</Badge>)
      const badge = screen.getByText('Gray')
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-800')
    })

    it('defaults to info variant when not specified', () => {
      render(<Badge>Default</Badge>)
      const badge = screen.getByText('Default')
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-800')
    })
  })

  describe('Custom Styling', () => {
    it('merges custom className with variant classes', () => {
      render(<Badge variant="success" className="ml-2">Custom</Badge>)
      const badge = screen.getByText('Custom')
      expect(badge).toHaveClass('ml-2')
      expect(badge).toHaveClass('bg-green-100')
    })

    it('applies dark mode classes', () => {
      render(<Badge variant="success">Dark Mode</Badge>)
      const badge = screen.getByText('Dark Mode')
      expect(badge).toHaveClass('dark:bg-green-900', 'dark:text-green-200')
    })
  })

  describe('Accessibility and HTML', () => {
    it('renders as span element', () => {
      render(<Badge>Span</Badge>)
      const badge = screen.getByText('Span')
      expect(badge.tagName).toBe('SPAN')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      render(<Badge ref={ref}>Ref Badge</Badge>)
      expect(ref.current).toBeInstanceOf(HTMLSpanElement)
    })

    it('passes through additional HTML attributes', () => {
      render(<Badge data-testid="test-badge" aria-label="Test">Attributes</Badge>)
      const badge = screen.getByText('Attributes')
      expect(badge).toHaveAttribute('data-testid', 'test-badge')
      expect(badge).toHaveAttribute('aria-label', 'Test')
    })

    it('renders children content correctly', () => {
      render(<Badge>Child Content</Badge>)
      expect(screen.getByText('Child Content')).toBeInTheDocument()
    })
  })

  describe('Base Classes', () => {
    it('has base padding and font classes', () => {
      render(<Badge>Base</Badge>)
      const badge = screen.getByText('Base')
      expect(badge).toHaveClass('px-2', 'py-1', 'text-xs', 'font-medium', 'rounded-full')
    })
  })
})
