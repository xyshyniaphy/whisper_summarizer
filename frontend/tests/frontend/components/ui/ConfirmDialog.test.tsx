/**
 * ConfirmDialogコンポーネントのテスト
 *
 * 確認ダイアログのレンダリング、動作をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmDialog } from '../../../../src/components/ui/ConfirmDialog'

describe('ConfirmDialog', () => {
  const mockOnClose = vi.fn()
  const mockOnConfirm = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('ダイアログが閉じている場合、何も表示されない', () => {
      const { container } = render(
        <ConfirmDialog
          isOpen={false}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="本当に実行しますか？"
        />
      )

      // Modalが閉じていることを確認
      expect(container.querySelector('.fixed')).toBeNull()
    })

    it('ダイアログが開いている場合、タイトルとメッセージが表示される', async () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="削除の確認"
          message="この操作は取り消せません。本当に削除しますか？"
        />
      )

      await waitFor(() => {
        expect(screen.getByText('削除の確認')).toBeTruthy()
        expect(screen.getByText('この操作は取り消せません。本当に削除しますか？')).toBeTruthy()
      })
    })

    it('デフォルトのボタンラベルが表示される', async () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="メッセージ"
        />
      )

      await waitFor(() => {
        expect(screen.getByText('确定')).toBeTruthy()
        expect(screen.getByText('取消')).toBeTruthy()
      })
    })

    it('カスタムボタンラベルが表示される', async () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="メッセージ"
          confirmLabel="削除する"
          cancelLabel="キャンセル"
        />
      )

      await waitFor(() => {
        expect(screen.getByText('削除する')).toBeTruthy()
        expect(screen.getByText('キャンセル')).toBeTruthy()
      })
    })
  })

  describe('User Interactions', () => {
    it('確認ボタンをクリックするとonConfirmとonCloseが呼ばれる', async () => {
      const user = userEvent.setup()
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="メッセージ"
        />
      )

      await waitFor(async () => {
        const confirmButton = await screen.findByText('确定')
        await user.click(confirmButton)
      })

      expect(mockOnConfirm).toHaveBeenCalledTimes(1)
      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('キャンセルボタンをクリックするとonCloseのみが呼ばれる', async () => {
      const user = userEvent.setup()
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="メッセージ"
        />
      )

      await waitFor(async () => {
        const cancelButton = await screen.findByText('取消')
        await user.click(cancelButton)
      })

      expect(mockOnClose).toHaveBeenCalledTimes(1)
      expect(mockOnConfirm).not.toHaveBeenCalled()
    })
  })

  describe('Danger Variant', () => {
    it('dangerバリアントの場合、警告アイコンが表示される', async () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="削除の確認"
          message="本当に削除しますか？"
          variant="danger"
        />
      )

      await waitFor(() => {
        const alertIcon = document.querySelector('[data-icon="alert-triangle"]')
        expect(alertIcon).toBeTruthy()
      })
    })
  })

  describe('Message Types', () => {
    it('文字列メッセージが表示される', async () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="これは文字列メッセージです"
        />
      )

      await waitFor(() => {
        expect(screen.getByText('これは文字列メッセージです')).toBeTruthy()
      })
    })

    it('Reactノードメッセージが表示される', async () => {
      const messageNode = (
        <div>
          <p>段落1</p>
          <p>段落2</p>
        </div>
      )

      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message={messageNode}
        />
      )

      await waitFor(() => {
        expect(screen.getByText('段落1')).toBeTruthy()
        expect(screen.getByText('段落2')).toBeTruthy()
      })
    })
  })

  describe('Accessibility', () => {
    it('適切なARIA属性が設定される', async () => {
      render(
        <ConfirmDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          title="確認"
          message="メッセージ"
        />
      )

      await waitFor(() => {
        // ModalからARIA attributesが継承されることを確認
        const modal = document.querySelector('[role="dialog"]')
        expect(modal).toBeTruthy()
      })
    })
  })
})
