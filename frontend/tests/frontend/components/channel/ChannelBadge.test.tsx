/**
 * ChannelBadgeコンポーネントのテスト
 *
 * チャンネルバッジの表示、複数チャンネル、
 * 個人コンテンツ、クリック動作をテストする。
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChannelBadge, Channel } from '../../../../src/components/channel/ChannelBadge'

const mockChannels: Channel[] = [
  { id: '1', name: 'Marketing', description: 'Marketing team content' },
  { id: '2', name: 'Sales', description: 'Sales team content' },
  { id: '3', name: 'Engineering', description: 'Engineering team content' }
]

const wrapper = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}

describe('ChannelBadge', () => {
  describe('Rendering', () => {
    it('個人コンテンツバッジが表示される (isPersonal=true)', () => {
      render(<ChannelBadge channels={[]} isPersonal={true} />, { wrapper })
      expect(screen.getByText('个人')).toBeTruthy()
    })

    it('個人コンテンツバッジが表示される (channels=empty)', () => {
      render(<ChannelBadge channels={[]} isPersonal={false} />, { wrapper })
      expect(screen.getByText('个人')).toBeTruthy()
    })

    it('単一チャンネルバッジが表示される', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />, { wrapper })
      expect(screen.getByText('Marketing')).toBeTruthy()
    })

    it('複数チャンネルバッジが表示される (2つまで)', () => {
      render(<ChannelBadge channels={mockChannels.slice(0, 2)} maxDisplay={2} />, { wrapper })
      expect(screen.getByText('Marketing')).toBeTruthy()
      expect(screen.getByText('Sales')).toBeTruthy()
    })

    it('チャンネル数がmaxDisplayを超えるとカウントが表示される', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={2} />, { wrapper })
      expect(screen.getByText('3 个频道')).toBeTruthy()
    })
  })

  describe('Styling', () => {
    it('個人バッジがグレースタイルで表示される', () => {
      const { container } = render(<ChannelBadge channels={[]} isPersonal={true} />, { wrapper })
      const badge = container.querySelector('span')
      expect(badge?.className).toContain('bg-gray-100')
    })

    it('チャンネルバッジがブルースタイルで表示される', () => {
      const { container } = render(<ChannelBadge channels={[mockChannels[0]]} />, { wrapper })
      const button = container.querySelector('button')
      expect(button?.className).toContain('bg-blue-100')
    })

    it('複数チャンネルバッジがパープルスタイルで表示される (maxDisplay超過)', () => {
      const { container } = render(<ChannelBadge channels={mockChannels} maxDisplay={2} />, { wrapper })
      const button = container.querySelector('button')
      expect(button?.className).toContain('bg-purple-100')
    })

    it('カスタムclassNameが適用される', () => {
      const { container } = render(
        <ChannelBadge channels={[]} isPersonal={true} className="custom-class" />,
        { wrapper }
      )
      const badge = container.querySelector('span')
      expect(badge?.className).toContain('custom-class')
    })
  })

  describe('Click Behavior', () => {
    it('onClickハンドラーが呼ばれる (単一チャンネル)', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(
        <ChannelBadge
          channels={[mockChannels[0]]}
          onClick={handleClick}
        />,
        { wrapper }
      )

      const button = screen.getByText('Marketing')
      await user.click(button)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('onClickハンドラーが呼ばれる (複数チャンネル、カウント表示)', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(
        <ChannelBadge
          channels={mockChannels}
          maxDisplay={2}
          onClick={handleClick}
        />,
        { wrapper }
      )

      const button = screen.getByText('3 个频道')
      await user.click(button)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('onClickなしでバッジが表示される', () => {
      render(<ChannelBadge channels={[mockChannels[0]]} />, { wrapper })
      expect(screen.getByText('Marketing')).toBeTruthy()
    })
  })

  describe('Tooltip/Title', () => {
    it('チャンネル説明がtitle属性に設定される (単一チャンネル)', () => {
      const { container } = render(
        <ChannelBadge channels={[mockChannels[0]]} />,
        { wrapper }
      )
      const button = container.querySelector('button')
      expect(button?.getAttribute('title')).toBe('Marketing team content')
    })

    it('チャンネル名がtitle属性に設定される (説明なし)', () => {
      const channelWithoutDesc: Channel = { id: '1', name: 'TestChannel' }
      const { container } = render(
        <ChannelBadge channels={[channelWithoutDesc]} />,
        { wrapper }
      )
      const button = container.querySelector('button')
      expect(button?.getAttribute('title')).toBe('TestChannel')
    })

    it('全チャンネル名がtitle属性に設定される (複数チャンネル、カウント表示)', () => {
      const { container } = render(
        <ChannelBadge channels={mockChannels} maxDisplay={2} />,
        { wrapper }
      )
      const button = container.querySelector('button')
      expect(button?.getAttribute('title')).toBe('Marketing, Sales, Engineering')
    })
  })

  describe('Edge Cases', () => {
    it('maxDisplay=1で複数チャンネルのカウントが表示される', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={1} />, { wrapper })
      expect(screen.getByText('3 个频道')).toBeTruthy()
    })

    it('maxDisplay=10で全チャンネルが表示される', () => {
      render(<ChannelBadge channels={mockChannels} maxDisplay={10} />, { wrapper })
      expect(screen.getByText('Marketing')).toBeTruthy()
      expect(screen.getByText('Sales')).toBeTruthy()
      expect(screen.getByText('Engineering')).toBeTruthy()
    })

    it('説明なしのチャンネルが正しく表示される', () => {
      const channelWithoutDesc: Channel = { id: '1', name: 'NoDescChannel' }
      render(<ChannelBadge channels={[channelWithoutDesc]} />, { wrapper })
      expect(screen.getByText('NoDescChannel')).toBeTruthy()
    })
  })
})
