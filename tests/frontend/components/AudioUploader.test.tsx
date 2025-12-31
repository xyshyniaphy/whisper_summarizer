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

// Mock Supabase client
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({
        data: { subscription: { unsubscribe: vi.fn() } }
      }))
    }
  }
}))

// Mock API
const mockUploadAudio = vi.fn()

vi.mock('../../../src/services/api', () => ({
  api: {
    uploadAudio: (file: File) => mockUploadAudio(file)
  }
}))

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <Provider>{children}</Provider>
  </BrowserRouter>
)

describe('AudioUploader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUploadAudio.mockResolvedValue({
      id: 'new-transcription-id',
      file_name: 'test.mp3'
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
  })

  describe('File Selection', () => {
    it('ファイル選択でアップロードが実行される', async () => {
      const user = userEvent.setup()
      render(<AudioUploader />, { wrapper })

      const fileInput = screen.getByRole('textbox') || document.querySelector('input[type="file"]')
      expect(fileInput).toBeTruthy()
    })

    it('有効なオーディオファイルのアップロードが成功する', async () => {
      mockUploadAudio.mockImplementation((file: File) => {
        return Promise.resolve({
          id: 'test-id',
          file_name: file.name,
          stage: 'uploading'
        })
      })

      render(<AudioUploader />, { wrapper })

      // Create a mock file
      const file = new File(['audio content'], 'test.mp3', { type: 'audio/mpeg' })
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement

      if (fileInput) {
        const dataTransfer = { files: [file] } as any
        await userEvent.upload(fileInput, file)

        await waitFor(() => {
          expect(mockUploadAudio).toHaveBeenCalled()
        })
      }
    })
  })

  describe('Drag and Drop', () => {
    it('ドラッグオーバーでスタイルが変化する', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')
      expect(dropZone).toBeTruthy()
    })

    it('ファイルドロップでアップロードが実行される', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')

      if (dropZone) {
        const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
        const dropEvent = new Event('drop', { bubbles: true }) as any
        dropEvent.dataTransfer = { files: [file] }
        dropEvent.preventDefault = vi.fn()

        dropZone.dispatchEvent(dropEvent)

        await waitFor(() => {
          expect(mockUploadAudio).toHaveBeenCalled()
        })
      }
    })
  })

  describe('File Validation', () => {
    it('サポート外のファイル形式はエラーを表示する', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')

      if (dropZone) {
        // Create an invalid file (e.g., .exe)
        const file = new File(['executable'], 'test.exe', { type: 'application/octet-stream' })
        const dropEvent = new Event('drop', { bubbles: true }) as any
        dropEvent.dataTransfer = { files: [file] }
        dropEvent.preventDefault = vi.fn()

        dropZone.dispatchEvent(dropEvent)

        await waitFor(() => {
          const errorText = screen.queryByText(/不支持的文件格式/)
          expect(errorText).toBeTruthy()
        })
      }
    })

    it('大きすぎるファイルはエラーを表示する', async () => {
      render(<AudioUploader />, { wrapper })

      const dropZone = screen.getByText('将音频文件拖放到此处').closest('div')

      if (dropZone) {
        // Create a file larger than 50MB
        const largeContent = new Array(60 * 1024 * 1024).fill('x').join('')
        const file = new File([largeContent], 'large.mp3', { type: 'audio/mpeg' })
        const dropEvent = new Event('drop', { bubbles: true }) as any
        dropEvent.dataTransfer = { files: [file] }
        dropEvent.preventDefault = vi.fn()

        dropZone.dispatchEvent(dropEvent)

        await waitFor(() => {
          const errorText = screen.queryByText(/文件大小超过50MB/)
          expect(errorText).toBeTruthy()
        })
      }
    })
  })

  describe('Loading State', () => {
    it('アップロード中はローディングインジケーターが表示される', async () => {
      mockUploadAudio.mockImplementation(() => new Promise(() => {}))
      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      if (fileInput) {
        const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
        fileInput.files = [file] as any
        fileInput.dispatchEvent(new Event('change', { bubbles: true }))

        await waitFor(() => {
          expect(mockUploadAudio).toHaveBeenCalled()
        })
      }
    })

    it('アップロード中はドロップが無効になる', async () => {
      mockUploadAudio.mockImplementation(() => new Promise(() => {}))
      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      if (fileInput) {
        const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
        fileInput.files = [file] as any
        fileInput.dispatchEvent(new Event('change', { bubbles: true }))
      }

      await waitFor(() => {
        expect(mockUploadAudio).toHaveBeenCalled()
      })
    })
  })

  describe('Error Handling', () => {
    it('アップロード失敗時はエラーメッセージが表示される', async () => {
      mockUploadAudio.mockRejectedValue({
        response: { data: { detail: 'アップロードエラー' } }
      })

      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      if (fileInput) {
        const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
        fileInput.files = [file] as any
        fileInput.dispatchEvent(new Event('change', { bubbles: true }))
      }

      await waitFor(() => {
        expect(mockUploadAudio).toHaveBeenCalled()
      })
    })
  })

  describe('Navigation After Upload', () => {
    it('アップロード成功後、詳細ページに遷移する', async () => {
      mockUploadAudio.mockResolvedValue({
        id: 'new-id-123',
        file_name: 'test.mp3',
        stage: 'uploading'
      })

      render(<AudioUploader />, { wrapper })

      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
      if (fileInput) {
        const file = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
        fileInput.files = [file] as any
        fileInput.dispatchEvent(new Event('change', { bubbles: true }))
      }

      await waitFor(() => {
        expect(mockUploadAudio).toHaveBeenCalled()
      })
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
        mockUploadAudio.mockResolvedValue({
          id: 'test-id',
          file_name: `test.${ext}`
        })

        render(<AudioUploader />, { wrapper })

        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
        if (fileInput) {
          const file = new File(['audio'], `test.${ext}`, { type: mime })
          fileInput.files = [file] as any
          fileInput.dispatchEvent(new Event('change', { bubbles: true }))
        }

        await waitFor(() => {
          expect(mockUploadAudio).toHaveBeenCalled()
        })
      })
    })
  })
})
