import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/Card'

describe('Card Components', () => {
  describe('Card Component', () => {
    it('renders with base classes', () => {
      render(<Card>Card Content</Card>)
      const card = screen.getByText('Card Content')
      expect(card).toHaveClass('bg-white', 'dark:bg-gray-800', 'rounded-lg', 'shadow-md')
    })

    it('merges custom className with base classes', () => {
      render(<Card className="p-4">Custom Card</Card>)
      const card = screen.getByText('Custom Card')
      expect(card).toHaveClass('p-4')
      expect(card).toHaveClass('bg-white')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      render(<Card ref={ref}>Ref Card</Card>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })

    it('passes through additional HTML attributes', () => {
      render(<Card data-testid="test-card">Attributes</Card>)
      const card = screen.getByText('Attributes')
      expect(card).toHaveAttribute('data-testid', 'test-card')
    })

    it('renders children correctly', () => {
      render(
        <Card>
          <span>Child Content</span>
        </Card>
      )
      expect(screen.getByText('Child Content')).toBeInTheDocument()
    })
  })

  describe('CardHeader Component', () => {
    it('renders with padding classes', () => {
      render(<CardHeader>Header Content</CardHeader>)
      const header = screen.getByText('Header Content')
      expect(header).toHaveClass('p-6')
    })

    it('merges custom className with base classes', () => {
      render(<CardHeader className="border-b">Custom Header</CardHeader>)
      const header = screen.getByText('Custom Header')
      expect(header).toHaveClass('border-b')
      expect(header).toHaveClass('p-6')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      render(<CardHeader ref={ref}>Ref Header</CardHeader>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('CardContent Component', () => {
    it('renders with padding classes and no top padding', () => {
      render(<CardContent>Content</CardContent>)
      const content = screen.getByText('Content')
      expect(content).toHaveClass('p-6', 'pt-0')
    })

    it('merges custom className with base classes', () => {
      render(<CardContent className="text-sm">Custom Content</CardContent>)
      const content = screen.getByText('Custom Content')
      expect(content).toHaveClass('text-sm')
      expect(content).toHaveClass('p-6')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      render(<CardContent ref={ref}>Ref Content</CardContent>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('CardTitle Component', () => {
    it('renders as h3 element with correct classes', () => {
      render(<CardTitle>Title</CardTitle>)
      const title = screen.getByText('Title')
      expect(title.tagName).toBe('H3')
      expect(title).toHaveClass('text-lg', 'font-semibold', 'leading-none', 'tracking-tight')
    })

    it('merges custom className with base classes', () => {
      render(<CardTitle className="text-blue-500">Custom Title</CardTitle>)
      const title = screen.getByText('Custom Title')
      expect(title).toHaveClass('text-blue-500')
      expect(title).toHaveClass('text-lg')
      expect(title).toHaveClass('font-semibold')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      render(<CardTitle ref={ref}>Ref Title</CardTitle>)
      expect(ref.current).toBeInstanceOf(HTMLHeadingElement)
    })
  })

  describe('Card Composition', () => {
    it('renders complete card with all components', () => {
      render(
        <Card data-testid="complete-card">
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Card content goes here</p>
          </CardContent>
        </Card>
      )

      expect(screen.getByText('Card Title')).toBeInTheDocument()
      expect(screen.getByText('Card content goes here')).toBeInTheDocument()
      expect(screen.getByTestId('complete-card')).toBeInTheDocument()
    })

    it('applies dark mode classes correctly', () => {
      render(<Card>Dark Mode Card</Card>)
      const card = screen.getByText('Dark Mode Card')
      expect(card).toHaveClass('dark:bg-gray-800')
    })

    it('renders multiple cards independently', () => {
      render(
        <>
          <Card data-testid="card-1">Card 1</Card>
          <Card data-testid="card-2">Card 2</Card>
        </>
      )

      expect(screen.getByTestId('card-1')).toHaveTextContent('Card 1')
      expect(screen.getByTestId('card-2')).toHaveTextContent('Card 2')
    })
  })
})
