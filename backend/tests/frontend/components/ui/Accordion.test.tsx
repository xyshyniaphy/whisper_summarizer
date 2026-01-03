/**
 * Tests for Accordion components
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Accordion, AccordionItem } from '@/components/ui/Accordion'

describe('Accordion Component', () => {
  describe('AccordionItem', () => {
    it('renders title in header button', () => {
      render(<AccordionItem title="Test Title">Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Test Title' })
      expect(header).toBeInTheDocument()
    })

    it('does not show content by default', () => {
      render(<AccordionItem title="Title">Hidden Content</AccordionItem>)
      expect(screen.queryByText('Hidden Content')).not.toBeInTheDocument()
    })

    it('shows content when defaultOpen is true', () => {
      render(<AccordionItem title="Title" defaultOpen>Visible Content</AccordionItem>)
      expect(screen.getByText('Visible Content')).toBeInTheDocument()
    })

    it('toggles content visibility when header is clicked', async () => {
      render(<AccordionItem title="Title">Toggle Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Title' })

      // Initially hidden
      expect(screen.queryByText('Toggle Content')).not.toBeInTheDocument()

      // Click to open
      await userEvent.click(header)
      expect(screen.getByText('Toggle Content')).toBeInTheDocument()

      // Click to close
      await userEvent.click(header)
      expect(screen.queryByText('Toggle Content')).not.toBeInTheDocument()
    })

    it('rotates chevron when opened', async () => {
      render(<AccordionItem title="Title">Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Title' })

      // Initial state - no rotation
      const chevron = header.querySelector('svg')
      expect(chevron).not.toHaveClass('rotate-180')

      // Click to open
      await userEvent.click(header)
      expect(chevron).toHaveClass('rotate-180')
    })
  })

  describe('Accordion', () => {
    it('renders children with spacing', () => {
      render(
        <Accordion>
          <AccordionItem title="Item 1">Content 1</AccordionItem>
          <AccordionItem title="Item 2">Content 2</AccordionItem>
        </Accordion>
      )
      const accordion = screen.getByRole('button', { name: 'Item 1' }).parentElement
      expect(accordion).toHaveClass('space-y-2')
    })

    it('merges custom className', () => {
      render(
        <Accordion className="custom-class">
          <AccordionItem title="Title">Content</AccordionItem>
        </Accordion>
      )
      const accordion = screen.getByRole('button', { name: 'Title' }).parentElement
      expect(accordion).toHaveClass('custom-class')
    })
  })

  describe('Multiple Items', () => {
    it('renders multiple accordion items', () => {
      render(
        <Accordion>
          <AccordionItem title="First Item">First Content</AccordionItem>
          <AccordionItem title="Second Item">Second Content</AccordionItem>
          <AccordionItem title="Third Item">Third Content</AccordionItem>
        </Accordion>
      )

      expect(screen.getByRole('button', { name: 'First Item' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Second Item' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Third Item' })).toBeInTheDocument()
    })

    it('allows multiple items to be open simultaneously', async () => {
      render(
        <Accordion>
          <AccordionItem title="First">First Content</AccordionItem>
          <AccordionItem title="Second">Second Content</AccordionItem>
        </Accordion>
      )

      const firstHeader = screen.getByRole('button', { name: 'First' })
      const secondHeader = screen.getByRole('button', { name: 'Second' })

      await userEvent.click(firstHeader)
      await userEvent.click(secondHeader)

      expect(screen.getByText('First Content')).toBeInTheDocument()
      expect(screen.getByText('Second Content')).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies border classes', () => {
      render(<AccordionItem title="Title">Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Title' })
      expect(header.parentElement).toHaveClass('border', 'dark:border-gray-700', 'rounded-lg', 'overflow-hidden')
    })

    it('applies header background classes', () => {
      render(<AccordionItem title="Title">Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Title' })
      expect(header).toHaveClass('bg-gray-50', 'dark:bg-gray-800')
    })

    it('applies header hover classes', () => {
      render(<AccordionItem title="Title">Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Title' })
      expect(header).toHaveClass('hover:bg-gray-100', 'dark:hover:bg-gray-700')
    })

    it('applies content container classes', () => {
      render(<AccordionItem title="Title" defaultOpen>Content</AccordionItem>)
      const content = screen.getByText('Content')
      expect(content.parentElement).toHaveClass('p-4', 'bg-white', 'dark:bg-gray-900')
    })
  })

  describe('Dark Mode', () => {
    it('includes dark mode classes', () => {
      render(<AccordionItem title="Title">Content</AccordionItem>)
      const header = screen.getByRole('button', { name: 'Title' })
      expect(header).toHaveClass('dark:bg-gray-800')
    })
  })
})
