import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '@/components/ui/Button'

describe('Button Component', () => {
  describe('Variant Rendering', () => {
    it('renders primary variant with correct classes', () => {
      render(<Button variant="primary">Primary</Button>)
      const button = screen.getByRole('button', { name: 'Primary' })
      expect(button).toHaveClass('bg-primary-600', 'text-white')
    })

    it('renders secondary variant with correct classes', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button', { name: 'Secondary' })
      expect(button).toHaveClass('bg-gray-200', 'text-gray-900')
    })

    it('renders ghost variant with correct classes', () => {
      render(<Button variant="ghost">Ghost</Button>)
      const button = screen.getByRole('button', { name: 'Ghost' })
      expect(button).toHaveClass('hover:bg-gray-100')
    })

    it('renders danger variant with correct classes', () => {
      render(<Button variant="danger">Danger</Button>)
      const button = screen.getByRole('button', { name: 'Danger' })
      expect(button).toHaveClass('bg-red-600', 'text-white')
    })

    it('defaults to primary variant when not specified', () => {
      render(<Button>Default</Button>)
      const button = screen.getByRole('button', { name: 'Default' })
      expect(button).toHaveClass('bg-primary-600')
    })
  })

  describe('Size Rendering', () => {
    it('renders sm size with correct classes', () => {
      render(<Button size="sm">Small</Button>)
      const button = screen.getByRole('button', { name: 'Small' })
      expect(button).toHaveClass('px-3', 'py-1.5', 'text-sm')
    })

    it('renders md size with correct classes', () => {
      render(<Button size="md">Medium</Button>)
      const button = screen.getByRole('button', { name: 'Medium' })
      expect(button).toHaveClass('px-4', 'py-2')
    })

    it('renders lg size with correct classes', () => {
      render(<Button size="lg">Large</Button>)
      const button = screen.getByRole('button', { name: 'Large' })
      expect(button).toHaveClass('px-6', 'py-3', 'text-lg')
    })

    it('renders icon size with correct classes', () => {
      render(<Button size="icon">Icon</Button>)
      const button = screen.getByRole('button', { name: 'Icon' })
      expect(button).toHaveClass('p-2')
    })

    it('defaults to md size when not specified', () => {
      render(<Button>Default Size</Button>)
      const button = screen.getByRole('button', { name: 'Default Size' })
      expect(button).toHaveClass('px-4', 'py-2')
    })
  })

  describe('Disabled State', () => {
    it('applies disabled styles when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>)
      const button = screen.getByRole('button', { name: 'Disabled' })
      expect(button).toHaveClass('disabled:opacity-50', 'disabled:pointer-events-none')
      expect(button).toBeDisabled()
    })

    it('does not apply disabled styles when enabled', () => {
      render(<Button>Enabled</Button>)
      const button = screen.getByRole('button', { name: 'Enabled' })
      expect(button).not.toBeDisabled()
    })
  })

  describe('Click Handlers', () => {
    it('calls onClick handler when clicked', () => {
      const handleClick = vi.fn()
      render(<Button onClick={handleClick}>Click Me</Button>)
      const button = screen.getByRole('button', { name: 'Click Me' })
      button.click()
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('does not call onClick when disabled', () => {
      const handleClick = vi.fn()
      render(<Button onClick={handleClick} disabled>Disabled</Button>)
      const button = screen.getByRole('button', { name: 'Disabled' })
      button.click()
      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('Custom Styling', () => {
    it('merges custom className with variant and size classes', () => {
      render(<Button className="ml-4" variant="primary">Custom</Button>)
      const button = screen.getByRole('button', { name: 'Custom' })
      expect(button).toHaveClass('ml-4')
      expect(button).toHaveClass('bg-primary-600')
    })

    it('applies dark mode classes', () => {
      render(<Button variant="secondary">Dark Mode</Button>)
      const button = screen.getByRole('button', { name: 'Dark Mode' })
      expect(button).toHaveClass('dark:bg-gray-700', 'dark:text-gray-100')
    })
  })

  describe('Accessibility and HTML', () => {
    it('renders as button element', () => {
      render(<Button>Button Element</Button>)
      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
    })

    it('forwards ref correctly', () => {
      const ref = { current: null }
      render(<Button ref={ref}>Ref Button</Button>)
      expect(ref.current).toBeInstanceOf(HTMLButtonElement)
    })

    it('passes through additional HTML attributes', () => {
      render(<Button data-testid="test-button" aria-label="Test Button">Attributes</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('data-testid', 'test-button')
      expect(button).toHaveAttribute('aria-label', 'Test Button')
    })

    it('renders children content correctly', () => {
      render(<Button>Child Content</Button>)
      expect(screen.getByText('Child Content')).toBeInTheDocument()
    })
  })

  describe('Base Classes', () => {
    it('has base layout and transition classes', () => {
      render(<Button>Base Classes</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'inline-flex',
        'items-center',
        'justify-center',
        'rounded-lg',
        'font-medium',
        'transition-colors',
        'focus:outline-none',
        'focus:ring-2',
        'focus:ring-offset-2'
      )
    })
  })

  describe('Hover States', () => {
    it('has hover classes for primary variant', () => {
      render(<Button variant="primary">Hover</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('hover:bg-primary-700')
    })

    it('has hover classes for secondary variant', () => {
      render(<Button variant="secondary">Hover</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('hover:bg-gray-300')
    })

    it('has hover classes for danger variant', () => {
      render(<Button variant="danger">Hover</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('hover:bg-red-700')
    })
  })
})
