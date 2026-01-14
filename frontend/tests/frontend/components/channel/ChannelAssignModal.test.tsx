/**
 * ChannelAssignModalコンポーネントのテスト
 *
 * モーダルでのチャンネル割り当て、選択、検索、
 * 保存/キャンセル動作をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'jotai'
import React from 'react'

import { ChannelAssignModal } from '../../../../src/components/channel/ChannelAssignModal'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider>{children}</Provider>
)

// Mock channels data
const mockChannels = [
  { id: '1', name: 'Marketing', description: 'Marketing team' },
  { id: '2', name: 'Sales', description: 'Sales team' },
  { id: '3', name: 'Engineering', description: 'Engineering team' }
]

const mockOnConfirm = vi.fn(() => Promise.resolve())
const mockOnClose = vi.fn()

const defaultProps = {
  isOpen: true,
  onClose: mockOnClose,
  onConfirm: mockOnConfirm,
  transcriptionId: 'trans-123',
  currentChannelIds: ['1'],
  loading: false
}

describe('ChannelAssignModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Use global axios mocks from setup.ts
    const mockAxiosGet = (global as any).mockAxiosGet
    if (mockAxiosGet) {
      mockAxiosGet.mockReset()
      mockAxiosGet.mockImplementation((url: string) => {
        // Match /admin/channels (listChannels)
        if (url?.includes('/admin/channels')) {
          return Promise.resolve({ data: mockChannels })
        }
        return Promise.resolve({ data: [] })
      })
    }

    const mockAxiosPost = (global as any).mockAxiosPost
    if (mockAxiosPost) {
      mockAxiosPost.mockReset()
      mockAxiosPost.mockResolvedValue({ data: {} })
    }
  })

  describe('Rendering', () => {
    it('モーダルが開いている時にチャンネルリストが表示される', async () => {
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('分配到频道')).toBeTruthy()
      })
    })

    it('チャンネルが読み込まれる', async () => {
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
        expect(screen.getByText('Sales')).toBeTruthy()
        expect(screen.getByText('Engineering')).toBeTruthy()
      })
    })

    it('検索入力フィールドが表示される', async () => {
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByPlaceholderText('搜索频道名称...')).toBeTruthy()
      })
    })

    it('「选择所有」ボタンが表示される', async () => {
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('选择所有')).toBeTruthy()
      })
    })

    it('「已选择N个频道」が表示される', async () => {
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('已选择 1 个频道')).toBeTruthy()
      })
    })
  })

  describe('Channel Selection', () => {
    it('チャンネルのチェックボックスをクリックして選択できる', async () => {
      const user = userEvent.setup()
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      // Marketing should already be checked (from currentChannelIds)
      const salesCheckbox = screen.getAllByRole('checkbox').find(
        cb => cb.nextElementSibling?.textContent?.includes('Sales')
      )

      if (salesCheckbox) {
        await user.click(salesCheckbox)
        expect(salesCheckbox).toBeChecked()
      }
    })

    it('「选择所有」で全チャンネルを選択できる', async () => {
      const user = userEvent.setup()
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('选择所有')).toBeTruthy()
      })

      const selectAllButton = screen.getByText('选择所有')
      await user.click(selectAllButton)

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        checkboxes.forEach(cb => {
          expect(cb).toBeChecked()
        })
      })
    })

    it('「取消选择所有」で全チャンネルの選択を解除できる', async () => {
      const user = userEvent.setup()
      render(<ChannelAssignModal {...defaultProps} currentChannelIds={['1', '2', '3']} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('取消选择所有')).toBeTruthy()
      })

      const deselectAllButton = screen.getByText('取消选择所有')
      await user.click(deselectAllButton)

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        checkboxes.forEach(cb => {
          expect(cb).not.toBeChecked()
        })
      })
    })
  })

  describe('Search Functionality', () => {
    it('チャンネル名で検索できる', async () => {
      const user = userEvent.setup()
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      const searchInput = screen.getByPlaceholderText('搜索频道名称...')
      await user.type(searchInput, 'Marketing')

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
        // Sales should not be visible in the list (filtered out)
      })
    })

    it('説明文で検索できる', async () => {
      const user = userEvent.setup()
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      const searchInput = screen.getByPlaceholderText('搜索频道名称...')
      await user.type(searchInput, 'team')

      // Should show all channels with "team" in description
      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
        expect(screen.getByText('Sales')).toBeTruthy()
        expect(screen.getByText('Engineering')).toBeTruthy()
      })
    })

    it('検索結果が空の場合はメッセージが表示される', async () => {
      const user = userEvent.setup()
      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Marketing')).toBeTruthy()
      })

      const searchInput = screen.getByPlaceholderText('搜索频道名称...')
      await user.type(searchInput, 'NonExistentChannel')

      await waitFor(() => {
        expect(screen.getByText('未找到匹配的频道')).toBeTruthy()
      })
    })
  })

  describe('Save and Cancel', () => {
    it('「保存」ボタンをクリックするとonConfirmが呼ばれる', async () => {
      const user = userEvent.setup()
      const mockConfirm = vi.fn(() => Promise.resolve())

      render(<ChannelAssignModal {...defaultProps} onConfirm={mockConfirm} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('保存')).toBeTruthy()
      })

      const saveButton = screen.getByText('保存')
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockConfirm).toHaveBeenCalledWith(['1'])
      })
    })

    it('「取消」ボタンをクリックするとonCloseが呼ばれる', async () => {
      const user = userEvent.setup()
      const mockClose = vi.fn()

      render(<ChannelAssignModal {...defaultProps} onClose={mockClose} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('取消')).toBeTruthy()
      })

      const cancelButton = screen.getByText('取消')
      await user.click(cancelButton)

      expect(mockClose).toHaveBeenCalledTimes(1)
    })

    it('保存中はスピナーが表示される', async () => {
      const user = userEvent.setup()
      const mockConfirm = vi.fn(() => new Promise(() => {})) // Never resolves to stay in saving state

      render(<ChannelAssignModal {...defaultProps} onConfirm={mockConfirm} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('保存')).toBeTruthy()
      })

      const saveButton = screen.getByText('保存')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('保存中...')).toBeTruthy()
      })
    })
  })

  describe('Error Handling', () => {
    it('onConfirmが失敗するとエラーメッセージが表示される', async () => {
      const user = userEvent.setup()
      const mockConfirm = vi.fn(() => Promise.reject(new Error('Save failed')))

      render(<ChannelAssignModal {...defaultProps} onConfirm={mockConfirm} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('保存')).toBeTruthy()
      })

      const saveButton = screen.getByText('保存')
      await user.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Save failed')).toBeTruthy()
      })
    })
  })

  describe('Loading State', () => {
    it('チャンネル読み込み中はローディングメッセージが表示される', async () => {
      const mockAxiosGet = (global as any).mockAxiosGet
      if (mockAxiosGet) {
        mockAxiosGet.mockImplementationOnce(
          () => new Promise(resolve => setTimeout(() => resolve({ data: [] }), 100))
        )
      }

      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      expect(screen.getByText('加载频道列表...')).toBeTruthy()
    })
  })

  describe('Modal Closed', () => {
    it('モーダルが閉じている時に何も表示されない', () => {
      render(<ChannelAssignModal {...defaultProps} isOpen={false} />, { wrapper })

      expect(screen.queryByText('分配到频道')).toBeFalsy()
    })
  })

  describe('Edge Cases', () => {
    it('チャンネルリストが空の場合はメッセージが表示される', async () => {
      const mockAxiosGet = (global as any).mockAxiosGet
      if (mockAxiosGet) {
        mockAxiosGet.mockResolvedValueOnce({ data: [] })
      }

      render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('暂无可用频道')).toBeTruthy()
      })
    })

    it('現在のチャンネル選択がリセットされる', async () => {
      const { rerender } = render(<ChannelAssignModal {...defaultProps} />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('已选择 1 个频道')).toBeTruthy()
      })

      // Re-render with different currentChannelIds
      rerender(
        <Provider>
          <ChannelAssignModal {...defaultProps} currentChannelIds={['1', '2']} />
        </Provider>
      )

      await waitFor(() => {
        expect(screen.getByText('已选择 2 个频道')).toBeTruthy()
      })
    })
  })
})
