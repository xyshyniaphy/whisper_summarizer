/**
 * GoogleButtonコンポーネントのテスト
 *
 * Google OAuthボタンのレンダリング、クリックハンドラー、
 * 無効状態、ローディング状態をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GoogleButton } from '../../../src/components/GoogleButton'

describe('GoogleButton', () => {
  const mockOnClick = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('Googleボタンが正常にレンダリングされる', () => {
      render(<GoogleButton onClick={mockOnClick} />)
      expect(screen.getByText(/使用 Google 继续/)).toBeTruthy()
    })

    it('Googleロゴが表示される', () => {
      const { container } = render(<GoogleButton onClick={mockOnClick} />)
      const svg = container.querySelector('svg')
      expect(svg).toBeTruthy()
    })

    it('正しい色のGoogleロゴが表示される', () => {
      const { container } = render(<GoogleButton onClick={mockOnClick} />)
      const paths = container.querySelectorAll('path')
      // Google logo has 4 colored paths
      expect(paths.length).toBe(4)
    })
  })

  describe('Click Handler', () => {
    it('ボタンをクリックするとonClickが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnClick).toHaveBeenCalledTimes(1)
    })

    it('複数回クリックすると複数回onClickが呼ばれる', async () => {
      const user = userEvent.setup()
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      await user.click(button)
      await user.click(button)

      expect(mockOnClick).toHaveBeenCalledTimes(2)
    })
  })

  describe('Disabled State', () => {
    it('disabled=trueの場合、ボタンが無効になる', () => {
      render(<GoogleButton onClick={mockOnClick} disabled={true} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('disabled時、クリックしてもonClickが呼ばれない', async () => {
      const user = userEvent.setup()
      render(<GoogleButton onClick={mockOnClick} disabled={true} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnClick).not.toHaveBeenCalled()
    })

    it('disabled時、スタイルが変化する', () => {
      render(<GoogleButton onClick={mockOnClick} disabled={true} />)

      const button = screen.getByRole('button')
      expect(button.className).toContain('disabled')
    })
  })

  describe('Loading State', () => {
    it('loading=trueの場合、「连接中...」が表示される', () => {
      render(<GoogleButton onClick={mockOnClick} loading={true} />)

      expect(screen.getByText('连接中...')).toBeTruthy()
    })

    it('loading時、ボタンが無効になる', () => {
      render(<GoogleButton onClick={mockOnClick} loading={true} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('loading時、クリックしてもonClickが呼ばれない', async () => {
      const user = userEvent.setup()
      render(<GoogleButton onClick={mockOnClick} loading={true} />)

      const button = screen.getByRole('button')
      await user.click(button)

      expect(mockOnClick).not.toHaveBeenCalled()
    })

    it('disabledとloadingの両方がtrueの場合、ボタンが無効になる', () => {
      render(<GoogleButton onClick={mockOnClick} disabled={true} loading={true} />)

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })
  })

  describe('Styling', () => {
    it('正しいCSSクラスが適用される', () => {
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      expect(button).toBeTruthy()
      expect(button.className).toContain('border')
    })

    it('ダークモード対応のクラスが含まれる', () => {
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      expect(button.className).toMatch(/dark:/)
    })
  })

  describe('Accessibility', () => {
    it('正しいaria-labelが設定される', () => {
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByLabelText('Sign in with Google')
      expect(button).toBeTruthy()
    })

    it('disabled時、正しいARIA属性が設定される', () => {
      render(<GoogleButton onClick={mockOnClick} disabled={true} />)

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('disabled')
    })
  })

  describe('Button Type', () => {
    it('buttonタイプが"type=button"である', () => {
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      expect(button.getAttribute('type')).toBe('button')
    })
  })

  describe('Icon and Text Layout', () => {
    it('アイコンとテキストが正しく配置される', () => {
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      expect(button.className).toContain('items-center')
      expect(button.className).toContain('justify-center')
    })

    it('アイコンとテキストの間にギャップがある', () => {
      render(<GoogleButton onClick={mockOnClick} />)

      const button = screen.getByRole('button')
      expect(button.className).toContain('gap')
    })
  })
})
