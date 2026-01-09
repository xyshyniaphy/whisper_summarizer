/**
 * Tests for Button component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

    it('uses primary variant as default', () => {
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

    it('uses md size as default', () => {
      render(<Button>Default</Button>)
      const button = screen.getByRole('button', { name: 'Default' })
      expect(button).toHaveClass('px-4', 'py-2')
    })
  })

  describe('Dark Mode', () => {
    it('includes dark mode classes for secondary variant', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button', { name: 'Secondary' })
      expect(button).toHaveClass('dark:bg-gray-700', 'dark:text-gray-100')
    })

    it('includes dark mode hover for ghost variant', () => {
      render(<Button variant="ghost">Ghost</Button>)
      const button = screen.getByRole('button', { name: 'Ghost' })
      expect(button).toHaveClass('dark:hover:bg-gray-800')
    })
  })

  describe('Disabled State', () => {
    it('applies disabled styles when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>)
      const button = screen.getByRole('button', { name: 'Disabled' })
      expect(button).toHaveClass('disabled:opacity-50', 'disabled:pointer-events-none')
    })

    it('prevents click when disabled', async () => {
      const handleClick = vi.fn()
      render(<Button disabled onClick={handleClick}>Click Me</Button>)
      const button = screen.getByRole('button', { name: 'Click Me' })
      await userEvent.click(button)
      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('Click Handler', () => {
    it('calls onClick handler when clicked', async () => {
      const handleClick = vi.fn()
      render(<Button onClick={handleClick}>Click Me</Button>)
      const button = screen.getByRole('button', { name: 'Click Me' })
      await userEvent.click(button)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Custom className', () => {
    it('merges custom className with variant classes', () => {
      render(<Button className="custom-class">Button</Button>)
      const button = screen.getByRole('button', { name: 'Button' })
      expect(button).toHaveClass('custom-class')
    })
  })

  describe('Base Classes', () => {
    it('includes base button classes', () => {
      render(<Button>Button</Button>)
      const button = screen.getByRole('button', { name: 'Button' })
      expect(button).toHaveClass('inline-flex', 'items-center', 'justify-center', 'rounded-lg', 'font-medium')
    })

    it('includes transition and focus classes', () => {
      render(<Button>Button</Button>)
      const button = screen.getByRole('button', { name: 'Button' })
      expect(button).toHaveClass('transition-colors', 'focus:outline-none', 'focus:ring-2', 'focus:ring-offset-2')
    })
  })

  describe('Accessibility', () => {
    it('renders as button element', () => {
      render(<Button>Button</Button>)
      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
    })
  })
})
