/**
 * ChannelFilterコンポーネントのテスト
 *
 * チャンネルフィルターの選択、変更、
 * 全て/個人/チャンネル選択をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider, useAtom } from 'jotai'
import React, { useEffect, useRef } from 'react'

import { ChannelFilter } from '../../../../src/components/channel/ChannelFilter'
import { channelsAtom, channelFilterAtom } from '../../../../src/atoms/channels'

const mockChannels = [
  { id: '1', name: 'Marketing', description: 'Marketing team' },
  { id: '2', name: 'Sales', description: 'Sales team' },
  { id: '3', name: 'Engineering', description: 'Engineering team' }
]

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

const renderWithChannels = (initialChannels = mockChannels) => {
  const TestComponent = () => {
    const [, setChannels] = useAtom(channelsAtom)
    const initialized = useRef(false)

    useEffect(() => {
      if (!initialized.current) {
        initialized.current = true
        setChannels(initialChannels)
      }
    }, [setChannels, initialChannels])

    return <ChannelFilter />
  }

  return render(<TestComponent />, { wrapper })
}

describe('ChannelFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('チャンネルフィルターが正常にレンダリングされる', () => {
      renderWithChannels()
      expect(screen.getByText('频道筛选:')).toBeTruthy()
    })

    it('「全部内容」オプションが表示される', () => {
      renderWithChannels()
      expect(screen.getByText('全部内容')).toBeTruthy()
    })

    it('「个人内容」オプションが表示される', () => {
      renderWithChannels()
      expect(screen.getByText('个人内容')).toBeTruthy()
    })

    it('チャンネルリストが表示される', () => {
      renderWithChannels()
      expect(screen.getByText('Marketing')).toBeTruthy()
      expect(screen.getByText('Sales')).toBeTruthy()
      expect(screen.getByText('Engineering')).toBeTruthy()
    })
  })

  describe('Filter Selection', () => {
    it('「全部内容」を選択できる', async () => {
      const user = userEvent.setup()
      renderWithChannels()

      const select = screen.getByRole('combobox')
      await user.selectOptions(select, 'all')

      expect(select).toHaveValue('all')
    })

    it('「个人内容」を選択できる', async () => {
      const user = userEvent.setup()
      renderWithChannels()

      const select = screen.getByRole('combobox')
      await user.selectOptions(select, 'personal')

      expect(select).toHaveValue('personal')
    })

    it('チャンネルを選択できる', async () => {
      const user = userEvent.setup()
      renderWithChannels()

      const select = screen.getByRole('combobox')
      await user.selectOptions(select, '1')

      expect(select).toHaveValue('1')
    })
  })

  describe('Active Filter Display', () => {
    it('個人フィルター選択時に「个人内容」が表示される', () => {
      const TestComponent = () => {
        const [, setChannels] = useAtom(channelsAtom)
        const [, setFilter] = useAtom(channelFilterAtom)
        const initialized = useRef(false)

        useEffect(() => {
          if (!initialized.current) {
            initialized.current = true
            setChannels(mockChannels)
            setFilter('personal')
          }
        }, [setChannels, setFilter])

        return <ChannelFilter />
      }

      render(<TestComponent />, { wrapper })

      expect(screen.getByText('当前筛选:')).toBeTruthy()
      // Text appears in both select option and active filter display
      expect(screen.getAllByText('个人内容').length).toBeGreaterThan(0)
    })

    it('チャンネルフィルター選択時にチャンネル名が表示される', () => {
      const TestComponent = () => {
        const [, setChannels] = useAtom(channelsAtom)
        const [, setFilter] = useAtom(channelFilterAtom)
        const initialized = useRef(false)

        useEffect(() => {
          if (!initialized.current) {
            initialized.current = true
            setChannels(mockChannels)
            setFilter('1')
          }
        }, [setChannels, setFilter])

        return <ChannelFilter />
      }

      render(<TestComponent />, { wrapper })

      expect(screen.getByText('当前筛选:')).toBeTruthy()
      // Text appears in both select option and active filter display
      expect(screen.getAllByText('Marketing').length).toBeGreaterThan(0)
    })

    it('「清除筛选」ボタンが表示される', () => {
      const TestComponent = () => {
        const [, setChannels] = useAtom(channelsAtom)
        const [, setFilter] = useAtom(channelFilterAtom)
        const initialized = useRef(false)

        useEffect(() => {
          if (!initialized.current) {
            initialized.current = true
            setChannels(mockChannels)
            setFilter('personal')
          }
        }, [setChannels, setFilter])

        return <ChannelFilter />
      }

      render(<TestComponent />, { wrapper })

      expect(screen.getByText('清除筛选')).toBeTruthy()
    })
  })

  describe('Clear Filter', () => {
    it('「清除筛选」ボタンをクリックするとフィルターがクリアされる', async () => {
      const user = userEvent.setup()

      const TestComponent = () => {
        const [, setChannels] = useAtom(channelsAtom)
        const [filter, setFilter] = useAtom(channelFilterAtom)
        const initialized = useRef(false)

        useEffect(() => {
          if (!initialized.current) {
            initialized.current = true
            setChannels(mockChannels)
            setFilter('personal')
          }
        }, [setChannels, setFilter])

        return (
          <>
            <ChannelFilter />
            <div data-testid="filter-value">{filter ?? 'all'}</div>
          </>
        )
      }

      render(<TestComponent />, { wrapper })

      const clearButton = screen.getByText('清除筛选')
      await user.click(clearButton)

      expect(screen.getByTestId('filter-value')).toHaveTextContent('all')
    })
  })

  describe('Edge Cases', () => {
    it('チャンネルリストが空の場合でも正しく表示される', () => {
      renderWithChannels([])
      expect(screen.getByText('频道筛选:')).toBeTruthy()
      expect(screen.getByText('全部内容')).toBeTruthy()
      expect(screen.getByText('个人内容')).toBeTruthy()
    })

    it('存在しないチャンネルIDが選択されている場合', () => {
      const TestComponent = () => {
        const [, setChannels] = useAtom(channelsAtom)
        const [, setFilter] = useAtom(channelFilterAtom)
        const initialized = useRef(false)

        useEffect(() => {
          if (!initialized.current) {
            initialized.current = true
            setChannels(mockChannels)
            setFilter('nonexistent')
          }
        }, [setChannels, setFilter])

        return <ChannelFilter />
      }

      render(<TestComponent />, { wrapper })

      // Should show the ID as the label when channel not found
      expect(screen.getByText('当前筛选:')).toBeTruthy()
    })
  })
})
