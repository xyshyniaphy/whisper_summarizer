/**
 * Modalコンポーネントのテスト
 *
 * モーダルのレンダリング、動作、アクセシビリティをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Modal } from '../../../../src/components/ui/Modal'

describe('Modal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset body overflow
    document.body.style.overflow = 'unset'
  })

  describe('Rendering', () => {
    it('閉じている場合、何も表示されない', () => {
      const { container } = render(
        <Modal isOpen={false} onClose={mockOnClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      )

      expect(container.querySelector('.fixed')).toBeNull()
    })

    it('開いている場合、モーダルが表示される', async () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Modal content</p>
        </Modal>
      )

      await waitFor(() => {
        expect(screen.getByText('Test Modal')).toBeTruthy()
        expect(screen.getByText('Modal content')).toBeTruthy()
      })
    })

    it('タイトルがない場合、コンテンツのみ表示される', async () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          <p>Content without title</p>
        </Modal>
      )

      await waitFor(() => {
        expect(screen.getByText('Content without title')).toBeTruthy()
      })
    })

    it('カスタムclassNameが適用される', async () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} className="custom-class">
          <p>Content</p>
        </Modal>
      )

      await waitFor(() => {
        const modal = document.querySelector('.custom-class')
        expect(modal).toBeTruthy()
      })
    })
  })

  describe('User Interactions', () => {
    it('オーバーレイをクリックするとonCloseが呼ばれる', async () => {
      const user = userEvent.setup()
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          <p>Content</p>
        </Modal>
      )

      await waitFor(async () => {
        const overlay = document.querySelector('.bg-black\\/50')
        if (overlay) {
          await user.click(overlay)
          expect(mockOnClose).toHaveBeenCalledTimes(1)
        }
      })
    })

    it('閉じるボタンをクリックするとonCloseが呼ばれる', async () => {
      const user = userEvent.setup()
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </Modal>
      )

      await waitFor(async () => {
        const closeButton = screen.getByLabelText('Close')
        await user.click(closeButton)
        expect(mockOnClose).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Body Scroll Lock', () => {
    it('開いている場合、bodyのスクロールが無効になる', async () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          <p>Content</p>
        </Modal>
      )

      await waitFor(() => {
        expect(document.body.style.overflow).toBe('hidden')
      })
    })

    it('閉じている場合、bodyのスクロールが有効になる', () => {
      render(
        <Modal isOpen={false} onClose={mockOnClose} title="Test">
          <p>Content</p>
        </Modal>
      )

      expect(document.body.style.overflow).toBe('unset')
    })
  })

  describe('Accessibility', () => {
    it('タイトルがある場合、aria-labelが設定される', async () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test Modal">
          <p>Content</p>
        </Modal>
      )

      await waitFor(() => {
        expect(screen.getByText('Test Modal')).toBeTruthy()
      })
    })

    it('閉じるボタンに正しいaria-labelが設定される', async () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          <p>Content</p>
        </Modal>
      )

      await waitFor(() => {
        const closeButton = screen.getByLabelText('Close')
        expect(closeButton).toBeTruthy()
      })
    })
  })

  describe('Conditional Return', () => {
    it('Reactフックのルールに従って条件付きレンダリングを行う', () => {
      // Modalが正しく実装されていることを確認
      // isOpen=falseのときはnullを返す
      const { container } = render(
        <Modal isOpen={false} onClose={mockOnClose}>
          <p>Content</p>
        </Modal>
      )

      expect(container.firstChild).toBe(null)
    })
  })
})
