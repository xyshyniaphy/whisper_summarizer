/**
 * Tests for Badge component
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
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

    it('uses info variant as default', () => {
      render(<Badge>Default</Badge>)
      const badge = screen.getByText('Default')
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-800')
    })
  })

  describe('Dark Mode Classes', () => {
    it('includes dark mode classes for success variant', () => {
      render(<Badge variant="success">Success</Badge>)
      const badge = screen.getByText('Success')
      expect(badge).toHaveClass('dark:bg-green-900', 'dark:text-green-200')
    })

    it('includes dark mode classes for error variant', () => {
      render(<Badge variant="error">Error</Badge>)
      const badge = screen.getByText('Error')
      expect(badge).toHaveClass('dark:bg-red-900', 'dark:text-red-200')
    })

    it('includes dark mode classes for info variant', () => {
      render(<Badge variant="info">Info</Badge>)
      const badge = screen.getByText('Info')
      expect(badge).toHaveClass('dark:bg-blue-900', 'dark:text-blue-200')
    })

    it('includes dark mode classes for warning variant', () => {
      render(<Badge variant="warning">Warning</Badge>)
      const badge = screen.getByText('Warning')
      expect(badge).toHaveClass('dark:bg-yellow-900', 'dark:text-yellow-200')
    })

    it('includes dark mode classes for gray variant', () => {
      render(<Badge variant="gray">Gray</Badge>)
      const badge = screen.getByText('Gray')
      expect(badge).toHaveClass('dark:bg-gray-700', 'dark:text-gray-200')
    })
  })

  describe('Custom className', () => {
    it('merges custom className with variant classes', () => {
      render(<Badge variant="success" className="custom-class">Badge</Badge>)
      const badge = screen.getByText('Badge')
      expect(badge).toHaveClass('bg-green-100', 'custom-class')
    })
  })

  describe('Base Classes', () => {
    it('includes base padding and text classes', () => {
      render(<Badge>Badge</Badge>)
      const badge = screen.getByText('Badge')
      expect(badge).toHaveClass('px-2', 'py-1', 'text-xs', 'font-medium', 'rounded-full')
    })
  })

  describe('HTML Attributes', () => {
    it('passes through data attributes', () => {
      render(<Badge data-testid="test-badge">Badge</Badge>)
      const badge = screen.getByTestId('test-badge')
      expect(badge).toBeInTheDocument()
    })

    it('passes through aria attributes', () => {
      render(<Badge aria-label="Test Badge">Badge</Badge>)
      const badge = screen.getByLabelText('Test Badge')
      expect(badge).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('renders as span element', () => {
      render(<Badge>Badge</Badge>)
      const badge = screen.getByText('Badge')
      expect(badge.tagName).toBe('SPAN')
    })
  })
})
