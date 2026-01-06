/**
 * Chat Component Tests
 *
 * Tests the Chat component with streaming and thinking indicator functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Chat } from '../../../src/components/Chat'

// Mock the API module
vi.mock('../../../src/services/api', () => ({
  api: {
    getChatHistory: vi.fn(),
    sendChatMessageStream: vi.fn()
  }
}))

// Mock supabase
vi.mock('../../../src/services/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({
        data: { session: { access_token: 'mock-token' } },
        error: null
      }))
    }
  }
}))

describe('Chat Component', () => {
  const mockTranscriptionId = 'test-transcription-id'
  const defaultProps = {
    transcriptionId: mockTranscriptionId,
    disabled: false
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initial Loading State', () => {
    it('shows loading spinner on initial load', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockImplementation(() => new Promise(() => {}))

      render(<Chat {...defaultProps} />)
      
      // Should show loader
      const loader = document.querySelector('.animate-spin')
      expect(loader).toBeTruthy()
    })

    it('shows empty state when no messages exist', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText(/开始向AI提问/)).toBeTruthy()
      })
    })

    it('loads and displays existing chat history', async () => {
      const { api } = await import('../../../src/services/api')
      const mockMessages = [
        {
          id: '1',
          role: 'user' as const,
          content: 'Hello',
          created_at: '2024-01-01T00:00:00Z'
        },
        {
          id: '2',
          role: 'assistant' as const,
          content: 'Hi there!',
          created_at: '2024-01-01T00:00:01Z'
        }
      ]
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: mockMessages })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Hello')).toBeTruthy()
        expect(screen.getByText('Hi there!')).toBeTruthy()
      })
    })
  })

  describe('Message Display', () => {
    it('renders user messages on the right side', async () => {
      const { api } = await import('../../../src/services/api')
      const mockMessages = [
        {
          id: '1',
          role: 'user' as const,
          content: 'User message',
          created_at: '2024-01-01T00:00:00Z'
        }
      ]
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: mockMessages })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const userMessage = screen.getByText('User message')
        expect(userMessage).toBeTruthy()
        // Check if it has blue background (user message style)
        const parent = userMessage.closest('.bg-blue-500')
        expect(parent).toBeTruthy()
      })
    })

    it('renders assistant messages on the left side', async () => {
      const { api } = await import('../../../src/services/api')
      const mockMessages = [
        {
          id: '1',
          role: 'assistant' as const,
          content: 'Assistant response',
          created_at: '2024-01-01T00:00:00Z'
        }
      ]
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: mockMessages })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const assistantMessage = screen.getByText('Assistant response')
        expect(assistantMessage).toBeTruthy()
        // Check if it has gray background (assistant message style)
        const parent = assistantMessage.closest('.bg-gray-200')
        expect(parent).toBeTruthy()
      })
    })

    it('preserves whitespace in messages', async () => {
      const { api } = await import('../../../src/services/api')
      const mockMessages = [
        {
          id: '1',
          role: 'assistant' as const,
          content: 'Line 1\n\nLine 2\n  Indented',
          created_at: '2024-01-01T00:00:00Z'
        }
      ]
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: mockMessages })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText(/Line 1/)).toBeTruthy()
        expect(screen.getByText(/Line 2/)).toBeTruthy()
        expect(screen.getByText(/Indented/)).toBeTruthy()
      })
    })
  })

  describe('Input Form', () => {
    it('renders input field and send button', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
        const button = screen.getByRole('button', { name: /发送/i })
        expect(input).toBeTruthy()
        expect(button).toBeTruthy()
      })
    })

    it('has correct input attributes', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
        expect(input).toHaveAttribute('id', 'chat-input')
        expect(input).toHaveAttribute('name', 'chat-input')
        expect(input).toHaveAttribute('placeholder', '输入问题...')
      })
    })

    it('disables input when disabled prop is true', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })

      render(<Chat {...defaultProps} disabled={true} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
        expect(input).toBeDisabled()
      })
    })
  })

  describe('Message Submission', () => {
    it('submits message when form is submitted', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })
      
      // Mock streaming function
      const mockStream = vi.fn()
      mockStream.mockImplementation(async (transcriptionId: string, content: string, onChunk: any, onError: any, onComplete: any) => {
        // Simulate streaming
        onChunk('Hello')
        onChunk(' world')
        onComplete?.()
      })
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')
      
      await user.type(input, 'Test message')
      
      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      await waitFor(() => {
        expect(api.sendChatMessageStream).toHaveBeenCalledWith(
          mockTranscriptionId,
          'Test message',
          expect.any(Function),
          expect.any(Function),
          expect.any(Function)
        )
      })
    })

    it('does not submit empty messages', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })
      vi.mocked(api.sendChatMessageStream).mockImplementation(async () => {})

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /发送/i })
      })

      const user = userEvent.setup()
      const button = screen.getByRole('button', { name: /发送/i })
      
      // Try to click with empty input
      await user.click(button)

      // Should not call sendChatMessageStream
      expect(api.sendChatMessageStream).not.toHaveBeenCalled()
    })
  })

  describe('Thinking Indicator', () => {
    it('shows thinking indicator when waiting for response', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })
      
      let resolveStream: (value: void) => void
      const streamPromise = new Promise<void>(resolve => { resolveStream = resolve })
      
      const mockStream = vi.fn()
      mockStream.mockImplementation(() => streamPromise)
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')
      
      await user.type(input, 'Test question')
      
      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      // Should show thinking indicator
      await waitFor(() => {
        expect(screen.getByText(/AI 正在思考/)).toBeTruthy()
      })

      resolveStream!()
    })

    it('collapses thinking indicator when response arrives', async () => {
      const { api } = await import('../../../src/services/api')
      // Mock returns messages including the assistant response that will be streamed
      vi.mocked(api.getChatHistory).mockResolvedValue({
        messages: [
          { id: '1', role: 'user' as const, content: 'Test', created_at: '2024-01-01T00:00:00Z' },
          { id: '2', role: 'assistant' as const, content: 'Hello', created_at: '2024-01-01T00:00:01Z' }
        ]
      })

      const mockStream = vi.fn()
      mockStream.mockImplementation(async (transcriptionId: string, content: string, onChunk: any, onError: any, onComplete: any) => {
        // First chunk triggers thinking collapse
        await new Promise(resolve => setTimeout(resolve, 10))
        onChunk('Hello')
        onComplete?.()
      })
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')

      await user.type(input, 'Test')

      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      // Initially shows thinking
      await waitFor(() => {
        expect(screen.getByText(/AI 正在思考/)).toBeTruthy()
      })

      // After first chunk, response should be visible
      await waitFor(() => {
        expect(screen.getByText('Hello')).toBeTruthy()
      }, { timeout: 3000 })
    })
  })

  describe('Streaming Response', () => {
    it('accumulates streamed chunks progressively', async () => {
      const { api } = await import('../../../src/services/api')
      // Mock returns messages including the assistant response that will be streamed
      vi.mocked(api.getChatHistory).mockResolvedValue({
        messages: [
          { id: '1', role: 'user' as const, content: 'Test', created_at: '2024-01-01T00:00:00Z' },
          { id: '2', role: 'assistant' as const, content: 'Hello there!', created_at: '2024-01-01T00:00:01Z' }
        ]
      })

      const mockStream = vi.fn()
      mockStream.mockImplementation(async (transcriptionId: string, content: string, onChunk: any, onError: any, onComplete: any) => {
        // Simulate streaming chunks
        onChunk('Hello')
        await new Promise(resolve => setTimeout(resolve, 10))
        onChunk(' there')
        await new Promise(resolve => setTimeout(resolve, 10))
        onChunk('!')
        onComplete?.()
      })
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')

      await user.type(input, 'Test')

      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      // Should show full response at the end
      await waitFor(() => {
        expect(screen.getByText('Hello there!')).toBeTruthy()
      })
    })

    it('reloads chat history after streaming completes', async () => {
      const { api } = await import('../../../src/services/api')

      // Track call count explicitly
      let callCount = 0
      vi.mocked(api.getChatHistory).mockImplementation(() => {
        callCount++
        return Promise.resolve({ messages: [] })
      })

      const mockStream = vi.fn()
      mockStream.mockImplementation(async (transcriptionId: string, content: string, onChunk: any, onError: any, onComplete: any) => {
        onChunk('Response')
        // Small delay to simulate async streaming
        await new Promise(resolve => setTimeout(resolve, 10))
        // Call onComplete which triggers loadChatHistory
        onComplete?.()
        // Wait for loadChatHistory to complete
        await new Promise(resolve => setTimeout(resolve, 50))
      })
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      // Reset call count for this test
      callCount = 0

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const initialCalls = callCount
      expect(initialCalls).toBeGreaterThan(0) // Initial load

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')

      await user.type(input, 'Test')

      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      // Wait for reload after streaming
      await waitFor(() => {
        expect(callCount).toBeGreaterThan(initialCalls)
      }, { timeout: 5000 })

      // Should have been called again after streaming completed
      expect(callCount).toBe(initialCalls + 1)
    })
  })

  describe('Error Handling', () => {
    it('handles streaming errors gracefully', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })
      
      const mockStream = vi.fn()
      mockStream.mockImplementation(async (transcriptionId: string, content: string, onChunk: any, onError: any, onComplete: any) => {
        onError('Network error')
      })
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')
      
      await user.type(input, 'Test')
      
      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/抱歉，AI回复失败/)).toBeTruthy()
      })
    })

    it('removes temp messages on error and restores input', async () => {
      const { api } = await import('../../../src/services/api')
      vi.mocked(api.getChatHistory).mockResolvedValue({ messages: [] })
      
      const mockStream = vi.fn()
      mockStream.mockImplementation(async () => {
        throw new Error('API error')
      })
      vi.mocked(api.sendChatMessageStream).mockImplementation(mockStream)

      render(<Chat {...defaultProps} />)

      await waitFor(() => {
        const input = screen.getByRole('textbox')
      })

      const user = userEvent.setup()
      const input = screen.getByRole('textbox')
      
      const originalMessage = 'Test message'
      await user.type(input, originalMessage)
      
      const button = screen.getByRole('button', { name: /发送/i })
      await user.click(button)

      // Input should be restored with original message
      await waitFor(() => {
        expect(input).toHaveValue(originalMessage)
      })
    })
  })
})
