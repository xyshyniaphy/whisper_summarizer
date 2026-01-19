/**
 * Chat Component
 *
 * AI chat interface for asking questions about transcriptions.
 */

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, ChevronDown, Brain } from 'lucide-react'
import { api } from '../services/api'
import { cn } from '../utils/cn'
import { MarkdownRenderer } from './MarkdownRenderer'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface ChatProps {
  transcriptionId: string
  disabled?: boolean
}

export function Chat({ transcriptionId, disabled = false }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [isThinking, setIsThinking] = useState(false)
  const [thinkingCollapsed, setThinkingCollapsed] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load chat history on mount
  useEffect(() => {
    loadChatHistory()
  }, [transcriptionId])

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadChatHistory = async () => {
    console.log('[Chat] Loading chat history for transcription:', transcriptionId)
    try {
      setIsInitialLoading(true)
      const response = await api.getChatHistory(transcriptionId)
      console.log('[Chat] Chat history response:', response)
      setMessages(response.messages || [])
    } catch (error) {
      console.error('[Chat] Failed to load chat history:', error)
    } finally {
      setIsInitialLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    console.log('[Chat] Submitting message, input:', input, 'isLoading:', isLoading, 'disabled:', disabled)

    if (!input.trim() || isLoading || disabled) {
      console.log('[Chat] Submit blocked - conditions not met')
      return
    }

    const userMessage = input.trim()
    console.log('[Chat] User message:', userMessage)
    setInput('')
    setIsLoading(true)
    setIsThinking(true)
    setThinkingCollapsed(false)

    // Optimistically add user message to the list immediately
    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, tempUserMessage])

    // Create a placeholder assistant message that will be updated with streamed content
    const tempAssistantId = `temp-assistant-${Date.now()}`
    setMessages(prev => [...prev, {
      id: tempAssistantId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    }])

    try {
      console.log('[Chat] Sending chat message to streaming API...')
      let fullContent = ''
      let firstChunkReceived = false

      await api.sendChatMessageStream(
        transcriptionId,
        userMessage,
        // onChunk - update the assistant message progressively
        (chunk: string) => {
          // Stop thinking indicator when first chunk arrives
          if (!firstChunkReceived) {
            firstChunkReceived = true
            setIsThinking(false)
            setThinkingCollapsed(true) // Auto-collapse thinking section
          }

          fullContent += chunk
          setMessages(prev => prev.map(msg =>
            msg.id === tempAssistantId
              ? { ...msg, content: fullContent }
              : msg
          ))
        },
        // onError
        (error: string) => {
          console.error('[Chat] Stream error:', error)
          setIsThinking(false)
          setMessages(prev => prev.map(msg =>
            msg.id === tempAssistantId
              ? { ...msg, content: '抱歉，AI回复失败，请稍后再试。' }
              : msg
          ))
        },
        // onComplete
        () => {
          console.log('[Chat] Stream complete, reloading history to get saved messages')
          setIsThinking(false)
          // Reload chat history to get the actual saved messages with real IDs
          loadChatHistory()
        }
      )

    } catch (error) {
      console.error('[Chat] Failed to send message:', error)
      setIsThinking(false)
      // Remove both temp messages on error
      setMessages(prev => prev.filter(m => m.id !== tempUserMessage.id && m.id !== tempAssistantId))
      // Re-add input on error
      setInput(userMessage)
    } finally {
      setIsLoading(false)
    }
  }

  if (isInitialLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 text-blue-500 dark:text-blue-400 animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[500px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            <p>开始向AI提问关于此转录的问题...</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                }`}
              >
                {message.role === 'assistant' ? (
                  <MarkdownRenderer content={message.content} />
                ) : (
                  <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
                )}
              </div>
            </div>
          ))
        )}

        {/* Collapsible Thinking Section */}
        {isThinking && (
          <div className="flex justify-start">
            <div className="max-w-[80%] w-full">
              <div className="border border-purple-200 dark:border-purple-800 rounded-lg overflow-hidden bg-purple-50 dark:bg-purple-900/20">
                {/* Thinking Header */}
                <button
                  onClick={() => setThinkingCollapsed(!thinkingCollapsed)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
                  aria-expanded={!thinkingCollapsed}
                  aria-label="AI思考状态"
                >
                  <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                  <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                    AI 正在思考...
                  </span>
                  <ChevronDown
                    className={cn(
                      "w-4 h-4 text-purple-600 dark:text-purple-400 ml-auto transition-transform flex-shrink-0",
                      !thinkingCollapsed && "rotate-180"
                    )}
                  />
                </button>

                {/* Thinking Content */}
                {!thinkingCollapsed && (
                  <div className="px-3 py-2 pt-0 border-t border-purple-200 dark:border-purple-800">
                    <div className="flex items-center gap-2 text-sm text-purple-600 dark:text-purple-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>正在分析转录内容并生成回复...</span>
                    </div>
                    {/* Animated dots */}
                    <div className="flex gap-1 mt-2 ml-6">
                      <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          id="chat-input"
          name="chat-input"
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题..."
          disabled={disabled || isLoading}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          data-testid="chat-send-button"
          disabled={!input.trim() || isLoading || disabled}
          aria-label={isLoading ? "发送中..." : "发送"}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </form>
    </div>
  )
}
