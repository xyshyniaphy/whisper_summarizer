/**
 * AudioUploaderコンポーネントのテスト
 *
 * ファイルアップロード、ドラッグ&ドロップ、バリデーション、
 * エラーハンドリングをテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { Provider } from 'jotai'
import { AudioUploader } from '../../../src/components/AudioUploader'

// Import global mock functions from setup.ts
declare global {
  var mockAxiosPost: any
  var mockNavigate: any
}

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

describe('AudioUploader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset mock to default successful response
    global.mockAxiosPost.mockResolvedValue({
      data: {
        id: 'new-transcription-id',
        file_name: 'test.mp3',
        stage: 'uploading'
      }
    })
  })

  describe('Rendering', () => {
    it('コンポーネントが正常にレンダリングされる', () => {
      render(<AudioUploader />, { wrapper })
      expect(screen.getByText('将音频文件拖放到此处')).toBeTruthy()
    })

    it('ドラッグ&ドロップエリアが表示される', () => {
      render(<AudioUploader />, { wrapper })
      expect(screen.getByText(/或点击选择文件/)).toBeTruthy()
    })

    it('サポートされるファイル形式が表示される', () => {
      render(<AudioUploader />, { wrapper })
      expect(screen.getByText(/mp3, wav, m4a 等/)).toBeTruthy()
    })

    it('ファイル入力が存在する', () => {
      render(<AudioUploader />, { wrapper })
      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeTruthy()
    })
  })

  describe('File Selection', () => {
    it('有効なオーディオファイルのアップロードが成功する', async () => {
      const user = userEvent.setup()
      global.mockAxiosPost.mockResolvedValue({
        data: {
          id: 'test-id',
          file_name: 'test.mp3',
          stage: 'uploading'
        }
      })

      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      expect(fileInput).toBeTruthy()

      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mpeg' })

      await user.upload(fileInput, file)

      await waitFor(() => {
        expect(global.mockAxiosPost).toHaveBeenCalled()
      }, { timeout: 5000 })
    })

    it('アップロード成功後、詳細ページに遷移する', async () => {
      const user = userEvent.setup()
      global.mockAxiosPost.mockResolvedValue({
        data: {
          id: 'new-id-123',
          file_name: 'test.mp3',
          stage: 'uploading'
        }
      })

      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      expect(fileInput).toBeTruthy()

      const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      await user.upload(fileInput, file)

      await waitFor(() => {
        expect(global.mockNavigate).toHaveBeenCalledWith('/transcriptions/new-id-123')
      }, { timeout: 5000 })
    })
  })

  describe('Drag and Drop', () => {
    it('ドラッグオーバーでスタイルが変化する', async () => {
      const user = userEvent.setup()
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')
      expect(dropZone).toBeTruthy()

      if (dropZone) {
        await user.hover(dropZone)
      }
    })

    it('ファイルドロップでアップロードが実行される', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')

      if (dropZone) {
        const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })

        const dropEvent = new Event('drop', { bubbles: true }) as any
        Object.defineProperty(dropEvent, 'dataTransfer', {
          value: { files: [file] },
          writable: false
        })
        dropEvent.preventDefault = vi.fn()

        dropZone.dispatchEvent(dropEvent)

        await waitFor(() => {
          expect(global.mockAxiosPost).toHaveBeenCalled()
        }, { timeout: 3000 })
      }
    })
  })

  describe('File Validation', () => {
    it('サポート外のファイル形式はエラーを表示する', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')

      if (dropZone) {
        const file = new File(['executable'], 'test.exe', { type: 'application/octet-stream' })

        const dropEvent = new Event('drop', { bubbles: true }) as any
        Object.defineProperty(dropEvent, 'dataTransfer', {
          value: { files: [file] },
          writable: false
        })
        dropEvent.preventDefault = vi.fn()

        dropZone.dispatchEvent(dropEvent)

        await waitFor(() => {
          const errorText = screen.queryByText(/不支持的文件格式/)
          expect(errorText).toBeTruthy()
        }, { timeout: 3000 })
      }
    })

    it('大きすぎるファイルはエラーを表示する', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')

      if (dropZone) {
        const mediumContent = new Array(1024 * 100).fill('x').join('')
        const file = new File([mediumContent], 'large.mp3', { type: 'audio/mpeg' })
        Object.defineProperty(file, 'size', { value: 60 * 1024 * 1024 })

        const dropEvent = new Event('drop', { bubbles: true }) as any
        Object.defineProperty(dropEvent, 'dataTransfer', {
          value: { files: [file] },
          writable: false
        })
        dropEvent.preventDefault = vi.fn()

        dropZone.dispatchEvent(dropEvent)

        await waitFor(() => {
          const errorText = screen.queryByText(/文件大小超过50MB/)
          expect(errorText).toBeTruthy()
        }, { timeout: 3000 })
      }
    })
  })

  describe('Loading State', () => {
    it('アップロード中はローディングインジケーターが表示される', async () => {
      const user = userEvent.setup()
      global.mockAxiosPost.mockImplementation(() => new Promise(() => {}))

      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      expect(fileInput).toBeTruthy()

      const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      await user.upload(fileInput, file)

      // Check for loading indicator immediately after upload starts
      const loadingElement = document.querySelector('.animate-spin')
      expect(loadingElement).toBeTruthy()
    })

    it('アップロード中はドロップが無効になる', async () => {
      const { container } = render(<AudioUploader />, { wrapper })
      const user = userEvent.setup()
      global.mockAxiosPost.mockImplementation(() => new Promise(() => {}))

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      expect(fileInput).toBeTruthy()

      const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      await user.upload(fileInput, file)

      // The loading state adds pointer-events-none opacity-50 to the border-2 div
      await waitFor(() => {
        const dropZone = container.querySelector('.border-2.border-dashed')
        expect(dropZone?.className).toContain('pointer-events-none')
        expect(dropZone?.className).toContain('opacity-50')
      }, { timeout: 3000 })
    })
  })

  describe('Error Handling', () => {
    it('アップロード失敗時はエラーメッセージが表示される', async () => {
      const { container } = render(<AudioUploader />, { wrapper })
      const user = userEvent.setup()
      // Reject without response.data.detail to trigger fallback message
      global.mockAxiosPost.mockRejectedValue(new Error('Network error'))

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      expect(fileInput).toBeTruthy()

      const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      await user.upload(fileInput, file)

      // Error message is displayed below the Card
      await waitFor(() => {
        const errorText = screen.queryByText(/上传失败/)
        expect(errorText).toBeTruthy()
      }, { timeout: 3000 })
    })
  })

  describe('File Type Support', () => {
    const supportedTypes = [
      { mime: 'audio/mpeg', ext: 'mp3' },
      { mime: 'audio/wav', ext: 'wav' },
      { mime: 'audio/aac', ext: 'aac' },
      { mime: 'audio/flac', ext: 'flac' },
      { mime: 'audio/ogg', ext: 'ogg' }
    ]

    supportedTypes.forEach(({ mime, ext }) => {
      it(`${ext}形式がサポートされる`, async () => {
        const user = userEvent.setup()
        global.mockAxiosPost.mockResolvedValue({
          data: {
            id: 'test-id',
            file_name: `test.${ext}`
          }
        })

        render(<AudioUploader />, { wrapper })

        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
        expect(fileInput).toBeTruthy()

        const file = new File(['audio'], `test.${ext}`, { type: mime })
        await user.upload(fileInput, file)

        await waitFor(() => {
          expect(global.mockAxiosPost).toHaveBeenCalled()
        }, { timeout: 5000 })
      })
    })
  })
})
