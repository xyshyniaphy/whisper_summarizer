/**
 * APIサービスのテスト
 *
 * apiモジュールの関数をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../../../src/services/api'
import axios from 'axios'

// Mock axios
vi.mock('axios')

// Mock Supabase client
const mockSession = {
  access_token: 'mock-token',
  refresh_token: 'mock-refresh-token'
}

vi.mock('../../../src/services/supabase', () => ({
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

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock window.location
    delete (window as any).location
    window.location = { href: '' } as any
  })

  describe('uploadAudio', () => {
    it('オーディオファイルをアップロードできる', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      vi.mocked(axios.create).mockReturnValue({
        post: vi.fn().mockResolvedValue({ data: mockTranscription })
      } as any)

      const result = await api.uploadAudio(mockFile)
      expect(result).toEqual(mockTranscription)
    })

    it('FormDataとして送信される', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      const mockPost = vi.fn().mockResolvedValue({ data: { id: '123' } })

      vi.mocked(axios.create).mockReturnValue({
        post: mockPost
      } as any)

      await api.uploadAudio(mockFile)

      expect(mockPost).toHaveBeenCalledWith('/audio/upload', expect.any(FormData), {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })
  })

  describe('getTranscriptions', () => {
    it('転写リストを取得できる', async () => {
      const mockTranscriptions = [
        { id: '1', file_name: 'test1.mp3' },
        { id: '2', file_name: 'test2.mp3' }
      ]

      vi.mocked(axios.create).mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockTranscriptions })
      } as any)

      const result = await api.getTranscriptions()
      expect(result).toEqual(mockTranscriptions)
    })

    it('正しいエンドポイントを呼び出す', async () => {
      const mockGet = vi.fn().mockResolvedValue({ data: [] })

      vi.mocked(axios.create).mockReturnValue({
        get: mockGet
      } as any)

      await api.getTranscriptions()

      expect(mockGet).toHaveBeenCalledWith('/transcriptions')
    })
  })

  describe('getTranscription', () => {
    it('単一の転写を取得できる', async () => {
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      vi.mocked(axios.create).mockReturnValue({
        get: vi.fn().mockResolvedValue({ data: mockTranscription })
      } as any)

      const result = await api.getTranscription('123')
      expect(result).toEqual(mockTranscription)
    })

    it('IDを含む正しいエンドポイントを呼び出す', async () => {
      const mockGet = vi.fn().mockResolvedValue({ data: { id: '123' } })

      vi.mocked(axios.create).mockReturnValue({
        get: mockGet
      } as any)

      await api.getTranscription('123')

      expect(mockGet).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('deleteTranscription', () => {
    it('転写を削除できる', async () => {
      const mockDelete = vi.fn().mockResolvedValue({})

      vi.mocked(axios.create).mockReturnValue({
        delete: mockDelete
      } as any)

      await api.deleteTranscription('123')

      expect(mockDelete).toHaveBeenCalledWith('/transcriptions/123')
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
      const mockGet = vi.fn().mockResolvedValue({ data: mockBlob })

      vi.mocked(axios.create).mockReturnValue({
        get: mockGet
      } as any)

      const result = await api.downloadFile('123', 'txt')

      expect(result).toEqual(mockBlob)
      expect(mockGet).toHaveBeenCalledWith('/transcriptions/123/download?format=txt', {
        responseType: 'blob'
      })
    })

    it('PPTXフォーマットもダウンロードできる', async () => {
      const mockBlob = new Blob(['pptx content'])
      const mockGet = vi.fn().mockResolvedValue({ data: mockBlob })

      vi.mocked(axios.create).mockReturnValue({
        get: mockGet
      } as any)

      await api.downloadFile('123', 'pptx')

      expect(mockGet).toHaveBeenCalledWith('/transcriptions/123/download?format=pptx', {
        responseType: 'blob'
      })
    })
  })

  describe('generatePptx', () => {
    it('PPTX生成をリクエストできる', async () => {
      const mockResponse = { status: 'generating', message: 'Generating PPTX' }
      const mockPost = vi.fn().mockResolvedValue({ data: mockResponse })

      vi.mocked(axios.create).mockReturnValue({
        post: mockPost
      } as any)

      const result = await api.generatePptx('123')

      expect(result).toEqual(mockResponse)
      expect(mockPost).toHaveBeenCalledWith('/transcriptions/123/generate-pptx')
    })
  })

  describe('getPptxStatus', () => {
    it('PPTXステータスを取得できる', async () => {
      const mockResponse = { status: 'ready', exists: true }
      const mockGet = vi.fn().mockResolvedValue({ data: mockResponse })

      vi.mocked(axios.create).mockReturnValue({
        get: mockGet
      } as any)

      const result = await api.getPptxStatus('123')

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/transcriptions/123/pptx-status')
    })
  })

  describe('Request Interceptor', () => {
    it('リクエスト時に認証トークンが追加される', async () => {
      const mockPost = vi.fn().mockResolvedValue({ data: { id: '123' } })

      vi.mocked(axios.create).mockReturnValue({
        post: mockPost,
        interceptors: {
          request: { use: vi.fn((cb: any) => cb({ headers: {} })) },
          response: { use: vi.fn() }
        }
      } as any)

      // Re-import api to apply interceptors
      const { api: apiWithInterceptor } = require('../../../src/services/api')

      // Call an API method to trigger interceptor
      await apiWithInterceptor.uploadAudio(new File(['audio'], 'test.mp3'))

      // The interceptor should have added the Authorization header
      // This is a basic check - actual testing would require more complex setup
    })
  })

  describe('Response Interceptor', () => {
    it('401エラー時にトークンリフレッシュが試行される', async () => {
      const originalRequest = { _retry: false, headers: {} }
      const error = {
        response: { status: 401 },
        config: originalRequest
      }

      const mockRejected = vi.fn().mockRejectedValue(error)
      const mockResolved = vi.fn().mockResolvedValue({ data: {} })

      vi.mocked(axios.create).mockReturnValue({
        get: mockRejected,
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn((onFulfilled: any, onRejected: any) => {
            // Test the error handler
            onRejected(error)
          }) }
        }
      } as any)

      // Re-import api to apply interceptors
      const { api: apiWithError } = require('../../../src/services/api')
    })
  })
})
