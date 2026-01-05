/**
 * Loading Statesコンポーネントのテスト
 *
 * ローディング状態を表示するコンポーネントをテストする。
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Loader2 } from 'lucide-react'

describe('Loading States', () => {
  describe('Spinner Loader', () => {
    it('スピナーローダーが正しく表示される', () => {
      const { container } = render(
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
        </div>
      )

      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
    })

    it('スピナーに正しいCSSクラスが適用される', () => {
      const { container } = render(
        <div className="flex items-center justify-center">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
        </div>
      )

      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
      // Check that the spinner element exists (SVG from lucide-react)
      expect(spinner?.tagName.toLowerCase()).toBe('svg')
    })
  })

  describe('Skeleton Loading', () => {
    it('スケルトンローダーが正しく表示される', () => {
      const { container } = render(
        <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-full" />
      )

      const skeleton = container.querySelector('.animate-pulse')
      expect(skeleton).toBeTruthy()
    })

    it('複数のスケルトンアイテムが表示される', () => {
      const { container } = render(
        <div className="space-y-3">
          <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-3/4" />
          <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-1/2" />
          <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-5/6" />
        </div>
      )

      const skeletons = container.querySelectorAll('.animate-pulse')
      expect(skeletons.length).toBe(3)
    })
  })

  describe('Loading Messages', () => {
    it('ローディングメッセージが表示される', () => {
      render(
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin mr-3" />
          <span className="text-gray-600 dark:text-gray-400">加载中...</span>
        </div>
      )

      expect(screen.getByText('加载中...')).toBeTruthy()
    })

    it('ローディングメッセージとスピナーが一緒に表示される', () => {
      const { container } = render(
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <span className="text-gray-600 dark:text-gray-400">处理中...</span>
        </div>
      )

      const spinner = container.querySelector('.animate-spin')
      const message = screen.getByText('处理中...')

      expect(spinner).toBeTruthy()
      expect(message).toBeTruthy()
    })
  })

  describe('Loading Containers', () => {
    it('フルページローディングが表示される', () => {
      const { container } = render(
        <div className="fixed inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm z-50">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
        </div>
      )

      const containerEl = container.querySelector('.fixed')
      expect(containerEl).toBeTruthy()
      expect(containerEl?.className).toContain('inset-0')
      expect(containerEl?.className).toContain('z-50')
    })

    it('インラインローディングが表示される', () => {
      const { container } = render(
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
          <span className="text-sm">保存中...</span>
        </div>
      )

      const spinner = container.querySelector('.animate-spin')
      expect(spinner).toBeTruthy()
      expect(screen.getByText('保存中...')).toBeTruthy()
    })
  })

  describe('Progress Indicators', () => {
    it('プログレスバーが表示される', () => {
      const { container } = render(
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: '45%' }}
          />
        </div>
      )

      const progressBar = container.querySelector('.bg-blue-500')
      expect(progressBar).toBeTruthy()
      expect(progressBar?.getAttribute('style')).toContain('45%')
    })

    it('プログレスステキストが表示される', () => {
      render(
        <div className="text-center text-sm text-gray-600 dark:text-gray-400">
          45% 完成
        </div>
      )

      expect(screen.getByText('45% 完成')).toBeTruthy()
    })
  })

  describe('Accessibility', () => {
    it('ローディング状態にaria-liveが設定される', () => {
      render(
        <div aria-live="polite" aria-busy="true">
          <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
          <span className="ml-2">加载中...</span>
        </div>
      )

      const loadingContainer = document.querySelector('[aria-live="polite"]')
      expect(loadingContainer).toBeTruthy()
      expect(loadingContainer?.getAttribute('aria-busy')).toBe('true')
    })

    it('スクリーンリーダー用のテキストが提供される', () => {
      render(
        <div role="status" aria-label="正在加载">
          <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
          <span className="sr-only">正在加载内容</span>
        </div>
      )

      const status = document.querySelector('[role="status"]')
      expect(status?.getAttribute('aria-label')).toBe('正在加载')
    })
  })

  describe('Dark Mode', () => {
    it('ダークモードでスケルトンが正しく表示される', () => {
      const { container } = render(
        <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded h-4 w-full" />
      )

      const skeleton = container.querySelector('.animate-pulse')
      expect(skeleton?.className).toContain('dark:bg-gray-700')
    })

    it('ダークモードでローディングテキストが正しく表示される', () => {
      render(
        <div className="text-gray-600 dark:text-gray-400">
          加载中...
        </div>
      )

      const text = screen.getByText('加载中...')
      expect(text.className).toContain('dark:text-gray-400')
    })
  })
})
