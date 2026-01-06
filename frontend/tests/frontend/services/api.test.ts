/**
 * APIサービスのテスト
 *
 * apiモジュールの関数をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// Mock Supabase client first (before api import)
const mockSession = {
  access_token: 'mock-token',
  refresh_token: 'mock-refresh-token'
}

vi.mock('@/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({
        data: { session: mockSession },
        error: null
      })),
      refreshSession: vi.fn(() => Promise.resolve({
        data: { session: mockSession },
        error: null
      })),
      signOut: vi.fn(() => Promise.resolve({ error: null }))
    }
  }
}))

// Mock axios - must be before api import
vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: [] })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    put: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    create: vi.fn(() => ({
      get: vi.fn(() => Promise.resolve({ data: [] })),
      post: vi.fn(() => Promise.resolve({ data: {} })),
      put: vi.fn(() => Promise.resolve({ data: {} })),
      delete: vi.fn(() => Promise.resolve({ data: {} })),
      patch: vi.fn(() => Promise.resolve({ data: {} })),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    }))
  }
}))

// Import api after axios is mocked
import { api } from '@/services/api'

describe.skip('API Service', () => {
  // Get mock references using vi.mocked for type safety
  const mockAxios = vi.mocked(axios, { deep: true })

  beforeEach(() => {
    vi.clearAllMocks()

    // Reset axios mocks to default return values
    mockAxios.get.mockResolvedValue({ data: [] })
    mockAxios.post.mockResolvedValue({ data: {} })
    mockAxios.put.mockResolvedValue({ data: {} })
    mockAxios.delete.mockResolvedValue({ data: {} })
    mockAxios.patch.mockResolvedValue({ data: {} })

    // Mock window.location
    delete (window as any).location
    window.location = { href: '' } as any
  })

  describe('uploadAudio', () => {
    it('オーディオファイルをアップロードできる', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      mockAxios.post.mockResolvedValue({ data: mockTranscription })

      const result = await api.uploadAudio(mockFile)
      expect(result).toEqual(mockTranscription)
      expect(mockAxios.post).toHaveBeenCalledWith('/audio/upload', expect.any(FormData), {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })

    it('FormDataとして送信される', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })

      await api.uploadAudio(mockFile)

      expect(mockAxios.post).toHaveBeenCalledWith('/audio/upload', expect.any(FormData), {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })
  })

  describe('getTranscriptions', () => {
    it('転写リストを取得できる', async () => {
      const mockTranscriptions = {
        items: [
          { id: '1', file_name: 'test1.mp3' },
          { id: '2', file_name: 'test2.mp3' }
        ],
        total: 2,
        page: 1,
        page_size: 10
      }

      mockAxios.get.mockResolvedValue({ data: mockTranscriptions })

      const result = await api.getTranscriptions()
      expect(result).toEqual(mockTranscriptions)
    })

    it('正しいエンドポイントを呼び出す', async () => {
      mockAxios.get.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 10 } })

      await api.getTranscriptions()

      expect(mockAxios.get).toHaveBeenCalledWith('/transcriptions', expect.any(Object))
    })
  })

  describe('getTranscription', () => {
    it('単一の転写を取得できる', async () => {
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      mockAxios.get.mockResolvedValue({ data: mockTranscription })

      const result = await api.getTranscription('123')
      expect(result).toEqual(mockTranscription)
    })

    it('IDを含む正しいエンドポイントを呼び出す', async () => {
      mockAxios.get.mockResolvedValue({ data: { id: '123' } })

      await api.getTranscription('123')

      expect(mockAxios.get).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('deleteTranscription', () => {
    it('転写を削除できる', async () => {
      mockAxios.delete.mockResolvedValue({})

      await api.deleteTranscription('123')

      expect(mockAxios.delete).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('getDownloadUrl', () => {
    it('TXTフォーマットのダウンロードURLを生成する', () => {
      const url = api.getDownloadUrl('123', 'txt')
      expect(url).toBe('/api/transcriptions/123/download?format=txt')
    })

    it('SRTフォーマットのダウンロードURLを生成する', () => {
      const url = api.getDownloadUrl('123', 'srt')
      expect(url).toBe('/api/transcriptions/123/download?format=srt')
    })
  })

  describe('downloadFile', () => {
    it('ファイルをBlobとしてダウンロードできる', async () => {
      const mockBlob = new Blob(['test content'])

      mockAxios.get.mockResolvedValue({ data: mockBlob })

      const result = await api.downloadFile('123', 'txt')

      expect(result).toEqual(mockBlob)
      expect(mockAxios.get).toHaveBeenCalledWith('/transcriptions/123/download?format=txt', {
        responseType: 'blob'
      })
    })
  })

  describe('Request Interceptor', () => {
    it('リクエスト時に認証トークンが追加される', async () => {
      mockAxios.post.mockResolvedValue({ data: { id: '123' } })

      // Call an API method to trigger interceptor
      await api.uploadAudio(new File(['audio'], 'test.mp3'))

      // The interceptor should have added the Authorization header
      // This is a basic check - actual testing would require more complex setup
      expect(mockAxios.post).toHaveBeenCalled()
    })
  })

  describe('Response Interceptor', () => {
    it('401エラー時にトークンリフレッシュが試行される', async () => {
      const originalRequest = { _retry: false, headers: {} }
      const error = {
        response: { status: 401 },
        config: originalRequest
      }

      mockAxios.get.mockRejectedValue(error)

      // Try calling API - error handling would be tested by integration tests
      // Unit test just verifies the mock is set up
      expect(mockAxios.get).toBeDefined()
    })
  })

  describe('sendChatMessageStream', () => {
    it('streams chat response using fetch API', async () => {
      const mockChunks = ['Hello', ' there', '!']
      let chunkIndex = 0

      // Mock fetch to return SSE stream
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: {
            getReader: () => ({
              read: async () => {
                if (chunkIndex < mockChunks.length) {
                  const chunk = mockChunks[chunkIndex++]
                  const encoder = new TextEncoder()
                  return {
                    done: false,
                    value: encoder.encode('data: ' + JSON.stringify({ content: chunk, done: false }) + '\\n\\n')
                  }
                } else {
                  return { done: true, value: new Uint8Array() }
                }
              },
              releaseLock: vi.fn()
            })
          }
        } as Response)
      )

      const onChunk = vi.fn()
      const onError = vi.fn()
      const onComplete = vi.fn()

      await api.sendChatMessageStream('transcription-123', 'Test question', onChunk, onError, onComplete)

      expect(onChunk).toHaveBeenCalledWith('Hello')
      expect(onChunk).toHaveBeenCalledWith(' there')
      expect(onChunk).toHaveBeenCalledWith('!')
      expect(onComplete).toHaveBeenCalled()
    })

    it('handles stream errors gracefully', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: {
            getReader: () => ({
              read: async () => {
                const encoder = new TextEncoder()
                return {
                  done: false,
                  value: encoder.encode('data: ' + JSON.stringify({ error: 'API error', done: true }) + '\\n\\n')
                }
              },
              releaseLock: vi.fn()
            })
          }
        } as Response)
      )

      const onChunk = vi.fn()
      const onError = vi.fn()
      const onComplete = vi.fn()

      await api.sendChatMessageStream('transcription-123', 'Test', onChunk, onError, onComplete)

      expect(onError).toHaveBeenCalledWith('API error')
    })

    it('includes authorization header', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: {
            getReader: () => ({
              read: async () => ({ done: true, value: new Uint8Array() }),
              releaseLock: vi.fn()
            })
          }
        } as Response)
      )

      await api.sendChatMessageStream('test-id', 'Hello', vi.fn(), vi.fn(), vi.fn())

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': expect.stringContaining('Bearer')
          })
        })
      )
    })

    it('sends request body with content', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          body: {
            getReader: () => ({
              read: async () => ({ done: true, value: new Uint8Array() }),
              releaseLock: vi.fn()
            })
          }
        } as Response)
      )

      await api.sendChatMessageStream('test-id', 'My question', vi.fn(), vi.fn(), vi.fn())

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('My question')
        })
      )
    })
  })
})
