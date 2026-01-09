/**
 * Tests for ChannelBadge component
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChannelBadge } from '@/components/channel/ChannelBadge'

describe('ChannelBadge Component', () => {
  const mockChannels = [
    { id: '1', name: 'Channel 1', description: 'First channel' },
    { id: '2', name: 'Channel 2', description: 'Second channel' },
    { id: '3', name: 'Channel 3', description: 'Third channel' }
  ]

  describe('Personal Content (No Channels)', () => {
    it('renders "个人" badge when isPersonal is true', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} />)
      expect(screen.getByText('个人')).toBeInTheDocument()
    })

    it('renders "个人" badge when channels array is empty', () => {
      render(<ChannelBadge channels={[]} isPersonal={false} />)
      expect(screen.getByText('个人')).toBeInTheDocument()
    })

    it('applies correct styles for personal badge', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} />)
      const badge = screen.getByText('个人')
      expect(badge).toHaveClass('bg-gray-100', 'dark:bg-gray-800', 'text-gray-600', 'dark:text-gray-400')
    })

    it('merges custom className for personal badge', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} className="custom-class" />)
      const badge = screen.getByText('个人')
      expect(badge).toHaveClass('custom-class')
    })
  })

  describe('Single Channel', () => {
    it('renders channel name for single channel', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />)
      expect(screen.getByText('Channel 1')).toBeInTheDocument()
    })

    it('renders as button for single channel', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />)
      const badge = screen.getByText('Channel 1')
      expect(badge.tagName).toBe('BUTTON')
    })

    it('calls onClick when single channel badge is clicked', async () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={[mockChannels[0]]} onClick={handleClick} />)
      
      const badge = screen.getByText('Channel 1')
      await userEvent.click(badge)
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('has title attribute with channel description', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />)
      const badge = screen.getByText('Channel 1')
      expect(badge).toHaveAttribute('title', 'First channel')
    })

    it('uses channel name as title when description is missing', () => {
      const channelWithoutDesc = { id: '1', name: 'Channel' }
      render(<ChannelBadge channels={[channelWithoutDesc]} />)
      const badge = screen.getByText('Channel')
      expect(badge).toHaveAttribute('title', 'Channel')
    })

    it('applies correct styles for single channel', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />)
      const badge = screen.getByText('Channel 1')
      expect(badge).toHaveClass('bg-blue-100', 'dark:bg-blue-900/30', 'text-blue-700', 'dark:text-blue-300')
    })
  })

  describe('Multiple Channels', () => {
    it('renders all channel names when within maxDisplay', () => {
      render(<ChannelBadge channels={mockChannels.slice(0, 2)} maxDisplay={2} />)
      expect(screen.getByText('Channel 1')).toBeInTheDocument()
      expect(screen.getByText('Channel 2')).toBeInTheDocument()
    })

    it('renders each channel as separate button', () => {
      render(<ChannelBadge channels={mockChannels.slice(0, 2)} maxDisplay={2} />)
      
      const buttons = screen.getAllByRole('button')
      expect(buttons).toHaveLength(2)
      expect(buttons[0]).toHaveTextContent('Channel 1')
      expect(buttons[1]).toHaveTextContent('Channel 2')
    })

    it('calls onClick for each channel button', async () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={mockChannels.slice(0, 2)} onClick={handleClick} maxDisplay={2} />)
      
      const buttons = screen.getAllByRole('button')
      
      await userEvent.click(buttons[0])
      await userEvent.click(buttons[1])
      
      expect(handleClick).toHaveBeenCalledTimes(2)
    })
  })

  describe('Too Many Channels', () => {
    it('renders count badge when channels exceed maxDisplay', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />)
      expect(screen.getByText('3 个频道')).toBeInTheDocument()
    })

    it('renders as button for count badge', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />)
      const badge = screen.getByText('3 个频道')
      expect(badge.tagName).toBe('BUTTON')
    })

    it('calls onClick when count badge is clicked', async () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} onClick={handleClick} />)
      
      const badge = screen.getByText('3 个频道')
      await userEvent.click(badge)
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('has title attribute with all channel names', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />)
      const badge = screen.getByText('3 个频道')
      expect(badge).toHaveAttribute('title', 'Channel 1, Channel 2, Channel 3')
    })

    it('applies correct styles for count badge', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />)
      const badge = screen.getByText('3 个频道')
      expect(badge).toHaveClass('bg-purple-100', 'dark:bg-purple-900/30', 'text-purple-700', 'dark:text-purple-300')
    })
  })

  describe('maxDisplay Prop', () => {
    it('respects custom maxDisplay value', () => {
      // With maxDisplay=1, should show count for 2 channels
      render(<ChannelBadge channels={mockChannels.slice(0, 2)} maxDisplay={1} />)
      expect(screen.getByText('2 个频道')).toBeInTheDocument()
    })

    it('uses default maxDisplay of 2', () => {
      // Default maxDisplay=2, 3 channels should show count
      render(<ChannelBadge channels={mockChannels} />)
      expect(screen.getByText('3 个频道')).toBeInTheDocument()
    })
  })

  describe('Custom className', () => {
    it('merges custom className for single channel', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} className="custom-class" />)
      const badge = screen.getByText('Channel 1')
      expect(badge).toHaveClass('custom-class')
    })

    it('merges custom className for personal badge', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} className="custom-class" />)
      const badge = screen.getByText('个人')
      expect(badge).toHaveClass('custom-class')
    })

    it('merges custom className for count badge', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} className="custom-class" />)
      const badge = screen.getByText('3 个频道')
      expect(badge).toHaveClass('custom-class')
    })
  })

  describe('Dark Mode', () => {
    it('includes dark mode classes for personal badge', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} />)
      const badge = screen.getByText('个人')
      expect(badge).toHaveClass('dark:bg-gray-800', 'dark:text-gray-400')
    })

    it('includes dark mode classes for channel badges', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />)
      const badge = screen.getByText('Channel 1')
      expect(badge).toHaveClass('dark:bg-blue-900/30', 'dark:text-blue-300')
    })

    it('includes dark mode classes for count badge', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />)
      const badge = screen.getByText('3 个频道')
      expect(badge).toHaveClass('dark:bg-purple-900/30', 'dark:text-purple-300')
    })
  })

  describe('Hover States', () => {
    it('includes hover classes for channel badges', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />)
      const badge = screen.getByText('Channel 1')
      expect(badge).toHaveClass('hover:bg-blue-200', 'dark:hover:bg-blue-900/50')
    })

    it('includes hover classes for count badge', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />)
      const badge = screen.getByText('3 个频道')
      expect(badge).toHaveClass('hover:bg-purple-200', 'dark:hover:bg-purple-900/50')
    })
  })
})
