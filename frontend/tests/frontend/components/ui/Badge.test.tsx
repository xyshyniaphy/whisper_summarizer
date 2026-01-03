/**
 * Badgeコンポーネントのテスト
 *
 * バッジのバリアント、スタイリング、表示をテストする。
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '../../../../src/components/ui/Badge'

describe('Badge', () => {
  describe('Rendering', () => {
    it('デフォルトでinfoバリアントが表示される', () => {
      render(<Badge>Info Badge</Badge>)

      const badge = screen.getByText('Info Badge')
      expect(badge).toBeTruthy()
      expect(badge.className).toContain('bg-blue-100')
    })

    it('successバリアントが正しく表示される', () => {
      render(<Badge variant="success">Success</Badge>)

      const badge = screen.getByText('Success')
      expect(badge.className).toContain('bg-green-100')
    })

    it('errorバリアントが正しく表示される', () => {
      render(<Badge variant="error">Error</Badge>)

      const badge = screen.getByText('Error')
      expect(badge.className).toContain('bg-red-100')
    })

    it('warningバリアントが正しく表示される', () => {
      render(<Badge variant="warning">Warning</Badge>)

      const badge = screen.getByText('Warning')
      expect(badge.className).toContain('bg-yellow-100')
    })

    it('grayバリアントが正しく表示される', () => {
      render(<Badge variant="gray">Gray</Badge>)

      const badge = screen.getByText('Gray')
      expect(badge.className).toContain('bg-gray-100')
    })
  })

  describe('Dark Mode', () => {
    it('successバリアントにダークモードクラスが含まれる', () => {
      render(<Badge variant="success">Success</Badge>)

      const badge = screen.getByText('Success')
      expect(badge.className).toContain('dark:bg-green-900')
      expect(badge.className).toContain('dark:text-green-200')
    })

    it('errorバリアントにダークモードクラスが含まれる', () => {
      render(<Badge variant="error">Error</Badge>)

      const badge = screen.getByText('Error')
      expect(badge.className).toContain('dark:bg-red-900')
    })

    it('infoバリアントにダークモードクラスが含まれる', () => {
      render(<Badge variant="info">Info</Badge>)

      const badge = screen.getByText('Info')
      expect(badge.className).toContain('dark:bg-blue-900')
    })

    it('warningバリアントにダークモードクラスが含まれる', () => {
      render(<Badge variant="warning">Warning</Badge>)

      const badge = screen.getByText('Warning')
      expect(badge.className).toContain('dark:bg-yellow-900')
    })

    it('grayバリアントにダークモードクラスが含まれる', () => {
      render(<Badge variant="gray">Gray</Badge>)

      const badge = screen.getByText('Gray')
      expect(badge.className).toContain('dark:bg-gray-700')
    })
  })

  describe('Styling', () => {
    it('基本のスタイリングクラスが含まれる', () => {
      render(<Badge>Test</Badge>)

      const badge = screen.getByText('Test')
      expect(badge.className).toContain('px-2')
      expect(badge.className).toContain('py-1')
      expect(badge.className).toContain('text-xs')
      expect(badge.className).toContain('font-medium')
      expect(badge.className).toContain('rounded-full')
    })

    it('カスタムclassNameがマージされる', () => {
      render(<Badge className="custom-class">Test</Badge>)

      const badge = screen.getByText('Test')
      expect(badge.className).toContain('custom-class')
    })
  })

  describe('HTML Attributes', () => {
    it('追加のHTML属性が渡される', () => {
      render(
        <Badge data-testid="test-badge" title="Badge Title">
          Test
        </Badge>
      )

      const badge = screen.getByText('Test')
      expect(badge.getAttribute('data-testid')).toBe('test-badge')
      expect(badge.getAttribute('title')).toBe('Badge Title')
    })
  })

  describe('Content', () => {
    it('テキストコンテンツが表示される', () => {
      render(<Badge>Text Content</Badge>)

      expect(screen.getByText('Text Content')).toBeTruthy()
    })

    it('数値コンテンツが表示される', () => {
      render(<Badge>{42}</Badge>)

      expect(screen.getByText('42')).toBeTruthy()
    })

    it('Reactノードコンテンツが表示される', () => {
      render(
        <Badge>
          <span>Nested Content</span>
        </Badge>
      )

      expect(screen.getByText('Nested Content')).toBeTruthy()
    })
  })

  describe('Display Name', () => {
    it('コンポーネントにdisplayNameが設定されている', () => {
      expect(Badge.displayName).toBe('Badge')
    })
  })
})
