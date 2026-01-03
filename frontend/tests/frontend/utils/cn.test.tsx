/**
 * cnユーティリティ関数のテスト
 *
 * Tailwind CSSクラスのマージと競合解決をテストする。
 */

import { describe, it, expect } from 'vitest'
import { cn } from '@/utils/cn'

describe('cn utility function', () => {
  describe('Basic Functionality', () => {
    it('単一のクラス文字列を正しく返す', () => {
      expect(cn('text-red-500')).toBe('text-red-500')
    })

    it('複数のクラス文字列を結合する', () => {
      expect(cn('text-red-500', 'bg-blue-500', 'p-4')).toBe('text-red-500 bg-blue-500 p-4')
    })

    it('空文字列を無視する', () => {
      expect(cn('text-red-500', '', 'bg-blue-500')).toBe('text-red-500 bg-blue-500')
    })

    it('undefinedとnullを無視する', () => {
      expect(cn('text-red-500', undefined, null, 'bg-blue-500')).toBe('text-red-500 bg-blue-500')
    })

    it('空の配列を無視する', () => {
      expect(cn('text-red-500', [], 'bg-blue-500')).toBe('text-red-500 bg-blue-500')
    })
  })

  describe('Conditional Classes', () => {
    it('条件付きクラスを正しく処理する', () => {
      const isActive = true
      expect(cn('base-class', isActive && 'active-class')).toBe('base-class active-class')
    })

    it('偽値の条件付きクラスを除外する', () => {
      const isActive = false
      expect(cn('base-class', isActive && 'active-class')).toBe('base-class')
    })

    it('三項演算子を正しく処理する', () => {
      const isActive = true
      expect(cn('base-class', isActive ? 'active' : 'inactive')).toBe('base-class active')
    })
  })

  describe('Tailwind Conflict Resolution', () => {
    it('同じプロパティの競合を解決する（後勝ち）', () => {
      expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500')
    })

    it('複数の競合するクラスを正しく解決する', () => {
      expect(cn('p-4 p-6 p-2')).toBe('p-2')
    })

    it('異なるプロパティのクラスは結合される', () => {
      expect(cn('text-red-500', 'bg-blue-500', 'p-4')).toBe('text-red-500 bg-blue-500 p-4')
    })

    it('Tailwindバリアントの競合を解決する', () => {
      expect(cn('hover:text-red-500', 'hover:text-blue-500')).toBe('hover:text-blue-500')
    })

    it('レスポンシブブレークポイントの競合を解決する', () => {
      expect(cn('md:p-4', 'md:p-6')).toBe('md:p-6')
    })
  })

  describe('Complex Use Cases', () => {
    it('配列内のクラスを結合する', () => {
      expect(cn(['text-red-500', 'bg-blue-500'], 'p-4')).toBe('text-red-500 bg-blue-500 p-4')
    })

    it 'オブジェクト形式の条件付きクラスを処理する', () => {
      expect(cn({
        'text-red-500': true,
        'bg-blue-500': true,
        'hidden': false
      })).toBe('text-red-500 bg-blue-500')
    })

    it('ネストした配列をフラット化する', () => {
      expect(cn(['text-red-500', ['bg-blue-500', ['p-4']]])).toBe('text-red-500 bg-blue-500 p-4')
    })
  })

  describe('Real Component Patterns', () => {
    it('ボタンバリアントパターン', () => {
      const variant = 'danger'
      const size = 'lg'
      const className = 'custom-class'
      
      expect(
        cn(
          'base-class',
          variant === 'danger' && 'bg-red-500 text-white',
          variant === 'primary' && 'bg-blue-500 text-white',
          size === 'lg' && 'px-6 py-3',
          size === 'sm' && 'px-2 py-1',
          className
        )
      ).toBe('base-class bg-red-500 text-white px-6 py-3 custom-class')
    })

    it('ダークモード対応パターン', () => {
      expect(cn('text-gray-900 dark:text-gray-100')).toBe('text-gray-900 dark:text-gray-100')
    })

    it('動的なクラス結合パターン', () => {
      const isActive = true
      const isDisabled = false
      const isLoading = true
      
      expect(
        cn(
          'base-class',
          isActive && 'active-class',
          isDisabled && 'disabled-class',
          isLoading && 'loading-class'
        )
      ).toBe('base-class active-class loading-class')
    })
  })

  describe('Edge Cases', () => {
    it('すべての値がfalsyの場合、空文字列を返す', () => {
      expect(cn('', false, undefined, null)).toBe('')
    })

    it '数字の0と1を正しく処理する', () => {
      expect(cn(0, 1, 'text-red-500')).toBe('0 1 text-red-500')
    })

    it '非常に長いクラスリストを処理する', () => {
      const classes = Array(100).fill(0).map((_, i) => `class-${i}`)
      const result = cn(...classes)
      expect(result).toBe(classes.join(' '))
    })

    it('重複するクラスを含む場合', () => {
      expect(cn('text-red-500', 'text-red-500', 'bg-blue-500')).toBe('text-red-500 bg-blue-500')
    })
  })

  describe('clsx Integration', () => {
    it('clsxの条件構文をサポートする', () => {
      expect(cn({
        'text-red-500': true,
        'bg-blue-500': false,
        'p-4': true
      })).toBe('text-red-500 p-4')
    })
  })

  describe('tailwind-merge Integration', () => {
    it('Tailwindのクラス優先順位を正しく処理する', () => {
      // Later classes should override earlier ones for the same property
      expect(cn('font-bold', 'font-normal')).toBe('font-normal')
    })

    it('重要でないクラスの競合を解決する', () => {
      expect(cn('w-full', 'w-1/2')).toBe('w-1/2')
    })
  })
})
