/**
 * Chat Component
 *
 * AI chat interface for asking questions about transcriptions.
 */

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { api } from '../services/api'

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

    // Optimistically add user message to the list immediately
    const tempUserMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, tempUserMessage])

    try {
      console.log('[Chat] Sending chat message to API...')
      const response = await api.sendChatMessage(transcriptionId, userMessage)
      console.log('[Chat] Chat response received:', response)

      // Keep the temp user message (same content as what was saved to DB)
      // and add the assistant's response
      setMessages(prev => [...prev, response])
    } catch (error) {
      console.error('[Chat] Failed to send message:', error)
      // Remove the temp user message on error
      setMessages(prev => prev.filter(m => m.id !== tempUserMessage.id))
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
                <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 dark:bg-gray-700 rounded-lg px-4 py-2">
              <Loader2 className="w-4 h-4 text-gray-500 dark:text-gray-400 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入问题..."
          disabled={disabled || isLoading}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading || disabled}
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
