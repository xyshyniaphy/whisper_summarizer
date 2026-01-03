/**
 * Tests for Card components
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card'

describe('Card Component', () => {
  describe('Card', () => {
    it('renders with base classes', () => {
      render(<Card>Card Content</Card>)
      const card = screen.getByText('Card Content')
      expect(card).toHaveClass('bg-white', 'dark:bg-gray-800', 'rounded-lg', 'shadow-md')
    })

    it('merges custom className', () => {
      render(<Card className="custom-class">Content</Card>)
      const card = screen.getByText('Content')
      expect(card).toHaveClass('custom-class')
    })

    it('passes through HTML attributes', () => {
      render(<Card data-testid="test-card">Content</Card>)
      const card = screen.getByTestId('test-card')
      expect(card).toBeInTheDocument()
    })
  })

  describe('CardHeader', () => {
    it('renders with base padding classes', () => {
      render(
        <Card>
          <CardHeader>Header</CardHeader>
        </Card>
      )
      const header = screen.getByText('Header')
      expect(header).toHaveClass('p-6')
    })

    it('merges custom className', () => {
      render(
        <Card>
          <CardHeader className="custom-class">Header</CardHeader>
        </Card>
      )
      const header = screen.getByText('Header')
      expect(header).toHaveClass('custom-class')
    })
  })

  describe('CardContent', () => {
    it('renders with base padding classes', () => {
      render(
        <Card>
          <CardContent>Content</CardContent>
        </Card>
      )
      const content = screen.getByText('Content')
      expect(content).toHaveClass('p-6', 'pt-0')
    })

    it('merges custom className', () => {
      render(
        <Card>
          <CardContent className="custom-class">Content</CardContent>
        </Card>
      )
      const content = screen.getByText('Content')
      expect(content).toHaveClass('custom-class')
    })
  })

  describe('CardTitle', () => {
    it('renders as h3 element', () => {
      render(
        <Card>
          <CardTitle>Title</CardTitle>
        </Card>
      )
      const title = screen.getByText('Title')
      expect(title.tagName).toBe('H3')
    })

    it('renders with base text classes', () => {
      render(
        <Card>
          <CardTitle>Title</CardTitle>
        </Card>
      )
      const title = screen.getByText('Title')
      expect(title).toHaveClass('text-lg', 'font-semibold', 'leading-none', 'tracking-tight')
    })

    it('merges custom className', () => {
      render(
        <Card>
          <CardTitle className="custom-class">Title</CardTitle>
        </Card>
      )
      const title = screen.getByText('Title')
      expect(title).toHaveClass('custom-class')
    })
  })

  describe('Composition', () => {
    it('renders complete card with all components', () => {
      render(
        <Card data-testid="test-card">
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
          </CardHeader>
          <CardContent>Card Content</CardContent>
        </Card>
      )

      expect(screen.getByText('Card Title')).toBeInTheDocument()
      expect(screen.getByText('Card Content')).toBeInTheDocument()
      expect(screen.getByTestId('test-card')).toBeInTheDocument()
    })
  })

  describe('Dark Mode', () => {
    it('includes dark mode classes', () => {
      render(<Card>Content</Card>)
      const card = screen.getByText('Content')
      expect(card).toHaveClass('dark:bg-gray-800')
    })
  })
})
