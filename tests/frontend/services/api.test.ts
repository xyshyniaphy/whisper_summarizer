/**
 * APIサービスのテスト
 *
 * apiモジュールの関数をテストする。
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../../../src/services/api'

// Import global mock functions from setup.ts
declare global {
  // eslint-disable-next-line no-var
  var mockAxiosGet: any
  // eslint-disable-next-line no-var
  var mockAxiosPost: any
  // eslint-disable-next-line no-var
  var mockAxiosDelete: any
  // eslint-disable-next-line no-var
  var mockAxiosPut: any
  // eslint-disable-next-line no-var
  var mockAxiosPatch: any
}

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Reset mocks to default return values
    global.mockAxiosGet.mockResolvedValue({ data: [] })
    global.mockAxiosPost.mockResolvedValue({ data: {} })
    global.mockAxiosDelete.mockResolvedValue({ data: {} })
    global.mockAxiosPut.mockResolvedValue({ data: {} })
    global.mockAxiosPatch.mockResolvedValue({ data: {} })

    // Mock window.location
    delete (window as any).location
    window.location = { href: '' } as any
  })

  describe('uploadAudio', () => {
    it('オーディオファイルをアップロードできる', async () => {
      const mockFile = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' })
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      global.mockAxiosPost.mockResolvedValueOnce({ data: mockTranscription })

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
      const mockTranscriptions = {
        items: [
          { id: '1', file_name: 'test1.mp3' },
          { id: '2', file_name: 'test2.mp3' }
        ],
        total: 2,
        page: 1,
        page_size: 10
      }

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockTranscriptions })

      const result = await api.getTranscriptions()
      expect(result).toEqual(mockTranscriptions)
    })

    it('正しいエンドポイントを呼び出す', async () => {
      global.mockAxiosGet.mockResolvedValueOnce({ data: { items: [], total: 0, page: 1, page_size: 10 } })

      await api.getTranscriptions()

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions', expect.any(Object))
    })

    it('ページパラメータを渡せる', async () => {
      global.mockAxiosGet.mockResolvedValueOnce({ data: { items: [], total: 0, page: 2, page_size: 10 } })

      await api.getTranscriptions(2)

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions', expect.objectContaining({
        params: expect.objectContaining({ page: 2 })
      }))
    })

    it('page_sizeパラメータを渡せる', async () => {
      global.mockAxiosGet.mockResolvedValueOnce({ data: { items: [], total: 0, page: 1, page_size: 20 } })

      await api.getTranscriptions(1, 20)

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions', expect.objectContaining({
        params: expect.objectContaining({ page_size: 20 })
      }))
    })

    it('channel_idパラメータを渡せる', async () => {
      global.mockAxiosGet.mockResolvedValueOnce({ data: { items: [], total: 0, page: 1, page_size: 10 } })

      await api.getTranscriptions(1, undefined, 'channel-123')

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions', expect.objectContaining({
        params: expect.objectContaining({ channel_id: 'channel-123' })
      }))
    })
  })

  describe('getTranscription', () => {
    it('単一の転写を取得できる', async () => {
      const mockTranscription = { id: '123', file_name: 'test.mp3' }

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockTranscription })

      const result = await api.getTranscription('123')
      expect(result).toEqual(mockTranscription)
    })

    it('IDを含む正しいエンドポイントを呼び出す', async () => {
      global.mockAxiosGet.mockResolvedValueOnce({ data: { id: '123' } })

      await api.getTranscription('123')

      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('deleteTranscription', () => {
    it('転写を削除できる', async () => {
      global.mockAxiosDelete.mockResolvedValueOnce({})

      await api.deleteTranscription('123')

      expect(global.mockAxiosDelete).toHaveBeenCalledWith('/transcriptions/123')
    })
  })

  describe('deleteAllTranscriptions', () => {
    it('全ての転写を削除できる', async () => {
      const mockResponse = { deleted_count: 5, message: 'Deleted 5 transcriptions' }
      global.mockAxiosDelete.mockResolvedValueOnce({ data: mockResponse })

      const result = await api.deleteAllTranscriptions()

      expect(result).toEqual(mockResponse)
      expect(global.mockAxiosDelete).toHaveBeenCalledWith('/transcriptions/all')
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

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockBlob })

      const result = await api.downloadFile('123', 'txt')

      expect(result).toEqual(mockBlob)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/download?format=txt', {
        responseType: 'blob'
      })
    })
  })

  describe('downloadSummaryDocx', () => {
    it('要約をDOCXとしてダウンロードできる', async () => {
      const mockBlob = new Blob(['docx content'])

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockBlob })

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

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockBlob })

      const result = await api.downloadNotebookLMGuideline('123')

      expect(result).toEqual(mockBlob)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/123/download-notebooklm', {
        responseType: 'blob'
      })
    })
  })

  describe('getChatHistory', () => {
    it('チャット履歴を取得できる', async () => {
      const mockHistory = {
        messages: [
          { id: '1', role: 'user' as const, content: 'Hello', created_at: '2024-01-01' },
          { id: '2', role: 'assistant' as const, content: 'Hi there!', created_at: '2024-01-01' }
        ]
      }

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockHistory })

      const result = await api.getChatHistory('transcription-123')

      expect(result).toEqual(mockHistory)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/transcription-123/chat')
    })
  })

  describe('sendChatMessage', () => {
    it('チャットメッセージを送信できる', async () => {
      const mockMessage = {
        id: '1',
        role: 'assistant' as const,
        content: 'Response message',
        created_at: '2024-01-01'
      }

      global.mockAxiosPost.mockResolvedValueOnce({ data: mockMessage })

      const result = await api.sendChatMessage('transcription-123', 'Test message')

      expect(result).toEqual(mockMessage)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/transcriptions/transcription-123/chat', {
        content: 'Test message'
      })
    })
  })

  describe('createShareLink', () => {
    it('共有リンクを作成できる', async () => {
      const mockShareLink = {
        id: 'share-123',
        transcription_id: 'transcription-123',
        share_token: 'abc123',
        share_url: 'https://example.com/share/abc123',
        created_at: '2024-01-01',
        access_count: 0
      }

      global.mockAxiosPost.mockResolvedValueOnce({ data: mockShareLink })

      const result = await api.createShareLink('transcription-123')

      expect(result).toEqual(mockShareLink)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/transcriptions/transcription-123/share')
    })
  })

  describe('getTranscriptionChannels', () => {
    it('転写のチャンネルを取得できる', async () => {
      const mockChannels = [
        { id: '1', name: 'Channel 1', description: 'First channel' },
        { id: '2', name: 'Channel 2', description: 'Second channel' }
      ]

      global.mockAxiosGet.mockResolvedValueOnce({ data: mockChannels })

      const result = await api.getTranscriptionChannels('transcription-123')

      expect(result).toEqual(mockChannels)
      expect(global.mockAxiosGet).toHaveBeenCalledWith('/transcriptions/transcription-123/channels')
    })
  })

  describe('assignTranscriptionToChannels', () => {
    it('転写をチャンネルに割り当てられる', async () => {
      const mockResponse = {
        message: 'Assigned to channels',
        channel_ids: ['channel-1', 'channel-2']
      }

      global.mockAxiosPost.mockResolvedValueOnce({ data: mockResponse })

      const result = await api.assignTranscriptionToChannels('transcription-123', ['channel-1', 'channel-2'])

      expect(result).toEqual(mockResponse)
      expect(global.mockAxiosPost).toHaveBeenCalledWith('/transcriptions/transcription-123/channels', {
        channel_ids: ['channel-1', 'channel-2']
      })
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
                    value: encoder.encode('data: ' + JSON.stringify({ content: chunk, done: false }) + '\n\n')
                  }
                } else {
                  return { done: true, value: new Uint8Array() }
                }
              },
              releaseLock: vi.fn()
            })
          }
        } as Response)
      ) as any

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
                  value: encoder.encode('data: ' + JSON.stringify({ error: 'API error', done: true }) + '\n\n')
                }
              },
              releaseLock: vi.fn()
            })
          }
        } as Response)
      ) as any

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
      ) as any

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
      ) as any

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
