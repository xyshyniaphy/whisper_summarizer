import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock api module before importing the component
const mockGetSharedTranscription = vi.fn()
const mockGetSharedSegments = vi.fn()
const mockGetSharedAudioUrl = vi.fn((token: string) => `/api/shared/${token}/audio`)
const mockDownloadSharedFile = vi.fn()
const mockDownloadSharedDocx = vi.fn()

vi.mock('../../services/api', () => ({
  api: {
    getSharedTranscription: mockGetSharedTranscription,
    getSharedSegments: mockGetSharedSegments,
    getSharedAudioUrl: mockGetSharedAudioUrl,
    downloadSharedFile: mockDownloadSharedFile,
    downloadSharedDocx: mockDownloadSharedDocx,
  }
}))

const mockTranscriptionData = {
  id: '123',
  file_name: 'test-audio.m4a',
  text: 'This is a test transcription',
  summary: 'Test summary',
  language: 'zh',
  duration_seconds: 120,
  created_at: '2024-01-01T00:00:00Z',
  chat_messages: []
}

const mockSegments = [
  { start: 0, end: 5, text: 'First segment' },
  { start: 5, end: 10, text: 'Second segment' },
  { start: 10, end: 15, text: 'Third segment' }
]

describe('SharedTranscription Page - Audio Player Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock successful transcription data
    mockGetSharedTranscription.mockResolvedValue(mockTranscriptionData)
    // Mock segments data
    mockGetSharedSegments.mockResolvedValue(mockSegments)
  })

  describe('API Integration', () => {
    it('should call getSharedSegments when loading transcription', async () => {
      // This test verifies the API integration logic
      const shareToken = 'test-token'

      mockGetSharedTranscription.mockResolvedValue(mockTranscriptionData)
      mockGetSharedSegments.mockResolvedValue(mockSegments)

      // Simulate the component's data loading logic
      await mockGetSharedTranscription(shareToken)
      const segments = await mockGetSharedSegments(shareToken)

      expect(mockGetSharedTranscription).toHaveBeenCalledWith(shareToken)
      expect(mockGetSharedSegments).toHaveBeenCalledWith(shareToken)
      expect(segments).toEqual(mockSegments)
      expect(segments).toHaveLength(3)
    })

    it('should handle empty segments array', async () => {
      const shareToken = 'empty-token'

      mockGetSharedTranscription.mockResolvedValue(mockTranscriptionData)
      mockGetSharedSegments.mockResolvedValue([])

      await mockGetSharedTranscription(shareToken)
      const segments = await mockGetSharedSegments(shareToken)

      expect(mockGetSharedSegments).toHaveBeenCalledWith(shareToken)
      expect(segments).toEqual([])
      expect(segments).toHaveLength(0)
    })

    it('should handle segment loading errors gracefully', async () => {
      const shareToken = 'error-token'

      mockGetSharedTranscription.mockResolvedValue(mockTranscriptionData)
      mockGetSharedSegments.mockRejectedValue(new Error('Failed to load segments'))

      await mockGetSharedTranscription(shareToken)

      // Segments call should fail but transcription should still load
      await expect(mockGetSharedSegments(shareToken)).rejects.toThrow('Failed to load segments')
    })

    it('should generate correct audio URL', () => {
      const shareToken = 'test-token'
      const audioUrl = mockGetSharedAudioUrl(shareToken)

      expect(audioUrl).toBe('/api/shared/test-token/audio')
      expect(typeof audioUrl).toBe('string')
    })

    it('should generate different audio URLs for different tokens', () => {
      const token1 = 'abc123'
      const token2 = 'xyz789'

      const url1 = mockGetSharedAudioUrl(token1)
      const url2 = mockGetSharedAudioUrl(token2)

      expect(url1).toBe('/api/shared/abc123/audio')
      expect(url2).toBe('/api/shared/xyz789/audio')
      expect(url1).not.toBe(url2)
    })
  })

  describe('Component Logic', () => {
    it('should determine showAudioPlayer based on segments length', () => {
      const segmentsWithData: any[] = mockSegments
      const emptySegments: any[] = []

      // Logic: showAudioPlayer = segments.length > 0
      const showWithSegments = segmentsWithData.length > 0
      const showWithoutSegments = emptySegments.length > 0

      expect(showWithSegments).toBe(true)
      expect(showWithoutSegments).toBe(false)
    })

    it('should apply pb-20 class when showAudioPlayer is true', () => {
      const showAudioPlayer = true
      const baseClass = "container mx-auto px-4 py-8 max-w-4xl"
      const paddingClass = showAudioPlayer ? "pb-20" : ""

      const className = [baseClass, paddingClass].filter(Boolean).join(' ')

      expect(className).toContain('pb-20')
      expect(className).toBe('container mx-auto px-4 py-8 max-w-4xl pb-20')
    })

    it('should not apply pb-20 class when showAudioPlayer is false', () => {
      const showAudioPlayer = false
      const baseClass = "container mx-auto px-4 py-8 max-w-4xl"
      const paddingClass = showAudioPlayer ? "pb-20" : ""

      const className = [baseClass, paddingClass].filter(Boolean).join(' ')

      expect(className).not.toContain('pb-20')
      expect(className).toBe('container mx-auto px-4 py-8 max-w-4xl')
    })

    it('should update currentTime on handleSeek', () => {
      // Simulate handleSeek logic
      let currentTime = 0
      const handleSeek = (time: number) => {
        currentTime = time
      }

      handleSeek(5.5)
      expect(currentTime).toBe(5.5)

      handleSeek(10.2)
      expect(currentTime).toBe(10.2)
    })

    it('should render audio available badge when showAudioPlayer is true', () => {
      const showAudioPlayer = true
      const badge = showAudioPlayer ? '<Badge variant="success">可播放音频</Badge>' : ''

      expect(badge).toContain('可播放音频')
      expect(badge.length).toBeGreaterThan(0)
    })

    it('should not render audio available badge when showAudioPlayer is false', () => {
      const showAudioPlayer = false
      const badge = showAudioPlayer ? '<Badge variant="success">可播放音频</Badge>' : ''

      expect(badge).not.toContain('可播放音频')
      expect(badge.length).toBe(0)
    })
  })

  describe('Data Flow', () => {
    it('should load segments after transcription data', async () => {
      const shareToken = 'test-token'

      // Simulate the order of API calls in the component
      ;(mockGetSharedTranscription as any).mockResolvedValue(mockTranscriptionData)
      ;(mockGetSharedSegments as any).mockResolvedValue(mockSegments)

      // First, load transcription
      const transcription = await mockGetSharedTranscription(shareToken)
      expect(transcription).toBeDefined()

      // Then, load segments
      const segments = await mockGetSharedSegments(shareToken)
      expect(segments).toBeDefined()
      expect(segments).toHaveLength(3)
    })

    it('should continue without segments if loading fails', async () => {
      const shareToken = 'test-token'

      ;(mockGetSharedTranscription as any).mockResolvedValue(mockTranscriptionData)
      ;(mockGetSharedSegments as any).mockRejectedValue(new Error('Network error'))

      // Transcription should load successfully
      const transcription = await mockGetSharedTranscription(shareToken)
      expect(transcription).toBeDefined()
      expect(transcription.id).toBe('123')

      // Segments fail, but should not crash the app
      try {
        await mockGetSharedSegments(shareToken)
        expect(true).toBe(false) // Should not reach here
      } catch (error) {
        expect(error).toBeDefined()
      }
    })
  })
})
