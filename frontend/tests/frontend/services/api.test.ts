/**
 * APIサービスのテスト
 *
 * apiモジュールの関数をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../../../src/services/api'

// Import global mock functions from setup.ts
declare global {
  var mockAxiosGet: any
  var mockAxiosPost: any
  var mockAxiosDelete: any
  var mockAxiosPut: any
  var mockAxiosPatch: any
}

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Reset mocks to default return values
    global.mockAxiosGet.mockResolvedValue({ data: [] })
    global.mockAxiosPost.mockResolvedValue({ data: {} })
    global.mockAxiosPut.mockResolvedValue({ data: {} })
    global.mockAxiosDelete.mockResolvedValue({ data: {} })
    global.mockAxiosPatch.mockResolvedValue({ data: {} })

    // Mock window.location
    delete (window as any).location
    window.location = { href: '' } as any
  })

  describe('uploadAudio', () => {
    it('オーディオファイルをアップロードできる', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      global.mockAxiosPost.mockResolvedValue({ data: mockTranscription })

      const result = await api.uploadAudio(mockFile)
      expect(result).toEqual(mockTranscription)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/audio/upload', expect.any(FormData), {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })

    it('FormDataとして送信される', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })

      await api.uploadAudio(mockFile)

      expect(global.mockAxiosPost).toHaveBeenCalledWith('/audio/upload', expect.any(FormData), {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    })
  })

  describe('getTranscriptions', () => {
    it('転写リストを取得できる', async () => {
      const mockResponse = {
        data: [
          { id: '1', file_name: 'test1.mp3' },
          { id: '2', file_name: 'test2.mp3' }
        ],
        total: 2,
        page: 1,
        page_size: 10,
        total_pages: 1
      }

      global.mockAxiosGet.mockResolvedValue({ data: mockResponse })

      const result = await api.getTranscriptions()
      expect(result).toEqual(mockResponse)
    })

    it('正しいエンドポイントを呼び出す', async () => {
      global.mockAxiosGet.mockResolvedValue({
        data: {
          data: [],
          total: 0,
          page: 1,
          page_size: 10,
          total_pages: 0
        }
      })

      await api.getTranscriptions()

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions', expect.any(Object))
    })
  })

  describe('getTranscription', () => {
    it('単一の転写を取得できる', async () => {
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      global.mockAxiosGet.mockResolvedValue({ data: mockTranscription })

      const result = await api.getTranscription('123')
      expect(result).toEqual(mockTranscription)
    })

    it('IDを含む正しいエンドポイントを呼び出す', async () => {
      global.mockAxiosGet.mockResolvedValue({ data: { id: '123' } })

      await api.getTranscription('123')

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('deleteTranscription', () => {
    it('転写を削除できる', async () => {
      global.mockAxiosDelete.mockResolvedValue({})

      await api.deleteTranscription('123')

      expect(global.mockAxiosDelete).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('deleteAllTranscriptions', () => {
    it('全転写を削除できる', async () => {
      const mockResponse = { deleted_count: 5, message: 'Deleted 5 transcriptions' }
      global.mockAxiosDelete.mockResolvedValue({ data: mockResponse })

      const result = await api.deleteAllTranscriptions()

      expect(result).toEqual(mockResponse)
      expect(global.mockAxiosDelete).toHaveBeenCalledWith('/transcriptions/all')
    })
  })

  describe('getDownloadUrl', () => {
    it('TXTダウンロードURLを生成できる', () => {
      const url = api.getDownloadUrl('123', 'txt')
      expect(url).toBe('/api/transcriptions/123/download?format=txt')
    })

    it('SRTダウンロードURLを生成できる', () => {
      const url = api.getDownloadUrl('123', 'srt')
      expect(url).toBe('/api/transcriptions/123/download?format=srt')
    })
  })

  describe('downloadFile', () => {
    it('ファイルをダウンロードできる', async () => {
      const mockBlob = new Blob(['test content'])
      global.mockAxiosGet.mockResolvedValue({ data: mockBlob })

      const result = await api.downloadFile('123', 'txt')

      expect(result).toEqual(mockBlob)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/download?format=txt', {
        responseType: 'blob'
      })
    })
  })

  describe('downloadSummaryDocx', () => {
    it('要約DOCXファイルをダウンロードできる', async () => {
      const mockBlob = new Blob(['docx content'])
      global.mockAxiosGet.mockResolvedValue({ data: mockBlob })

      const result = await api.downloadSummaryDocx('123')

      expect(result).toEqual(mockBlob)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/download-docx', {
        responseType: 'blob'
      })
    })
  })

  describe('downloadNotebookLMGuideline', () => {
    it('NotebookLMガイドラインをダウンロードできる', async () => {
      const mockBlob = new Blob(['notebooklm content'])
      global.mockAxiosGet.mockResolvedValue({ data: mockBlob })

      const result = await api.downloadNotebookLMGuideline('123')

      expect(result).toEqual(mockBlob)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/download-notebooklm', {
        responseType: 'blob'
      })
    })
  })

  describe('Chat endpoints', () => {
    it('チャット履歴を取得できる', async () => {
      const mockMessages = {
        messages: [
          { id: '1', role: 'user', content: 'Hello', created_at: '2024-01-01T00:00:00Z' },
          { id: '2', role: 'assistant', content: 'Hi there!', created_at: '2024-01-01T00:00:01Z' }
        ]
      }
      global.mockAxiosGet.mockResolvedValue({ data: mockMessages })

      const result = await api.getChatHistory('123')

      expect(result).toEqual(mockMessages)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/chat')
    })

    it('チャットメッセージを送信できる', async () => {
      const mockResponse = {
        id: 'msg-1',
        role: 'assistant',
        content: 'Response',
        created_at: '2024-01-01T00:00:00Z'
      }
      global.mockAxiosPost.mockResolvedValue({ data: mockResponse })

      const result = await api.sendChatMessage('123', 'Hello')

      expect(result).toEqual(mockResponse)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/transcriptions/123/chat', { content: 'Hello' })
    })
  })

  describe('Share endpoints', () => {
    it('共有リンクを作成できる', async () => {
      const mockShare = {
        id: 'share-1',
        transcription_id: '123',
        share_token: 'abc123',
        share_url: 'https://example.com/shared/abc123',
        created_at: '2024-01-01T00:00:00Z',
        access_count: 0
      }
      global.mockAxiosPost.mockResolvedValue({ data: mockShare })

      const result = await api.createShareLink('123')

      expect(result).toEqual(mockShare)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/transcriptions/123/share')
    })

    it('共有された転写を取得できる', async () => {
      const mockTranscription = {
        id: '123',
        file_name: 'test.mp3',
        text: 'Test transcription',
        summary: 'Test summary',
        language: 'zh',
        duration_seconds: 120,
        created_at: '2024-01-01T00:00:00Z'
      }

      // Use axios directly for this endpoint (not apiClient)
      const axios = (await import('axios')).default
      vi.mocked(axios.get).mockResolvedValue({ data: mockTranscription })

      const result = await api.getSharedTranscription('abc123')

      expect(result).toEqual(mockTranscription)
    })
  })

  describe('Channel endpoints', () => {
    it('転写のチャンネルを取得できる', async () => {
      const mockChannels = [
        { id: 'ch-1', name: 'Channel 1', description: 'Test channel' }
      ]
      global.mockAxiosGet.mockResolvedValue({ data: mockChannels })

      const result = await api.getTranscriptionChannels('123')

      expect(result).toEqual(mockChannels)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/channels')
    })

    it('転写をチャンネルに割り当てることができる', async () => {
      const mockResponse = {
        message: 'Assigned to channels',
        channel_ids: ['ch-1', 'ch-2']
      }
      global.mockAxiosPost.mockResolvedValue({ data: mockResponse })

      const result = await api.assignTranscriptionToChannels('123', ['ch-1', 'ch-2'])

      expect(result).toEqual(mockResponse)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/transcriptions/123/channels', {
        channel_ids: ['ch-1', 'ch-2']
      })
    })
  })
})
