import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { Accordion, AccordionItem } from '@/components/ui/Accordion'

describe('Accordion Component', () => {
  describe('Accordion Component', () => {
    it('renders with base classes', () => {
      render(
        <Accordion>
          <div>Child Content</div>
        </Accordion>
      )
      const accordion = screen.getByText('Child Content').parentElement
      expect(accordion).toHaveClass('space-y-2')
    })

    it('merges custom className with base classes', () => {
      render(
        <Accordion className="gap-4">
          <div>Custom Accordion</div>
        </Accordion>
      )
      const accordion = screen.getByText('Custom Accordion').parentElement
      expect(accordion).toHaveClass('gap-4')
      expect(accordion).toHaveClass('space-y-2')
    })

    it('renders multiple children correctly', () => {
      render(
        <Accordion>
          <div>Item 1</div>
          <div>Item 2</div>
          <div>Item 3</div>
        </Accordion>
      )
      expect(screen.getByText('Item 1')).toBeInTheDocument()
      expect(screen.getByText('Item 2')).toBeInTheDocument()
      expect(screen.getByText('Item 3')).toBeInTheDocument()
    })
  })

  describe('AccordionItem Component', () => {
    it('renders title correctly', () => {
      render(<AccordionItem title="Test Title">Content</AccordionItem>)
      expect(screen.getByText('Test Title')).toBeInTheDocument()
    })

    it('renders children when open', () => {
      render(<AccordionItem title="Title" defaultOpen={true}>Content</AccordionItem>)
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('does not render children when closed', () => {
      render(<AccordionItem title="Title" defaultOpen={false}>Hidden Content</AccordionItem>)
      expect(screen.queryByText('Hidden Content')).not.toBeInTheDocument()
    })

    it('opens when defaultOpen is true', () => {
      render(<AccordionItem title="Title" defaultOpen={true}>Default Open</AccordionItem>)
      expect(screen.getByText('Default Open')).toBeVisible()
    })

    it('stays closed when defaultOpen is false', () => {
      render(<AccordionItem title="Title" defaultOpen={false}>Default Closed</AccordionItem>)
      expect(screen.queryByText('Default Closed')).not.toBeInTheDocument()
    })

    it('has proper border and rounded classes', () => {
      render(<AccordionItem title="Border Test">Content</AccordionItem>)
      const item = screen.getByText('Border Test').closest('.border')
      expect(item).toHaveClass('border', 'rounded-lg', 'overflow-hidden')
    })

    it('applies dark mode classes', () => {
      render(<AccordionItem title="Dark Mode">Content</AccordionItem>)
      const item = screen.getByText('Dark Mode').closest('.border')
      expect(item).toHaveClass('dark:border-gray-700')
    })
  })

  describe('AccordionItem Interaction', () => {
    it('toggles open when clicked', async () => {
      const user = userEvent.setup()
      render(<AccordionItem title="Click to Open">Toggle Content</AccordionItem>)

      // Initially closed
      expect(screen.queryByText('Toggle Content')).not.toBeInTheDocument()

      // Click to open
      const button = screen.getByRole('button', { name: /Click to Open/ })
      await user.click(button)

      // Now open
      expect(screen.getByText('Toggle Content')).toBeInTheDocument()
    })

    it('toggles closed when clicked while open', async () => {
      const user = userEvent.setup()
      render(<AccordionItem title="Click to Close" defaultOpen={true}>Toggle Content</AccordionItem>)

      // Initially open
      expect(screen.getByText('Toggle Content')).toBeInTheDocument()

      // Click to close
      const button = screen.getByRole('button', { name: /Click to Close/ })
      await user.click(button)

      // Now closed
      expect(screen.queryByText('Toggle Content')).not.toBeInTheDocument()
    })

    it('rotates chevron icon when open', async () => {
      const user = userEvent.setup()
      render(<AccordionItem title="Chevron Test">Content</AccordionItem>)

      const button = screen.getByRole('button', { name: /Chevron Test/ })
      const chevron = button.querySelector('svg')

      // Initially not rotated
      expect(chevron).not.toHaveClass('rotate-180')

      // Click to open
      await user.click(button)

      // Should be rotated now
      expect(chevron).toHaveClass('rotate-180')
    })

    it('has hover state on button', () => {
      render(<AccordionItem title="Hover Test">Content</AccordionItem>)
      const button = screen.getByRole('button', { name: /Hover Test/ })
      expect(button).toHaveClass('hover:bg-gray-100', 'dark:hover:bg-gray-700')
    })
  })

  describe('Multiple Accordion Items', () => {
    it('renders multiple accordion items independently', async () => {
      const user = userEvent.setup()
      render(
        <Accordion>
          <AccordionItem title="Item 1">Content 1</AccordionItem>
          <AccordionItem title="Item 2">Content 2</AccordionItem>
          <AccordionItem title="Item 3">Content 3</AccordionItem>
        </Accordion>
      )

      // Initially all closed
      expect(screen.queryByText('Content 1')).not.toBeInTheDocument()
      expect(screen.queryByText('Content 2')).not.toBeInTheDocument()
      expect(screen.queryByText('Content 3')).not.toBeInTheDocument()

      // Open first item
      await user.click(screen.getByRole('button', { name: /Item 1/ }))
      expect(screen.getByText('Content 1')).toBeInTheDocument()
      expect(screen.queryByText('Content 2')).not.toBeInTheDocument()

      // Open second item
      await user.click(screen.getByRole('button', { name: /Item 2/ }))
      expect(screen.getByText('Content 1')).toBeInTheDocument()
      expect(screen.getByText('Content 2')).toBeInTheDocument()
    })

    it('allows multiple items to be open simultaneously', async () => {
      const user = userEvent.setup()
      render(
        <Accordion>
          <AccordionItem title="Item 1">Content 1</AccordionItem>
          <AccordionItem title="Item 2">Content 2</AccordionItem>
        </Accordion>
      )

      // Open both
      await user.click(screen.getByRole('button', { name: /Item 1/ }))
      await user.click(screen.getByRole('button', { name: /Item 2/ }))

      expect(screen.getByText('Content 1')).toBeInTheDocument()
      expect(screen.getByText('Content 2')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('renders button with proper role', () => {
      render(<AccordionItem title="A11y Test">Content</AccordionItem>)
      const button = screen.getByRole('button')
      expect(button).toBeInTheDocument()
    })

    it('has focusable button', () => {
      render(<AccordionItem title="Focus Test">Content</AccordionItem>)
      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
    })

    it('button has proper styling classes', () => {
      render(<AccordionItem title="Style Test">Content</AccordionItem>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass(
        'w-full',
        'flex',
        'items-center',
        'justify-between',
        'p-4',
        'transition-colors'
      )
    })

    it('applies custom className to AccordionItem', () => {
      render(
        <AccordionItem title="Custom Class" className="border-red-500">
          Content
        </AccordionItem>
      )
      const item = screen.getByText('Custom Class').closest('.border')
      expect(item).toHaveClass('border-red-500')
    })
  })

  describe('Content Area', () => {
    it('has proper padding when open', () => {
      render(<AccordionItem title="Padding Test" defaultOpen={true}>Padded Content</AccordionItem>)
      // Content is wrapped in a div with p-4 class
      const content = screen.getByText('Padded Content').parentElement
      expect(content).toHaveClass('bg-white', 'dark:bg-gray-900', 'p-4')
    })

    it('has correct background colors', () => {
      render(<AccordionItem title="Bg Test" defaultOpen={true}>Content</AccordionItem>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-gray-50', 'dark:bg-gray-800')
    })
  })
})
