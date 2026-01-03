import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { ChannelBadge } from '@/components/channel/ChannelBadge'

describe('ChannelBadge Component', () => {
  const mockChannel = {
    id: '1',
    name: 'Test Channel',
    description: 'Test Description'
  }

  describe('Personal Content Display', () => {
    it('shows "个人" badge when isPersonal is true', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} />)
      expect(screen.getByText('个人')).toBeInTheDocument()
    })

    it('shows "个人" badge when channels array is empty', () => {
      render(<ChannelBadge channels={[]} isPersonal={false} />)
      expect(screen.getByText('个人')).toBeInTheDocument()
    })

    it('has proper styling for personal badge', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} />)
      const badge = screen.getByText('个人')
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-600', 'dark:bg-gray-800')
    })

    it('is not clickable when personal', () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={[]} isPersonal={true} onClick={handleClick} />)
      const badge = screen.getByText('个人')
      expect(badge.tagName).toBe('SPAN')
    })
  })

  describe('Single Channel Display', () => {
    it('displays single channel name', () => {
      render(<ChannelBadge channels={[mockChannel]} />)
      expect(screen.getByText('Test Channel')).toBeInTheDocument()
    })

    it('renders as button when onClick provided', () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={[mockChannel]} onClick={handleClick} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toBeInTheDocument()
    })

    it('calls onClick when clicked', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      render(<ChannelBadge channels={[mockChannel]} onClick={handleClick} />)

      const button = screen.getByRole('button', { name: 'Test Channel' })
      await user.click(button)

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('has proper styling for single channel', () => {
      render(<ChannelBadge channels={[mockChannel]} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toHaveClass(
        'bg-blue-100',
        'text-blue-700',
        'dark:bg-blue-900/30',
        'dark:text-blue-300'
      )
    })

    it('has hover state', () => {
      render(<ChannelBadge channels={[mockChannel]} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toHaveClass('hover:bg-blue-200', 'dark:hover:bg-blue-900/50')
    })

    it('shows description as title attribute', () => {
      render(<ChannelBadge channels={[mockChannel]} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toHaveAttribute('title', 'Test Description')
    })

    it('uses channel name as title when no description', () => {
      const channelNoDesc = { id: '1', name: 'No Desc' }
      render(<ChannelBadge channels={[channelNoDesc]} />)
      const button = screen.getByRole('button', { name: 'No Desc' })
      expect(button).toHaveAttribute('title', 'No Desc')
    })
  })

  describe('Multiple Channels Display', () => {
    const twoChannels = [
      { id: '1', name: 'Channel 1' },
      { id: '2', name: 'Channel 2' }
    ]

    const threeChannels = [
      { id: '1', name: 'Channel 1' },
      { id: '2', name: 'Channel 2' },
      { id: '3', name: 'Channel 3' }
    ]

    it('displays all channels when within maxDisplay limit', () => {
      render(<ChannelBadge channels={twoChannels} maxDisplay={2} />)
      expect(screen.getByText('Channel 1')).toBeInTheDocument()
      expect(screen.getByText('Channel 2')).toBeInTheDocument()
    })

    it('shows individual buttons for each channel', () => {
      render(<ChannelBadge channels={twoChannels} maxDisplay={2} />)
      const buttons = screen.getAllByRole('button')
      expect(buttons).toHaveLength(2)
    })

    it('uses flex layout for multiple channels', () => {
      render(<ChannelBadge channels={twoChannels} maxDisplay={2} />)
      const container = screen.getByText('Channel 1').parentElement
      expect(container).toHaveClass('inline-flex', 'gap-1', 'flex-wrap')
    })

    it('respects custom maxDisplay prop', () => {
      render(<ChannelBadge channels={threeChannels} maxDisplay={5} />)
      expect(screen.getByText('Channel 1')).toBeInTheDocument()
      expect(screen.getByText('Channel 2')).toBeInTheDocument()
      expect(screen.getByText('Channel 3')).toBeInTheDocument()
    })
  })

  describe('Too Many Channels Display', () => {
    const manyChannels = Array.from({ length: 5 }, (_, i) => ({
      id: String(i),
      name: `Channel ${i + 1}`
    }))

    it('shows channel count when exceeds maxDisplay', () => {
      render(<ChannelBadge channels={manyChannels} maxDisplay={2} />)
      expect(screen.getByText('5 个频道')).toBeInTheDocument()
    })

    it('has purple styling for count badge', () => {
      render(<ChannelBadge channels={manyChannels} maxDisplay={2} />)
      const button = screen.getByRole('button', { name: '5 个频道' })
      expect(button).toHaveClass(
        'bg-purple-100',
        'text-purple-700',
        'dark:bg-purple-900/30',
        'dark:text-purple-300'
      )
    })

    it('shows all channel names in title attribute', () => {
      render(<ChannelBadge channels={manyChannels} maxDisplay={2} />)
      const button = screen.getByRole('button', { name: '5 个频道' })
      expect(button).toHaveAttribute(
        'title',
        'Channel 1, Channel 2, Channel 3, Channel 4, Channel 5'
      )
    })

    it('is clickable when onClick provided', () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={manyChannels} maxDisplay={2} onClick={handleClick} />)
      const button = screen.getByRole('button', { name: '5 个频道' })
      expect(button).toBeInTheDocument()
    })

    it('calls onClick when count badge is clicked', async () => {
      const user = userEvent.setup()
      const handleClick = vi.fn()
      render(<ChannelBadge channels={manyChannels} maxDisplay={2} onClick={handleClick} />)

      const button = screen.getByRole('button', { name: '5 个频道' })
      await user.click(button)

      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Custom Styling', () => {
    it('merges custom className', () => {
      render(<ChannelBadge channels={[]} className="ml-2 custom-class" />)
      const badge = screen.getByText('个人')
      expect(badge).toHaveClass('ml-2', 'custom-class')
    })

    it('preserves base classes with custom className', () => {
      render(<ChannelBadge channels={[mockChannel]} className="custom" />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toHaveClass('custom')
      expect(button).toHaveClass('bg-blue-100')
    })
  })

  describe('Accessibility', () => {
    it('button has proper styling when clickable', () => {
      const handleClick = vi.fn()
      render(<ChannelBadge channels={[mockChannel]} onClick={handleClick} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toHaveClass('cursor-pointer')
    })

    it('lacks cursor-pointer when onClick not provided', () => {
      render(<ChannelBadge channels={[mockChannel]} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).not.toHaveClass('cursor-pointer')
    })
  })

  describe('Transitions', () => {
    it('has transition-colors class for smooth hover', () => {
      render(<ChannelBadge channels={[mockChannel]} />)
      const button = screen.getByRole('button', { name: 'Test Channel' })
      expect(button).toHaveClass('transition-colors')
    })
  })
})
