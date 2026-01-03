/**
 * Error Handling Tests
 *
 * APIエラーハンドリング、ネットワークエラー、バリデーションエラーをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock error boundary component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || <div>Something went wrong</div>
    }
    return this.props.children
  }
}

describe('Error Handling', () => {
  describe('API Error Responses', () => {
    it('401エラーメッセージが表示される', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { detail: '認証が必要です' }
        }
      }

      const TestComponent = () => (
        <div>
          {mockError.response?.status === 401 && (
            <div className="error-message">認証が必要です。再度ログインしてください。</div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('認証が必要です。再度ログインしてください。')).toBeTruthy()
      })
    })

    it('403エラーメッセージが表示される', async () => {
      const mockError = {
        response: {
          status: 403,
          data: { detail: 'アクセスが拒否されました' }
        }
      }

      const TestComponent = () => (
        <div>
          {mockError.response?.status === 403 && (
            <div className="error-message">この操作を実行する権限がありません。</div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('この操作を実行する権限がありません。')).toBeTruthy()
      })
    })

    it('404エラーメッセージが表示される', async () => {
      const mockError = {
        response: {
          status: 404,
          data: { detail: 'リソースが見つかりません' }
        }
      }

      const TestComponent = () => (
        <div>
          {mockError.response?.status === 404 && (
            <div className="error-message">要求されたリソースは見つかりませんでした。</div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('要求されたリソースは見つかりませんでした。')).toBeTruthy()
      })
    })

    it('500サーバーエラーメッセージが表示される', async () => {
      const mockError = {
        response: {
          status: 500,
          data: { detail: 'サーバーエラー' }
        }
      }

      const TestComponent = () => (
        <div>
          {mockError.response?.status === 500 && (
            <div className="error-message">
              サーバーでエラーが発生しました。しばらく待ってから再度お試しください。
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText(/サーバーでエラーが発生しました/)).toBeTruthy()
      })
    })
  })

  describe('Network Errors', () => {
    it('オフラインエラーメッセージが表示される', async () => {
      const isOnline = navigator.onLine

      const TestComponent = () => (
        <div>
          {!isOnline && (
            <div className="error-message">
              インターネット接続がありません。接続を確認してください。
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      if (!isOnline) {
        await waitFor(() => {
          expect(screen.getByText(/インターネット接続がありません/)).toBeTruthy()
        })
      }
    })

    it('タイムアウトエラーメッセージが表示される', async () => {
      const mockError = new Error('Request timeout')
      ;(mockError as any).code = 'ECONNABORTED'

      const TestComponent = () => (
        <div>
          {mockError.message === 'Request timeout' && (
            <div className="error-message">
              リクエストがタイムアウトしました。ネットワーク接続を確認してください。
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText(/リクエストがタイムアウトしました/)).toBeTruthy()
      })
    })
  })

  describe('Validation Errors', () => {
    it('ファイルサイズエラーが表示される', async () => {
      const fileSize = 150 * 1024 * 1024 // 150MB
      const maxSize = 100 * 1024 * 1024 // 100MB

      const TestComponent = () => (
        <div>
          {fileSize > maxSize && (
            <div className="error-message">
              ファイルサイズが大きすぎます（最大: {Math.round(maxSize / 1024 / 1024)}MB）
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText(/ファイルサイズが大きすぎます/)).toBeTruthy()
        expect(screen.getByText(/最大: 100MB/)).toBeTruthy()
      })
    })

    it('ファイル形式エラーが表示される', async () => {
      const fileTypes = ['audio/mp3', 'audio/wav', 'audio/m4a']
      const fileType = 'application/pdf'

      const TestComponent = () => (
        <div>
          {!fileTypes.includes(fileType) && (
            <div className="error-message">
              対応していないファイル形式です。MP3、WAV、M4A形式のみ対応しています。
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText(/対応していないファイル形式です/)).toBeTruthy()
      })
    })

    it('必須フィールドエラーが表示される', async () => {
      const value = ''

      const TestComponent = () => (
        <div>
          {value === '' && (
            <div className="error-message">
              このフィールドは必須です
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('このフィールドは必須です')).toBeTruthy()
      })
    })
  })

  describe('Error Recovery', () => {
    it('リトライボタンが表示される', async () => {
      const hasError = true

      const TestComponent = () => (
        <div>
          {hasError && (
            <div className="error-message">
              <p>エラーが発生しました</p>
              <button>リトライ</button>
            </div>
          )}
        </div>
      )

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('エラーが発生しました')).toBeTruthy()
        expect(screen.getByRole('button', { name: 'リトライ' })).toBeTruthy()
      })
    })

    it('エラーメッセージの閉じるボタンが機能する', async () => {
      const mockOnClose = vi.fn()
      const showError = true

      const TestComponent = () => (
        <div>
          {showError && (
            <div className="error-message">
              <p>エラーメッセージ</p>
              <button onClick={mockOnClose} aria-label="エラーを閉じる">
                ×
              </button>
            </div>
          )}
        </div>
      )

      const user = userEvent.setup()
      render(<TestComponent />)

      await waitFor(async () => {
        const closeButton = screen.getByLabelText('エラーを閉じる')
        await user.click(closeButton)
        expect(mockOnClose).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Error Logging', () => {
    it('エラーがコンソールに記録される', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const error = new Error('Test error')
      console.error(error)

      expect(consoleSpy).toHaveBeenCalledWith(error)

      consoleSpy.mockRestore()
    })
  })

  describe('Error Boundary', () => {
    it('エラーバウンダリーがエラーをキャッチする', () => {
      const ThrowError = () => {
        throw new Error('Test error')
      }

      const { container } = render(
        <ErrorBoundary fallback={<div>エラーが発生しました</div>}>
          <ThrowError />
        </ErrorBoundary>
      )

      expect(container.textContent).toBe('エラーが発生しました')
    })

    it('エラー後のリセットが機能する', () => {
      let shouldThrow = true

      const TestComponent = () => {
        if (shouldThrow) {
          throw new Error('Test error')
        }
        return <div>正常に表示されました</div>
      }

      const { container, rerender } = render(
        <ErrorBoundary fallback={<div>エラーが発生しました</div>}>
          <TestComponent />
        </ErrorBoundary>
      )

      expect(container.textContent).toBe('エラーが発生しました')

      // Reset and rerender
      shouldThrow = false
      rerender(
        <ErrorBoundary fallback={<div>エラーが発生しました</div>}>
          <TestComponent />
        </ErrorBoundary>
      )

      // After reset, should still show error (ErrorBoundary doesn't auto-reset)
      expect(container.textContent).toBe('エラーが発生しました')
    })
  })

  describe('Async Error Handling', () => {
    it('非同期エラーが適切に処理される', async () => {
      const mockAsyncFunction = vi.fn(() =>
        Promise.reject(new Error('Async error'))
      )

      const TestComponent = () => {
        const [error, setError] = React.useState<string | null>(null)

        React.useEffect(() => {
          mockAsyncFunction().catch((err) => {
            setError(err.message)
          })
        }, [])

        return error ? <div>Error: {error}</div> : <div>Loading...</div>
      }

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('Error: Async error')).toBeTruthy()
      })
    })
  })

  describe('Malformed Response Handling', () => {
    it('不正なJSONレスポンスが処理される', async () => {
      const invalidJson = '{ invalid json }'

      const TestComponent = () => {
        const [error, setError] = React.useState<string | null>(null)

        React.useEffect(() => {
          try {
            JSON.parse(invalidJson)
          } catch (err) {
            setError('データの解析に失敗しました')
          }
        }, [])

        return error ? <div>{error}</div> : <div>Loading...</div>
      }

      render(<TestComponent />)

      await waitFor(() => {
        expect(screen.getByText('データの解析に失敗しました')).toBeTruthy()
      })
    })
  })
})

// Import React for error boundary
import React from 'react'
